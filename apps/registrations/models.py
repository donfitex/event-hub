from django.conf import settings
from django.db import models


class Registration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        WAITLISTED = "WAITLISTED", "Waitlisted"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registrations"
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.PROTECT, related_name="registrations"
    )
    status = models.CharField(max_length=12, choices=Status.choices, db_index=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registered_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=models.Q(status__in=["REGISTERED", "WAITLISTED"]),
                name="one_active_registration",
            )
        ]
        indexes = [models.Index(fields=["event", "status", "registered_at"])]


class Notification(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)


class Reminder(models.Model):
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
