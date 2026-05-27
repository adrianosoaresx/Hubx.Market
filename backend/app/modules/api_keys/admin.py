from django.contrib import admin

from app.modules.api_keys.models import ApiKey, ApiKeyQuota, ApiKeyQuotaUsage


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("tenant", "name", "prefix", "status", "created_at", "last_used_at", "revoked_at")
    list_filter = ("status", "created_at", "revoked_at")
    search_fields = ("name", "prefix", "tenant__name")
    readonly_fields = ("prefix", "key_hash", "created_at", "updated_at", "last_used_at", "revoked_at")


@admin.register(ApiKeyQuota)
class ApiKeyQuotaAdmin(admin.ModelAdmin):
    list_display = ("tenant", "api_key", "endpoint", "scope", "limit", "window_seconds", "status", "updated_at")
    list_filter = ("status", "scope", "endpoint", "updated_at")
    search_fields = ("api_key__name", "api_key__prefix", "tenant__name", "endpoint")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ApiKeyQuotaUsage)
class ApiKeyQuotaUsageAdmin(admin.ModelAdmin):
    list_display = ("tenant", "api_key", "endpoint", "window_start", "window_seconds", "count", "updated_at")
    list_filter = ("endpoint", "window_seconds", "window_start", "updated_at")
    search_fields = ("api_key__name", "api_key__prefix", "tenant__name", "endpoint")
    readonly_fields = ("created_at", "updated_at")
