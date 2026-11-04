from types import SimpleNamespace
import time
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from apps.users.models import User
from apps.users.neon import identity_user
from rest_framework.exceptions import AuthenticationFailed

pytestmark = pytest.mark.django_db


@pytest.fixture
def identity(settings, monkeypatch):
    settings.NEON_AUTH_BASE_URL = "https://identity.example.com/eventhub/auth"
    settings.NEON_AUTH_JWKS_URL = "https://identity.example.com/eventhub/auth/.well-known/jwks.json"
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(
        "apps.users.neon.jwks_client",
        lambda url: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
        ),
    )

    def token(**overrides):
        return jwt.encode(
            {
                "sub": "neon-user-1",
                "email": "neon@example.com",
                "name": "Neon Guest",
                "iss": "https://identity.example.com",
                "aud": "https://identity.example.com",
                "iat": int(time.time()),
                "exp": int(time.time()) + 900,
                **overrides,
            },
            key,
            algorithm="EdDSA",
        )

    return token


def test_signed_identity_exchange(client, identity):
    response = client.post(
        "/identity/exchange/",
        {"token": identity(), "next": "https://attacker.example/"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["next"] == "/dashboard/"
    assert client.get("/dashboard/").status_code == 200
    user = User.objects.get(neon_subject="neon-user-1")
    assert not user.has_usable_password() and not user.is_staff and not user.is_organizer


def test_bearer_identity(api, identity):
    api.credentials(HTTP_AUTHORIZATION="Bearer " + identity(role="admin", is_staff=True))
    assert api.get("/api/v1/users/profile/").status_code == 200
    assert api.get("/api/v1/users/manage/").status_code == 403


@pytest.mark.parametrize(
    "claims", [{"exp": 1}, {"iss": "https://attacker.example"}, {"banned": True}]
)
def test_bad_claims_rejected(api, identity, claims):
    api.credentials(HTTP_AUTHORIZATION="Bearer " + identity(**claims))
    assert api.get("/api/v1/users/profile/").status_code == 401


def test_no_automatic_email_link(user):
    with pytest.raises(AuthenticationFailed):
        identity_user({"sub": "attacker", "email": user.email})


def test_managed_mode_disables_local_signup(api, identity):
    assert (
        api.post(
            "/api/v1/users/register/", {"email": "x@example.com", "password": "Strong!Password2026"}
        ).status_code
        == 400
    )
    assert api.post("/api/v1/users/login/", {}).status_code == 400


def test_proxy_is_not_an_open_proxy(client, identity):
    assert client.get("/identity/neon/admin/list-users").status_code == 404


def test_proxy_preserves_cookie_expiry(client, identity, monkeypatch):
    import httpx

    response = httpx.Response(
        200,
        json={"ok": True},
        headers={
            "set-cookie": "neon-auth.session_token=sample; Max-Age=3600; Path=/; HttpOnly; Secure; SameSite=None; Partitioned"
        },
    )
    monkeypatch.setattr("apps.users.identity.httpx.request", lambda *args, **kwargs: response)
    result = client.post("/identity/neon/sign-in/email", {}, content_type="application/json")
    assert result.status_code == 200
    assert result.cookies["neon-auth.session_token"]["max-age"] == 3600
    assert result.cookies["neon-auth.session_token"]["httponly"]


def test_django_admin_can_sign_in_to_organizer_site(client, identity):
    admin = User.objects.create_superuser("staff@example.com", "Strong!Password2026")
    page = client.get("/login/", follow=True)
    assert b"/admin/login/" not in page.content

    response = client.post(
        "/admin/login/?next=/organizer/",
        {"username": admin.email, "password": "Strong!Password2026", "next": "/organizer/"},
        follow=True,
    )
    assert response.redirect_chain[-1][0] == "/organizer/"
    assert response.status_code == 200
    assert client.get("/login/?next=/organizer/")["Location"] == "/organizer/"
