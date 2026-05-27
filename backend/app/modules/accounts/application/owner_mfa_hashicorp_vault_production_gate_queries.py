from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_production_readiness_queries import (
    owner_mfa_vault_kms_provider_production_readiness_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultProductionGateDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultProductionGateQueryService:
    confirmations = (
        "tenant_scope_confirmed",
        "rollout_order_confirmed",
        "feature_flags_confirmed",
        "support_standby_confirmed",
        "rollback_window_confirmed",
        "post_activation_monitoring_confirmed",
    )

    def get_gate(
        self,
        *,
        tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        tenant_scope_confirmed: bool = False,
        rollout_order_confirmed: bool = False,
        feature_flags_confirmed: bool = False,
        support_standby_confirmed: bool = False,
        rollback_window_confirmed: bool = False,
        post_activation_monitoring_confirmed: bool = False,
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        readiness = owner_mfa_vault_kms_provider_production_readiness_queries.get_review(
            tenant_id=tenant_id,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            runbook_reviewed=True,
            rollback_owner_confirmed=True,
            monitoring_confirmed=True,
            change_window_confirmed=True,
            credential_rotation_confirmed=True,
        )
        confirmation_values = {
            "tenant_scope_confirmed": bool(tenant_scope_confirmed),
            "rollout_order_confirmed": bool(rollout_order_confirmed),
            "feature_flags_confirmed": bool(feature_flags_confirmed),
            "support_standby_confirmed": bool(support_standby_confirmed),
            "rollback_window_confirmed": bool(rollback_window_confirmed),
            "post_activation_monitoring_confirmed": bool(post_activation_monitoring_confirmed),
        }
        blockers = list(readiness.get("blockers", ()))
        if not readiness.get("ready"):
            blockers.append("production-readiness-not-go")
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-production-gate-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": readiness["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": readiness["canary_owner_email"],
            "readiness": readiness,
            "confirmations": confirmation_values,
            "activation_plan": self._activation_plan(),
            "rollback": self._rollback(),
            "go_no_go": self._go_no_go(status=status, blockers=unique_blockers),
            "decisions": self._decisions(readiness=readiness, confirmations=confirmation_values),
            "blockers": unique_blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _activation_plan(self) -> tuple[str, ...]:
        return (
            "1. aplicar flags Hashicorp Vault apenas no tenant canário",
            "2. executar activation evidence imediatamente após deploy/restart",
            "3. monitorar provider health e owner login/challenge por janela curta",
            "4. expandir para demais tenants somente após janela canário sem blockers",
            "5. manter token/AppRole pronto para rotação se houver exposição operacional",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se houver impacto em login/challenge",
            "reexecutar provider health closure e staging smoke após rollback",
            "não reativar parser local/plain como fallback",
        )

    def _go_no_go(self, *, status: str, blockers: tuple[str, ...]) -> dict[str, object]:
        return {
            "decision": "GO" if status == "ready" else "NO-GO",
            "activation_allowed": status == "ready",
            "blocker_count": len(blockers),
        }

    def _decisions(
        self,
        *,
        readiness: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaHashicorpVaultProductionGateDecision, ...]:
        return (
            OwnerMfaHashicorpVaultProductionGateDecision(
                key="production-readiness",
                status=str(readiness.get("status", "blocked")),
                summary="gate de ativação só segue quando production readiness está GO",
            ),
            OwnerMfaHashicorpVaultProductionGateDecision(
                key="tenant-scope",
                status="ready" if confirmations["tenant_scope_confirmed"] else "blocked",
                summary="ativação deve começar por tenant canário explícito",
            ),
            OwnerMfaHashicorpVaultProductionGateDecision(
                key="rollout-flags",
                status=(
                    "ready"
                    if confirmations["rollout_order_confirmed"] and confirmations["feature_flags_confirmed"]
                    else "blocked"
                ),
                summary="ordem de rollout e flags precisam estar revisadas antes da janela",
            ),
            OwnerMfaHashicorpVaultProductionGateDecision(
                key="support-rollback",
                status=(
                    "ready"
                    if confirmations["support_standby_confirmed"] and confirmations["rollback_window_confirmed"]
                    else "blocked"
                ),
                summary="plantão e janela de rollback precisam estar confirmados",
            ),
            OwnerMfaHashicorpVaultProductionGateDecision(
                key="post-activation-monitoring",
                status="ready" if confirmations["post_activation_monitoring_confirmed"] else "blocked",
                summary="monitoramento pós-ativação precisa estar reservado antes do GO",
            ),
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Production Activation Evidence",
                "Owner MFA Hashicorp Vault Post-Activation Monitoring Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Production Readiness Review",
            "Owner MFA Hashicorp Vault Staging Smoke Evidence",
        )


owner_mfa_hashicorp_vault_production_gate_queries = OwnerMfaHashicorpVaultProductionGateQueryService()
