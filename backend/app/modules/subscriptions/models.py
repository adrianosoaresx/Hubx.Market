from __future__ import annotations

from django.db import models
from django.db.models import Q


class SubscriptionPlan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        ARCHIVED = "archived", "Arquivado"

    class BillingModel(models.TextChoices):
        TAKE_RATE_ONLY = "take_rate_only", "Percentual sobre vendas"
        MINIMUM_COMMITMENT = "minimum_commitment", "Mínimo abatível"
        CUSTOM = "custom", "Sob consulta"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=3, default="BRL")
    included_api_quota = models.PositiveIntegerField(default=0)
    trial_days = models.PositiveSmallIntegerField(default=0)
    requires_payment_method = models.BooleanField(default=False)
    billing_model = models.CharField(max_length=32, choices=BillingModel.choices, default=BillingModel.TAKE_RATE_ONLY)
    platform_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    minimum_monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    product_limit = models.PositiveIntegerField(default=0)
    monthly_paid_order_limit = models.PositiveIntegerField(default=0)
    requires_hubx_checkout = models.BooleanField(default=True)
    requires_billing_method = models.BooleanField(default=False)
    feature_list = models.TextField(blank=True)
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
            models.CheckConstraint(
                check=Q(billing_model__in=("take_rate_only", "minimum_commitment", "custom")),
                name="subscription_plan_billing_model_valid",
            ),
            models.CheckConstraint(
                check=Q(platform_fee_percent__gte=0),
                name="subscription_plan_fee_percent_non_negative",
            ),
            models.CheckConstraint(
                check=Q(minimum_monthly_fee__gte=0),
                name="subscription_plan_minimum_fee_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "code"), name="sub_plan_status_code_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}:{self.status}"


class SubscriptionCoupon(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentual"
        FIXED = "fixed", "Valor fixo"

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscription_coupons",
        null=True,
        blank=True,
    )
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    discount_type = models.CharField(max_length=16, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("active", "inactive")),
                name="subscription_coupon_status_valid",
            ),
            models.CheckConstraint(
                check=Q(discount_type__in=("percent", "fixed")),
                name="subscription_coupon_discount_type_valid",
            ),
            models.CheckConstraint(
                check=Q(discount_value__gt=0),
                name="subscription_coupon_discount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "code"), name="sub_coupon_status_code_idx"),
            models.Index(fields=("plan", "status"), name="sub_coupon_plan_status_idx"),
        ]

    def save(self, *args, **kwargs):
        self.code = str(self.code or "").strip().upper()[:64]
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code}:{self.status}"


class TenantSubscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trial"
        ACTIVE = "active", "Ativa"
        PAST_DUE = "past_due", "Em atraso"
        SUSPENDED = "suspended", "Suspensa"
        CANCELED = "canceled", "Cancelada"

    class BillingMethodStatus(models.TextChoices):
        MISSING = "missing", "Não informado"
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Ativo"
        FAILED = "failed", "Falhou"

    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="tenant_subscriptions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TRIALING)
    started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_ends_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    external_reference = models.CharField(max_length=180, blank=True)
    billing_provider_code = models.CharField(max_length=64, blank=True)
    billing_provider_label = models.CharField(max_length=120, blank=True)
    billing_external_reference = models.CharField(max_length=180, blank=True)
    billing_checkout_url = models.URLField(max_length=500, blank=True)
    billing_method_status = models.CharField(
        max_length=16,
        choices=BillingMethodStatus.choices,
        default=BillingMethodStatus.MISSING,
    )
    billing_method_reference = models.CharField(max_length=180, blank=True)
    billing_method_verified_at = models.DateTimeField(null=True, blank=True)
    coupon_code_snapshot = models.CharField(max_length=64, blank=True)
    coupon_discount_type_snapshot = models.CharField(max_length=16, blank=True)
    coupon_discount_value_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_discount_total_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_monthly_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promotion_snapshot = models.JSONField(default=dict, blank=True)
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
            models.CheckConstraint(
                check=Q(billing_method_status__in=("missing", "pending", "active", "failed")),
                name="tenant_sub_billing_method_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "current_period_ends_at"), name="tenant_sub_status_period_idx"),
            models.Index(fields=("billing_method_status", "updated_at"), name="tenant_sub_bill_method_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.plan_id}:{self.status}"


class SubscriptionAcquisitionLead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Novo"
        CONVERTED = "converted", "Convertido"
        DISCARDED = "discarded", "Descartado"

    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="acquisition_leads")
    onboarding = models.OneToOneField(
        "tenants.TenantOnboarding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_acquisition_lead",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    plan_code_snapshot = models.SlugField(max_length=80)
    plan_name_snapshot = models.CharField(max_length=120)
    plan_monthly_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_currency_snapshot = models.CharField(max_length=3, default="BRL")
    coupon_code_snapshot = models.CharField(max_length=64, blank=True)
    coupon_discount_type_snapshot = models.CharField(max_length=16, blank=True)
    coupon_discount_value_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_discount_total_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_monthly_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promotion_snapshot = models.JSONField(default=dict, blank=True)
    store_name = models.CharField(max_length=150)
    desired_subdomain = models.SlugField(max_length=63)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=80, default="public-plans")
    converted_at = models.DateTimeField(null=True, blank=True)
    discarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("new", "converted", "discarded")),
                name="sub_acq_lead_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "-created_at"), name="sub_acq_status_created_idx"),
            models.Index(fields=("desired_subdomain",), name="sub_acq_subdomain_idx"),
            models.Index(fields=("contact_email",), name="sub_acq_contact_email_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.id}:{self.desired_subdomain}:{self.status}"
