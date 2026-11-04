from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.events.api import Categories, Events

router = DefaultRouter()
router.register("events", Events, basename="event")
router.register("categories", Categories, basename="category")
urlpatterns = [path("api/v1/", include(router.urls))]
