from __future__ import annotations

import uuid

from django.db import models


class CheckoutSession(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        COMPLETED = "completed", "Concluída"
        EXPIRED = "expired", "Expirada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="checkout_sessions")
    session_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=64, blank=True)
    zip_code = models.CharField(max_length=32, blank=True)

    shipping_methods = models.JSONField(default=list, blank=True)
    shipping_method_selected = models.CharField(max_length=64, blank=True)
    payment_methods = models.JSONField(default=list, blank=True)
    payment_method_selected = models.CharField(max_length=64, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    installments_summary = models.CharField(max_length=120, blank=True)
    installments_selected = models.CharField(max_length=32, blank=True)
    installments_options = models.JSONField(default=list, blank=True)
    accept_terms = models.BooleanField(default=False)

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-updated_at")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.session_key}"


class CheckoutSessionItem(models.Model):
    checkout_session = models.ForeignKey(
        CheckoutSession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    meta = models.CharField(max_length=255, blank=True)
    variant_sku = models.CharField(max_length=120, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    image_alt = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    compare_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    quantity_readonly = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("checkout_session_id", "sort_order", "id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.checkout_session_id}:{self.title}"
