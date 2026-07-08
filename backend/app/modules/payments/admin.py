from django.contrib import admin

from app.modules.payments.models import PaymentAttempt, PaymentRefund, PlatformFeeLedger


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("tenant", "order", "provider_code", "status", "amount", "external_reference", "updated_at")
    list_filter = ("status", "provider_code", "created_at")
    search_fields = ("tenant__name", "order__number", "external_reference", "provider_request_key")
    readonly_fields = ("attempt_key", "created_at", "updated_at")


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ("tenant", "order", "status", "amount", "provider_code", "provider_refund_reference", "updated_at")
    list_filter = ("status", "provider_code", "created_at")
    search_fields = ("tenant__name", "order__number", "idempotency_key", "external_reference", "provider_refund_reference")
    readonly_fields = ("refund_key", "created_at", "updated_at")


@admin.register(PlatformFeeLedger)
class PlatformFeeLedgerAdmin(admin.ModelAdmin):
    list_display = ("tenant", "kind", "status", "plan_code_snapshot", "basis_amount", "fee_amount", "provider_code", "updated_at")
    list_filter = ("kind", "status", "plan_code_snapshot", "provider_code", "created_at")
    search_fields = ("tenant__name", "tenant__slug", "order__number", "ledger_key", "provider_payment_reference")
    readonly_fields = ("ledger_key", "created_at", "updated_at")
