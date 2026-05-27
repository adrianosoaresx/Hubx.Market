from django.apps import apps
from django.core.exceptions import ValidationError
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


class OwnerUser(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="owner_users")
    email = models.EmailField()
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=64, default="owner")
    is_active = models.BooleanField(default=True)
    receives_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "email")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "email"), name="accounts_owner_unique_email_per_tenant"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.email}"


class OwnerMfaFactor(models.Model):
    class FactorType(models.TextChoices):
        TOTP = "totp", "TOTP"
        RECOVERY_CODE = "recovery_code", "Código de recuperação"
        EXTERNAL = "external", "Provider externo"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="owner_mfa_factors")
    owner = models.ForeignKey("accounts.OwnerUser", on_delete=models.CASCADE, related_name="mfa_factors")
    factor_type = models.CharField(max_length=32, choices=FactorType.choices)
    provider_key = models.CharField(max_length=64, blank=True)
    label = models.CharField(max_length=120, blank=True)
    secret_reference = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    last_challenged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "owner_id", "factor_type", "provider_key")
        indexes = [
            models.Index(fields=("tenant", "owner", "is_active"), name="accounts_mfa_owner_act_idx"),
            models.Index(fields=("tenant", "factor_type"), name="accounts_mfa_tenant_type_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "owner", "factor_type", "provider_key"),
                name="accounts_mfa_unique_factor_per_owner",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.owner_id:
            owner_tenant_id = self.owner.tenant_id
            if not self.tenant_id:
                self.tenant_id = owner_tenant_id
            elif self.tenant_id != owner_tenant_id:
                raise ValidationError("OwnerMfaFactor deve pertencer ao mesmo tenant do OwnerUser.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.owner_id}:{self.factor_type}:{self.provider_key or 'default'}"


class OwnerMfaRecoveryCode(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="owner_mfa_recovery_codes")
    owner = models.ForeignKey("accounts.OwnerUser", on_delete=models.CASCADE, related_name="mfa_recovery_codes")
    code_hash = models.CharField(max_length=255)
    label = models.CharField(max_length=120, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("tenant_id", "owner_id", "created_at")
        indexes = [
            models.Index(fields=("tenant", "owner", "used_at"), name="accounts_mfa_rc_owner_idx"),
        ]

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def save(self, *args, **kwargs):
        if self.owner_id:
            owner_tenant_id = self.owner.tenant_id
            if not self.tenant_id:
                self.tenant_id = owner_tenant_id
            elif self.tenant_id != owner_tenant_id:
                raise ValidationError("OwnerMfaRecoveryCode deve pertencer ao mesmo tenant do OwnerUser.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.owner_id}:recovery-code:{self.id}"
