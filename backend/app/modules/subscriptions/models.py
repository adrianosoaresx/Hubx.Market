from __future__ import annotations

from django.db import models
from django.db.models import Q


class SubscriptionPlan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        ARCHIVED = "archived", "Arquivado"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=3, default="BRL")
    included_api_quota = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("monthly_price", "code")
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("active", "archived")),
                name="subscription_plan_status_valid",
            ),
            models.CheckConstraint(
                check=Q(monthly_price__gte=0),
                name="subscription_plan_price_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "code"), name="sub_plan_status_code_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}:{self.status}"


class TenantSubscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trial"
        ACTIVE = "active", "Ativa"
        PAST_DUE = "past_due", "Em atraso"
        SUSPENDED = "suspended", "Suspensa"
        CANCELED = "canceled", "Cancelada"

    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="tenant_subscriptions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRIALING)
    started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_ends_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    external_reference = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id",)
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("trialing", "active", "past_due", "suspended", "canceled")),
                name="tenant_subscription_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "current_period_ends_at"), name="tenant_sub_status_period_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.plan_id}:{self.status}"
