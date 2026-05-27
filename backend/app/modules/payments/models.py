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
