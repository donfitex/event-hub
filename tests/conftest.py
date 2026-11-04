from datetime import timedelta
import pytest
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APIClient
from apps.users.models import User
from apps.events.models import Event, Category


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user("attendee@example.com", "Strong!Password2026")


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        "organizer@example.com", "Strong!Password2026", is_organizer=True
    )


@pytest.fixture
def event(owner):
    return Event.objects.create(
        title="Community conference",
        description="Meet and learn together.",
        organizer=owner,
        category=Category.objects.create(name="Technology"),
        location="Lagos",
        venue="Community Hall",
        start_datetime=timezone.now() + timedelta(days=3),
        end_datetime=timezone.now() + timedelta(days=3, hours=4),
        registration_deadline=timezone.now() + timedelta(days=2),
        capacity=1,
        status="PUBLISHED",
    )


@pytest.fixture
def api():
    return APIClient()
