from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries import (
    owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderSdkDependencyDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderSdkDependencyReviewQueryService:
    sdk_dependency_contracts = {
        "hashicorp-vault": {
            "packages": ("hvac",),
            "imports": ("hvac",),
            "credential_source": "Vault token/AppRole deve vir de secret manager/env operacional, nunca do banco",
        },
        "aws-secrets-manager": {
            "packages": ("boto3",),
            "imports": ("boto3",),
            "credential_source": "IAM role/ambient credentials devem ser preferidos a access keys estáticas",
        },
        "gcp-secret-manager": {
            "packages": ("google-cloud-secret-manager",),
            "imports": ("google.cloud.secretmanager",),
            "credential_source": "service account/ambient credentials devem ser resolvidas fora do domínio accounts",
        },
        "azure-key-vault": {
            "packages": ("azure-identity", "azure-keyvault-secrets"),
            "imports": ("azure.identity", "azure.keyvault.secrets"),
            "credential_source": "managed identity/service principal deve ser configurado fora do domínio accounts",
        },
    }

    confirmations = (
        "dependency_pinned_confirmed",
        "import_optional_confirmed",
        "deploy_rollback_confirmed",
        "license_review_confirmed",
    )

    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
        probe_reference: object = "owners/vault-kms/real-adapter-probe",
        canary_owner_email: object = "",
        dependency_pinned_confirmed: bool = False,
        import_optional_confirmed: bool = False,
        deploy_rollback_confirmed: bool = False,
        license_review_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        skeleton = owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=tenant_id,
            target_provider=normalized_target,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
        )
        dependency_contract = self.sdk_dependency_contracts.get(normalized_target)
        confirmation_values = {
            "dependency_pinned_confirmed": bool(dependency_pinned_confirmed),
            "import_optional_confirmed": bool(import_optional_confirmed),
            "deploy_rollback_confirmed": bool(deploy_rollback_confirmed),
            "license_review_confirmed": bool(license_review_confirmed),
        }
        blockers = list(skeleton.get("blockers", ()))
        if not skeleton.get("ready"):
            blockers.append("real-adapter-skeleton-not-ready")
        if dependency_contract is None:
            blockers.append("sdk-target-provider-unsupported")
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-sdk-dependency-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": skeleton["tenant_id"],
            "target_provider": normalized_target,
            "canary_owner_email": skeleton["canary_owner_email"],
            "real_adapter_skeleton": skeleton,
            "confirmations": confirmation_values,
            "dependency_contract": self._dependency_contract(dependency_contract),
            "import_contract": self._import_contract(dependency_contract),
            "failure_contract": self._failure_contract(),
            "test_contract": self._test_contract(normalized_target),
            "decisions": self._decisions(
                skeleton=skeleton,
                dependency_contract=dependency_contract,
                confirmations=confirmation_values,
            ),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _dependency_contract(self, dependency_contract: dict[str, object] | None) -> dict[str, object]:
        if not dependency_contract:
            return {
                "packages": (),
                "pinning": "nenhuma dependência aprovada para provider alvo",
                "credential_source": "indefinido",
            }
        return {
            "packages": dependency_contract["packages"],
            "pinning": "adicionar dependências com versões fixadas antes de habilitar adapter SDK real",
            "credential_source": dependency_contract["credential_source"],
        }

    def _import_contract(self, dependency_contract: dict[str, object] | None) -> dict[str, object]:
        return {
            "imports": tuple(dependency_contract["imports"]) if dependency_contract else (),
            "strategy": "imports do SDK devem ser opcionais/lazy dentro do adapter, nunca no module load",
            "missing_dependency_result": "owner-mfa-secret-provider-vault-unavailable",
        }

    def _failure_contract(self) -> tuple[str, ...]:
        return (
            "timeout deve mapear para owner-mfa-secret-provider-vault-timeout",
            "permission denied deve mapear para owner-mfa-secret-provider-vault-permission-denied",
            "SDK ausente ou indisponível deve mapear para owner-mfa-secret-provider-vault-unavailable",
            "referência inválida deve ser bloqueada antes de qualquer chamada ao SDK",
            "valor secreto nunca deve aparecer em stdout, log, exception ou AuditLog",
        )

    def _test_contract(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"teste de contrato para pacote/import opcional do provider {target_provider}",
            "teste de provider SDK ausente retornando unavailable sem quebrar login",
            "teste de timeout/permission denied sem expor segredo",
            "teste de rollback para modo real-adapter desabilitado",
        )

    def _decisions(
        self,
        *,
        skeleton: dict[str, object],
        dependency_contract: dict[str, object] | None,
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderSdkDependencyDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderSdkDependencyDecision(
                key="real-adapter-skeleton",
                status=str(skeleton.get("status", "blocked")),
                summary="dependência SDK só segue depois do branch real/mocável pronto",
            ),
            OwnerMfaVaultKmsProviderSdkDependencyDecision(
                key="sdk-target",
                status="ready" if dependency_contract else "blocked",
                summary="provider alvo precisa ter pacote/import e estratégia de credencial definidos",
            ),
            OwnerMfaVaultKmsProviderSdkDependencyDecision(
                key="optional-import",
                status="ready" if confirmations["import_optional_confirmed"] else "blocked",
                summary="SDK real não pode ser import obrigatório no caminho de login ou startup",
            ),
            OwnerMfaVaultKmsProviderSdkDependencyDecision(
                key="deploy-rollback",
                status="ready" if confirmations["deploy_rollback_confirmed"] else "blocked",
                summary="deploy precisa ter rollback claro para desligar adapter SDK real",
            ),
            OwnerMfaVaultKmsProviderSdkDependencyDecision(
                key="license-pinning",
                status=(
                    "ready"
                    if confirmations["dependency_pinned_confirmed"] and confirmations["license_review_confirmed"]
                    else "blocked"
                ),
                summary="dependência deve entrar com versão fixada e licença revisada",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "remover/ignorar adapter SDK real e manter OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED desabilitado",
            "manter skeleton real/mocável como única rota Vault/KMS até nova evidência",
            "não reativar segredo local/plain nem fallback automático para env",
            "reexecutar skeleton real e provider health antes de nova tentativa",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider SDK Adapter Execution",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution",
            "Owner MFA Vault/KMS Provider Real Adapter Contract Review",
        )


owner_mfa_vault_kms_provider_sdk_dependency_review_queries = OwnerMfaVaultKmsProviderSdkDependencyReviewQueryService()
