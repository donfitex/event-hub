import csv
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, Count, ProtectedError
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.registrations.models import Registration
from apps.registrations.services import register, cancel, transition, Conflict
from .models import Event, Category


class Organizer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated and (request.user.is_organizer or request.user.is_staff)
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
        read_only_fields = ["slug"]


class Categories(viewsets.ModelViewSet):
    queryset = Category.objects.order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        cls = (
            permissions.AllowAny
            if self.action in ["list", "retrieve"]
            else permissions.IsAdminUser
            if self.action in ["destroy", "update", "partial_update"]
            else Organizer
        )
        return [cls()]

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise Conflict("This category is used by an event.") from exc


class EventSerializer(serializers.ModelSerializer):
    registration_count = serializers.IntegerField(read_only=True)
    organizer_name = serializers.CharField(source="organizer.get_full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "organizer",
            "organizer_name",
            "category",
            "category_name",
            "location",
            "venue",
            "start_datetime",
            "end_datetime",
            "registration_deadline",
            "capacity",
            "status",
            "image",
            "registration_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "organizer", "status", "created_at", "updated_at"]

    def validate(self, data):
        from django.conf import settings

        if not settings.EVENT_IMAGE_UPLOADS_ENABLED and data.get("image"):
            raise ValidationError({"image": "Uploads are disabled on the free preview host."})
        instance = self.instance or Event()
        candidate = Event()
        for field in Event._meta.concrete_fields:
            if not field.primary_key:
                setattr(candidate, field.attname, getattr(instance, field.attname))
        for key, value in data.items():
            setattr(candidate, key, value)
        candidate.clean()
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Registration
        fields = [
            "id",
            "user",
            "user_email",
            "event",
            "event_title",
            "status",
            "registered_at",
            "cancelled_at",
        ]
        read_only_fields = fields


EVENT_FILTERS = [
    OpenApiParameter("category", str, description="Category slug."),
    OpenApiParameter("location", str, description="Case-insensitive substring."),
    OpenApiParameter("status", str, enum=list(Event.Status.values)),
    OpenApiParameter("date_from", str, description="Inclusive start date (YYYY-MM-DD)."),
    OpenApiParameter("date_to", str, description="Inclusive end date (YYYY-MM-DD)."),
]


@extend_schema_view(list=extend_schema(parameters=EVENT_FILTERS))
class Events(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "location", "venue"]
    ordering_fields = ["start_datetime", "created_at", "title"]

    def get_queryset(self):
        qs = Event.objects.select_related("organizer", "category").annotate(
            registration_count=Count("registrations", filter=Q(registrations__status="REGISTERED"))
        )
        user = self.request.user
        if not user.is_staff:
            visible = Q(status__in=["PUBLISHED", "CANCELLED", "COMPLETED"])
            if user.is_authenticated:
                visible |= Q(organizer=user)
            qs = qs.filter(visible)
        for name, lookup in [
            ("category", "category__slug"),
            ("location", "location__icontains"),
            ("status", "status"),
            ("date_from", "start_datetime__date__gte"),
            ("date_to", "start_datetime__date__lte"),
        ]:
            if self.request.query_params.get(name):
                value = self.request.query_params[name]
                if name.startswith("date_"):
                    from datetime import date

                    try:
                        date.fromisoformat(value)
                    except ValueError:
                        raise ValidationError({name: "Use YYYY-MM-DD."})
                qs = qs.filter(**{lookup: value})
        return qs.order_by("start_datetime", "pk")

    def get_permissions(self):
        cls = (
            permissions.AllowAny
            if self.action in ["list", "retrieve"]
            else permissions.IsAuthenticated
            if self.action == "register"
            else Organizer
        )
        return [cls()]

    def owned(self):
        event = self.get_object()
        if event.organizer_id != self.request.user.pk and not self.request.user.is_staff:
            raise PermissionDenied("Only the event owner can manage this event.")
        return event

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        event = self.owned()
        event = Event.objects.select_for_update().get(pk=event.pk)
        if event.status in ["CANCELLED", "COMPLETED"]:
            raise Conflict("This event can no longer be edited.")
        serializer = self.get_serializer(
            event, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        capacity = serializer.validated_data.get("capacity", event.capacity)
        if capacity < event.registrations.filter(status="REGISTERED").count():
            raise Conflict("Capacity cannot be below confirmed registrations.")
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def perform_destroy(self, instance):
        event = self.owned()
        event = Event.objects.select_for_update().get(pk=event.pk)
        if event.status != "DRAFT" or event.registrations.exists():
            raise Conflict("Only empty drafts can be deleted.")
        event.delete()

    @extend_schema(
        request=None,
        responses={201: RegistrationSerializer},
        description="Reserve a seat or join the FIFO waitlist.",
    )
    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        self.get_object()
        return Response(RegistrationSerializer(register(request.user, pk)).data, status=201)

    @extend_schema(request=None, responses={200: EventSerializer})
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        self.owned()
        transition(pk, "PUBLISHED")
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=None, responses={200: EventSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.owned()
        transition(pk, "CANCELLED")
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(request=None, responses={200: EventSerializer})
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        self.owned()
        transition(pk, "COMPLETED")
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(parameters=EVENT_FILTERS, responses=EventSerializer(many=True))
    @action(detail=False)
    def mine(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(organizer=request.user))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(
        responses=inline_serializer(
            name="OrganizerDashboard",
            fields={
                key: serializers.IntegerField()
                for key in ("events", "published", "completed", "registrations")
            },
        )
    )
    @action(detail=False)
    def dashboard(self, request):
        qs = self.get_queryset().filter(organizer=request.user)
        return Response(
            {
                "events": qs.count(),
                "published": qs.filter(status="PUBLISHED").count(),
                "completed": qs.filter(status="COMPLETED").count(),
                "registrations": Registration.objects.filter(
                    event__organizer=request.user, status="REGISTERED"
                ).count(),
            }
        )

    @extend_schema(
        parameters=[OpenApiParameter("search", str, description="Attendee email substring.")],
        responses=RegistrationSerializer(many=True),
    )
    @action(detail=True, url_path="registrations", filter_backends=[])
    def attendees(self, request, pk=None):
        event = self.owned()
        qs = event.registrations.select_related("event", "user")
        if request.query_params.get("search"):
            qs = qs.filter(user__email__icontains=request.query_params["search"])
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(RegistrationSerializer(page, many=True).data)

    @extend_schema(responses={(200, "text/csv"): str})
    @action(detail=True, url_path="registrations/export")
    def export(self, request, pk=None):
        event = self.owned()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendees.csv"'
        writer = csv.writer(response)
        writer.writerow(["Email", "Status", "Registered at"])
        for r in event.registrations.select_related("user").iterator():
            email = r.user.email
            writer.writerow(
                [
                    "'" + email if email.startswith(("=", "+", "-", "@", "\t", "\r")) else email,
                    r.status,
                    r.registered_at.isoformat(),
                ]
            )
        return response


class Registrations(viewsets.ReadOnlyModelViewSet):
    queryset = Registration.objects.none()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Registration.objects.none()
        qs = Registration.objects.select_related("event", "user")
        return qs if self.request.user.is_staff else qs.filter(user=self.request.user)

    @extend_schema(request=None, responses={200: RegistrationSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(cancel(pk)).data)
