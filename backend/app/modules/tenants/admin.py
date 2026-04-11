from django.contrib import admin
from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "subdomain",
        "custom_domain",
        "is_active",
        "maintenance_mode",
        "created_at",
    )
    search_fields = ("name", "slug", "subdomain", "custom_domain")
    list_filter = ("is_active", "maintenance_mode")
    ordering = ("slug",)