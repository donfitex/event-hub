from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException
from apps.events.models import Event
from .models import Registration


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"




def lock_event(pk):
    return Event.objects.select_for_update().get(pk=pk)


@transaction.atomic
def register(user, event_id):
    event = lock_event(event_id)
    if (
        event.status != Event.Status.PUBLISHED
        or event.registration_deadline <= timezone.now()
        or event.start_datetime <= timezone.now()
    ):
        raise Conflict("Registration is closed.", code="registration_closed")
    if Registration.objects.filter(user=user, event=event).exclude(status="CANCELLED").exists():
        raise Conflict("You already registered for this event.", code="duplicate_registration")
    count = event.registrations.filter(status="REGISTERED").count()
    if count >= event.capacity:
        raise Conflict("Event is at capacity.")
    registration = Registration.objects.create(user=user, event=event, status="REGISTERED")
    return registration


@transaction.atomic
def cancel(registration_id):
    event_id = Registration.objects.values_list("event_id", flat=True).get(pk=registration_id)
    event = lock_event(event_id)
    registration = (
        Registration.objects.select_for_update()
        .select_related("user", "event")
        .get(pk=registration_id)
    )
    if registration.status == "CANCELLED":
        raise Conflict("Registration already cancelled.")
    if event.start_datetime <= timezone.now():
        raise Conflict("Cancellation is closed after the event starts.")
    registration.status = "CANCELLED"
    registration.cancelled_at = timezone.now()
    registration.save()
    return registration


@transaction.atomic
def transition(event_id, status):
    event = lock_event(event_id)
    allowed = {"DRAFT": {"PUBLISHED", "CANCELLED"}, "PUBLISHED": {"CANCELLED", "COMPLETED"}}
    if status not in allowed.get(event.status, set()):
        raise Conflict("Invalid event status transition.")
    if status == "PUBLISHED" and event.registration_deadline <= timezone.now():
        raise Conflict("Cannot publish after the registration deadline.")
    if status == "COMPLETED" and event.end_datetime > timezone.now():
        raise Conflict("Cannot complete an event before it ends.")
    event.status = status
    event.save()
    if status == "CANCELLED":
        for registration in event.registrations.exclude(status="CANCELLED").select_related(
            "user", "event"
        ):
            registration.status = "CANCELLED"
            registration.cancelled_at = timezone.now()
            registration.save()
    return event
