from __future__ import annotations

from dataclasses import dataclass

from django.db import DatabaseError

from app.modules.accounts.application.owner_mfa_secret_storage_readiness_queries import owner_mfa_secret_storage_readiness_queries
from app.modules.accounts.models import OwnerMfaFactor


@dataclass(frozen=True)
class OwnerMfaLegacyDataTenantSummary:
    tenant_id: int
    status: str
    local_plain_count: int
    external_reference_count: int
    missing_count: int
    blockers: tuple[str, ...]


@dataclass
class OwnerMfaLegacyDataGlobalSweepQueryService:
    def get_sweep(self) -> dict[str, object]:
        try:
            tenant_ids = tuple(
                OwnerMfaFactor.objects.filter(
                    factor_type=OwnerMfaFactor.FactorType.TOTP,
                    is_active=True,
                )
                .values_list("tenant_id", flat=True)
                .distinct()
                .order_by("tenant_id")
            )
        except DatabaseError:
            return {
                "result": "owner-mfa-legacy-data-global-sweep-db-unavailable",
                "ready": False,
                "status": "blocked",
                "tenant_summaries": (),
                "tenant_count": 0,
                "totals": self._totals(()),
                "blockers": ("database-unavailable",),
                "next_tracks": ("Run accounts migrations",),
            }
        summaries = tuple(self._summary(tenant_id=tenant_id) for tenant_id in tenant_ids)
        blockers = []
        for summary in summaries:
            if summary.local_plain_count:
                blockers.append(f"tenant-{summary.tenant_id}:local-plain-factors-present")
            if summary.missing_count:
                blockers.append(f"tenant-{summary.tenant_id}:missing-secret-factors-present")
            for blocker in summary.blockers:
                if "external-secret-unresolved" in blocker:
                    blockers.append(f"tenant-{summary.tenant_id}:external-secret-unresolved")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready"
        if not summaries:
            status = "watch"
        if unique_blockers:
            status = "blocked"
        return {
            "result": f"owner-mfa-legacy-data-global-sweep-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_summaries": summaries,
            "tenant_count": len(summaries),
            "totals": self._totals(summaries),
            "blockers": unique_blockers,
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _summary(self, *, tenant_id: int) -> OwnerMfaLegacyDataTenantSummary:
        readiness = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=tenant_id)
        blockers = tuple(str(blocker) for blocker in readiness.get("blockers", ()))
        local_plain_count = int(readiness.get("local_plain_count", 0))
        missing_count = int(readiness.get("missing_count", 0))
        status = "ready" if not blockers and not local_plain_count and not missing_count else "blocked"
        return OwnerMfaLegacyDataTenantSummary(
            tenant_id=int(tenant_id),
            status=status,
            local_plain_count=local_plain_count,
            external_reference_count=int(readiness.get("external_reference_count", 0)),
            missing_count=missing_count,
            blockers=blockers,
        )

    def _totals(self, summaries: tuple[OwnerMfaLegacyDataTenantSummary, ...]) -> dict[str, int]:
        return {
            "local_plain_count": sum(summary.local_plain_count for summary in summaries),
            "external_reference_count": sum(summary.external_reference_count for summary in summaries),
            "missing_count": sum(summary.missing_count for summary in summaries),
            "blocked_tenant_count": sum(1 for summary in summaries if summary.status == "blocked"),
        }

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "sweep cobre apenas fatores TOTP ativos persistidos",
            "segredos locais em backups, fixtures ou dumps externos ficam fora do banco atual",
            "provider env ainda é adapter mínimo antes de vault/KMS real",
            "remoção do parser local deve aguardar sweep ready em ambiente real",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Local Secret Parser Removal Review",
                "Owner MFA Vault/KMS Provider Review",
            )
        return (
            "Owner MFA Tenant Legacy Cleanup Plan",
            "Owner MFA TOTP Secret Migration Execution Review",
        )


owner_mfa_legacy_data_global_sweep_queries = OwnerMfaLegacyDataGlobalSweepQueryService()
