from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_readiness_evidence_queries import (
    owner_mfa_vault_kms_provider_readiness_evidence_queries,
)


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderStagingCanaryDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderStagingCanaryQueryService:
    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/skeleton-probe",
        canary_owner_email: object = "",
    ) -> dict[str, object]:
        normalized_tenant_id = _string(tenant_id, limit=64)
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        normalized_probe = _string(probe_reference, limit=255)
        normalized_owner_email = _string(canary_owner_email, limit=255).lower()
        readiness = owner_mfa_vault_kms_provider_readiness_evidence_queries.get_evidence(
            tenant_id=normalized_tenant_id,
            target_provider=normalized_target,
            probe_reference=normalized_probe,
        )
        blockers = list(readiness.get("blockers", ()))
        if not readiness.get("ready"):
            blockers.append("readiness-evidence-not-ready")
        if not normalized_owner_email:
            blockers.append("canary-owner-email-required")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-staging-canary-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": normalized_tenant_id,
            "target_provider": normalized_target,
            "probe_reference": normalized_probe,
            "canary_owner_email": normalized_owner_email,
            "readiness_evidence": readiness,
            "decisions": self._decisions(readiness=readiness, canary_owner_email=normalized_owner_email),
            "blockers": unique_blockers,
            "preflight": self._preflight(),
            "manual_checklist": self._manual_checklist(),
            "success_signals": self._success_signals(),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        readiness: dict[str, object],
        canary_owner_email: str,
    ) -> tuple[OwnerMfaVaultKmsProviderStagingCanaryDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderStagingCanaryDecision(
                key="readiness-evidence",
                status=str(readiness.get("status", "blocked")),
                summary="canário staging só pode seguir quando readiness evidence está ready",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryDecision(
                key="canary-owner",
                status="ready" if canary_owner_email else "blocked",
                summary="canário precisa de owner/admin explícito para login/challenge manual",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryDecision(
                key="execution-mode",
                status="manual-checklist",
                summary="esta wave não executa login real; entrega checklist e Go/No-Go",
            ),
            OwnerMfaVaultKmsProviderStagingCanaryDecision(
                key="secret-exposure",
                status="guarded",
                summary="checklist não deve coletar segredo, código TOTP ou reference path completo",
            ),
        )

    def _preflight(self) -> tuple[str, ...]:
        return (
            "staging com tenant canário isolado e owner/admin ativo",
            "OWNER_MFA_SECRET_PROVIDER apontando para target provider",
            "readiness evidence pronta para o mesmo tenant/probe",
            "observabilidade de provider health disponível",
            "rollback para env documentado antes do teste manual",
        )

    def _manual_checklist(self) -> tuple[str, ...]:
        return (
            "1. confirmar sessão limpa do owner canário",
            "2. autenticar senha do owner/admin canário",
            "3. completar challenge MFA TOTP uma vez",
            "4. validar redirecionamento para /ops/ e ausência de pending MFA",
            "5. repetir tentativa com código inválido e confirmar bloqueio",
            "6. rodar readiness evidence novamente após o teste",
        )

    def _success_signals(self) -> tuple[str, ...]:
        return (
            "login owner/admin canário conclui com MFA válido",
            "código inválido não cria sessão efetiva",
            "provider health permanece HEALTHY",
            "external_reference_unresolved_count permanece 0",
            "logs/comandos não exibem segredo ou código TOTP",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter OWNER_MFA_SECRET_PROVIDER para env se refs equivalentes existirem",
            "limpar sessão do owner canário após rollback",
            "rodar provider health closure e readiness evidence novamente",
            "não reativar parser local/plain",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Staging Canary Evidence Execution",
                "Owner MFA Vault/KMS Provider Real Adapter Contract Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Readiness Evidence Review",
            "Owner MFA Vault/KMS Provider Adapter Skeleton Execution",
        )


owner_mfa_vault_kms_provider_staging_canary_queries = OwnerMfaVaultKmsProviderStagingCanaryQueryService()
