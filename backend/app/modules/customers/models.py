from django.db import models


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        VIP = "vip", "VIP"
        INACTIVE = "inactive", "Inativo"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="customers")
    slug = models.SlugField(max_length=150)
    reference = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    account_type = models.CharField(max_length=64, blank=True, default="Storefront")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "full_name")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "slug"), name="customers_unique_slug_per_tenant"),
            models.UniqueConstraint(fields=("tenant", "email"), name="customers_unique_email_per_tenant"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.email}"


class CustomerAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=64, default="Casa")
    recipient_name = models.CharField(max_length=150, blank=True)
    line_1 = models.CharField(max_length=255)
    line_2 = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=16)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("customer_id", "-is_default", "label", "id")

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer_id}:{self.label}"
