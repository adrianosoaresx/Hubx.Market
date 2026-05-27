from __future__ import annotations

from dataclasses import dataclass

from django.db import DatabaseError

from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor


@dataclass(frozen=True)
class OwnerMfaSecretStorageItem:
    factor_id: int
    owner_id: int
    owner_email: str
    storage_mode: str
    ready: bool
    result: str


@dataclass
class OwnerMfaSecretStorageReadinessQueryService:
    def get_readiness(self, *, tenant_id: int | str | None) -> dict[str, object]:
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return {
                "result": "owner-mfa-secret-storage-tenant-required",
                "ready": False,
                "items": (),
                "blockers": ("tenant-required",),
            }
        factors = OwnerMfaFactor.objects.filter(
            tenant_id=normalized_tenant_id,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            is_active=True,
        ).select_related("owner").order_by("owner__email", "id")
        try:
            items = tuple(self._item(factor) for factor in factors)
        except DatabaseError:
            return {
                "result": "owner-mfa-secret-storage-db-unavailable",
                "ready": False,
                "allow_local_plain": owner_mfa_secret_storage.can_accept_local_plain(),
                "items": (),
                "local_plain_count": 0,
                "external_reference_count": 0,
                "missing_count": 0,
                "blockers": ("database-unavailable",),
                "next_tracks": ("Run accounts migrations",),
            }
        blockers = []
        for item in items:
            if item.storage_mode == "missing":
                blockers.append(f"factor-{item.factor_id}:secret-missing")
            if item.storage_mode == "external-reference" and not item.ready:
                blockers.append(f"factor-{item.factor_id}:external-secret-unresolved")
            if item.storage_mode in {"local-plain", "unsupported-local"}:
                blockers.append(f"factor-{item.factor_id}:local-secret-unsupported")
        return {
            "result": "owner-mfa-secret-storage-ready" if not blockers else "owner-mfa-secret-storage-blocked",
            "ready": not blockers,
            "allow_local_plain": owner_mfa_secret_storage.can_accept_local_plain(),
            "items": items,
            "local_plain_count": sum(1 for item in items if item.storage_mode in {"local-plain", "unsupported-local"}),
            "external_reference_count": sum(1 for item in items if item.storage_mode == "external-reference"),
            "missing_count": sum(1 for item in items if item.storage_mode == "missing"),
            "blockers": tuple(blockers),
            "next_tracks": (
                "Owner MFA External Secret Provider Adapter Review",
                "Owner MFA TOTP Secret Migration Plan",
            ),
        }

    def _item(self, factor: OwnerMfaFactor) -> OwnerMfaSecretStorageItem:
        resolution = owner_mfa_secret_storage.resolve(factor.secret_reference)
        return OwnerMfaSecretStorageItem(
            factor_id=factor.id,
            owner_id=factor.owner_id,
            owner_email=factor.owner.email,
            storage_mode=resolution.storage_mode,
            ready=resolution.ready,
            result=resolution.result,
        )


owner_mfa_secret_storage_readiness_queries = OwnerMfaSecretStorageReadinessQueryService()
