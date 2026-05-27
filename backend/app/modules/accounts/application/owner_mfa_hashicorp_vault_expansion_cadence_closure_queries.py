from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_next_tenant_expansion_queries import (
    owner_mfa_hashicorp_vault_next_tenant_expansion_queries,
)


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultExpansionCadenceClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultExpansionCadenceClosureQueryService:
    def get_closure(
        self,
        *,
        canary_tenant_id: int | str | None,
        current_target_tenant_id: int | str | None,
        next_target_tenant_ids: object = "",
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        canary_monitoring_window_elapsed: bool = False,
        canary_provider_health_stable: bool = False,
        canary_owner_login_error_spike_absent: bool = False,
        canary_support_incidents_absent: bool = False,
        canary_rollback_signal_absent: bool = False,
        canary_evidence_redacted: bool = False,
        rollback_runbook_confirmed: bool = False,
        residual_risks_accepted: bool = False,
        tenant_expansion_plan_documented: bool = False,
        expansion_window_confirmed: bool = False,
        per_tenant_evidence_required: bool = False,
        support_standby_confirmed: bool = False,
        rollback_window_confirmed: bool = False,
        target_flags_enabled: bool = False,
        target_activation_evidence_captured: bool = False,
        target_monitoring_scheduled: bool = False,
        target_owner_login_challenge_passed: bool = False,
        target_provider_health_ready: bool = False,
        rollback_not_required: bool = False,
        expansion_evidence_redacted: bool = False,
        target_monitoring_window_elapsed: bool = False,
        target_provider_health_stable: bool = False,
        target_owner_login_error_spike_absent: bool = False,
        target_support_incidents_absent: bool = False,
        target_rollback_signal_absent: bool = False,
        evidence_redacted: bool = False,
        next_window_confirmed: bool = False,
        operator_capacity_confirmed: bool = False,
        previous_target_evidence_archived: bool = False,
        stop_after_current_target: bool = False,
        max_parallel_tenants: int = 1,
        cadence_decision_recorded: bool = False,
        evidence_archive_complete: bool = False,
        residual_risks_reviewed: bool = False,
        rotation_runbook_queued: bool = False,
        audit_evidence_ready: bool = False,
    ) -> dict[str, object]:
        cadence = owner_mfa_hashicorp_vault_next_tenant_expansion_queries.get_review(
            canary_tenant_id=canary_tenant_id,
            current_target_tenant_id=current_target_tenant_id,
            next_target_tenant_ids=next_target_tenant_ids,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
            canary_monitoring_window_elapsed=canary_monitoring_window_elapsed,
            canary_provider_health_stable=canary_provider_health_stable,
            canary_owner_login_error_spike_absent=canary_owner_login_error_spike_absent,
            canary_support_incidents_absent=canary_support_incidents_absent,
            canary_rollback_signal_absent=canary_rollback_signal_absent,
            canary_evidence_redacted=canary_evidence_redacted,
            rollback_runbook_confirmed=rollback_runbook_confirmed,
            residual_risks_accepted=residual_risks_accepted,
            tenant_expansion_plan_documented=tenant_expansion_plan_documented,
            expansion_window_confirmed=expansion_window_confirmed,
            per_tenant_evidence_required=per_tenant_evidence_required,
            support_standby_confirmed=support_standby_confirmed,
            rollback_window_confirmed=rollback_window_confirmed,
            target_flags_enabled=target_flags_enabled,
            target_activation_evidence_captured=target_activation_evidence_captured,
            target_monitoring_scheduled=target_monitoring_scheduled,
            target_owner_login_challenge_passed=target_owner_login_challenge_passed,
            target_provider_health_ready=target_provider_health_ready,
            rollback_not_required=rollback_not_required,
            expansion_evidence_redacted=expansion_evidence_redacted,
            target_monitoring_window_elapsed=target_monitoring_window_elapsed,
            target_provider_health_stable=target_provider_health_stable,
            target_owner_login_error_spike_absent=target_owner_login_error_spike_absent,
            target_support_incidents_absent=target_support_incidents_absent,
            target_rollback_signal_absent=target_rollback_signal_absent,
            evidence_redacted=evidence_redacted,
            next_window_confirmed=next_window_confirmed,
            operator_capacity_confirmed=operator_capacity_confirmed,
            previous_target_evidence_archived=previous_target_evidence_archived,
            stop_after_current_target=stop_after_current_target,
            max_parallel_tenants=max_parallel_tenants,
        )
        closure_signals = {
            "cadence_decision_recorded": bool(cadence_decision_recorded),
            "evidence_archive_complete": bool(evidence_archive_complete),
            "residual_risks_reviewed": bool(residual_risks_reviewed),
            "rotation_runbook_queued": bool(rotation_runbook_queued),
            "audit_evidence_ready": bool(audit_evidence_ready),
        }
        blockers = self._blockers(cadence=cadence, closure_signals=closure_signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-expansion-cadence-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "cadence_status": cadence["status"],
            "canary_tenant_id": cadence["canary_tenant_id"],
            "current_target_tenant_id": cadence["current_target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "cadence": cadence,
            "closure_signals": closure_signals,
            "decisions": self._decisions(cadence=cadence, closure_signals=closure_signals, status=status),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "runbook": self._runbook(cadence_status=str(cadence["status"])),
            "next_tracks": self._next_tracks(status=status, cadence_status=str(cadence["status"])),
        }

    def _blockers(
        self,
        *,
        cadence: dict[str, object],
        closure_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if cadence["status"] == "blocked":
            blockers.extend(f"cadence:{blocker}" for blocker in cadence["blockers"])
            blockers.append("cadence:blocked")
        for key, ready in closure_signals.items():
            if not ready:
                blockers.append(f"closure:{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        cadence: dict[str, object],
        closure_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultExpansionCadenceClosureDecision, ...]:
        return (
            OwnerMfaHashicorpVaultExpansionCadenceClosureDecision(
                key="cadence-review",
                status=str(cadence["status"]),
                summary="closure aceita cadência READY ou PAUSED, mas bloqueia cadência BLOCKED",
            ),
            OwnerMfaHashicorpVaultExpansionCadenceClosureDecision(
                key="evidence-archive",
                status="ready" if closure_signals["evidence_archive_complete"] else "blocked",
                summary="evidências do canário e targets precisam estar arquivadas antes do closure",
            ),
            OwnerMfaHashicorpVaultExpansionCadenceClosureDecision(
                key="rotation-runbook",
                status="ready" if closure_signals["rotation_runbook_queued"] else "blocked",
                summary="rotação de credenciais/segredos precisa estar na fila operacional pós-expansão",
            ),
            OwnerMfaHashicorpVaultExpansionCadenceClosureDecision(
                key="audit-evidence",
                status="ready" if closure_signals["audit_evidence_ready"] else "blocked",
                summary="closure deve deixar pacote pronto para export/auditoria sem expor secret material",
            ),
            OwnerMfaHashicorpVaultExpansionCadenceClosureDecision(
                key="classification",
                status=status,
                summary="closure encerra ou consolida a cadência sem ativar novos tenants",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "cadência futura ainda depende de janelas operacionais e operadores com acesso ao ambiente",
            "tokens/AppRole Hashicorp Vault continuam exigindo rotação e auditoria externas",
            "cada tenant futuro ainda precisa de evidence e monitoring próprios",
            "rollback permanece ação operacional fora do command",
        )

    def _runbook(self, *, cadence_status: str) -> tuple[str, ...]:
        if cadence_status == "paused":
            return (
                "manter cadência pausada até nova decisão operacional",
                "preservar evidência do canário e do target atual",
                "priorizar rotação/runbook/audit evidence antes de nova expansão",
            )
        return (
            "não ativar próximo tenant a partir do closure",
            "se continuar, voltar para tenant expansion review do próximo target",
            "repetir evidence e monitoring por tenant",
        )

    def _next_tracks(self, *, status: str, cadence_status: str) -> tuple[str, ...]:
        if status != "ready":
            return (
                "Owner MFA Hashicorp Vault Next Tenant Expansion Review",
                "Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review",
            )
        if cadence_status == "ready":
            return (
                "Owner MFA Hashicorp Vault Tenant Expansion Review",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Vault/KMS Rotation Runbook Review",
            "Owner MFA Audit Evidence Export Review",
        )


owner_mfa_hashicorp_vault_expansion_cadence_closure_queries = (
    OwnerMfaHashicorpVaultExpansionCadenceClosureQueryService()
)
