from django.db import models


class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        DRAFT = "draft", "Rascunho"
        INACTIVE = "inactive", "Inativo"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    brand_name = models.CharField(max_length=120, blank=True)
    category_label = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    is_active = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "name")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "slug"), name="catalog_product_unique_slug_per_tenant"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    compare_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("product_id", "-is_default", "sku")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_id}:{self.sku}"
