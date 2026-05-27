from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_rotation_evidence_queries import (
    owner_mfa_vault_kms_rotation_evidence_queries,
)


@dataclass(frozen=True)
class OwnerMfaVaultKmsPostRotationMonitoringDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsPostRotationMonitoringQueryService:
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
        rotation_executed: bool = False,
        new_credential_active: bool = False,
        old_credential_revoked_or_scheduled: bool = False,
        post_rotation_probe_passed: bool = False,
        owner_login_challenge_passed: bool = False,
        provider_health_ready: bool = False,
        rotation_rollback_not_required: bool = False,
        rotation_evidence_redacted: bool = False,
        post_rotation_window_elapsed: bool = False,
        provider_health_stable: bool = False,
        owner_login_error_spike_absent: bool = False,
        support_incidents_absent: bool = False,
        rollback_signal_absent: bool = False,
        post_rotation_evidence_redacted: bool = False,
    ) -> dict[str, object]:
        evidence = owner_mfa_vault_kms_rotation_evidence_queries.get_evidence(
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
            rotation_scope_documented=rotation_scope_documented,
            rotation_owner_confirmed=rotation_owner_confirmed,
            vault_access_validated=vault_access_validated,
            rotation_window_confirmed=rotation_window_confirmed,
            rollback_credentials_available=rollback_credentials_available,
            post_rotation_probe_defined=post_rotation_probe_defined,
            affected_tenants_listed=affected_tenants_listed,
            evidence_redaction_confirmed=evidence_redaction_confirmed,
            rotation_executed=rotation_executed,
            new_credential_active=new_credential_active,
            old_credential_revoked_or_scheduled=old_credential_revoked_or_scheduled,
            post_rotation_probe_passed=post_rotation_probe_passed,
            owner_login_challenge_passed=owner_login_challenge_passed,
            provider_health_ready=provider_health_ready,
            rotation_rollback_not_required=rotation_rollback_not_required,
            rotation_evidence_redacted=rotation_evidence_redacted,
        )
        signals = {
            "post_rotation_window_elapsed": bool(post_rotation_window_elapsed),
            "provider_health_stable": bool(provider_health_stable),
            "owner_login_error_spike_absent": bool(owner_login_error_spike_absent),
            "support_incidents_absent": bool(support_incidents_absent),
            "rollback_signal_absent": bool(rollback_signal_absent),
            "evidence_redacted": bool(post_rotation_evidence_redacted),
        }
        blockers = self._blockers(evidence=evidence, signals=signals)
        status = self._status(evidence_ready=bool(evidence["ready"]), signals=signals, blockers=blockers)
        return {
            "result": f"owner-mfa-vault-kms-post-rotation-monitoring-{status}",
            "ready": status == "healthy",
            "status": status,
            "classification": status.upper(),
            "canary_tenant_id": evidence["canary_tenant_id"],
            "current_target_tenant_id": evidence["current_target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "rotation_evidence": evidence,
            "signals": signals,
            "decisions": self._decisions(evidence=evidence, signals=signals, status=status),
            "watch_items": self._watch_items(signals=signals),
            "rollback": self._rollback(status=status),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _status(
        self,
        *,
        evidence_ready: bool,
        signals: dict[str, bool],
        blockers: tuple[str, ...],
    ) -> str:
        if not evidence_ready:
            return "blocked"
        if not signals["rollback_signal_absent"]:
            return "rollback"
        if blockers:
            return "blocked"
        if all(signals.values()):
            return "healthy"
        return "watch"

    def _blockers(self, *, evidence: dict[str, object], signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        if not evidence["ready"]:
            blockers.extend(f"evidence:{blocker}" for blocker in evidence["blockers"])
            blockers.append(f"evidence:{evidence['status']}")
        if not signals["rollback_signal_absent"]:
            blockers.append("rollback-signal-present")
        if not signals["evidence_redacted"]:
            blockers.append("evidence-redaction-missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        evidence: dict[str, object],
        signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaVaultKmsPostRotationMonitoringDecision, ...]:
        return (
            OwnerMfaVaultKmsPostRotationMonitoringDecision(
                key="rotation-evidence",
                status=str(evidence["status"]),
                summary="monitoring pós-rotação só segue quando evidence de rotação está READY",
            ),
            OwnerMfaVaultKmsPostRotationMonitoringDecision(
                key="provider-health",
                status="ready" if signals["provider_health_stable"] else "watch",
                summary="provider health precisa permanecer estável após rotação",
            ),
            OwnerMfaVaultKmsPostRotationMonitoringDecision(
                key="owner-login-support",
                status=(
                    "ready"
                    if signals["owner_login_error_spike_absent"] and signals["support_incidents_absent"]
                    else "watch"
                ),
                summary="login/challenge owner e suporte não podem indicar regressão pós-rotação",
            ),
            OwnerMfaVaultKmsPostRotationMonitoringDecision(
                key="rollback-signal",
                status="ready" if signals["rollback_signal_absent"] else "rollback",
                summary="rollback signal pós-rotação exige parar expansão e restaurar credencial se necessário",
            ),
            OwnerMfaVaultKmsPostRotationMonitoringDecision(
                key="classification",
                status=status,
                summary="classificação decide se rotação está estável para retomar operação normal",
            ),
        )

    def _watch_items(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        items = []
        if not signals["post_rotation_window_elapsed"]:
            items.append("post-rotation-window-not-elapsed")
        if not signals["provider_health_stable"]:
            items.append("provider-health-not-stable")
        if not signals["owner_login_error_spike_absent"]:
            items.append("owner-login-error-spike-present")
        if not signals["support_incidents_absent"]:
            items.append("support-incidents-present")
        if not signals["evidence_redacted"]:
            items.append("evidence-redaction-missing")
        return tuple(items)

    def _rollback(self, *, status: str) -> tuple[str, ...]:
        if status == "rollback":
            return (
                "restaurar credencial anterior dentro da janela aprovada",
                "desabilitar endpoint Hashicorp Vault por tenant afetado se login/challenge falhar",
                "interromper expansão de novos tenants",
                "capturar rollback evidence redigida",
            )
        return (
            "não retomar expansão enquanto status for WATCH/BLOCKED",
            "manter credencial anterior disponível até janela pós-rotação fechar HEALTHY",
            "se sinais piorarem, executar rollback operacional documentado",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "healthy":
            return (
                "Owner MFA Vault/KMS Rotation Closure Review",
                "Owner MFA Audit Evidence Export Review",
            )
        if status == "rollback":
            return (
                "Owner MFA Vault/KMS Rotation Rollback Evidence",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Vault/KMS Extended Post-Rotation Monitoring Evidence",
            "Owner MFA Vault/KMS Rotation Evidence Execution",
        )


owner_mfa_vault_kms_post_rotation_monitoring_queries = OwnerMfaVaultKmsPostRotationMonitoringQueryService()
