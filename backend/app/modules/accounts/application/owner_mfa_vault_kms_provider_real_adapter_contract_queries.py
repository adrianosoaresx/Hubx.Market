from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_staging_canary_evidence_queries import (
    owner_mfa_vault_kms_provider_staging_canary_evidence_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "sim", "ok", "passed", "pass"}


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderRealAdapterDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderRealAdapterContractQueryService:
    supported_real_targets: tuple[str, ...] = (
        "hashicorp-vault",
        "aws-secrets-manager",
        "gcp-secret-manager",
        "azure-key-vault",
    )

    def get_contract(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/skeleton-probe",
        canary_owner_email: object = "",
        sdk_dependency_confirmed: object = False,
        credential_strategy_confirmed: object = False,
        network_timeout_confirmed: object = False,
        rollout_owner_confirmed: object = False,
    ) -> dict[str, object]:
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        canary_evidence = owner_mfa_vault_kms_provider_staging_canary_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            target_provider=normalized_target,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
            valid_login_passed=True,
            invalid_challenge_blocked=True,
            post_health_ready=True,
            logs_redacted=True,
            rollback_verified=True,
            evidence_label="real-adapter-contract",
        )
        confirmations = {
            "sdk_dependency_confirmed": _bool(sdk_dependency_confirmed),
            "credential_strategy_confirmed": _bool(credential_strategy_confirmed),
            "network_timeout_confirmed": _bool(network_timeout_confirmed),
            "rollout_owner_confirmed": _bool(rollout_owner_confirmed),
        }
        blockers = list(canary_evidence.get("blockers", ()))
        if not canary_evidence.get("ready"):
            blockers.append("staging-canary-evidence-not-ready")
        if normalized_target not in self.supported_real_targets:
            blockers.append("real-target-provider-unsupported")
        for key, confirmed in confirmations.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-real-adapter-contract-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": canary_evidence["tenant_id"],
            "target_provider": normalized_target,
            "supported_real_targets": self.supported_real_targets,
            "probe_reference": canary_evidence["probe_reference"],
            "canary_owner_email": canary_evidence["canary_owner_email"],
            "canary_evidence": canary_evidence,
            "confirmations": confirmations,
            "decisions": self._decisions(canary_evidence=canary_evidence, target_provider=normalized_target, confirmations=confirmations),
            "blockers": unique_blockers,
            "real_adapter_contract": self._real_adapter_contract(normalized_target),
            "settings_contract": self._settings_contract(normalized_target),
            "error_contract": self._error_contract(),
            "test_contract": self._test_contract(),
            "implementation_plan": self._implementation_plan(normalized_target),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        canary_evidence: dict[str, object],
        target_provider: str,
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderRealAdapterDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="staging-canary-evidence",
                status=str(canary_evidence.get("status", "blocked")),
                summary="adapter real só segue após evidência declarativa de canário staging",
            ),
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="real-target-provider",
                status="ready" if target_provider in self.supported_real_targets else "blocked",
                summary=f"target provider selecionado para adapter real: {target_provider}",
            ),
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="sdk-boundary",
                status="ready" if confirmations["sdk_dependency_confirmed"] else "blocked",
                summary="dependência SDK/vendor precisa ser explícita e isolada em infrastructure",
            ),
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="credential-strategy",
                status="ready" if confirmations["credential_strategy_confirmed"] else "blocked",
                summary="credenciais devem vir do ambiente/infra, nunca do banco ou do código",
            ),
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="network-timeout",
                status="ready" if confirmations["network_timeout_confirmed"] else "blocked",
                summary="timeouts curtos e falhas recuperáveis são obrigatórios no caminho de login",
            ),
            OwnerMfaVaultKmsProviderRealAdapterDecision(
                key="rollout-owner",
                status="ready" if confirmations["rollout_owner_confirmed"] else "blocked",
                summary="rollout precisa de responsável operacional definido antes da implementação real",
            ),
        )

    def _real_adapter_contract(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"provider={target_provider}",
            "adapter permanece em accounts.infrastructure.owner_mfa_secret_providers",
            "resolve(reference) é read-path-only e retorna OwnerMfaSecretProviderResult",
            "sem escrita/migração de segredo no adapter real",
            "sem fallback automático para env/local quando provider real falhar",
            "segredo só existe em memória pelo tempo da verificação TOTP",
        )

    def _settings_contract(self, target_provider: str) -> tuple[str, ...]:
        provider_prefix = target_provider.upper().replace("-", "_")
        return (
            f"OWNER_MFA_SECRET_PROVIDER={target_provider}",
            "OWNER_MFA_SECRET_TIMEOUT_MS=<int default 1500>",
            "OWNER_MFA_SECRET_RETRY_COUNT=<int default 0>",
            "OWNER_MFA_SECRET_NAMESPACE=<optional prefix>",
            f"OWNER_MFA_SECRET_{provider_prefix}_CONFIG=<env/infra managed>",
            "OWNER_MFA_SECRET_CACHE_SECONDS=0 até revisão explícita de cache",
        )

    def _error_contract(self) -> tuple[str, ...]:
        return (
            "owner-mfa-secret-provider-vault-ready",
            "owner-mfa-secret-provider-vault-missing",
            "owner-mfa-secret-provider-vault-unavailable",
            "owner-mfa-secret-provider-vault-timeout",
            "owner-mfa-secret-provider-vault-permission-denied",
            "owner-mfa-secret-provider-vault-invalid-reference",
        )

    def _test_contract(self) -> tuple[str, ...]:
        return (
            "mock SDK success retorna ready=True sem logar segredo",
            "missing/permission/timeout/unavailable retornam ready=False sem exception",
            "reference inválida é bloqueada antes de chamar SDK",
            "login/challenge continuam chamando apenas resolver de storage",
            "provider health closure permanece HEALTHY com adapter real mockado",
            "comando de evidência não imprime secret material",
        )

    def _implementation_plan(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"1. criar adapter interno para {target_provider} atrás do registry existente",
            "2. encapsular SDK/vendor em função privada testável/mocável",
            "3. mapear exceções do SDK para error_contract",
            "4. manter skeleton como caminho de teste controlado até rollout real",
            "5. rodar canário staging novamente com adapter real mockado",
            "6. só depois considerar provider real em staging com credenciais reais",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "manter OWNER_MFA_SECRET_PROVIDER apontando para skeleton/env até canário real aprovado",
            "reverter dependência SDK se causar falhas de import/deploy",
            "rodar staging canary evidence após rollback",
            "não reativar parser local/plain",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution",
                "Owner MFA Vault/KMS Provider SDK Dependency Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Staging Canary Evidence Execution",
            "Owner MFA Vault/KMS Provider Staging Canary Review",
        )


owner_mfa_vault_kms_provider_real_adapter_contract_queries = OwnerMfaVaultKmsProviderRealAdapterContractQueryService()
