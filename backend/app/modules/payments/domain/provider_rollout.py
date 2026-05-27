from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


def _string(value: object) -> str:
    return str(value or "").strip()


def _tenant_allowlist(value: object) -> set[str]:
    if isinstance(value, str):
        return {item.strip().lower() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set)):
        return {_string(item).lower() for item in value if _string(item)}
    return set()


@dataclass(frozen=True)
class ProviderRolloutDecision:
    allow_real_provider: bool
    fallback_mode: str
    rollout_mode: str
    reason_code: str


def decide_provider_rollout(*, provider_code: str, tenant=None) -> ProviderRolloutDecision:
    normalized_provider = _string(provider_code).lower()
    fallback_mode = _string(getattr(settings, "PAYMENTS_REAL_PROVIDER_FALLBACK_MODE", "lite")).lower() or "lite"
    rollout_mode = _string(getattr(settings, "PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE", "sandbox")).lower() or "sandbox"
    live_global_enabled = bool(getattr(settings, "PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED", False))

    if normalized_provider != "pagarme":
        return ProviderRolloutDecision(False, fallback_mode, rollout_mode, "provider-lite-only")

    if rollout_mode == "sandbox":
        return ProviderRolloutDecision(True, fallback_mode, rollout_mode, f"{rollout_mode}-enabled")

    if rollout_mode == "live":
        if live_global_enabled:
            return ProviderRolloutDecision(True, fallback_mode, rollout_mode, "live-global-enabled")
        return ProviderRolloutDecision(False, fallback_mode, rollout_mode, "live-global-not-enabled")

    if rollout_mode == "off":
        return ProviderRolloutDecision(False, fallback_mode, rollout_mode, "rollout-disabled")

    enabled_tenants = _tenant_allowlist(getattr(settings, "PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS", []))
    tenant_slug = _string(getattr(tenant, "slug", "")).lower()
    tenant_subdomain = _string(getattr(tenant, "subdomain", "")).lower()
    if tenant_slug in enabled_tenants or tenant_subdomain in enabled_tenants:
        return ProviderRolloutDecision(True, fallback_mode, rollout_mode, "tenant-allowlisted")
    return ProviderRolloutDecision(False, fallback_mode, rollout_mode, "tenant-not-allowlisted")
