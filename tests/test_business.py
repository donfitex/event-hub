from datetime import timedelta
import pytest
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.registrations.models import Registration, Notification
from apps.registrations.services import register, cancel, transition, Conflict

pytestmark = pytest.mark.django_db




def test_duplicate_and_database_constraint(event, user):
    register(user, event.pk)
    with pytest.raises(Conflict):
        register(user, event.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        Registration.objects.create(user=user, event=event, status="WAITLISTED")










def test_model_dates(event):
    event.end_datetime = event.start_datetime
    with pytest.raises(ValidationError):
        event.clean()


def test_email_uniqueness(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(user.email.upper(), "pass")
