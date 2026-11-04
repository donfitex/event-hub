import logging
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from apps.registrations.models import Notification


class Command(BaseCommand):
    help = "Deliver pending outbox messages; run every minute. Delivery is at least once."

    def handle(self, **options):
        for pk in Notification.objects.filter(sent_at=None).values_list("pk", flat=True)[:500]:
            with transaction.atomic():
                item = Notification.objects.select_for_update().get(pk=pk)
                if item.sent_at:
                    continue
                item.attempts += 1
                try:
                    send_mail(item.subject, item.body, None, [item.recipient], fail_silently=False)
                    item.sent_at = timezone.now()
                except Exception:
                    logging.getLogger(__name__).exception("Notification delivery failed id=%s", pk)
                item.save()
