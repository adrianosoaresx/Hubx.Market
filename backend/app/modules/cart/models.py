from django.db import models
from django.db.models import Q


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        CONVERTED = "converted", "Convertido"
        ABANDONED = "abandoned", "Abandonado"
        EXPIRED = "expired", "Expirado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="carts")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="carts",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    currency = models.CharField(max_length=8, default="BRL")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=64, blank=True)
    converted_checkout_session_key = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-updated_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "customer"),
                condition=Q(status="active", customer__isnull=False),
                name="cart_active_unique_customer_per_tenant",
            ),
            models.UniqueConstraint(
                fields=("tenant", "session_key"),
                condition=Q(status="active") & ~Q(session_key=""),
                name="cart_active_unique_session_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="cart_tenant_status_idx"),
            models.Index(fields=("tenant", "session_key"), name="cart_tenant_session_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        owner = self.customer_id or self.session_key or "anonymous"
        return f"{self.tenant_id}:{owner}:{self.status}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.SET_NULL,
        related_name="cart_items",
        null=True,
        blank=True,
    )
    product_slug = models.SlugField(max_length=255, blank=True)
    product_name = models.CharField(max_length=255)
    variant_sku = models.CharField(max_length=120, blank=True)
    variant_label = models.CharField(max_length=120, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    image_alt = models.CharField(max_length=255, blank=True)
    price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    compare_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("cart_id", "sort_order", "id")
        indexes = [
            models.Index(fields=("cart", "variant_sku"), name="cart_item_variant_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.cart_id}:{self.variant_sku or self.product_slug}"


class CartMutation(models.Model):
    class MutationType(models.TextChoices):
        ADD_ITEM = "add_item", "Adicionar item"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="cart_mutations")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="mutations")
    mutation_key = models.CharField(max_length=120)
    mutation_type = models.CharField(max_length=32, choices=MutationType.choices)
    result_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "cart", "mutation_key"), name="cart_mutation_unique_key"),
        ]
        indexes = [
            models.Index(fields=("tenant", "mutation_type"), name="cart_mut_tenant_type_idx"),
            models.Index(fields=("cart", "mutation_key"), name="cart_mut_cart_key_idx"),
        ]

    def save(self, *args, **kwargs):
        self.mutation_key = str(self.mutation_key or "").strip()[:120]
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.cart_id}:{self.mutation_type}:{self.mutation_key}"
