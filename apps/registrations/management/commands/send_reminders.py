from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.registrations.models import Registration, Reminder
from apps.registrations.services import notify


class Command(BaseCommand):
    help = "Queue reminders once for confirmed registrations in the next 24 hours."

    def handle(self, **options):
        qs = Registration.objects.filter(
            status="REGISTERED",
            event__status="PUBLISHED",
            event__start_datetime__gt=timezone.now(),
            event__start_datetime__lte=timezone.now() + timedelta(hours=24),
        ).select_related("event", "user")
        for r in qs:
            with transaction.atomic():
                _, created = Reminder.objects.get_or_create(registration=r)
                if created:
                    notify(r, "Your event starts soon")
