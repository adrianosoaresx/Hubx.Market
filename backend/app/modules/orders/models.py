from django.apps import apps
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Pago"
        PENDING = "pending", "Pendente"
        SHIPPED = "shipped", "Enviado"
        CANCELED = "canceled", "Cancelado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    number = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    customer_name = models.CharField(max_length=150, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    fulfillment_status_label = models.CharField(max_length=120, blank=True)
    fulfillment_status_variant = models.CharField(max_length=32, blank=True)
    payment_status = models.CharField(max_length=120, blank=True)
    shipping_status = models.CharField(max_length=120, blank=True)
    shipping_address_summary = models.CharField(max_length=255, blank=True)
    notes_content = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installments_summary = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-updated_at")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "number"), name="orders_unique_number_per_tenant"),
        ]

    def save(self, *args, **kwargs):
        if self.customer_id is None:
            self.customer = self._resolve_customer_link()
        super().save(*args, **kwargs)

    def _resolve_customer_link(self):
        normalized_email = str(self.customer_email or "").strip()
        if not self.tenant_id or not normalized_email:
            return None
        try:
            customer_model = apps.get_model("customers", "Customer")
        except Exception:
            return None
        matches = list(
            customer_model._default_manager.filter(
                tenant_id=self.tenant_id,
                email__iexact=normalized_email,
            )[:2]
        )
        if len(matches) != 1:
            return None
        return matches[0]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    meta = models.CharField(max_length=255, blank=True)
    price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    quantity_readonly = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order_id", "sort_order", "id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.order_id}:{self.title}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    event_type = models.CharField(max_length=32, blank=True)
    source_type = models.CharField(max_length=32, blank=True, default="")
    source_label = models.CharField(max_length=64, blank=True, default="")
    actor_label = models.CharField(max_length=120, blank=True, default="")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    badge_label = models.CharField(max_length=64, blank=True)
    badge_variant = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.order_id}:{self.title}"
