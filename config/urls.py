from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.events.api import Events, Categories, Registrations
from apps.users import api, identity
from apps.common import web

router = DefaultRouter()
router.register("events", Events, basename="event")
router.register("categories", Categories, basename="category")
router.register("registrations", Registrations, basename="registration")
urlpatterns = [
    path("identity/", identity.page),
    path("identity/exchange/", identity.exchange),
    path("identity/neon/<path:endpoint>", identity.proxy),
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api/v1/users/register/", api.Signup.as_view()),
    path("api/v1/users/login/", api.Login.as_view()),
    path("api/v1/users/logout/", api.Logout.as_view()),
    path("api/v1/users/profile/", api.Profile.as_view()),
    path("api/v1/users/manage/", api.ManageUsers.as_view()),
    path("api/v1/users/manage/<int:pk>/", api.ManageUser.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("health/", web.health),
    path("", web.public_events, name="home"),
    path("events/", web.public_events, name="events"),
    path("events/<int:pk>/", web.detail, name="detail"),
    path("events/<int:pk>/register/", web.register_event, name="register_event"),
    path("registrations/<int:pk>/cancel/", web.cancel_registration, name="cancel_registration"),
    path("signup/", web.signup, name="signup"),
    path("login/", web.Signin.as_view(), name="login"),
    path("logout/", identity.local_logout, name="logout"),
    path("dashboard/", web.dashboard, name="dashboard"),
    path("profile/", web.profile, name="profile"),
    path("organizer/", web.organizer, name="organizer"),
    path("organizer/new/", web.edit_event, name="create_event"),
    path("organizer/<int:pk>/edit/", web.edit_event, name="edit_event"),
    path("organizer/<int:pk>/attendees/", web.attendees, name="attendees"),
    path("organizer/<int:pk>/<str:action>/", web.event_action, name="event_action"),
    path(
        "password-reset/",
        identity.reset_page,
        name="password_reset",
    ),
    path(
        "password-reset/sent/",
        auth.PasswordResetDoneView.as_view(template_name="reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth.PasswordResetConfirmView.as_view(
            template_name="form.html", extra_context={"title": "Choose a new password"}
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth.PasswordResetCompleteView.as_view(template_name="reset_done.html"),
        name="password_reset_complete",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
