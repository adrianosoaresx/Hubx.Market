from __future__ import annotations

from django.db import models


class Shipment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Criado"
        SENT = "sent", "Enviado"
        DELIVERED = "delivered", "Entregue"
        CANCELED = "canceled", "Cancelado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="shipments")
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="shipment")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED)
    tracking_code = models.CharField(max_length=120, blank=True)
    tracking_url = models.URLField(blank=True)
    carrier_name = models.CharField(max_length=120, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "-created_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "status"), name="ship_tenant_status_idx"),
            models.Index(fields=("tenant", "tracking_code"), name="ship_tenant_tracking_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.order_id}:{self.status}"


class ShipmentStatusHistory(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="history_entries")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="shipment_status_history")
    event_type = models.CharField(max_length=64)
    source_type = models.CharField(max_length=64, blank=True)
    source_label = models.CharField(max_length=120, blank=True)
    actor_label = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    provider_http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    provider_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "event_type"), name="ship_hist_tenant_event_idx"),
            models.Index(fields=("shipment", "-created_at"), name="ship_hist_shipment_time_idx"),
            models.Index(fields=("tenant", "provider_http_status"), name="ship_hist_provider_http_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.shipment_id}:{self.event_type}"


class ShippingProviderSettings(models.Model):
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.CASCADE, related_name="shipping_provider_settings")
    provider_name = models.CharField(max_length=80, default="manual")
    base_url = models.URLField(blank=True)
    api_token = models.CharField(max_length=255, blank=True)
    timeout_seconds = models.DecimalField(max_digits=4, decimal_places=2, default=3)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id",)
        indexes = [
            models.Index(fields=("tenant", "is_active"), name="ship_provider_active_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.provider_name}:{self.is_active}"


class ShippingProviderSettingsHistory(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="shipping_provider_settings_history")
    settings = models.ForeignKey(
        ShippingProviderSettings,
        on_delete=models.CASCADE,
        related_name="history_entries",
    )
    event_type = models.CharField(max_length=64)
    source_type = models.CharField(max_length=64, blank=True)
    source_label = models.CharField(max_length=120, blank=True)
    actor_label = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "event_type"), name="ship_provider_hist_event_idx"),
            models.Index(fields=("settings", "-created_at"), name="ship_provider_hist_time_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.settings_id}:{self.event_type}"
