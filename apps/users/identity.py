import json
import httpx
from django.conf import settings
from django.contrib.auth import login, logout
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_http_methods
from rest_framework.exceptions import AuthenticationFailed
from .neon import verified_claims, identity_user


def page(request):
    if not settings.NEON_AUTH_BASE_URL:
        return redirect("login")
    return render(
        request,
        "identity.html",
        {"mode": request.GET.get("mode", "login"), "next": request.GET.get("next", "/dashboard/")},
    )


@require_POST
@csrf_protect
def exchange(request):
    try:
        body = json.loads(request.body)
        claims = verified_claims(body.get("token", ""))
        user = identity_user(claims)
    except (ValueError, TypeError, AttributeError, AuthenticationFailed):
        return JsonResponse({"error": "Unable to verify your identity."}, status=401)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["neon_expiry"] = claims["exp"]
    request.session.set_expiry(max(1, int(claims["exp"] - __import__("time").time())))
    target = body.get("next", "/dashboard/")
    if not isinstance(target, str) or not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/dashboard/"
    return JsonResponse({"next": target})


@require_http_methods(["GET", "POST"])
@csrf_protect
def proxy(request, endpoint):
    # Fixed upstream and explicit public auth route allowlist; no administrative proxying.
    allowed = {
        "sign-in/email",
        "sign-up/email",
        "sign-out",
        "get-session",
        "token",
        "request-password-reset",
        "reset-password",
        "email-otp/send-verification-otp",
        "email-otp/verify-email",
        "email-otp/reset-password",
        "email-otp/request-password-reset",
    }
    if endpoint not in allowed or not settings.NEON_AUTH_BASE_URL:
        return HttpResponse(status=404)
    if request.method == "POST" and endpoint in {
        "sign-in/email",
        "sign-up/email",
        "request-password-reset",
        "reset-password",
    }:
        from django.core.cache import cache
        import hashlib

        key = (
            "neon-proxy:"
            + hashlib.sha256((endpoint + request.META.get("REMOTE_ADDR", "")).encode()).hexdigest()
        )
        cache.add(key, 0, 3600)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, 3600)
            count = 1
        if count > 30:
            return JsonResponse({"message": "Too many attempts. Try again later."}, status=429)
    headers = {
        "Content-Type": "application/json",
        "Origin": request.build_absolute_uri("/").rstrip("/"),
    }
    if request.headers.get("Cookie"):
        # Never send the Django session or CSRF cookie upstream.
        cookies = [
            f"{key}={value}"
            for key, value in request.COOKIES.items()
            if "auth" in key.lower()
            and key not in {settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME}
        ]
        headers["Cookie"] = "; ".join(cookies)
    try:
        response = httpx.request(
            request.method,
            settings.NEON_AUTH_BASE_URL + "/" + endpoint,
            headers=headers,
            content=request.body,
            params=request.GET,
            timeout=15,
            follow_redirects=False,
        )
    except httpx.HTTPError:
        return JsonResponse({"message": "Identity service temporarily unavailable."}, status=503)
    result = HttpResponse(
        response.content, status=response.status_code, content_type="application/json"
    )
    from http.cookies import SimpleCookie

    for raw in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(
            ";".join(part for part in raw.split(";") if part.strip().lower() != "partitioned")
        )
        for name, morsel in parsed.items():
            result.set_cookie(
                name,
                morsel.value,
                max_age=int(morsel["max-age"]) if morsel["max-age"] else None,
                expires=(morsel["expires"] or None) if not morsel["max-age"] else None,
                path="/",
                secure=not settings.DEBUG,
                httponly=bool(morsel["httponly"]),
                samesite="Lax",
            )
    result["Cache-Control"] = "no-store"
    return result


@require_POST
def local_logout(request):
    logout(request)
    if settings.NEON_AUTH_BASE_URL:
        return redirect("/identity/?mode=logout")
    return redirect("/")


def reset_page(request):
    if settings.NEON_AUTH_BASE_URL:
        return redirect("/identity/?mode=reset")
    from django.contrib.auth.views import PasswordResetView

    return PasswordResetView.as_view(
        template_name="form.html", extra_context={"title": "Reset your password"}
    )(request)
