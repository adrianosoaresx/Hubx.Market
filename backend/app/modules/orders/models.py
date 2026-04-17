from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Pago"
        PENDING = "pending", "Pendente"
        SHIPPED = "shipped", "Enviado"
        CANCELED = "canceled", "Cancelado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="orders")
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
