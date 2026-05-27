from django.db import models
from django.db.models import Q


class ApiKey(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        REVOKED = "revoked", "Revogada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="api_keys")
    owner = models.ForeignKey(
        "accounts.OwnerUser",
        on_delete=models.SET_NULL,
        related_name="api_keys",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    prefix = models.CharField(max_length=24, unique=True)
    key_hash = models.CharField(max_length=255)
    scopes = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_by_label = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_label = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("active", "revoked")),
                name="api_key_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="api_key_tenant_status_idx"),
            models.Index(fields=("tenant", "created_at"), name="api_key_tenant_created_idx"),
            models.Index(fields=("prefix",), name="api_key_prefix_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.prefix}:{self.status}"


class ApiKeyQuota(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        DISABLED = "disabled", "Desativada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="api_key_quotas")
    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name="quotas")
    endpoint = models.CharField(max_length=120)
    scope = models.CharField(max_length=80, default="read:catalog")
    window_seconds = models.PositiveIntegerField(default=86400)
    limit = models.PositiveIntegerField(default=10000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_by_label = models.CharField(max_length=180, blank=True)
    updated_by_label = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "api_key_id", "endpoint")
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=("active", "disabled")),
                name="api_key_quota_status_valid",
            ),
            models.CheckConstraint(
                check=Q(limit__gt=0),
                name="api_key_quota_limit_positive",
            ),
            models.CheckConstraint(
                check=Q(window_seconds__gt=0),
                name="api_key_quota_window_positive",
            ),
            models.UniqueConstraint(
                fields=("tenant", "api_key", "endpoint"),
                name="api_key_quota_tenant_key_endpoint_unique",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status"), name="api_key_quota_tenant_stat_idx"),
            models.Index(fields=("tenant", "api_key", "endpoint"), name="api_key_quota_lookup_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.api_key_id}:{self.endpoint}:{self.limit}/{self.window_seconds}"


class ApiKeyQuotaUsage(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="api_key_quota_usages")
    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name="quota_usages")
    quota = models.ForeignKey(ApiKeyQuota, on_delete=models.SET_NULL, related_name="usages", null=True, blank=True)
    endpoint = models.CharField(max_length=120)
    window_start = models.DateTimeField()
    window_seconds = models.PositiveIntegerField(default=86400)
    count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "api_key_id", "endpoint", "-window_start")
        constraints = [
            models.CheckConstraint(
                check=Q(count__gte=0),
                name="api_key_quota_usage_count_non_negative",
            ),
            models.CheckConstraint(
                check=Q(window_seconds__gt=0),
                name="api_key_quota_usage_window_positive",
            ),
            models.UniqueConstraint(
                fields=("tenant", "api_key", "endpoint", "window_start", "window_seconds"),
                name="api_key_quota_usage_window_unique",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "api_key", "endpoint", "window_start"), name="api_key_quota_usage_lookup_idx"),
            models.Index(fields=("quota", "window_start"), name="api_key_quota_usage_quota_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.api_key_id}:{self.endpoint}:{self.window_start}:{self.count}"
