from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_secret_storage_readiness_queries import owner_mfa_secret_storage_readiness_queries


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class OwnerMfaProviderHealthQueryService:
    def get_health(self, *, tenant_id: int | str | None) -> dict[str, object]:
        readiness = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=tenant_id)
        items = tuple(readiness.get("items", ()))
        external_items = tuple(item for item in items if item.storage_mode == "external-reference")
        unresolved_items = tuple(item for item in external_items if not item.ready)
        local_plain_count = int(readiness.get("local_plain_count", 0))
        missing_count = int(readiness.get("missing_count", 0))
        provider = _string(getattr(settings, "OWNER_MFA_SECRET_PROVIDER", "none"), limit=32).lower() or "none"
        blockers = list(readiness.get("blockers", ()))
        if provider == "none" and external_items:
            blockers.append("provider-not-configured")
        if unresolved_items:
            blockers.append("external-reference-unresolved")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = self._status(
            provider=provider,
            external_count=len(external_items),
            unresolved_count=len(unresolved_items),
            local_plain_count=local_plain_count,
            missing_count=missing_count,
            readiness_ready=bool(readiness.get("ready")),
        )
        return {
            "result": f"owner-mfa-provider-health-{status.lower()}",
            "ready": status == "HEALTHY",
            "status": status,
            "provider": provider,
            "storage_result": readiness.get("result"),
            "external_reference_count": len(external_items),
            "external_reference_unresolved_count": len(unresolved_items),
            "local_plain_count": local_plain_count,
            "missing_count": missing_count,
            "items": items,
            "blockers": unique_blockers,
            "signals": self._signals(
                provider=provider,
                external_count=len(external_items),
                unresolved_count=len(unresolved_items),
                local_plain_count=local_plain_count,
                missing_count=missing_count,
            ),
            "runbook": (
                "1. confirmar OWNER_MFA_SECRET_PROVIDER no ambiente",
                "2. validar que cada ref:<path> possui valor no provider",
                "3. rodar owner_mfa_secret_storage_readiness",
                "4. testar challenge/login MFA de owner afetado",
                "5. se necessário, restaurar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True enquanto provider é corrigido",
            ),
            "next_tracks": (
                "Owner MFA Provider Health Metrics Review",
                "Owner MFA Local Secret Code Retirement Review",
            ),
        }

    def _status(
        self,
        *,
        provider: str,
        external_count: int,
        unresolved_count: int,
        local_plain_count: int,
        missing_count: int,
        readiness_ready: bool,
    ) -> str:
        if missing_count or unresolved_count or (provider == "none" and external_count):
            return "CRITICAL"
        if local_plain_count or not external_count or not readiness_ready:
            return "WATCH"
        return "HEALTHY"

    def _signals(
        self,
        *,
        provider: str,
        external_count: int,
        unresolved_count: int,
        local_plain_count: int,
        missing_count: int,
    ) -> tuple[str, ...]:
        signals = []
        if provider == "none" and external_count:
            signals.append("provider-not-configured")
        if unresolved_count:
            signals.append("external-reference-unresolved")
        if missing_count:
            signals.append("secret-missing")
        if local_plain_count:
            signals.append("local-plain-still-present")
        if not external_count:
            signals.append("no-external-reference-factors")
        return tuple(signals)


owner_mfa_provider_health_queries = OwnerMfaProviderHealthQueryService()
