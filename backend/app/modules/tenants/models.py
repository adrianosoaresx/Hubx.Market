from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    subdomain = models.SlugField(max_length=63, unique=True)
    custom_domain = models.CharField(max_length=255, null=True, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    conversion_primary_color = models.CharField(max_length=7, blank=True)
    storefront_hero_enabled = models.BooleanField(default=True)
    storefront_hero_title = models.CharField(max_length=160, blank=True)
    storefront_hero_description = models.TextField(blank=True)
    storefront_hero_image_url = models.URLField(max_length=500, blank=True)
    storefront_hero_cta_label = models.CharField(max_length=80, blank=True)
    storefront_hero_cta_href = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ("slug",)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.slug})"


class TenantOnboarding(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        IN_PROGRESS = "in_progress", "Em andamento"
        READY_FOR_REVIEW = "ready_for_review", "Pronto para revisão"
        COMPLETED = "completed", "Concluído"
        BLOCKED = "blocked", "Bloqueado"

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        related_name="onboarding",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    store_name = models.CharField(max_length=150, blank=True)
    store_slug = models.SlugField(max_length=150, blank=True)
    store_subdomain = models.SlugField(max_length=63, blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)
    plan_code = models.SlugField(max_length=80, blank=True)
    coupon_code_snapshot = models.CharField(max_length=64, blank=True)
    coupon_discount_type_snapshot = models.CharField(max_length=16, blank=True)
    coupon_discount_value_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    coupon_discount_total_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    effective_monthly_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promotion_snapshot = models.JSONField(default=dict, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_name = models.CharField(max_length=150, blank=True)
    owner_role = models.CharField(max_length=64, blank=True, default="owner")
    store_display_name = models.CharField(max_length=150, blank=True)
    primary_color = models.CharField(max_length=7, blank=True)
    blockers = models.JSONField(default=list, blank=True)
    created_by_label = models.CharField(max_length=180, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant onboarding"
        verbose_name_plural = "Tenant onboardings"
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=("status", "updated_at"), name="tenant_onboarding_status_idx"),
            models.Index(fields=("store_slug",), name="tenant_onboarding_slug_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.store_name or self.store_slug or self.pk}:{self.status}"
