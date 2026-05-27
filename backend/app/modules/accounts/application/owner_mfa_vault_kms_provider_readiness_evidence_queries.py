from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_provider_health_closure_queries import owner_mfa_provider_health_closure_queries
from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries import (
    owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries,
)


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderReadinessEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderReadinessEvidenceQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/skeleton-probe",
    ) -> dict[str, object]:
        normalized_tenant_id = _string(tenant_id, limit=64)
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        normalized_probe = _string(probe_reference, limit=255)
        skeleton = owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=normalized_tenant_id,
            target_provider=normalized_target,
            probe_reference=normalized_probe,
        )
        health_closure = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=normalized_tenant_id)
        blockers = list(skeleton.get("blockers", ()))
        if not normalized_tenant_id:
            blockers.append("tenant-required")
        if not skeleton.get("ready"):
            blockers.append("skeleton-execution-not-ready")
        if health_closure["status"] == "blocked":
            blockers.append("provider-health-closure-blocked")
        if health_closure["status"] == "watch":
            blockers.append("provider-health-closure-watch")
        if health_closure["provider_health"]["provider"] != normalized_target:
            blockers.append("provider-health-target-mismatch")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-readiness-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": normalized_tenant_id,
            "target_provider": normalized_target,
            "probe_reference": normalized_probe,
            "skeleton_execution": skeleton,
            "provider_health_closure": health_closure,
            "decisions": self._decisions(skeleton=skeleton, health_closure=health_closure, target_provider=normalized_target),
            "blockers": unique_blockers,
            "evidence_pack": self._evidence_pack(skeleton=skeleton, health_closure=health_closure),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        skeleton: dict[str, object],
        health_closure: dict[str, object],
        target_provider: str,
    ) -> tuple[OwnerMfaVaultKmsProviderReadinessEvidenceDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderReadinessEvidenceDecision(
                key="skeleton-execution",
                status=str(skeleton.get("status", "blocked")),
                summary="probe do skeleton deve resolver pelo target provider sem fallback automático",
            ),
            OwnerMfaVaultKmsProviderReadinessEvidenceDecision(
                key="provider-health-closure",
                status=str(health_closure.get("status", "blocked")),
                summary="health closure tenant-scoped precisa estar ready para pacote canário",
            ),
            OwnerMfaVaultKmsProviderReadinessEvidenceDecision(
                key="target-provider",
                status="ready" if health_closure["provider_health"]["provider"] == target_provider else "blocked",
                summary="provider observado no health precisa bater com o target da evidência",
            ),
            OwnerMfaVaultKmsProviderReadinessEvidenceDecision(
                key="secret-exposure",
                status="guarded",
                summary="evidence pack não inclui valor do segredo nem reference path completo em métricas",
            ),
        )

    def _evidence_pack(self, *, skeleton: dict[str, object], health_closure: dict[str, object]) -> tuple[str, ...]:
        provider_health = health_closure["provider_health"]
        probe = skeleton["probe"]
        return (
            f"skeleton_status={skeleton['status']}",
            f"probe_result={probe['result']}",
            f"probe_ready={probe['ready']}",
            f"probe_secret_returned={probe['secret_returned']}",
            f"health_status={provider_health['status']}",
            f"health_provider={provider_health['provider']}",
            f"external_reference_count={provider_health['external_reference_count']}",
            f"external_reference_unresolved_count={provider_health['external_reference_unresolved_count']}",
            f"local_plain_count={provider_health['local_plain_count']}",
            f"missing_count={provider_health['missing_count']}",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter OWNER_MFA_SECRET_PROVIDER para env se refs equivalentes existirem",
            "rodar owner_mfa_vault_kms_provider_adapter_skeleton_execute para confirmar rollback do probe",
            "rodar owner_mfa_provider_health_closure para o tenant canário",
            "não reativar parser local/plain como rollback da evidência",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Staging Canary Review",
                "Owner MFA Vault/KMS Provider Real Adapter Contract Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Adapter Skeleton Execution",
            "Owner MFA Provider Health Closure Review",
        )


owner_mfa_vault_kms_provider_readiness_evidence_queries = OwnerMfaVaultKmsProviderReadinessEvidenceQueryService()
