from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_real_adapter_contract_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderRealAdapterSkeletonExecutionQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/real-adapter-probe",
        canary_owner_email: object = "",
    ) -> dict[str, object]:
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        normalized_probe = _string(probe_reference, limit=255)
        contract = owner_mfa_vault_kms_provider_real_adapter_contract_queries.get_contract(
            tenant_id=tenant_id,
            target_provider=normalized_target,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            sdk_dependency_confirmed=True,
            credential_strategy_confirmed=True,
            network_timeout_confirmed=True,
            rollout_owner_confirmed=True,
        )
        current_provider = self._current_provider()
        real_adapter_enabled = bool(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED", False))
        probe = owner_mfa_secret_providers.resolve(normalized_probe)
        blockers = list(contract.get("blockers", ()))
        if not contract.get("ready"):
            blockers.append("real-adapter-contract-not-ready")
        if current_provider != normalized_target:
            blockers.append("current-provider-does-not-match-target")
        if not real_adapter_enabled:
            blockers.append("real-adapter-mode-not-enabled")
        if not probe.ready:
            blockers.append(f"probe:{probe.result}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-real-adapter-skeleton-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": contract["tenant_id"],
            "target_provider": normalized_target,
            "current_provider": current_provider,
            "probe_reference": normalized_probe,
            "canary_owner_email": contract["canary_owner_email"],
            "real_adapter_enabled": real_adapter_enabled,
            "contract": contract,
            "probe": {
                "result": probe.result,
                "ready": probe.ready,
                "provider": probe.provider,
                "reference": probe.reference,
                "secret_returned": bool(probe.secret),
            },
            "decisions": self._decisions(
                contract=contract,
                current_provider=current_provider,
                target_provider=normalized_target,
                real_adapter_enabled=real_adapter_enabled,
                probe_ready=probe.ready,
            ),
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
        current_provider: str,
        target_provider: str,
        real_adapter_enabled: bool,
        probe_ready: bool,
    ) -> tuple[OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision(
                key="real-adapter-contract",
                status=str(contract.get("status", "blocked")),
                summary="skeleton real só segue quando o contrato real está ready",
            ),
            OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision(
                key="provider-branch",
                status="ready" if current_provider == target_provider else "blocked",
                summary="OWNER_MFA_SECRET_PROVIDER precisa apontar para o target provider",
            ),
            OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision(
                key="real-adapter-mode",
                status="ready" if real_adapter_enabled else "blocked",
                summary="modo real-adapter mock precisa estar habilitado para provar o branch separado",
            ),
            OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision(
                key="probe-resolution",
                status="ready" if probe_ready else "blocked",
                summary="probe confirma resolve read-only pelo branch real/mocável sem fallback",
            ),
            OwnerMfaVaultKmsProviderRealAdapterSkeletonDecision(
                key="secret-exposure",
                status="guarded",
                summary="evidência indica apenas se segredo retornou ao resolver, nunca o valor",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED",
            "reverter OWNER_MFA_SECRET_PROVIDER para skeleton/env se necessário",
            "rodar provider health closure e staging canary evidence após rollback",
            "não reativar parser local/plain",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider SDK Dependency Review",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Real Adapter Contract Review",
            "Owner MFA Vault/KMS Provider Staging Canary Evidence Execution",
        )


owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries = OwnerMfaVaultKmsProviderRealAdapterSkeletonExecutionQueryService()
