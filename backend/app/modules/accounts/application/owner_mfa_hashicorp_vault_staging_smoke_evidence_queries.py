from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_real_endpoint_execution_queries import (
    owner_mfa_hashicorp_vault_real_endpoint_execution_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultStagingSmokeEvidenceQueryService:
    confirmations = (
        "staging_probe_passed",
        "invalid_path_blocked",
        "logs_redacted",
        "rollback_verified",
        "post_smoke_health_ready",
    )

    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        staging_probe_passed: bool = False,
        invalid_path_blocked: bool = False,
        logs_redacted: bool = False,
        rollback_verified: bool = False,
        post_smoke_health_ready: bool = False,
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        execution = owner_mfa_hashicorp_vault_real_endpoint_execution_queries.get_evidence(
            tenant_id=tenant_id,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
        )
        confirmation_values = {
            "staging_probe_passed": bool(staging_probe_passed),
            "invalid_path_blocked": bool(invalid_path_blocked),
            "logs_redacted": bool(logs_redacted),
            "rollback_verified": bool(rollback_verified),
            "post_smoke_health_ready": bool(post_smoke_health_ready),
        }
        blockers = list(execution.get("blockers", ()))
        if not execution.get("ready"):
            blockers.append("hashicorp-vault-real-endpoint-execution-not-ready")
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-staging-smoke-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": execution["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": execution["canary_owner_email"],
            "execution": execution,
            "confirmations": confirmation_values,
            "evidence_pack": self._evidence_pack(execution=execution, confirmations=confirmation_values),
            "decisions": self._decisions(execution=execution, confirmations=confirmation_values),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _evidence_pack(self, *, execution: dict[str, object], confirmations: dict[str, bool]) -> tuple[str, ...]:
        probe = execution.get("probe", {})
        return (
            f"execution_status={execution.get('status', 'blocked')}",
            f"probe_result={probe.get('result', 'unknown')}",
            f"staging_probe_passed={confirmations['staging_probe_passed']}",
            f"invalid_path_blocked={confirmations['invalid_path_blocked']}",
            f"logs_redacted={confirmations['logs_redacted']}",
            f"rollback_verified={confirmations['rollback_verified']}",
            f"post_smoke_health_ready={confirmations['post_smoke_health_ready']}",
        )

    def _decisions(
        self,
        *,
        execution: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision, ...]:
        return (
            OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision(
                key="real-endpoint-execution",
                status=str(execution.get("status", "blocked")),
                summary="smoke staging só segue quando a execution Hashicorp Vault está ready",
            ),
            OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision(
                key="staging-probe",
                status="ready" if confirmations["staging_probe_passed"] else "blocked",
                summary="probe staging precisa ter resolvido o segredo sem expor valor",
            ),
            OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision(
                key="negative-path",
                status="ready" if confirmations["invalid_path_blocked"] else "blocked",
                summary="path inválido precisa falhar fechado antes de chamar Vault",
            ),
            OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision(
                key="redaction",
                status="ready" if confirmations["logs_redacted"] else "blocked",
                summary="stdout/logs/evidence não podem conter segredo, token ou path completo",
            ),
            OwnerMfaHashicorpVaultStagingSmokeEvidenceDecision(
                key="rollback-health",
                status=(
                    "ready"
                    if confirmations["rollback_verified"] and confirmations["post_smoke_health_ready"]
                    else "blocked"
                ),
                summary="rollback e health pós-smoke precisam estar confirmados antes de produção",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se smoke afetar login/challenge",
            "rotacionar token/AppRole se houver suspeita de exposição",
            "manter parser local/plain aposentado; rollback não deve reintroduzir segredo local",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Production Readiness Review",
                "Owner MFA Hashicorp Vault Production Gate Review",
            )
        return (
            "Owner MFA Hashicorp Vault Real Endpoint Execution",
            "Owner MFA Vault/KMS Provider Real Endpoint Review",
        )


owner_mfa_hashicorp_vault_staging_smoke_evidence_queries = OwnerMfaHashicorpVaultStagingSmokeEvidenceQueryService()
