from functools import lru_cache
from urllib.parse import urlsplit
import jwt
from django.conf import settings
from django.db import transaction, IntegrityError
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .models import User


@lru_cache(maxsize=4)
def jwks_client(url):
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=300, timeout=10)


def verified_claims(token):
    if not settings.NEON_AUTH_BASE_URL or not settings.NEON_AUTH_JWKS_URL:
        raise AuthenticationFailed("Managed identity is not configured.")
    try:
        key = jwks_client(settings.NEON_AUTH_JWKS_URL).get_signing_key_from_jwt(token)
        origin = urlsplit(settings.NEON_AUTH_BASE_URL)
        issuer = f"{origin.scheme}://{origin.netloc}"
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["EdDSA"],
            issuer=issuer,
            audience=issuer,
            leeway=30,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        if claims.get("banned") or not claims.get("email") or not isinstance(claims["sub"], str):
            raise ValueError("Invalid identity")
        return claims
    except Exception as exc:
        raise AuthenticationFailed("Invalid or expired identity token.") from exc


def identity_user(claims):
    # Never infer privileged application roles from identity-provider claims or auto-link by email.
    subject = claims["sub"]
    email = claims["email"].strip().lower()
    user = User.objects.filter(neon_subject=subject).first()
    if user:
        if not user.is_active:
            raise AuthenticationFailed("Account disabled.")
        return user
    try:
        with transaction.atomic():
            user = User(
                email=email, neon_subject=subject, first_name=str(claims.get("name", ""))[:150]
            )
            user.set_unusable_password()
            user.save()
    except IntegrityError:
        user = User.objects.filter(neon_subject=subject).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed("Identity cannot be linked. Contact an administrator.")
    return user


class NeonAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Invalid bearer header.")
        claims = verified_claims(header[1].decode())
        return identity_user(claims), claims

    def authenticate_header(self, request):
        return "Bearer"
