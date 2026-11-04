from datetime import timedelta
import pytest
from django.utils import timezone
from apps.users.models import User
from apps.registrations.services import register

pytestmark = pytest.mark.django_db
API = "/api/v1"


def test_public_discovery_and_filters(api, event):
    response = api.get(f"{API}/events/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert api.get(f"{API}/events/?search=missing").data["count"] == 0
    assert api.get(f"{API}/events/?category=technology").data["count"] == 1
    assert api.get(f"{API}/events/?date_from=oops").status_code == 400
    event.status = "DRAFT"
    event.save()
    assert api.get(f"{API}/events/{event.pk}/").status_code == 404


@pytest.mark.parametrize("role", ["anonymous", "user", "other", "owner", "admin"])
@pytest.mark.parametrize("action", ["edit", "attendees", "publish", "export", "dashboard"])
def test_organizer_permissions(api, event, user, owner, role, action):
    if role == "user":
        person = user
    elif role == "other":
        person = User.objects.create_user("other@example.com", "pass", is_organizer=True)
    elif role == "owner":
        person = owner
    elif role == "admin":
        person = User.objects.create_superuser("admin@example.com", "pass")
    else:
        person = None
    if person:
        api.force_authenticate(person)
    suffix = {
        "attendees": "registrations/",
        "export": "registrations/export/",
        "publish": "publish/",
    }
    if action == "edit":
        response = api.patch(f"{API}/events/{event.pk}/", {"title": "Renamed"})
    elif action == "dashboard":
        response = api.get(f"{API}/events/dashboard/")
    elif action == "publish":
        event.status = "DRAFT"
        event.save()
        response = api.post(f"{API}/events/{event.pk}/publish/")
    else:
        response = api.get(f"{API}/events/{event.pk}/{suffix[action]}")
    if role == "anonymous":
        assert response.status_code == 401
    elif role == "user":
        assert response.status_code == 403
    elif role == "other" and action != "dashboard":
        assert response.status_code in [403, 404]
    else:
        assert response.status_code == 200, response.data


def test_registration_privacy(api, event, user, owner):
    r = register(user, event.pk)
    api.force_authenticate(owner)
    assert api.get(f"{API}/registrations/{r.pk}/").status_code == 404
    assert api.post(f"{API}/registrations/{r.pk}/cancel/").status_code == 404


def test_registration_journey(api, event):
    response = api.post(
        f"{API}/users/register/",
        {"email": "new@example.com", "password": "Strong!Password2026"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert not response.data.get("is_organizer", False)
    response = api.post(
        f"{API}/users/login/",
        {"email": "new@example.com", "password": "Strong!Password2026"},
        format="json",
    )
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])
    response = api.post(f"{API}/events/{event.pk}/register/")
    assert response.status_code == 201
    pk = response.data["id"]
    assert api.post(f"{API}/events/{event.pk}/register/").status_code == 409
    assert api.get(f"{API}/registrations/").data["count"] == 1
    assert api.post(f"{API}/registrations/{pk}/cancel/").data["status"] == "CANCELLED"
    assert api.post(f"{API}/users/logout/").status_code == 204
    assert api.get(f"{API}/users/profile/").status_code == 401


def test_capacity_cannot_shrink_below_attendees(api, event, user, owner):
    register(user, event.pk)
    api.force_authenticate(owner)
    assert api.patch(f"{API}/events/{event.pk}/", {"capacity": 0}).status_code == 400


def test_role_escalation_blocked(api, user):
    api.force_authenticate(user)
    assert (
        api.patch(f"{API}/users/profile/", {"is_organizer": True, "is_staff": True}).status_code
        == 200
    )
    user.refresh_from_db()
    assert not user.is_organizer and not user.is_staff


def test_token_expiry(api, user):
    from rest_framework.authtoken.models import Token

    token = Token.objects.create(user=user)
    Token.objects.filter(pk=token.pk).update(created=timezone.now() - timedelta(days=15))
    api.credentials(HTTP_AUTHORIZATION="Token " + token.key)
    assert api.get(f"{API}/users/profile/").status_code == 401


def test_lockout(api, user):
    for _ in range(5):
        assert (
            api.post(f"{API}/users/login/", {"email": user.email, "password": "wrong"}).status_code
            == 400
        )
    assert (
        api.post(
            f"{API}/users/login/", {"email": user.email, "password": "Strong!Password2026"}
        ).status_code
        == 429
    )


def test_envelope(api, event):
    import json

    body = json.loads(api.get(f"{API}/events/").content)
    assert body["data"]["count"] == 1
    body = json.loads(api.get(f"{API}/events/9999/").content)
    assert body["error"]["code"] == "NOT_FOUND"
