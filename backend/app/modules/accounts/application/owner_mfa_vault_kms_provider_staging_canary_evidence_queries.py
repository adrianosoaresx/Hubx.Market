from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_staging_canary_queries import (
    owner_mfa_vault_kms_provider_staging_canary_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "sim", "ok", "passed", "pass"}


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderStagingCanaryEvidenceQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/skeleton-probe",
        canary_owner_email: object = "",
        valid_login_passed: object = False,
        invalid_challenge_blocked: object = False,
        post_health_ready: object = False,
        logs_redacted: object = False,
        rollback_verified: object = False,
        evidence_label: object = "staging-canary",
    ) -> dict[str, object]:
        normalized_label = _string(evidence_label, limit=120) or "staging-canary"
        canary = owner_mfa_vault_kms_provider_staging_canary_queries.get_review(
            tenant_id=tenant_id,
            target_provider=target_provider,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
        )
        checks = {
            "valid_login_passed": _bool(valid_login_passed),
            "invalid_challenge_blocked": _bool(invalid_challenge_blocked),
            "post_health_ready": _bool(post_health_ready),
            "logs_redacted": _bool(logs_redacted),
            "rollback_verified": _bool(rollback_verified),
        }
        blockers = list(canary.get("blockers", ()))
        if not canary.get("ready"):
            blockers.append("staging-canary-review-not-ready")
        for key, passed in checks.items():
            if not passed:
                blockers.append(f"manual-check-failed:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-staging-canary-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": canary["tenant_id"],
            "target_provider": canary["target_provider"],
            "probe_reference": canary["probe_reference"],
            "canary_owner_email": canary["canary_owner_email"],
            "evidence_label": normalized_label,
            "canary_review": canary,
            "manual_results": checks,
            "decisions": self._decisions(canary=canary, checks=checks),
            "blockers": unique_blockers,
            "evidence_pack": self._evidence_pack(canary=canary, checks=checks, evidence_label=normalized_label),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        canary: dict[str, object],
        checks: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="canary-review",
                status=str(canary.get("status", "blocked")),
                summary="evidência de execução só é Go quando a review do canário está ready",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="valid-login",
                status="passed" if checks["valid_login_passed"] else "blocked",
                summary="login owner/admin com TOTP válido deve concluir sessão efetiva",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="invalid-challenge",
                status="passed" if checks["invalid_challenge_blocked"] else "blocked",
                summary="challenge inválido deve permanecer bloqueado sem sessão efetiva",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="post-health",
                status="passed" if checks["post_health_ready"] else "blocked",
                summary="provider health/readiness deve permanecer saudável após o teste manual",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="secret-exposure",
                status="passed" if checks["logs_redacted"] else "blocked",
                summary="logs/comandos não devem conter segredo, código TOTP ou reference path completo",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryEvidenceDecision(
                key="rollback",
                status="passed" if checks["rollback_verified"] else "blocked",
                summary="rollback documentado deve ter sido verificado ou simulado antes de avançar",
            ),
        )

    def _evidence_pack(
        self,
        *,
        canary: dict[str, object],
        checks: dict[str, bool],
        evidence_label: str,
    ) -> tuple[str, ...]:
        return (
            f"evidence_label={evidence_label}",
            f"canary_status={canary['status']}",
            f"target_provider={canary['target_provider']}",
            f"valid_login_passed={checks['valid_login_passed']}",
            f"invalid_challenge_blocked={checks['invalid_challenge_blocked']}",
            f"post_health_ready={checks['post_health_ready']}",
            f"logs_redacted={checks['logs_redacted']}",
            f"rollback_verified={checks['rollback_verified']}",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter OWNER_MFA_SECRET_PROVIDER para env se o canário degradar",
            "limpar sessão do owner canário",
            "rodar readiness evidence e provider health closure após rollback",
            "não reativar parser local/plain",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Real Adapter Contract Review",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Staging Canary Review",
            "Owner MFA Vault/KMS Provider Readiness Evidence Review",
        )


owner_mfa_vault_kms_provider_staging_canary_evidence_queries = OwnerMfaVaultKmsProviderStagingCanaryEvidenceQueryService()
