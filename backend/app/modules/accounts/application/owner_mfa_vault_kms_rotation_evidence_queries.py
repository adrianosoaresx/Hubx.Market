from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_rotation_runbook_queries import (
    owner_mfa_vault_kms_rotation_runbook_queries,
)


@dataclass(frozen=True)
class OwnerMfaVaultKmsRotationEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsRotationEvidenceQueryService:
    confirmations = (
        "rotation_executed",
        "new_credential_active",
        "old_credential_revoked_or_scheduled",
        "post_rotation_probe_passed",
        "owner_login_challenge_passed",
        "provider_health_ready",
        "rollback_not_required",
        "evidence_redacted",
    )

    def get_evidence(
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
    ) -> dict[str, object]:
        runbook = owner_mfa_vault_kms_rotation_runbook_queries.get_review(
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
        )
        confirmation_values = {
            "rotation_executed": bool(rotation_executed),
            "new_credential_active": bool(new_credential_active),
            "old_credential_revoked_or_scheduled": bool(old_credential_revoked_or_scheduled),
            "post_rotation_probe_passed": bool(post_rotation_probe_passed),
            "owner_login_challenge_passed": bool(owner_login_challenge_passed),
            "provider_health_ready": bool(provider_health_ready),
            "rollback_not_required": bool(rotation_rollback_not_required),
            "evidence_redacted": bool(rotation_evidence_redacted),
        }
        blockers = self._blockers(runbook=runbook, confirmations=confirmation_values)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-vault-kms-rotation-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": runbook["canary_tenant_id"],
            "current_target_tenant_id": runbook["current_target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "runbook": runbook,
            "confirmations": confirmation_values,
            "evidence_pack": self._evidence_pack(runbook=runbook, confirmations=confirmation_values),
            "decisions": self._decisions(runbook=runbook, confirmations=confirmation_values, status=status),
            "rollback": self._rollback(),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(
        self,
        *,
        runbook: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not runbook["ready"]:
            blockers.extend(f"runbook:{blocker}" for blocker in runbook["blockers"])
            blockers.append(f"runbook:{runbook['status']}")
        for key, confirmed in confirmations.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        return tuple(dict.fromkeys(blockers))

    def _evidence_pack(
        self,
        *,
        runbook: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[str, ...]:
        return (
            f"runbook_status={runbook['status']}",
            f"canary_tenant_id={runbook['canary_tenant_id']}",
            f"current_target_tenant_id={runbook['current_target_tenant_id']}",
            f"target_provider={runbook['target_provider']}",
            f"rotation_executed={confirmations['rotation_executed']}",
            f"new_credential_active={confirmations['new_credential_active']}",
            f"old_credential_revoked_or_scheduled={confirmations['old_credential_revoked_or_scheduled']}",
            f"post_rotation_probe_passed={confirmations['post_rotation_probe_passed']}",
            f"owner_login_challenge_passed={confirmations['owner_login_challenge_passed']}",
            f"provider_health_ready={confirmations['provider_health_ready']}",
            f"rollback_not_required={confirmations['rollback_not_required']}",
            f"evidence_redacted={confirmations['evidence_redacted']}",
        )

    def _decisions(
        self,
        *,
        runbook: dict[str, object],
        confirmations: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaVaultKmsRotationEvidenceDecision, ...]:
        return (
            OwnerMfaVaultKmsRotationEvidenceDecision(
                key="rotation-runbook",
                status=str(runbook["status"]),
                summary="evidence só segue quando runbook de rotação está READY",
            ),
            OwnerMfaVaultKmsRotationEvidenceDecision(
                key="credential-state",
                status=(
                    "ready"
                    if confirmations["rotation_executed"]
                    and confirmations["new_credential_active"]
                    and confirmations["old_credential_revoked_or_scheduled"]
                    else "blocked"
                ),
                summary="nova credencial precisa estar ativa e a anterior revogada ou com revogação agendada",
            ),
            OwnerMfaVaultKmsRotationEvidenceDecision(
                key="runtime-validation",
                status=(
                    "ready"
                    if confirmations["post_rotation_probe_passed"]
                    and confirmations["owner_login_challenge_passed"]
                    and confirmations["provider_health_ready"]
                    else "blocked"
                ),
                summary="probe, login/challenge owner e provider health precisam passar após rotação",
            ),
            OwnerMfaVaultKmsRotationEvidenceDecision(
                key="rollback-redaction",
                status=(
                    "ready"
                    if confirmations["rollback_not_required"] and confirmations["evidence_redacted"]
                    else "blocked"
                ),
                summary="rollback não pode ser necessário e evidence precisa permanecer redigida",
            ),
            OwnerMfaVaultKmsRotationEvidenceDecision(
                key="classification",
                status=status,
                summary="evidence registra a rotação executada fora do command sem secret material",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "se validação falhar, restaurar credencial anterior dentro da janela aprovada",
            "desabilitar endpoint Hashicorp Vault por tenant afetado se login/challenge falhar",
            "interromper expansão de novos tenants até provider health voltar a HEALTHY",
            "registrar rollback evidence redigida sem token, secret ou path completo",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Post-Rotation Monitoring Review",
                "Owner MFA Audit Evidence Export Review",
            )
        return (
            "Owner MFA Vault/KMS Rotation Runbook Review",
            "Owner MFA Hashicorp Vault Expansion Cadence Closure Review",
        )


owner_mfa_vault_kms_rotation_evidence_queries = OwnerMfaVaultKmsRotationEvidenceQueryService()
