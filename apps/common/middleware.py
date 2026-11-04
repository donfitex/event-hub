from django.utils.cache import add_never_cache_headers


class Headers:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and (
            request.path in ["/signup/", "/login/", "/password-reset/"]
            or request.path.startswith("/reset/")
        ):
            import hashlib
            from django.core.cache import cache
            from django.http import HttpResponse
            from rest_framework.throttling import BaseThrottle

            key = (
                "web-rate:"
                + hashlib.sha256(
                    (request.path + BaseThrottle().get_ident(request)).encode()
                ).hexdigest()
            )
            limit = 5 if request.path == "/password-reset/" else 20
            cache.add(key, 0, 3600)
            try:
                attempts = cache.incr(key)
            except ValueError:
                cache.set(key, 1, 3600)
                attempts = 1
            if attempts > limit:
                response = HttpResponse("Too many requests. Please try again later.", status=429)
                response["Retry-After"] = "3600"
                return response
        if (
            getattr(request, "user", None)
            and request.user.is_authenticated
            and request.session.get("neon_expiry", float("inf")) <= __import__("time").time()
        ):
            from django.contrib.auth import logout

            logout(request)
        response = self.get_response(request)
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if not request.path.startswith(("/admin/", "/api/")):
            response["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
            )
        if (
            request.path.startswith("/api/")
            or getattr(request, "user", None)
            and request.user.is_authenticated
        ):
            add_never_cache_headers(response)
        return response
