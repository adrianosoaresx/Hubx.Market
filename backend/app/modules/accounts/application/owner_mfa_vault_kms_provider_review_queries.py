from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_execution_queries import (
    owner_mfa_local_secret_parser_removal_execution_queries,
)
from app.modules.accounts.application.owner_mfa_provider_health_closure_queries import owner_mfa_provider_health_closure_queries


def _string(value: object, *, limit: int = 120) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderReviewQueryService:
    supported_targets: tuple[str, ...] = (
        "hashicorp-vault",
        "aws-secrets-manager",
        "aws-kms",
        "gcp-secret-manager",
        "azure-key-vault",
    )

    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        target_provider: object = "hashicorp-vault",
    ) -> dict[str, object]:
        normalized_tenant_id = _string(tenant_id, limit=64)
        normalized_target = _string(target_provider, limit=64).lower() or "hashicorp-vault"
        if not normalized_tenant_id:
            return {
                "result": "owner-mfa-vault-kms-provider-tenant-required",
                "ready": False,
                "status": "blocked",
                "tenant_id": "",
                "current_provider": self._current_provider(),
                "target_provider": normalized_target,
                "provider_health_closure": {},
                "parser_removal_execution": {},
                "decisions": (),
                "blockers": ("tenant-required",),
                "adapter_contract": self._adapter_contract(normalized_target),
                "rollout_plan": self._rollout_plan(),
                "rollback": self._rollback(),
                "next_tracks": ("Owner MFA Vault/KMS Provider Adapter Contract Review",),
            }
        provider_health_closure = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=normalized_tenant_id)
        parser_removal_execution = owner_mfa_local_secret_parser_removal_execution_queries.get_evidence()
        current_provider = self._current_provider()
        blockers = []
        if normalized_target not in self.supported_targets:
            blockers.append("target-provider-unsupported")
        if provider_health_closure["status"] == "blocked":
            blockers.append("provider-health-closure-blocked")
        if provider_health_closure["status"] == "watch":
            blockers.append("provider-health-closure-watch")
        if not parser_removal_execution["ready"]:
            blockers.append("local-parser-removal-not-ready")
        if current_provider in {"none", ""}:
            blockers.append("current-provider-missing")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": normalized_tenant_id,
            "current_provider": current_provider,
            "target_provider": normalized_target,
            "supported_targets": self.supported_targets,
            "provider_health_closure": provider_health_closure,
            "parser_removal_execution": parser_removal_execution,
            "decisions": self._decisions(
                current_provider=current_provider,
                target_provider=normalized_target,
                provider_health_closure=provider_health_closure,
                parser_removal_execution=parser_removal_execution,
            ),
            "blockers": unique_blockers,
            "adapter_contract": self._adapter_contract(normalized_target),
            "rollout_plan": self._rollout_plan(),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _current_provider(self) -> str:
        return _string(getattr(settings, "OWNER_MFA_SECRET_PROVIDER", "none"), limit=32).lower() or "none"

    def _decisions(
        self,
        *,
        current_provider: str,
        target_provider: str,
        provider_health_closure: dict[str, object],
        parser_removal_execution: dict[str, object],
    ) -> tuple[OwnerMfaVaultKmsProviderDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderDecision(
                key="current-provider",
                status="transitional" if current_provider == "env" else current_provider,
                summary="provider env é aceitável como ponte, mas não como storage final de produção",
            ),
            OwnerMfaVaultKmsProviderDecision(
                key="target-provider",
                status="ready" if target_provider in self.supported_targets else "blocked",
                summary=f"target provider selecionado para contrato: {target_provider}",
            ),
            OwnerMfaVaultKmsProviderDecision(
                key="health-closure",
                status=str(provider_health_closure.get("status", "blocked")),
                summary="tenant precisa estar saudável antes de trocar adapter de segredo MFA",
            ),
            OwnerMfaVaultKmsProviderDecision(
                key="local-parser-removal",
                status="ready" if parser_removal_execution.get("ready") else "blocked",
                summary="parser local/plain precisa estar removido para evitar fallback silencioso",
            ),
            OwnerMfaVaultKmsProviderDecision(
                key="secret-exposure",
                status="guarded",
                summary="adapter não deve logar segredo, reference path completo, owner ou factor",
            ),
        )

    def _adapter_contract(self, target_provider: str) -> tuple[str, ...]:
        return (
            f"provider_key={target_provider}",
            "entrada: reference sem prefixo ref:",
            "saída: result, secret, ready, provider, reference",
            "erro recuperável: ready=False sem exception para segredo ausente/unavailable",
            "timeout/retry pertence ao adapter, sem bloquear login além do timeout configurado",
            "observabilidade só pode expor provider, status e contagens por tenant",
            "nenhum comando deve imprimir secret material",
        )

    def _rollout_plan(self) -> tuple[str, ...]:
        return (
            "1. criar adapter skeleton para target provider atrás de OWNER_MFA_SECRET_PROVIDER",
            "2. validar refs existentes em modo read-only contra o novo provider",
            "3. rodar provider health closure e parser removal execution",
            "4. habilitar target provider em staging com owner MFA canário",
            "5. capturar evidência de login/challenge e rollback",
            "6. promover para produção com janela curta e monitoramento ativo",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter OWNER_MFA_SECRET_PROVIDER para env enquanto refs permanecem equivalentes",
            "restaurar variáveis OWNER_MFA_SECRET_* para owners canário se necessário",
            "rodar owner_mfa_provider_health_closure após rollback",
            "não reativar parser local/plain como rollback de provider",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Adapter Contract Review",
                "Owner MFA Vault/KMS Provider Adapter Skeleton Execution",
            )
        return (
            "Owner MFA Provider Health Closure Review",
            "Owner MFA Local Secret Parser Removal Execution Review",
        )


owner_mfa_vault_kms_provider_review_queries = OwnerMfaVaultKmsProviderReviewQueryService()
