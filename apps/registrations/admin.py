from django.contrib import admin
from .models import Registration, Notification


@admin.register(Registration)
class Registrations(admin.ModelAdmin):
    list_display = ["user", "event", "status", "registered_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "event__title"]
    readonly_fields = [f.name for f in Registration._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class Notifications(admin.ModelAdmin):
    list_display = ["recipient", "subject", "sent_at", "attempts"]
    readonly_fields = [f.name for f in Notification._meta.fields]

    def has_add_permission(self, request):
        return False
