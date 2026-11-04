from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.events.models import Event, Category


class Command(BaseCommand):
    help = "Create clearly marked sample discovery events once; no login credentials are created."

    def handle(self, **options):
        user, created = User.objects.get_or_create(
            email="demo-organizer@eventhub.invalid",
            defaults={"first_name": "EventHub Demo", "is_active": False, "is_organizer": True},
        )
        if created:
            user.set_unusable_password()
            user.save()
        for index, (title, category, city, venue) in enumerate(
            [
                ("Lagos: ideas that move us", "Technology", "Lagos", "Innovation House"),
                ("The creative gathering", "Community", "Abuja", "Community Studio"),
                ("Build something together", "Workshop", "Lagos", "Makers Hall"),
            ]
        ):
            cat, _ = Category.objects.get_or_create(name=category)
            Event.objects.get_or_create(
                slug=f"demo-{index}",
                defaults={
                    "title": title + " (Demo)",
                    "description": "A sample EventHub event for exploring the platform. This is a demonstration, not a real scheduled gathering.",
                    "organizer": user,
                    "category": cat,
                    "location": city,
                    "venue": venue,
                    "capacity": 100,
                    "status": "PUBLISHED",
                    "start_datetime": timezone.now() + timedelta(days=14 + index * 3),
                    "end_datetime": timezone.now() + timedelta(days=14 + index * 3, hours=4),
                    "registration_deadline": timezone.now() + timedelta(days=13 + index * 3),
                },
            )
