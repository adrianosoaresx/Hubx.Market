from django.db import models


class EmailLog(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planejado"
        REQUESTED = "requested", "Solicitado"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"
        SKIPPED = "skipped", "Ignorado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="email_logs")
    source_event = models.CharField(max_length=64)
    intent_key = models.CharField(max_length=120)
    audience = models.CharField(max_length=32)
    channel = models.CharField(max_length=32, default="email")
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=120)
    idempotency_key = models.CharField(max_length=255)
    recipient_delivery_key = models.CharField(max_length=255, unique=True)
    recipient_type = models.CharField(max_length=64)
    recipient_id = models.CharField(max_length=120)
    recipient_email = models.EmailField()
    recipient_display_name = models.CharField(max_length=150, blank=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cta_label = models.CharField(max_length=80, blank=True)
    cta_target = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    requested_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "status"), name="email_logs_tenant_status_idx"),
            models.Index(fields=("tenant", "source_event"), name="email_logs_tenant_event_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.intent_key}:{self.status}"
