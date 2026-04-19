from django.apps import apps
from django.db import models


class AccountProfile(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="account_profiles")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="account_profiles",
        null=True,
        blank=True,
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    newsletter_opt_in = models.BooleanField(default=False)
    order_updates_opt_in = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "email")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "email"), name="accounts_profile_unique_email_per_tenant"),
        ]

    def save(self, *args, **kwargs):
        if self.customer_id is None:
            self.customer = self._resolve_customer_link()
        super().save(*args, **kwargs)

    def _resolve_customer_link(self):
        normalized_email = str(self.email or "").strip()
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
        return f"{self.tenant_id}:{self.email}"
