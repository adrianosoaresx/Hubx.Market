from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_sdk_dependency_review_queries import (
    owner_mfa_vault_kms_provider_sdk_dependency_review_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderSdkAdapterExecutionQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/sdk-adapter-probe",
        canary_owner_email: object = "",
    ) -> dict[str, object]:
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        normalized_probe = _string(probe_reference, limit=255)
        dependency_review = owner_mfa_vault_kms_provider_sdk_dependency_review_queries.get_review(
            tenant_id=tenant_id,
            target_provider=normalized_target,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            dependency_pinned_confirmed=True,
            import_optional_confirmed=True,
            deploy_rollback_confirmed=True,
            license_review_confirmed=True,
        )
        sdk_adapter_enabled = bool(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED", False))
        probe = owner_mfa_secret_providers.resolve(normalized_probe)
        blockers = list(dependency_review.get("blockers", ()))
        if not dependency_review.get("ready"):
            blockers.append("sdk-dependency-review-not-ready")
        if not sdk_adapter_enabled:
            blockers.append("sdk-adapter-mode-not-enabled")
        if not probe.ready:
            blockers.append(f"probe:{probe.result}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-sdk-adapter-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": dependency_review["tenant_id"],
            "target_provider": normalized_target,
            "probe_reference": normalized_probe,
            "canary_owner_email": dependency_review["canary_owner_email"],
            "sdk_adapter_enabled": sdk_adapter_enabled,
            "dependency_review": dependency_review,
            "probe": {
                "result": probe.result,
                "ready": probe.ready,
                "provider": probe.provider,
                "reference": probe.reference,
                "secret_returned": bool(probe.secret),
            },
            "decisions": self._decisions(
                dependency_review=dependency_review,
                sdk_adapter_enabled=sdk_adapter_enabled,
                probe_ready=probe.ready,
            ),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        dependency_review: dict[str, object],
        sdk_adapter_enabled: bool,
        probe_ready: bool,
    ) -> tuple[OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision(
                key="sdk-dependency-review",
                status=str(dependency_review.get("status", "blocked")),
                summary="adapter SDK só segue quando pacote/import/rollback/licença estão aprovados",
            ),
            OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision(
                key="sdk-adapter-mode",
                status="ready" if sdk_adapter_enabled else "blocked",
                summary="OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED precisa ativar o branch SDK",
            ),
            OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision(
                key="lazy-import",
                status="guarded",
                summary="SDK é importado dentro do resolver e falha como unavailable se pacote não existir",
            ),
            OwnerMfaVaultKmsProviderSdkAdapterExecutionDecision(
                key="probe-resolution",
                status="ready" if probe_ready else "blocked",
                summary="probe confirma o branch SDK sem imprimir valor do segredo",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED",
            "manter OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED apenas se o branch real/mocável anterior estiver saudável",
            "reverter dependência SDK no deploy se import opcional causar falha inesperada",
            "reexecutar dependency review e skeleton real após rollback",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Real Endpoint Review",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider SDK Dependency Review",
            "Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution",
        )


owner_mfa_vault_kms_provider_sdk_adapter_execution_queries = OwnerMfaVaultKmsProviderSdkAdapterExecutionQueryService()
