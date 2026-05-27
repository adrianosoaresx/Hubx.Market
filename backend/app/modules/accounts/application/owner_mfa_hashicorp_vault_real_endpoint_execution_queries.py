from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_endpoint_review_queries import (
    owner_mfa_vault_kms_provider_real_endpoint_review_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultRealEndpointExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultRealEndpointExecutionQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        review = owner_mfa_vault_kms_provider_real_endpoint_review_queries.get_review(
            tenant_id=tenant_id,
            target_provider="hashicorp-vault",
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            endpoint_url_confirmed=True,
            auth_strategy_confirmed=True,
            secret_path_contract_confirmed=True,
            timeout_budget_confirmed=True,
            rollback_confirmed=True,
        )
        endpoint_enabled = bool(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED", False))
        probe = owner_mfa_secret_providers.resolve(normalized_probe)
        blockers = list(review.get("blockers", ()))
        if not review.get("ready"):
            blockers.append("real-endpoint-review-not-ready")
        if not endpoint_enabled:
            blockers.append("hashicorp-vault-endpoint-not-enabled")
        if not probe.ready:
            blockers.append(f"probe:{probe.result}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-real-endpoint-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": review["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": review["canary_owner_email"],
            "endpoint_enabled": endpoint_enabled,
            "review": review,
            "probe": {
                "result": probe.result,
                "ready": probe.ready,
                "provider": probe.provider,
                "secret_returned": bool(probe.secret),
            },
            "settings_contract": self._settings_contract(),
            "decisions": self._decisions(review=review, endpoint_enabled=endpoint_enabled, probe_ready=probe.ready),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _settings_contract(self) -> tuple[str, ...]:
        return (
            "OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "OWNER_MFA_HASHICORP_VAULT_ADDR",
            "OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD",
            "OWNER_MFA_HASHICORP_VAULT_TOKEN ou OWNER_MFA_HASHICORP_VAULT_ROLE_ID/SECRET_ID",
            "OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT",
            "OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD",
        )

    def _decisions(
        self,
        *,
        review: dict[str, object],
        endpoint_enabled: bool,
        probe_ready: bool,
    ) -> tuple[OwnerMfaHashicorpVaultRealEndpointExecutionDecision, ...]:
        return (
            OwnerMfaHashicorpVaultRealEndpointExecutionDecision(
                key="real-endpoint-review",
                status=str(review.get("status", "blocked")),
                summary="execução Hashicorp Vault só segue quando a review do endpoint está ready",
            ),
            OwnerMfaHashicorpVaultRealEndpointExecutionDecision(
                key="endpoint-flag",
                status="ready" if endpoint_enabled else "blocked",
                summary="OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED precisa ativar a chamada hvac",
            ),
            OwnerMfaHashicorpVaultRealEndpointExecutionDecision(
                key="secret-redaction",
                status="guarded",
                summary="evidência não imprime segredo, token, role secret ou path completo",
            ),
            OwnerMfaHashicorpVaultRealEndpointExecutionDecision(
                key="probe-resolution",
                status="ready" if probe_ready else "blocked",
                summary="probe confirma leitura real/mockada via hvac com resultado mapeado",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se houver falha no SDK",
            "manter parser local/plain aposentado; não usar segredo local como rollback",
            "reexecutar real endpoint review e provider health antes de nova tentativa",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Staging Smoke Evidence",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Real Endpoint Review",
            "Owner MFA Vault/KMS Provider SDK Adapter Execution",
        )


owner_mfa_hashicorp_vault_real_endpoint_execution_queries = OwnerMfaHashicorpVaultRealEndpointExecutionQueryService()
