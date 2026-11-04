from uuid import uuid4
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from apps.common.validators import image_path, validate_image


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.slug = self.slug or slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="events")
    location = models.CharField(max_length=200)
    venue = models.CharField(max_length=200)
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField()
    registration_deadline = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    image = models.ImageField(upload_to=image_path, validators=[validate_image], blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_datetime", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="positive_capacity"),
            models.CheckConstraint(
                condition=Q(end_datetime__gt=F("start_datetime")), name="event_end_after_start"
            ),
            models.CheckConstraint(
                condition=Q(registration_deadline__lte=F("start_datetime")),
                name="deadline_before_start",
            ),
        ]

    def clean(self):
        errors = {}
        if self.end_datetime and self.start_datetime and self.end_datetime <= self.start_datetime:
            errors["end_datetime"] = "End must follow start."
        if (
            self.registration_deadline
            and self.start_datetime
            and self.registration_deadline > self.start_datetime
        ):
            errors["registration_deadline"] = "Deadline must be before start."
        if self.capacity is not None and self.capacity < 1:
            errors["capacity"] = "Capacity must be positive."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.slug = self.slug or f"{slugify(self.title)[:190]}-{uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
