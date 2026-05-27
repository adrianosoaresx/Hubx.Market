from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_expansion_cadence_closure_queries import (
    owner_mfa_hashicorp_vault_expansion_cadence_closure_queries,
)


@dataclass(frozen=True)
class OwnerMfaVaultKmsRotationRunbookDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsRotationRunbookQueryService:
    def get_review(
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
        rotation_scope_documented: bool = False,
        rotation_owner_confirmed: bool = False,
        vault_access_validated: bool = False,
        rotation_window_confirmed: bool = False,
        rollback_credentials_available: bool = False,
        post_rotation_probe_defined: bool = False,
        affected_tenants_listed: bool = False,
        evidence_redaction_confirmed: bool = False,
    ) -> dict[str, object]:
        closure = owner_mfa_hashicorp_vault_expansion_cadence_closure_queries.get_closure(
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
            cadence_decision_recorded=cadence_decision_recorded,
            evidence_archive_complete=evidence_archive_complete,
            residual_risks_reviewed=residual_risks_reviewed,
            rotation_runbook_queued=rotation_runbook_queued,
            audit_evidence_ready=audit_evidence_ready,
        )
        runbook_signals = {
            "rotation_scope_documented": bool(rotation_scope_documented),
            "rotation_owner_confirmed": bool(rotation_owner_confirmed),
            "vault_access_validated": bool(vault_access_validated),
            "rotation_window_confirmed": bool(rotation_window_confirmed),
            "rollback_credentials_available": bool(rollback_credentials_available),
            "post_rotation_probe_defined": bool(post_rotation_probe_defined),
            "affected_tenants_listed": bool(affected_tenants_listed),
            "evidence_redaction_confirmed": bool(evidence_redaction_confirmed),
        }
        blockers = self._blockers(closure=closure, runbook_signals=runbook_signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-rotation-runbook-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": closure["canary_tenant_id"],
            "current_target_tenant_id": closure["current_target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "closure": closure,
            "runbook_signals": runbook_signals,
            "decisions": self._decisions(closure=closure, runbook_signals=runbook_signals, status=status),
            "blockers": blockers,
            "rotation_steps": self._rotation_steps(),
            "rollback_steps": self._rollback_steps(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(
        self,
        *,
        closure: dict[str, object],
        runbook_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not closure["ready"]:
            blockers.extend(f"closure:{blocker}" for blocker in closure["blockers"])
            blockers.append(f"closure:{closure['status']}")
        for key, ready in runbook_signals.items():
            if not ready:
                blockers.append(f"runbook:{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        closure: dict[str, object],
        runbook_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaVaultKmsRotationRunbookDecision, ...]:
        return (
            OwnerMfaVaultKmsRotationRunbookDecision(
                key="cadence-closure",
                status=str(closure["status"]),
                summary="rotação só é revisada após closure da cadência estar READY",
            ),
            OwnerMfaVaultKmsRotationRunbookDecision(
                key="rotation-scope",
                status="ready" if runbook_signals["rotation_scope_documented"] and runbook_signals["affected_tenants_listed"] else "blocked",
                summary="escopo e tenants afetados precisam estar explícitos antes da rotação",
            ),
            OwnerMfaVaultKmsRotationRunbookDecision(
                key="operator-access",
                status="ready" if runbook_signals["rotation_owner_confirmed"] and runbook_signals["vault_access_validated"] else "blocked",
                summary="owner de rotação e acesso ao Vault precisam estar validados",
            ),
            OwnerMfaVaultKmsRotationRunbookDecision(
                key="rollback-validation",
                status=(
                    "ready"
                    if runbook_signals["rollback_credentials_available"]
                    and runbook_signals["post_rotation_probe_defined"]
                    and runbook_signals["evidence_redaction_confirmed"]
                    else "blocked"
                ),
                summary="rollback, probe pós-rotação e redaction precisam estar definidos",
            ),
            OwnerMfaVaultKmsRotationRunbookDecision(
                key="classification",
                status=status,
                summary="runbook prepara rotação operacional, mas não executa credencial",
            ),
        )

    def _rotation_steps(self) -> tuple[str, ...]:
        return (
            "congelar expansão de novos tenants durante a janela de rotação",
            "gerar nova credencial/token/AppRole fora do command",
            "atualizar segredo/configuração operacional fora do command",
            "executar probe Hashicorp Vault pós-rotação",
            "executar login/challenge owner em tenant canário e target afetado",
            "arquivar evidência redigida sem token, secret ou path completo",
        )

    def _rollback_steps(self) -> tuple[str, ...]:
        return (
            "restaurar credencial anterior somente dentro da janela aprovada",
            "desabilitar endpoint Hashicorp Vault por tenant se login/challenge falhar",
            "interromper novas expansões até health voltar a HEALTHY",
            "registrar evidência de rollback redigida",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Rotation Evidence Execution",
                "Owner MFA Audit Evidence Export Review",
            )
        return (
            "Owner MFA Hashicorp Vault Expansion Cadence Closure Review",
            "Owner MFA Vault/KMS Rotation Runbook Review",
        )


owner_mfa_vault_kms_rotation_runbook_queries = OwnerMfaVaultKmsRotationRunbookQueryService()
