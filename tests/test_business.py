from datetime import timedelta
import pytest
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.registrations.models import Registration, Notification
from apps.registrations.services import register, cancel, transition, Conflict

pytestmark = pytest.mark.django_db


def test_fifo_promotion_and_outbox(event, user):
    second = User.objects.create_user("second@example.com", "pass")
    third = User.objects.create_user("third@example.com", "pass")
    first = register(user, event.pk)
    waiting = register(second, event.pk)
    last = register(third, event.pk)
    assert first.status == "REGISTERED"
    assert waiting.status == last.status == "WAITLISTED"
    cancel(first.pk)
    waiting.refresh_from_db()
    last.refresh_from_db()
    assert waiting.status == "REGISTERED" and last.status == "WAITLISTED"
    assert Notification.objects.count() == 5
    with pytest.raises(Conflict):
        cancel(first.pk)


def test_duplicate_and_database_constraint(event, user):
    register(user, event.pk)
    with pytest.raises(Conflict):
        register(user, event.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        Registration.objects.create(user=user, event=event, status="WAITLISTED")


def test_cancelled_user_can_register_again(event, user):
    original = register(user, event.pk)
    cancel(original.pk)
    assert register(user, event.pk).status == "REGISTERED"


@pytest.mark.parametrize("state", ["DRAFT", "CANCELLED", "COMPLETED"])
def test_closed_states(event, user, state):
    event.status = state
    event.save()
    with pytest.raises(Conflict):
        register(user, event.pk)


def test_expired_deadline(event, user):
    event.registration_deadline = timezone.now() - timedelta(seconds=1)
    event.save()
    with pytest.raises(Conflict):
        register(user, event.pk)


def test_event_cancel_cancels_everyone(event, user):
    register(user, event.pk)
    transition(event.pk, "CANCELLED")
    assert not event.registrations.exclude(status="CANCELLED").exists()
    assert Notification.objects.filter(subject="Event cancelled").count() == 1
    with pytest.raises(Conflict):
        transition(event.pk, "PUBLISHED")


def test_model_dates(event):
    event.end_datetime = event.start_datetime
    with pytest.raises(ValidationError):
        event.clean()


def test_email_uniqueness(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(user.email.upper(), "pass")
