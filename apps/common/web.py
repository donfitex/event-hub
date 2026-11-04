from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from rest_framework.exceptions import APIException
from apps.users.models import User
from apps.users.security import login_attempt
from apps.events.models import Event, Category
from apps.registrations.models import Registration
from apps.registrations.services import register, cancel, transition, Conflict


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]


class SecureLoginForm(AuthenticationForm):
    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email and password:
            self.user_cache, error = login_attempt(self.request, email, password)
            if error:
                raise forms.ValidationError(error)
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class Signin(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if settings.NEON_AUTH_BASE_URL:
            from urllib.parse import urlencode

            return redirect(
                "/identity/?"
                + urlencode({"mode": "login", "next": request.GET.get("next", "/dashboard/")})
            )
        return super().dispatch(request, *args, **kwargs)

    template_name = "form.html"
    authentication_form = SecureLoginForm
    extra_context = {"title": "Welcome back", "subtitle": "Sign in to your EventHub account."}


class EventForm(forms.ModelForm):
    def clean_image(self):
        image = self.cleaned_data.get("image")
        if settings.PREVIEW_MODE and image and not getattr(image, "_committed", False):
            raise forms.ValidationError("Uploads are disabled on the free preview host.")
        return image

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "category",
            "location",
            "venue",
            "start_datetime",
            "end_datetime",
            "registration_deadline",
            "capacity",
            "image",
        ]
        widgets = {
            name: forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            for name in ["start_datetime", "end_datetime", "registration_deadline"]
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name"]


def public_events(request):
    qs = (
        Event.objects.filter(status="PUBLISHED")
        .select_related("category", "organizer")
        .annotate(
            registration_count=Count("registrations", filter=Q(registrations__status="REGISTERED"))
        )
    )
    if request.GET.get("q"):
        qs = qs.filter(
            Q(title__icontains=request.GET["q"]) | Q(location__icontains=request.GET["q"])
        )
    if request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])
    return render(
        request,
        "events.html",
        {
            "page": Paginator(qs.order_by("start_datetime", "pk"), 9).get_page(
                request.GET.get("page")
            ),
            "categories": Category.objects.all(),
        },
    )


def detail(request, pk):
    qs = Event.objects.select_related("category", "organizer")
    if not request.user.is_staff:
        visible = ~Q(status="DRAFT")
        if request.user.is_authenticated:
            visible |= Q(organizer=request.user)
        qs = qs.filter(visible)
    event = get_object_or_404(qs, pk=pk)
    count = event.registrations.filter(status="REGISTERED").count()
    registration = (
        event.registrations.filter(user=request.user).exclude(status="CANCELLED").first()
        if request.user.is_authenticated
        else None
    )
    from django.utils import timezone

    available = (
        event.status == "PUBLISHED"
        and event.registration_deadline > timezone.now()
        and event.start_datetime > timezone.now()
    )
    return render(
        request,
        "detail.html",
        {
            "event": event,
            "count": count,
            "remaining": max(0, event.capacity - count),
            "registration": registration,
            "available": available,
        },
    )


def signup(request):
    if settings.NEON_AUTH_BASE_URL:
        return redirect("/identity/?mode=signup")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(
        request,
        "form.html",
        {
            "form": form,
            "title": "Find your next great experience",
            "subtitle": "Create your free EventHub account.",
        },
    )


@login_required
def dashboard(request):
    registrations = request.user.registrations.select_related("event", "event__category").order_by(
        "-registered_at"
    )
    return render(request, "dashboard.html", {"registrations": registrations})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "form.html", {"form": form, "title": "Your profile"})


@login_required
@require_POST
def register_event(request, pk):
    get_object_or_404(Event, pk=pk, status="PUBLISHED")
    try:
        registration = register(request.user, pk)
        messages.success(
            request,
            "You are on the waitlist."
            if registration.status == "WAITLISTED"
            else "Your place is confirmed!",
        )
    except APIException as exc:
        messages.error(request, str(exc.detail))
    return redirect("detail", pk=pk)


@login_required
@require_POST
def cancel_registration(request, pk):
    registration = get_object_or_404(Registration, pk=pk, user=request.user)
    try:
        cancel(registration.pk)
        messages.success(request, "Registration cancelled.")
    except APIException as exc:
        messages.error(request, str(exc.detail))
    return redirect("dashboard")


def can_organize(user):
    return user.is_organizer or user.is_staff


@login_required
def organizer(request):
    if not can_organize(request.user):
        return HttpResponseForbidden("Organizer access required. Contact an administrator.")
    qs = Event.objects.filter(organizer=request.user).annotate(
        registration_count=Count("registrations", filter=Q(registrations__status="REGISTERED"))
    )
    return render(
        request,
        "organizer.html",
        {
            "events": qs,
            "total": Registration.objects.filter(
                event__organizer=request.user, status="REGISTERED"
            ).count(),
        },
    )


@login_required
@transaction.atomic
def edit_event(request, pk=None):
    if not can_organize(request.user):
        return HttpResponseForbidden("Organizer access required.")
    event = (
        get_object_or_404(Event.objects.select_for_update(), pk=pk, organizer=request.user)
        if pk
        else Event(organizer=request.user)
    )
    if pk and event.status in ["CANCELLED", "COMPLETED"]:
        return HttpResponseForbidden("This event can no longer be edited.")
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == "POST" and form.is_valid():
        if (
            pk
            and form.cleaned_data["capacity"]
            < event.registrations.filter(status="REGISTERED").count()
        ):
            form.add_error("capacity", "Capacity cannot be below confirmed registrations.")
        else:
            form.save()
            return redirect("organizer")
    return render(
        request, "form.html", {"form": form, "title": "Edit event" if pk else "Create an event"}
    )


@login_required
@require_POST
def event_action(request, pk, action):
    get_object_or_404(Event, pk=pk, organizer=request.user)
    if action not in ["publish", "cancel", "complete"]:
        return HttpResponseForbidden()
    try:
        transition(
            pk, {"publish": "PUBLISHED", "cancel": "CANCELLED", "complete": "COMPLETED"}[action]
        )
        messages.success(request, "Event updated.")
    except Conflict as exc:
        messages.error(request, str(exc.detail))
    return redirect("organizer")


@login_required
def attendees(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    qs = event.registrations.select_related("user")
    if request.GET.get("q"):
        qs = qs.filter(user__email__icontains=request.GET["q"])
    if request.GET.get("export") == "csv":
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendees.csv"'
        writer = csv.writer(response)
        writer.writerow(["Email", "Status"])
        for r in qs:
            writer.writerow(["'" + r.user.email, r.status])
        return response
    return render(
        request,
        "attendees.html",
        {"event": event, "page": Paginator(qs, 50).get_page(request.GET.get("page"))},
    )


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
