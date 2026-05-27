from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries import (
    owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries,
)


class Command(BaseCommand):
    help = "Classifica monitoramento pós-expansão Hashicorp Vault MFA para um tenant-alvo."

    def add_arguments(self, parser):
        parser.add_argument("--canary-tenant-id", dest="canary_tenant_id", required=True)
        parser.add_argument("--target-tenant-id", dest="target_tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--canary-monitoring-window-elapsed", action="store_true")
        parser.add_argument("--canary-provider-health-stable", action="store_true")
        parser.add_argument("--canary-owner-login-error-spike-absent", action="store_true")
        parser.add_argument("--canary-support-incidents-absent", action="store_true")
        parser.add_argument("--canary-rollback-signal-absent", action="store_true")
        parser.add_argument("--canary-evidence-redacted", action="store_true")
        parser.add_argument("--rollback-runbook-confirmed", action="store_true")
        parser.add_argument("--residual-risks-accepted", action="store_true")
        parser.add_argument("--tenant-expansion-plan-documented", action="store_true")
        parser.add_argument("--expansion-window-confirmed", action="store_true")
        parser.add_argument("--per-tenant-evidence-required", action="store_true")
        parser.add_argument("--support-standby-confirmed", action="store_true")
        parser.add_argument("--rollback-window-confirmed", action="store_true")
        parser.add_argument("--target-flags-enabled", action="store_true")
        parser.add_argument("--target-activation-evidence-captured", action="store_true")
        parser.add_argument("--target-monitoring-scheduled", action="store_true")
        parser.add_argument("--target-owner-login-challenge-passed", action="store_true")
        parser.add_argument("--target-provider-health-ready", action="store_true")
        parser.add_argument("--rollback-not-required", action="store_true")
        parser.add_argument("--expansion-evidence-redacted", action="store_true")
        parser.add_argument("--target-monitoring-window-elapsed", action="store_true")
        parser.add_argument("--target-provider-health-stable", action="store_true")
        parser.add_argument("--target-owner-login-error-spike-absent", action="store_true")
        parser.add_argument("--target-support-incidents-absent", action="store_true")
        parser.add_argument("--target-rollback-signal-absent", action="store_true")
        parser.add_argument("--evidence-redacted", action="store_true")
        parser.add_argument("--fail-on-rollback", action="store_true")

    def handle(self, *args, **options):
        review = owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries.get_review(
            canary_tenant_id=options["canary_tenant_id"],
            target_tenant_id=options["target_tenant_id"],
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
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} canary_tenant_id={review['canary_tenant_id']} "
            f"target_tenant_id={review['target_tenant_id']} target_provider={review['target_provider']} "
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
            raise CommandError("Owner MFA Hashicorp Vault target post-expansion monitoring requires rollback.")
