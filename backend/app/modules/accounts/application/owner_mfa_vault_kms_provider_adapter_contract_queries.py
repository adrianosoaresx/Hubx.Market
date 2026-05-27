from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_review_queries import (
    owner_mfa_vault_kms_provider_review_queries,
)


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsAdapterContractDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderAdapterContractQueryService:
    def get_contract(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
    ) -> dict[str, object]:
        normalized_tenant_id = _string(tenant_id, limit=64)
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        provider_review = owner_mfa_vault_kms_provider_review_queries.get_review(
            tenant_id=normalized_tenant_id,
            target_provider=normalized_target,
        )
        blockers = list(provider_review.get("blockers", ()))
        if not provider_review.get("ready"):
            blockers.append("vault-kms-provider-review-not-ready")
        if normalized_target not in provider_review.get("supported_targets", ()):
            blockers.append("target-provider-unsupported")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-adapter-contract-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": normalized_tenant_id,
            "target_provider": normalized_target,
            "provider_review": provider_review,
            "decisions": self._decisions(provider_review=provider_review, target_provider=normalized_target),
            "blockers": unique_blockers,
            "settings_contract": self._settings_contract(normalized_target),
            "adapter_interface": self._adapter_interface(normalized_target),
            "recoverable_errors": self._recoverable_errors(),
            "security_controls": self._security_controls(),
            "test_contract": self._test_contract(),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        provider_review: dict[str, object],
        target_provider: str,
    ) -> tuple[OwnerMfaVaultKmsAdapterContractDecision, ...]:
        return (
            OwnerMfaVaultKmsAdapterContractDecision(
                key="provider-review",
                status=str(provider_review.get("status", "blocked")),
                summary="adapter skeleton só deve seguir quando a review Vault/KMS estiver ready",
            ),
            OwnerMfaVaultKmsAdapterContractDecision(
                key="target-provider",
                status="ready" if target_provider in provider_review.get("supported_targets", ()) else "blocked",
                summary=f"contrato do adapter será gerado para {target_provider}",
            ),
            OwnerMfaVaultKmsAdapterContractDecision(
                key="read-path-only",
                status="guarded",
                summary="primeiro adapter só resolve segredo por reference; escrita/migração fica fora do skeleton",
            ),
            OwnerMfaVaultKmsAdapterContractDecision(
                key="failure-mode",
                status="recoverable",
                summary="falhas de provider retornam ready=False/result explícito sem exception no login",
            ),
            OwnerMfaVaultKmsAdapterContractDecision(
                key="secret-material",
                status="redacted",
                summary="segredo nunca deve aparecer em logs, comandos, metrics, audit metadata ou exceptions",
            ),
        )

    def _settings_contract(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"OWNER_MFA_SECRET_PROVIDER={target_provider}",
            "OWNER_MFA_SECRET_TIMEOUT_MS=<int default 1500>",
            "OWNER_MFA_SECRET_RETRY_COUNT=<int default 0>",
            "OWNER_MFA_SECRET_NAMESPACE=<optional tenant-safe prefix>",
            "OWNER_MFA_SECRET_CACHE_SECONDS=0 nesta primeira versão",
            "credenciais do provider ficam fora do banco e fora do código",
        )

    def _adapter_interface(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"registrar branch provider == '{target_provider}' em owner_mfa_secret_providers",
            "input: reference normalizada sem prefixo ref:",
            "output: OwnerMfaSecretProviderResult(result, secret, ready, provider, reference)",
            "ready=True somente quando o segredo TOTP não vazio é obtido",
            "ready=False para missing, unavailable, timeout, permission-denied e invalid-reference",
            "não alterar OwnerMfaFactor, settings, env ou AuditLog durante resolve",
        )

    def _recoverable_errors(self) -> tuple[str, ...]:
        return (
            "owner-mfa-secret-provider-vault-missing",
            "owner-mfa-secret-provider-vault-unavailable",
            "owner-mfa-secret-provider-vault-timeout",
            "owner-mfa-secret-provider-vault-permission-denied",
            "owner-mfa-secret-provider-vault-invalid-reference",
        )

    def _security_controls(self) -> tuple[str, ...]:
        return (
            "não imprimir secret material em stdout/stderr/logs",
            "não incluir owner_id, factor_id ou reference path completo em métricas",
            "não fazer fallback para env/local automaticamente quando Vault/KMS falhar",
            "não aceitar reference absoluta, vazia ou com traversal",
            "não cachear segredo na primeira versão",
            "timeouts curtos para evitar travar login owner/admin",
        )

    def _test_contract(self) -> tuple[str, ...]:
        return (
            "resolve sucesso retorna ready=True sem logar secret",
            "missing retorna ready=False/result missing",
            "timeout/unavailable/permission denied retornam ready=False sem exception",
            "provider desconhecido continua unavailable",
            "login/challenge MFA usa resolver e não chama adapter diretamente",
            "health/readiness não expõe segredo nem reference path completo",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "trocar OWNER_MFA_SECRET_PROVIDER de volta para env se refs equivalentes existirem",
            "rodar owner_mfa_provider_health_closure para tenant canário",
            "não reativar parser local/plain",
            "não migrar dados automaticamente durante rollback do skeleton",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Adapter Skeleton Execution",
                "Owner MFA Vault/KMS Provider Readiness Evidence Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Review",
            "Owner MFA Provider Health Closure Review",
        )


owner_mfa_vault_kms_provider_adapter_contract_queries = OwnerMfaVaultKmsProviderAdapterContractQueryService()
