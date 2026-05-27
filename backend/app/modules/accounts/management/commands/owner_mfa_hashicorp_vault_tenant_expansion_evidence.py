from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries import (
    owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries,
)


class Command(BaseCommand):
    help = "Captura evidência declarativa da expansão Hashicorp Vault MFA para um tenant-alvo."

    def add_arguments(self, parser):
        parser.add_argument("--canary-tenant-id", dest="canary_tenant_id", required=True)
        parser.add_argument("--target-tenant-id", dest="target_tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--monitoring-window-elapsed", action="store_true")
        parser.add_argument("--provider-health-stable", action="store_true")
        parser.add_argument("--owner-login-error-spike-absent", action="store_true")
        parser.add_argument("--support-incidents-absent", action="store_true")
        parser.add_argument("--rollback-signal-absent", action="store_true")
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
        parser.add_argument("--evidence-redacted", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        evidence = owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries.get_evidence(
            canary_tenant_id=options["canary_tenant_id"],
            target_tenant_id=options["target_tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            monitoring_window_elapsed=options["monitoring_window_elapsed"],
            provider_health_stable=options["provider_health_stable"],
            owner_login_error_spike_absent=options["owner_login_error_spike_absent"],
            support_incidents_absent=options["support_incidents_absent"],
            rollback_signal_absent=options["rollback_signal_absent"],
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
            evidence_redacted=options["evidence_redacted"],
        )
        self.stdout.write(
            f"[{str(evidence['status']).upper()}] result={evidence['result']} "
            f"canary_tenant_id={evidence['canary_tenant_id']} target_tenant_id={evidence['target_tenant_id']} "
            f"target_provider={evidence['target_provider']}"
        )
        for item in evidence["evidence_pack"]:
            self.stdout.write(f"evidence={item}")
        for key, confirmed in evidence["confirmations"].items():
            self.stdout.write(f"confirmation key={key} confirmed={confirmed}")
        for decision in evidence["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for rollback in evidence["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for blocker in evidence["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in evidence["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and evidence["blockers"]:
            raise CommandError("Owner MFA Hashicorp Vault tenant expansion evidence is blocked.")
