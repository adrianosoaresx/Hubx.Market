from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_sdk_adapter_execution_queries import (
    owner_mfa_vault_kms_provider_sdk_adapter_execution_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderRealEndpointDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderRealEndpointReviewQueryService:
    supported_endpoint_targets: tuple[str, ...] = ("hashicorp-vault",)

    confirmations = (
        "endpoint_url_confirmed",
        "auth_strategy_confirmed",
        "secret_path_contract_confirmed",
        "timeout_budget_confirmed",
        "rollback_confirmed",
    )

    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/sdk-adapter-probe",
        canary_owner_email: object = "",
        endpoint_url_confirmed: bool = False,
        auth_strategy_confirmed: bool = False,
        secret_path_contract_confirmed: bool = False,
        timeout_budget_confirmed: bool = False,
        rollback_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        sdk_adapter = owner_mfa_vault_kms_provider_sdk_adapter_execution_queries.get_evidence(
            tenant_id=tenant_id,
            target_provider=normalized_target,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
        )
        confirmation_values = {
            "endpoint_url_confirmed": bool(endpoint_url_confirmed),
            "auth_strategy_confirmed": bool(auth_strategy_confirmed),
            "secret_path_contract_confirmed": bool(secret_path_contract_confirmed),
            "timeout_budget_confirmed": bool(timeout_budget_confirmed),
            "rollback_confirmed": bool(rollback_confirmed),
        }
        blockers = list(sdk_adapter.get("blockers", ()))
        if not sdk_adapter.get("ready"):
            blockers.append("sdk-adapter-execution-not-ready")
        if normalized_target not in self.supported_endpoint_targets:
            blockers.append("real-endpoint-target-not-supported")
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-real-endpoint-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": sdk_adapter["tenant_id"],
            "target_provider": normalized_target,
            "canary_owner_email": sdk_adapter["canary_owner_email"],
            "sdk_adapter": sdk_adapter,
            "confirmations": confirmation_values,
            "endpoint_contract": self._endpoint_contract(normalized_target),
            "secret_contract": self._secret_contract(normalized_target),
            "failure_contract": self._failure_contract(),
            "test_contract": self._test_contract(normalized_target),
            "decisions": self._decisions(
                sdk_adapter=sdk_adapter,
                target_provider=normalized_target,
                confirmations=confirmation_values,
            ),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _endpoint_contract(self, target_provider: str) -> dict[str, object]:
        if target_provider != "hashicorp-vault":
            return {
                "provider": target_provider,
                "settings": (),
                "auth_methods": (),
                "summary": "endpoint real ainda não aprovado para este provider",
            }
        return {
            "provider": target_provider,
            "settings": (
                "OWNER_MFA_HASHICORP_VAULT_ADDR",
                "OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD",
                "OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT",
                "OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD",
            ),
            "auth_methods": ("token", "approle"),
            "summary": "primeiro endpoint real deve usar hvac com endereço, auth method, mount e campo de segredo explícitos",
        }

    def _secret_contract(self, target_provider: str) -> dict[str, object]:
        if target_provider != "hashicorp-vault":
            return {
                "reference_format": "indefinido",
                "expected_shape": (),
                "redaction": "nenhum path completo deve ser impresso",
            }
        return {
            "reference_format": "owners/<tenant-or-scope>/<factor-or-owner-key>",
            "expected_shape": ("secret field contém base32 TOTP",),
            "redaction": "comandos/evidências podem mostrar provider/status, mas não secret value nem path completo",
        }

    def _failure_contract(self) -> tuple[str, ...]:
        return (
            "endpoint indisponível ou SDK ausente retorna owner-mfa-secret-provider-vault-unavailable",
            "timeout retorna owner-mfa-secret-provider-vault-timeout",
            "403/permission denied retorna owner-mfa-secret-provider-vault-permission-denied",
            "secret ausente retorna owner-mfa-secret-provider-vault-missing",
            "referência inválida é bloqueada antes de montar path do provider",
        )

    def _test_contract(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"teste de adapter {target_provider} com client mockado retornando secret field",
            f"teste de adapter {target_provider} mapeando missing/timeout/permission denied",
            "teste de command sem imprimir secret value ou path completo",
            "teste de rollback por desligamento do SDK adapter",
        )

    def _decisions(
        self,
        *,
        sdk_adapter: dict[str, object],
        target_provider: str,
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderRealEndpointDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderRealEndpointDecision(
                key="sdk-adapter",
                status=str(sdk_adapter.get("status", "blocked")),
                summary="endpoint real só segue depois do branch SDK lazy ready",
            ),
            OwnerMfaVaultKmsProviderRealEndpointDecision(
                key="endpoint-target",
                status="ready" if target_provider in self.supported_endpoint_targets else "blocked",
                summary="primeiro endpoint real aprovado é Hashicorp Vault",
            ),
            OwnerMfaVaultKmsProviderRealEndpointDecision(
                key="endpoint-url",
                status="ready" if confirmations["endpoint_url_confirmed"] else "blocked",
                summary="URL/base address do Vault precisa estar definida fora do banco",
            ),
            OwnerMfaVaultKmsProviderRealEndpointDecision(
                key="auth-secret-path-timeout",
                status=(
                    "ready"
                    if confirmations["auth_strategy_confirmed"]
                    and confirmations["secret_path_contract_confirmed"]
                    and confirmations["timeout_budget_confirmed"]
                    else "blocked"
                ),
                summary="auth strategy, secret path e timeout precisam ser explícitos antes da execução",
            ),
            OwnerMfaVaultKmsProviderRealEndpointDecision(
                key="rollback",
                status="ready" if confirmations["rollback_confirmed"] else "blocked",
                summary="rollback deve desligar SDK adapter sem reativar segredo local/plain",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED",
            "manter OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED apenas se a probe mocável continuar saudável",
            "não reativar parser local/plain como fallback",
            "reexecutar SDK adapter execution e provider health antes de nova tentativa",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Real Endpoint Execution",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider SDK Adapter Execution",
            "Owner MFA Vault/KMS Provider SDK Dependency Review",
        )


owner_mfa_vault_kms_provider_real_endpoint_review_queries = OwnerMfaVaultKmsProviderRealEndpointReviewQueryService()
