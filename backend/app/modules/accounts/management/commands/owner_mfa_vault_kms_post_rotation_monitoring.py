from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_post_rotation_monitoring_queries import (
    owner_mfa_vault_kms_post_rotation_monitoring_queries,
)


class Command(BaseCommand):
    help = "Classifica monitoramento pós-rotação Vault/KMS MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--canary-tenant-id", dest="canary_tenant_id", required=True)
        parser.add_argument("--current-target-tenant-id", dest="current_target_tenant_id", required=True)
        parser.add_argument("--next-target-tenant-ids", dest="next_target_tenant_ids", default="")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        for name in (
            "canary-monitoring-window-elapsed",
            "canary-provider-health-stable",
            "canary-owner-login-error-spike-absent",
            "canary-support-incidents-absent",
            "canary-rollback-signal-absent",
            "canary-evidence-redacted",
            "rollback-runbook-confirmed",
            "residual-risks-accepted",
            "tenant-expansion-plan-documented",
            "expansion-window-confirmed",
            "per-tenant-evidence-required",
            "support-standby-confirmed",
            "rollback-window-confirmed",
            "target-flags-enabled",
            "target-activation-evidence-captured",
            "target-monitoring-scheduled",
            "target-owner-login-challenge-passed",
            "target-provider-health-ready",
            "rollback-not-required",
            "expansion-evidence-redacted",
            "target-monitoring-window-elapsed",
            "target-provider-health-stable",
            "target-owner-login-error-spike-absent",
            "target-support-incidents-absent",
            "target-rollback-signal-absent",
            "evidence-redacted",
            "next-window-confirmed",
            "operator-capacity-confirmed",
            "previous-target-evidence-archived",
            "stop-after-current-target",
            "cadence-decision-recorded",
            "evidence-archive-complete",
            "residual-risks-reviewed",
            "rotation-runbook-queued",
            "audit-evidence-ready",
            "rotation-scope-documented",
            "rotation-owner-confirmed",
            "vault-access-validated",
            "rotation-window-confirmed",
            "rollback-credentials-available",
            "post-rotation-probe-defined",
            "affected-tenants-listed",
            "evidence-redaction-confirmed",
            "rotation-executed",
            "new-credential-active",
            "old-credential-revoked-or-scheduled",
            "post-rotation-probe-passed",
            "owner-login-challenge-passed",
            "provider-health-ready",
            "rotation-rollback-not-required",
            "rotation-evidence-redacted",
            "post-rotation-window-elapsed",
            "provider-health-stable",
            "owner-login-error-spike-absent",
            "support-incidents-absent",
            "rollback-signal-absent",
            "post-rotation-evidence-redacted",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--max-parallel-tenants", type=int, default=1)
        parser.add_argument("--fail-on-rollback", action="store_true")

    def handle(self, *args, **options):
        review = owner_mfa_vault_kms_post_rotation_monitoring_queries.get_review(
            canary_tenant_id=options["canary_tenant_id"],
            current_target_tenant_id=options["current_target_tenant_id"],
            next_target_tenant_ids=options["next_target_tenant_ids"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            canary_monitoring_window_elapsed=options["canary_monitoring_window_elapsed"],
            canary_provider_health_stable=options["canary_provider_health_stable"],
            canary_owner_login_error_spike_absent=options["canary_owner_login_error_spike_absent"],
            canary_support_incidents_absent=options["canary_support_incidents_absent"],
            canary_rollback_signal_absent=options["canary_rollback_signal_absent"],
            canary_evidence_redacted=options["canary_evidence_redacted"],
            rollback_runbook_confirmed=options["rollback_runbook_confirmed"],
            residual_risks_accepted=options["residual_risks_accepted"],
            tenant_expansion_plan_documented=options["tenant_expansion_plan_documented"],
            expansion_window_confirmed=options["expansion_window_confirmed"],
            per_tenant_evidence_required=options["per_tenant_evidence_required"],
            support_standby_confirmed=options["support_standby_confirmed"],
            rollback_window_confirmed=options["rollback_window_confirmed"],
            target_flags_enabled=options["target_flags_enabled"],
            target_activation_evidence_captured=options["target_activation_evidence_captured"],
            target_monitoring_scheduled=options["target_monitoring_scheduled"],
            target_owner_login_challenge_passed=options["target_owner_login_challenge_passed"],
            target_provider_health_ready=options["target_provider_health_ready"],
            rollback_not_required=options["rollback_not_required"],
            expansion_evidence_redacted=options["expansion_evidence_redacted"],
            target_monitoring_window_elapsed=options["target_monitoring_window_elapsed"],
            target_provider_health_stable=options["target_provider_health_stable"],
            target_owner_login_error_spike_absent=options["target_owner_login_error_spike_absent"],
            target_support_incidents_absent=options["target_support_incidents_absent"],
            target_rollback_signal_absent=options["target_rollback_signal_absent"],
            evidence_redacted=options["evidence_redacted"],
            next_window_confirmed=options["next_window_confirmed"],
            operator_capacity_confirmed=options["operator_capacity_confirmed"],
            previous_target_evidence_archived=options["previous_target_evidence_archived"],
            stop_after_current_target=options["stop_after_current_target"],
            max_parallel_tenants=options["max_parallel_tenants"],
            cadence_decision_recorded=options["cadence_decision_recorded"],
            evidence_archive_complete=options["evidence_archive_complete"],
            residual_risks_reviewed=options["residual_risks_reviewed"],
            rotation_runbook_queued=options["rotation_runbook_queued"],
            audit_evidence_ready=options["audit_evidence_ready"],
            rotation_scope_documented=options["rotation_scope_documented"],
            rotation_owner_confirmed=options["rotation_owner_confirmed"],
            vault_access_validated=options["vault_access_validated"],
            rotation_window_confirmed=options["rotation_window_confirmed"],
            rollback_credentials_available=options["rollback_credentials_available"],
            post_rotation_probe_defined=options["post_rotation_probe_defined"],
            affected_tenants_listed=options["affected_tenants_listed"],
            evidence_redaction_confirmed=options["evidence_redaction_confirmed"],
            rotation_executed=options["rotation_executed"],
            new_credential_active=options["new_credential_active"],
            old_credential_revoked_or_scheduled=options["old_credential_revoked_or_scheduled"],
            post_rotation_probe_passed=options["post_rotation_probe_passed"],
            owner_login_challenge_passed=options["owner_login_challenge_passed"],
            provider_health_ready=options["provider_health_ready"],
            rotation_rollback_not_required=options["rotation_rollback_not_required"],
            rotation_evidence_redacted=options["rotation_evidence_redacted"],
            post_rotation_window_elapsed=options["post_rotation_window_elapsed"],
            provider_health_stable=options["provider_health_stable"],
            owner_login_error_spike_absent=options["owner_login_error_spike_absent"],
            support_incidents_absent=options["support_incidents_absent"],
            rollback_signal_absent=options["rollback_signal_absent"],
            post_rotation_evidence_redacted=options["post_rotation_evidence_redacted"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} canary_tenant_id={review['canary_tenant_id']} "
            f"current_target_tenant_id={review['current_target_tenant_id']} target_provider={review['target_provider']} "
            f"classification={review['classification']}"
        )
        for key, value in review["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for item in review["watch_items"]:
            self.stdout.write(f"watch_item={item}")
        for rollback in review["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_rollback"] and review["status"] == "rollback":
            raise CommandError("Owner MFA Vault/KMS post-rotation monitoring requires rollback.")
