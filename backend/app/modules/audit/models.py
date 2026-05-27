from django.db import models


class AuditLog(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    module = models.CharField(max_length=80)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120, blank=True)
    entity_id = models.CharField(max_length=120, blank=True)
    actor_label = models.CharField(max_length=180, blank=True)
    summary = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "created_at"), name="audit_tenant_created_idx"),
            models.Index(fields=("tenant", "module", "action"), name="audit_tenant_mod_action_idx"),
            models.Index(fields=("module", "action", "created_at"), name="audit_mod_action_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        scope = self.tenant_id if self.tenant_id else "platform"
        return f"{scope}:{self.module}:{self.action}"
