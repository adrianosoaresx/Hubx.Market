from django.db import models


class Coupon(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentual"
        FIXED = "fixed", "Valor fixo"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    discount_type = models.CharField(max_length=16, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "code")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "code"), name="coupon_unique_code_per_tenant"),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="coupon_tenant_status_idx"),
            models.Index(fields=("tenant", "code"), name="coupon_tenant_code_idx"),
        ]

    def save(self, *args, **kwargs):
        self.code = str(self.code or "").strip().upper()[:64]
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.code}"


class CouponRedemption(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Aplicado"
        REVERSED = "reversed", "Revertido"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="coupon_redemptions")
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        related_name="redemptions",
        null=True,
        blank=True,
    )
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="coupon_redemptions")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="coupon_redemptions",
        null=True,
        blank=True,
    )
    coupon_code_snapshot = models.CharField(max_length=64)
    discount_total_snapshot = models.DecimalField(max_digits=12, decimal_places=2)
    promotion_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.APPLIED)
    source_type = models.CharField(max_length=64, blank=True)
    source_label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "order", "coupon_code_snapshot"),
                name="coupon_redemption_unique_order_code",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "coupon_code_snapshot"), name="coupon_red_tenant_code_idx"),
            models.Index(fields=("tenant", "status"), name="coupon_red_tenant_status_idx"),
            models.Index(fields=("coupon", "created_at"), name="coupon_red_coupon_time_idx"),
        ]

    def save(self, *args, **kwargs):
        self.coupon_code_snapshot = str(self.coupon_code_snapshot or "").strip().upper()[:64]
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.order_id}:{self.coupon_code_snapshot}"
