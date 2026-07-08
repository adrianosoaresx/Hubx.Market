from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        FAILED = "failed", "Falhou"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="payment_attempts")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payment_attempts")
    attempt_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_method_code = models.CharField(max_length=64, blank=True)
    provider_code = models.CharField(max_length=64, blank=True)
    provider_label = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=8, default="BRL")
    provider_request_key = models.CharField(max_length=120, blank=True)
    bootstrapped_at = models.DateTimeField(null=True, blank=True)
    external_reference = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("order",),
                condition=Q(status="pending"),
                name="payments_single_pending_attempt_per_order",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "order", "status"), name="pay_att_tenant_ord_stat_idx"),
            models.Index(fields=("tenant", "external_reference"), name="pay_att_tenant_extref_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.order_id}:{self.status}"


class PaymentRefund(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Solicitado"
        BLOCKED = "blocked", "Bloqueado"
        PROCESSING = "processing", "Processando"
        SUCCEEDED = "succeeded", "Concluído"
        FAILED = "failed", "Falhou"
        REVERSED = "reversed", "Revertido"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="payment_refunds")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payment_refunds")
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.PROTECT,
        related_name="refunds",
        null=True,
        blank=True,
    )
    refund_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=120)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=8, default="BRL")
    provider_code = models.CharField(max_length=64, blank=True)
    external_reference = models.CharField(max_length=120, blank=True)
    provider_refund_reference = models.CharField(max_length=120, blank=True)
    reason_code = models.CharField(max_length=64, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "idempotency_key"),
                name="payments_unique_refund_idempotency_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "order", "status"), name="pay_ref_tenant_ord_stat_idx"),
            models.Index(fields=("tenant", "status", "created_at"), name="pay_ref_tenant_stat_cr_idx"),
            models.Index(fields=("tenant", "external_reference"), name="pay_ref_tenant_extref_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.order_id}:{self.status}"


class PlatformFeeLedger(models.Model):
    class Kind(models.TextChoices):
        ORDER_TAKE_RATE = "order_take_rate", "Taxa por pedido"
        PRO_MINIMUM_ADJUSTMENT = "pro_minimum_adjustment", "Complemento mínimo Pro"

    class Status(models.TextChoices):
        EXPECTED = "expected", "Esperada"
        SPLIT_REQUESTED = "split_requested", "Split solicitado"
        PAID = "paid", "Paga"
        PENDING_COLLECTION = "pending_collection", "Cobrança pendente"
        ADJUSTMENT_REQUIRED = "adjustment_required", "Ajuste necessário"
        CANCELED = "canceled", "Cancelada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="platform_fee_ledger_entries")
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="platform_fee_ledger_entries",
        null=True,
        blank=True,
    )
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        related_name="platform_fee_ledger_entries",
        null=True,
        blank=True,
    )
    ledger_key = models.CharField(max_length=180, unique=True)
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.ORDER_TAKE_RATE)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.EXPECTED)
    plan_code_snapshot = models.CharField(max_length=80, blank=True)
    billing_model_snapshot = models.CharField(max_length=32, blank=True)
    platform_fee_percent_snapshot = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    minimum_monthly_fee_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    billing_period_start = models.DateTimeField(null=True, blank=True)
    billing_period_end = models.DateTimeField(null=True, blank=True)
    basis_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=8, default="BRL")
    provider_code = models.CharField(max_length=64, blank=True)
    provider_split_reference = models.CharField(max_length=120, blank=True)
    provider_payment_reference = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                check=Q(kind__in=("order_take_rate", "pro_minimum_adjustment")),
                name="platform_fee_kind_valid",
            ),
            models.CheckConstraint(
                check=Q(status__in=("expected", "split_requested", "paid", "pending_collection", "adjustment_required", "canceled")),
                name="platform_fee_status_valid",
            ),
            models.CheckConstraint(
                check=Q(basis_amount__gte=0),
                name="platform_fee_basis_non_negative",
            ),
            models.CheckConstraint(
                check=Q(fee_amount__gte=0),
                name="platform_fee_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "created_at"), name="platform_fee_tenant_stat_idx"),
            models.Index(fields=("tenant", "kind", "billing_period_start"), name="platform_fee_period_idx"),
            models.Index(fields=("tenant", "order", "kind"), name="platform_fee_order_kind_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.kind}:{self.status}:{self.fee_amount}"
