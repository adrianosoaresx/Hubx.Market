from __future__ import annotations

from dataclasses import dataclass

from app.modules.shipping.application.shipping_provider_contracts import (
    ShippingProviderGateway,
    manual_shipment_provider_gateway,
)
from app.modules.shipping.infrastructure.http_tracking_provider import HttpTrackingProviderGateway


class DjangoOrmShippingProviderSettingsRepository:
    def __init__(self) -> None:
        try:
            from app.modules.shipping.models import ShippingProviderSettings
        except Exception:
            self.settings_model = None
            return
        self.settings_model = ShippingProviderSettings

    def get_active_settings(self, *, tenant_id: int | str):
        if self.settings_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        try:
            return self.settings_model._default_manager.filter(
                tenant_id=normalized_tenant_id,
                is_active=True,
            ).first()
        except Exception:
            return None


@dataclass
class ShippingProviderSettingsService:
    repository: DjangoOrmShippingProviderSettingsRepository

    def get_gateway_for_tenant(self, *, tenant_id: int | str) -> ShippingProviderGateway:
        settings = self.repository.get_active_settings(tenant_id=tenant_id)
        if settings is None:
            return manual_shipment_provider_gateway
        provider_name = str(getattr(settings, "provider_name", "") or "").strip().lower()
        base_url = str(getattr(settings, "base_url", "") or "").strip()
        if provider_name != "http" or not base_url:
            return manual_shipment_provider_gateway
        return HttpTrackingProviderGateway(
            base_url=base_url,
            token=str(getattr(settings, "api_token", "") or ""),
            timeout_seconds=float(getattr(settings, "timeout_seconds", 3) or 3),
        )


shipping_provider_settings = ShippingProviderSettingsService(
    repository=DjangoOrmShippingProviderSettingsRepository(),
)
