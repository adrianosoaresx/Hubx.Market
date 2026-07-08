from django.contrib import admin

from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionCoupon, SubscriptionPlan, TenantSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "billing_model",
        "platform_fee_percent",
        "minimum_monthly_fee",
        "product_limit",
        "monthly_paid_order_limit",
        "requires_billing_method",
        "status",
    )
    list_filter = ("status", "billing_model", "currency_code", "requires_billing_method")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionCoupon)
class SubscriptionCouponAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "discount_type", "discount_value", "plan", "starts_at", "ends_at", "updated_at")
    list_filter = ("status", "discount_type", "plan")
    search_fields = ("code", "name", "plan__code", "plan__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "plan",
        "status",
        "billing_provider_code",
        "billing_method_status",
        "trial_ends_at",
        "current_period_ends_at",
        "updated_at",
    )
    list_filter = ("status", "plan", "billing_provider_code", "billing_method_status", "current_period_ends_at")
    search_fields = ("tenant__name", "tenant__slug", "plan__code", "external_reference", "billing_external_reference")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubscriptionAcquisitionLead)
class SubscriptionAcquisitionLeadAdmin(admin.ModelAdmin):
    list_display = ("store_name", "desired_subdomain", "plan_code_snapshot", "contact_email", "status", "created_at")
    list_filter = ("status", "plan", "source", "created_at")
    search_fields = ("store_name", "desired_subdomain", "contact_email", "contact_name", "plan_code_snapshot")
    readonly_fields = ("created_at", "updated_at", "converted_at", "discarded_at")
