from io import BytesIO
from datetime import timedelta
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.management import call_command
from apps.common.validators import validate_image
from apps.registrations.services import register
from apps.registrations.models import Notification

pytestmark = pytest.mark.django_db


def test_image_validation():
    data = BytesIO()
    Image.new("RGB", (10, 10)).save(data, format="PNG")
    validate_image(SimpleUploadedFile("photo.png", data.getvalue()))
    for name, body in [
        ("attack.svg", b"<svg/>"),
        ("fake.png", b"not an image"),
        ("big.jpg", b"x" * (5 * 1024 * 1024 + 1)),
    ]:
        with pytest.raises(ValidationError):
            validate_image(SimpleUploadedFile(name, body))


def test_reminder_is_queued_only_once(event, user):
    event.start_datetime = timezone.now() + timedelta(hours=20)
    event.end_datetime = event.start_datetime + timedelta(hours=2)
    event.registration_deadline = timezone.now() + timedelta(hours=10)
    event.save()
    register(user, event.pk)
    call_command("send_reminders")
    call_command("send_reminders")
    assert Notification.objects.filter(subject="Your event starts soon").count() == 1


def test_web_reset_limit(client):
    for _ in range(5):
        assert client.post("/password-reset/", {"email": "nobody@example.com"}).status_code == 302
    assert client.post("/password-reset/", {"email": "nobody@example.com"}).status_code == 429


def test_organizer_create_publish_journey(api, event, owner):
    api.force_authenticate(owner)
    body = {
        "title": "New workshop",
        "description": "Build together",
        "category": event.category_id,
        "location": "Abuja",
        "venue": "Workshop Hall",
        "start_datetime": event.start_datetime.isoformat(),
        "end_datetime": event.end_datetime.isoformat(),
        "registration_deadline": event.registration_deadline.isoformat(),
        "capacity": 10,
    }
    response = api.post("/api/v1/events/", body, format="json")
    assert response.status_code == 201, response.data
    pk = response.data["id"]
    assert response.data["status"] == "DRAFT"
    assert api.post(f"/api/v1/events/{pk}/publish/").status_code == 200
    assert api.get(f"/api/v1/events/{pk}/registrations/").status_code == 200
    assert api.post(f"/api/v1/events/{pk}/cancel/").status_code == 200
