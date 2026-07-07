from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.modules.accounts.application.admin_permissions import PERMISSION_SHIPPING_MANAGE, admin_permissions


@dataclass(frozen=True)
class AdminProviderSettingsItem:
    provider_name: str
    base_url: str
    timeout_seconds: str
    is_active: bool
    mode_label: str
    token_configured: bool
    history_summary: tuple[str, ...]


class DjangoOrmAdminProviderSettingsRepository:
    def __init__(self) -> None:
        try:
            from app.modules.shipping.models import ShippingProviderSettings
        except Exception:
            self.settings_model = None
            return
        self.settings_model = ShippingProviderSettings

    def get_settings(self, *, tenant_id: int | str):
        if self.settings_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        return self.settings_model._default_manager.filter(tenant_id=normalized_tenant_id).first()

    def upsert_settings(
        self,
        *,
        tenant_id: int | str,
        provider_name: str,
        base_url: str,
        api_token: str,
        timeout_seconds: Decimal,
        is_active: bool,
    ):
        if self.settings_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        settings = self.get_settings(tenant_id=normalized_tenant_id)
        if settings is None:
            settings = self.settings_model(tenant_id=normalized_tenant_id)
        settings.provider_name = provider_name
        settings.base_url = base_url
        if api_token:
            settings.api_token = api_token
        settings.timeout_seconds = timeout_seconds
        settings.is_active = is_active
        settings.save()
        return settings


@dataclass
class AdminProviderSettingsService:
    repository: DjangoOrmAdminProviderSettingsRepository

    @staticmethod
    def _write_guard(*, tenant_id: int | str, actor_role: str) -> str:
        if not str(tenant_id or "").strip():
            return "provider-settings-tenant-missing"
        normalized_role = str(actor_role or "").strip()
        if not normalized_role:
            return "provider-settings-permission-denied"
        if not admin_permissions.check(role=normalized_role, permission=PERMISSION_SHIPPING_MANAGE).allowed:
            return "provider-settings-permission-denied"
        return ""

    def get_settings_item(self, *, tenant_id: int | str) -> AdminProviderSettingsItem:
        settings = self.repository.get_settings(tenant_id=tenant_id)
        if settings is None:
            return AdminProviderSettingsItem(
                provider_name="manual",
                base_url="",
                timeout_seconds="3.00",
                is_active=False,
                mode_label="Manual/local",
                token_configured=False,
                history_summary=(),
            )
        provider_name = str(settings.provider_name or "manual")
        return AdminProviderSettingsItem(
            provider_name=provider_name,
            base_url=str(settings.base_url or ""),
            timeout_seconds=f"{settings.timeout_seconds:.2f}",
            is_active=bool(settings.is_active),
            mode_label="HTTP ativo" if provider_name == "http" and settings.is_active and settings.base_url else "Manual/local",
            token_configured=bool(settings.api_token),
            history_summary=self._history_summary(settings),
        )

    def update_settings(
        self,
        *,
        tenant_id: int | str,
        provider_name: str,
        base_url: str,
        api_token: str,
        timeout_seconds: str,
        is_active: bool,
        actor_role: str = "",
    ) -> str:
        guard_result = self._write_guard(tenant_id=tenant_id, actor_role=actor_role)
        if guard_result:
            return guard_result
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return "provider-settings-tenant-missing"
        normalized_provider = str(provider_name or "manual").strip().lower()
        if normalized_provider not in {"manual", "http"}:
            return "provider-settings-invalid-provider"
        normalized_base_url = str(base_url or "").strip()
        if normalized_provider == "http" and is_active and not normalized_base_url:
            return "provider-settings-base-url-required"
        try:
            normalized_timeout = Decimal(str(timeout_seconds or "3"))
        except InvalidOperation:
            return "provider-settings-timeout-invalid"
        if normalized_timeout <= 0:
            return "provider-settings-timeout-invalid"
        settings = self.repository.upsert_settings(
            tenant_id=normalized_tenant_id,
            provider_name=normalized_provider,
            base_url=normalized_base_url,
            api_token=str(api_token or "").strip(),
            timeout_seconds=normalized_timeout,
            is_active=bool(is_active),
        )
        if settings is None:
            return "provider-settings-unavailable"
        self._create_history_entry(settings=settings)
        return "provider-settings-updated"

    def _history_summary(self, settings) -> tuple[str, ...]:
        try:
            entries = settings.history_entries.all()[:3]
        except Exception:
            return ()
        return tuple(f"{entry.title} · {entry.created_at.strftime('%d/%m/%Y %H:%M')}" for entry in entries)

    def _create_history_entry(self, *, settings) -> None:
        try:
            from app.modules.shipping.models import ShippingProviderSettingsHistory
        except Exception:
            return
        mode = "ativo" if settings.is_active else "inativo"
        ShippingProviderSettingsHistory.objects.create(
            tenant_id=settings.tenant_id,
            settings=settings,
            event_type="provider_settings_updated",
            source_type="admin_action",
            source_label="Shipping Provider Settings",
            actor_label="Operação interna",
            title="Provider atualizado",
            description=f"Provider {settings.provider_name} salvo como {mode}.",
        )


admin_provider_settings = AdminProviderSettingsService(repository=DjangoOrmAdminProviderSettingsRepository())
