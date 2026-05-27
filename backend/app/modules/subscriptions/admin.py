from django.contrib import admin

from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "monthly_price", "currency_code", "included_api_quota", "status")
    list_filter = ("status", "currency_code")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "trial_ends_at", "current_period_ends_at", "updated_at")
    list_filter = ("status", "plan", "current_period_ends_at")
    search_fields = ("tenant__name", "tenant__slug", "plan__code", "external_reference")
    readonly_fields = ("created_at", "updated_at")
