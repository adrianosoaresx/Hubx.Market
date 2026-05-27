from django.db import models
from django.db.models import Q


class NewsletterSubscriber(models.Model):
    class Status(models.TextChoices):
        SUBSCRIBED = "subscribed", "Inscrito"
        UNSUBSCRIBED = "unsubscribed", "Descadastrado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="newsletter_subscribers")
    email = models.EmailField(max_length=254)
    name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBSCRIBED)
    source = models.CharField(max_length=80, blank=True)
    consent_label = models.CharField(max_length=180, blank=True)
    consented_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-updated_at", "email")
        constraints = [
            models.UniqueConstraint(fields=("tenant", "email"), name="newsletter_unique_email_per_tenant"),
            models.CheckConstraint(
                check=Q(status__in=("subscribed", "unsubscribed")),
                name="newsletter_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "updated_at"), name="newsletter_tenant_status_idx"),
            models.Index(fields=("tenant", "email"), name="newsletter_tenant_email_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.email}:{self.status}"
