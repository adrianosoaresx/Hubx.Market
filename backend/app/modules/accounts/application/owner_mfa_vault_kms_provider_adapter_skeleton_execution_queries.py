from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_adapter_contract_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderAdapterSkeletonDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderAdapterSkeletonExecutionQueryService:
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
        contract = owner_mfa_vault_kms_provider_adapter_contract_queries.get_contract(
            tenant_id=normalized_tenant_id,
            target_provider=normalized_target,
        )
        provider = self._current_provider()
        probe = owner_mfa_secret_providers.resolve(normalized_probe)
        blockers = list(contract.get("blockers", ()))
        if not contract.get("ready"):
            blockers.append("adapter-contract-not-ready")
        if provider != normalized_target:
            blockers.append("current-provider-does-not-match-target")
        if not probe.ready:
            blockers.append(f"probe:{probe.result}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-adapter-skeleton-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": normalized_tenant_id,
            "target_provider": normalized_target,
            "current_provider": provider,
            "probe_reference": normalized_probe,
            "contract": contract,
            "probe": {
                "result": probe.result,
                "ready": probe.ready,
                "provider": probe.provider,
                "reference": probe.reference,
                "secret_returned": bool(probe.secret),
            },
            "decisions": self._decisions(contract=contract, provider=provider, target_provider=normalized_target, probe_ready=probe.ready),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _current_provider(self) -> str:
        return _string(getattr(settings, "OWNER_MFA_SECRET_PROVIDER", "none"), limit=32).lower() or "none"

    def _decisions(
        self,
        *,
        contract: dict[str, object],
        provider: str,
        target_provider: str,
        probe_ready: bool,
    ) -> tuple[OwnerMfaVaultKmsProviderAdapterSkeletonDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderAdapterSkeletonDecision(
                key="adapter-contract",
                status=str(contract.get("status", "blocked")),
                summary="skeleton só é Go quando o contrato técnico anterior está ready",
            ),
            OwnerMfaVaultKmsProviderAdapterSkeletonDecision(
                key="provider-branch",
                status="ready" if provider == target_provider else "blocked",
                summary="OWNER_MFA_SECRET_PROVIDER precisa apontar para o target provider durante a prova",
            ),
            OwnerMfaVaultKmsProviderAdapterSkeletonDecision(
                key="probe-resolution",
                status="ready" if probe_ready else "blocked",
                summary="probe confirma caminho read-only do skeleton sem fallback local/env automático",
            ),
            OwnerMfaVaultKmsProviderAdapterSkeletonDecision(
                key="secret-exposure",
                status="guarded",
                summary="evidência só expõe se secret foi retornado ao resolver, nunca o valor do segredo",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter OWNER_MFA_SECRET_PROVIDER para env se refs equivalentes existirem",
            "remover OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS=ready do ambiente de teste",
            "rodar owner_mfa_provider_health_closure para o tenant canário",
            "não reativar parser local/plain como rollback do skeleton",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Readiness Evidence Review",
                "Owner MFA Vault/KMS Provider Staging Canary Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Adapter Contract Review",
            "Owner MFA Provider Health Closure Review",
        )


owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries = OwnerMfaVaultKmsProviderAdapterSkeletonExecutionQueryService()
