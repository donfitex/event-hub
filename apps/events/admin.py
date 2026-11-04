from django.contrib import admin
from .models import Event, Category


@admin.register(Event)
class Events(admin.ModelAdmin):
    list_display = ["title", "organizer", "status", "start_datetime", "capacity"]
    list_filter = ["status", "category"]
    search_fields = ["title", "location", "organizer__email"]
    readonly_fields = [f.name for f in Event._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Category)
