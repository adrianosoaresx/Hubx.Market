from django.db import models
from django.db.models import Q


class Page(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="pages")
    slug = models.SlugField(max_length=160)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    seo_title = models.CharField(max_length=180, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "title", "id")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "slug"), name="page_unique_slug_per_tenant"),
            models.CheckConstraint(
                check=Q(status__in=("draft", "published")),
                name="page_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "slug"), name="page_tenant_stat_slug_idx"),
            models.Index(fields=("tenant", "updated_at"), name="page_tenant_updated_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.slug}"
