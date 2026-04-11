from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    subdomain = models.SlugField(max_length=63, unique=True)
    custom_domain = models.CharField(max_length=255, null=True, blank=True)
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