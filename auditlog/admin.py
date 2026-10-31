from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "school", "actor", "action", "entity_type", "entity_id", "summary"]
    list_filter = ["school", "action", "entity_type"]
    search_fields = ["school__name", "actor__username", "entity_type", "entity_id", "summary"]
    readonly_fields = ["school", "actor", "action", "entity_type", "entity_id", "summary", "metadata", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
