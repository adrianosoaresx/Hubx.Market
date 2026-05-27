from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.application.owner_mfa_local_secret_code_retirement_queries import owner_mfa_local_secret_code_retirement_queries


@dataclass(frozen=True)
class OwnerMfaLocalSecretCodeRetirementExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaLocalSecretCodeRetirementExecutionQueryService:
    def get_evidence(self, *, tenant_id: int | str | None) -> dict[str, object]:
        readiness = owner_mfa_local_secret_code_retirement_queries.get_readiness(tenant_id=tenant_id)
        allow_local_plain = owner_mfa_secret_storage.can_accept_local_plain()
        blockers = list(readiness.get("blockers", ()))
        if allow_local_plain:
            blockers.append("local-secret-default-or-env-enabled")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers and readiness["ready"] else "blocked"
        return {
            "result": f"owner-mfa-local-secret-code-retirement-execution-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "allow_local_plain": allow_local_plain,
            "readiness": readiness,
            "decisions": self._decisions(allow_local_plain=allow_local_plain, readiness=readiness),
            "blockers": unique_blockers,
            "rollback": (
                "definir OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1 no ambiente",
                "reiniciar processos Django/workers do ambiente",
                "rodar owner_mfa_secret_storage_readiness para confirmar fallback local aceito temporariamente",
                "corrigir provider externo e retornar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=0",
            ),
            "next_tracks": (
                "Owner MFA Vault/KMS Provider Review",
                "Owner MFA Legacy Data Global Sweep Review",
                "Owner MFA Incident Runbook Review",
            ),
        }

    def _decisions(
        self,
        *,
        allow_local_plain: bool,
        readiness: dict[str, object],
    ) -> tuple[OwnerMfaLocalSecretCodeRetirementExecutionDecision, ...]:
        return (
            OwnerMfaLocalSecretCodeRetirementExecutionDecision(
                key="default-local-secret-disabled",
                status="ready" if not allow_local_plain else "blocked",
                summary="default de OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET agora é desabilitado; env explícito pode rollbackar",
            ),
            OwnerMfaLocalSecretCodeRetirementExecutionDecision(
                key="readiness",
                status=str(readiness["status"]),
                summary="readiness tenant-scoped precisa estar ready para confirmar a execution",
            ),
            OwnerMfaLocalSecretCodeRetirementExecutionDecision(
                key="rollback",
                status="available",
                summary="rollback permanece por env OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1, não por retorno do default inseguro",
            ),
        )


owner_mfa_local_secret_code_retirement_execution_queries = OwnerMfaLocalSecretCodeRetirementExecutionQueryService()
