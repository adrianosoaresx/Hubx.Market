from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_production_gate_queries import (
    owner_mfa_hashicorp_vault_production_gate_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProviderProductionActivationEvidenceQueryService:
    confirmations = (
        "deployment_completed",
        "flags_enabled_for_tenant",
        "post_deploy_probe_passed",
        "owner_login_challenge_passed",
        "provider_health_ready",
        "rollback_not_required",
        "evidence_redacted",
    )

    def get_evidence(
        self,
        *,
        tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        deployment_completed: bool = False,
        flags_enabled_for_tenant: bool = False,
        post_deploy_probe_passed: bool = False,
        owner_login_challenge_passed: bool = False,
        provider_health_ready: bool = False,
        rollback_not_required: bool = False,
        evidence_redacted: bool = False,
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        gate = owner_mfa_hashicorp_vault_production_gate_queries.get_gate(
            tenant_id=tenant_id,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            tenant_scope_confirmed=True,
            rollout_order_confirmed=True,
            feature_flags_confirmed=True,
            support_standby_confirmed=True,
            rollback_window_confirmed=True,
            post_activation_monitoring_confirmed=True,
        )
        confirmation_values = {
            "deployment_completed": bool(deployment_completed),
            "flags_enabled_for_tenant": bool(flags_enabled_for_tenant),
            "post_deploy_probe_passed": bool(post_deploy_probe_passed),
            "owner_login_challenge_passed": bool(owner_login_challenge_passed),
            "provider_health_ready": bool(provider_health_ready),
            "rollback_not_required": bool(rollback_not_required),
            "evidence_redacted": bool(evidence_redacted),
        }
        blockers = list(gate.get("blockers", ()))
        if not gate.get("ready"):
            blockers.append("production-gate-not-go")
        for key, confirmed in confirmation_values.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-provider-production-activation-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": gate["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": gate["canary_owner_email"],
            "gate": gate,
            "confirmations": confirmation_values,
            "evidence_pack": self._evidence_pack(gate=gate, confirmations=confirmation_values),
            "decisions": self._decisions(gate=gate, confirmations=confirmation_values),
            "rollback": self._rollback(),
            "blockers": unique_blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _evidence_pack(self, *, gate: dict[str, object], confirmations: dict[str, bool]) -> tuple[str, ...]:
        go_no_go = gate.get("go_no_go", {})
        return (
            f"gate_decision={go_no_go.get('decision', 'NO-GO')}",
            f"deployment_completed={confirmations['deployment_completed']}",
            f"flags_enabled_for_tenant={confirmations['flags_enabled_for_tenant']}",
            f"post_deploy_probe_passed={confirmations['post_deploy_probe_passed']}",
            f"owner_login_challenge_passed={confirmations['owner_login_challenge_passed']}",
            f"provider_health_ready={confirmations['provider_health_ready']}",
            f"rollback_not_required={confirmations['rollback_not_required']}",
            f"evidence_redacted={confirmations['evidence_redacted']}",
        )

    def _decisions(
        self,
        *,
        gate: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision, ...]:
        return (
            OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision(
                key="production-gate",
                status=str(gate.get("status", "blocked")),
                summary="activation evidence só segue quando o production gate está GO",
            ),
            OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision(
                key="deployment-flags",
                status=(
                    "ready"
                    if confirmations["deployment_completed"] and confirmations["flags_enabled_for_tenant"]
                    else "blocked"
                ),
                summary="deploy/restart e flags por tenant precisam ter sido aplicados fora do comando",
            ),
            OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision(
                key="runtime-validation",
                status=(
                    "ready"
                    if confirmations["post_deploy_probe_passed"]
                    and confirmations["owner_login_challenge_passed"]
                    and confirmations["provider_health_ready"]
                    else "blocked"
                ),
                summary="probe, login/challenge owner e health precisam estar saudáveis após ativação",
            ),
            OwnerMfaVaultKmsProviderProductionActivationEvidenceDecision(
                key="rollback-redaction",
                status=(
                    "ready"
                    if confirmations["rollback_not_required"] and confirmations["evidence_redacted"]
                    else "blocked"
                ),
                summary="rollback deve estar disponível e a evidência precisa permanecer redigida",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "se qualquer validação falhar, desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED",
            "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se falha afetar login/challenge",
            "rotacionar token/AppRole se evidência ou logs indicarem exposição",
            "reexecutar production gate e provider health após rollback",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Post-Activation Monitoring Review",
                "Owner MFA Vault/KMS Production Closure Review",
            )
        return (
            "Owner MFA Hashicorp Vault Production Gate Review",
            "Owner MFA Vault/KMS Provider Production Readiness Review",
        )


owner_mfa_vault_kms_provider_production_activation_evidence_queries = OwnerMfaVaultKmsProviderProductionActivationEvidenceQueryService()
