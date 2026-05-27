from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "tenant", "module", "action", "entity_type", "entity_id", "actor_label")
    list_filter = ("module", "action", "tenant")
    search_fields = ("summary", "entity_type", "entity_id", "actor_label")
    readonly_fields = ("created_at",)
