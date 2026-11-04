from datetime import timedelta

import pytest
from django.utils import timezone

from apps.registrations.services import register
from apps.users.models import User

pytestmark = pytest.mark.django_db
API = "/api/v1"


def test_category_crud_and_permissions(api, event, owner, user):
    assert api.get(f"{API}/categories/").json()["data"]["count"] == 1
    assert api.get(f"{API}/categories/{event.category_id}/").json()["data"]["name"] == "Technology"
    api.force_authenticate(user)
    assert api.post(f"{API}/categories/", {"name": "Art"}).status_code == 403
    api.force_authenticate(owner)
    created = api.post(f"{API}/categories/", {"name": "Art"})
    assert created.status_code == 201
    path = f"{API}/categories/{created.json()['data']['id']}/"
    assert api.patch(path, {"name": "Arts"}).status_code == 403
    assert api.delete(path).status_code == 403
    api.force_authenticate(User.objects.create_superuser("admin@example.com", "pass"))
    assert api.put(path, {"name": "Music"}).json()["data"]["name"] == "Music"
    assert api.patch(path, {"name": "Design"}).json()["data"]["name"] == "Design"
    assert api.delete(f"{API}/categories/{event.category_id}/").status_code == 409
    assert api.delete(path).status_code == 204


def test_staff_user_management_and_profile(api, user):
    management = f"{API}/users/manage/"
    profile = f"{API}/users/profile/"
    assert api.get(management).status_code == 401
    api.force_authenticate(user)
    assert api.get(management).status_code == 403
    assert api.get(profile).json()["data"]["email"] == user.email
    assert api.put(profile, {"first_name": "Jo", "last_name": "Doe"}).status_code == 200
    assert api.patch(profile, {"first_name": "Joe"}).json()["data"]["last_name"] == "Doe"
    admin = User.objects.create_superuser("admin@example.com", "pass")
    api.force_authenticate(admin)
    assert api.get(management).json()["data"]["count"] == 2
    detail = f"{management}{user.pk}/"
    assert api.get(detail).json()["data"]["email"] == user.email
    assert (
        api.put(detail, {"first_name": "Jo", "last_name": "Doe", "is_organizer": True}).status_code
        == 200
    )
    assert api.patch(detail, {"is_active": False, "is_staff": True}).status_code == 200
    user.refresh_from_db()
    assert user.is_organizer and not user.is_active and not user.is_staff


def test_organizer_event_lifecycle(api, event, owner, user):
    path = f"{API}/events/{event.pk}/"
    assert api.get(path).json()["data"]["id"] == event.pk
    assert api.post(path + "register/").status_code == 401
    api.force_authenticate(owner)
    assert api.get(f"{API}/events/mine/").json()["data"]["count"] == 1
    event.organizer = user
    event.save(update_fields=["organizer"])
    assert api.get(f"{API}/events/mine/").json()["data"]["count"] == 0
    assert api.delete(path).status_code == 403
    event.organizer = owner
    event.save(update_fields=["organizer"])
    payload = api.get(path).json()["data"]
    payload.pop("image", None)
    payload["title"] = "Updated conference"
    assert api.put(path, payload, format="json").json()["data"]["title"] == "Updated conference"
    assert api.delete(path).status_code == 409
    assert api.post(path + "complete/").status_code == 409
    now = timezone.now()
    event.registration_deadline = now - timedelta(days=3)
    event.start_datetime = now - timedelta(days=2)
    event.end_datetime = now - timedelta(days=1)
    event.save(update_fields=["registration_deadline", "start_datetime", "end_datetime"])
    assert api.post(path + "complete/").json()["data"]["status"] == "COMPLETED"
    assert api.patch(path, {"title": "Too late"}).status_code == 409
    event.status = "DRAFT"
    event.save(update_fields=["status"])
    assert api.delete(path).status_code == 204
    assert api.get(path).status_code == 404


def test_attendee_search_and_csv(api, event, user, owner):
    registration = register(user, event.pk)
    api.force_authenticate(user)
    assert (
        api.get(f"{API}/registrations/{registration.pk}/").json()["data"]["user_email"]
        == user.email
    )
    api.force_authenticate(owner)
    url = f"{API}/events/{event.pk}/registrations/"
    assert api.get(url, {"search": "missing"}).json()["data"]["count"] == 0
    assert api.get(url, {"search": user.email}).json()["data"]["count"] == 1
    csv = api.get(url + "export/")
    assert csv["Content-Type"] == "text/csv"
    assert "attachment" in csv["Content-Disposition"]
    assert user.email.encode() in csv.content


def test_published_schema_matches_key_wire_contracts(client):
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert len(paths) == 21
    assert sum(len(operations) for operations in paths.values()) == 33
    register = paths["/api/v1/events/{id}/register/"]["post"]
    assert "requestBody" not in register
    payload = register["responses"]["201"]["content"]["application/json"]["schema"]
    assert payload["properties"]["data"]["$ref"].endswith("/Registration")
    assert "409" in register["responses"]
    csv = paths["/api/v1/events/{id}/registrations/export/"]["get"]
    assert "text/csv" in csv["responses"]["200"]["content"]
    logout = paths["/api/v1/users/logout/"]["post"]
    assert "requestBody" not in logout
    assert "content" not in logout["responses"]["204"]
    assert client.get("/api/docs/").status_code == 200
    assert client.get("/api/v1/").status_code == 200


def test_health_database_failure(client, monkeypatch):
    from django.db import OperationalError
    from apps.common import web

    def unavailable():
        raise OperationalError("Sensitive connection detail")

    monkeypatch.setattr(web.connection, "cursor", unavailable)
    response = client.get("/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
