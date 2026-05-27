from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_staging_smoke_evidence_queries import (
    owner_mfa_hashicorp_vault_staging_smoke_evidence_queries,
)
from app.modules.accounts.application.owner_mfa_provider_health_closure_queries import (
    owner_mfa_provider_health_closure_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderProductionReadinessDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderProductionReadinessQueryService:
    confirmations = (
        "runbook_reviewed",
        "rollback_owner_confirmed",
        "monitoring_confirmed",
        "change_window_confirmed",
        "credential_rotation_confirmed",
    )

    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        runbook_reviewed: bool = False,
        rollback_owner_confirmed: bool = False,
        monitoring_confirmed: bool = False,
        change_window_confirmed: bool = False,
        credential_rotation_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        smoke = owner_mfa_hashicorp_vault_staging_smoke_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            staging_probe_passed=True,
            invalid_path_blocked=True,
            logs_redacted=True,
            rollback_verified=True,
            post_smoke_health_ready=True,
        )
        health_closure = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=tenant_id)
        confirmation_values = {
            "runbook_reviewed": bool(runbook_reviewed),
            "rollback_owner_confirmed": bool(rollback_owner_confirmed),
            "monitoring_confirmed": bool(monitoring_confirmed),
            "change_window_confirmed": bool(change_window_confirmed),
            "credential_rotation_confirmed": bool(credential_rotation_confirmed),
        }
        blockers = list(smoke.get("blockers", ()))
        if not smoke.get("ready"):
            blockers.append("hashicorp-vault-staging-smoke-not-ready")
        if health_closure.get("status") != "ready":
            blockers.append(f"provider-health-closure:{health_closure.get('status', 'blocked')}")
            blockers.extend(str(blocker) for blocker in health_closure.get("blockers", ()))
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-production-readiness-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": smoke["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": smoke["canary_owner_email"],
            "smoke_evidence": smoke,
            "provider_health_closure": health_closure,
            "confirmations": confirmation_values,
            "go_no_go": self._go_no_go(status=status, blockers=unique_blockers),
            "runbook": self._runbook(),
            "rollback": self._rollback(),
            "decisions": self._decisions(
                smoke=smoke,
                health_closure=health_closure,
                confirmations=confirmation_values,
            ),
            "blockers": unique_blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _go_no_go(self, *, status: str, blockers: tuple[str, ...]) -> dict[str, object]:
        return {
            "decision": "GO" if status == "ready" else "NO-GO",
            "production_allowed": status == "ready",
            "blocker_count": len(blockers),
        }

    def _runbook(self) -> tuple[str, ...]:
        return (
            "1. confirmar hvac instalado e versão fixada no release candidate",
            "2. aplicar flags do provider em staging antes de produção",
            "3. rodar smoke evidence e provider health closure no tenant canário",
            "4. habilitar produção em janela controlada por tenant",
            "5. monitorar métricas owner MFA provider health e login/challenge owner",
            "6. se houver falha, desligar endpoint Hashicorp Vault e SDK adapter",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se o SDK afetar login/challenge",
            "rotacionar token/AppRole se redaction ou operação indicar exposição",
            "não reativar parser local/plain como fallback de produção",
            "reexecutar health closure após rollback",
        )

    def _decisions(
        self,
        *,
        smoke: dict[str, object],
        health_closure: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderProductionReadinessDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderProductionReadinessDecision(
                key="staging-smoke",
                status=str(smoke.get("status", "blocked")),
                summary="produção só segue se o smoke staging Hashicorp Vault está ready",
            ),
            OwnerMfaVaultKmsProviderProductionReadinessDecision(
                key="provider-health",
                status=str(health_closure.get("status", "blocked")),
                summary="provider health closure precisa estar ready com artefatos de observabilidade presentes",
            ),
            OwnerMfaVaultKmsProviderProductionReadinessDecision(
                key="monitoring-runbook",
                status="ready" if confirmations["monitoring_confirmed"] and confirmations["runbook_reviewed"] else "blocked",
                summary="monitoramento e runbook precisam estar confirmados antes do Go",
            ),
            OwnerMfaVaultKmsProviderProductionReadinessDecision(
                key="rollback-change-window",
                status=(
                    "ready"
                    if confirmations["rollback_owner_confirmed"] and confirmations["change_window_confirmed"]
                    else "blocked"
                ),
                summary="rollback owner e janela de mudança precisam estar definidos",
            ),
            OwnerMfaVaultKmsProviderProductionReadinessDecision(
                key="credential-rotation",
                status="ready" if confirmations["credential_rotation_confirmed"] else "blocked",
                summary="plano de rotação de token/AppRole precisa existir antes da ativação",
            ),
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Production Gate Review",
                "Owner MFA Vault/KMS Provider Production Activation Evidence",
            )
        return (
            "Owner MFA Hashicorp Vault Staging Smoke Evidence",
            "Owner MFA Provider Health Closure Review",
        )


owner_mfa_vault_kms_provider_production_readiness_queries = OwnerMfaVaultKmsProviderProductionReadinessQueryService()
