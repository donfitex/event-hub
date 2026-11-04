import pytest
from django.core.management import call_command
from apps.registrations.models import Notification
from apps.registrations.services import register

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path", ["/", "/events/", "/login/", "/signup/", "/password-reset/", "/health/"]
)
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


def test_website_journey(client, event):
    response = client.post(
        "/signup/",
        {
            "email": "web@example.com",
            "first_name": "Web",
            "last_name": "Guest",
            "password1": "Strong!Password2026",
            "password2": "Strong!Password2026",
        },
    )
    assert response.status_code == 302
    assert client.get(f"/events/{event.pk}/").status_code == 200
    assert client.post(f"/events/{event.pk}/register/").status_code == 302
    response = client.get("/dashboard/")
    assert b"Community conference" in response.content
    from apps.registrations.models import Registration

    r = Registration.objects.get(user__email="web@example.com")
    assert client.post(f"/registrations/{r.pk}/cancel/").status_code == 302
    r.refresh_from_db()
    assert r.status == "CANCELLED"




def test_organizer_pages(client, event, owner):
    client.force_login(owner)
    for path in [
        "/organizer/",
        "/organizer/new/",
        f"/organizer/{event.pk}/edit/",
        f"/organizer/{event.pk}/attendees/",
    ]:
        assert client.get(path).status_code == 200




def test_outbox_delivery(event, user):
    from django.core import mail

    register(user, event.pk)
    call_command("send_notifications")
    assert len(mail.outbox) == 1
    assert Notification.objects.filter(sent_at__isnull=True).count() == 0
    call_command("send_notifications")
    assert len(mail.outbox) == 1
