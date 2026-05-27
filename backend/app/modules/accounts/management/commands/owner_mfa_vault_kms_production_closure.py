from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_production_closure_queries import (
    owner_mfa_vault_kms_production_closure_queries,
)


class Command(BaseCommand):
    help = "Fecha a trilha production do provider Vault/KMS MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--monitoring-window-elapsed", action="store_true")
        parser.add_argument("--provider-health-stable", action="store_true")
        parser.add_argument("--owner-login-error-spike-absent", action="store_true")
        parser.add_argument("--support-incidents-absent", action="store_true")
        parser.add_argument("--rollback-signal-absent", action="store_true")
        parser.add_argument("--evidence-redacted", action="store_true")
        parser.add_argument("--rollback-runbook-confirmed", action="store_true")
        parser.add_argument("--residual-risks-accepted", action="store_true")
        parser.add_argument("--tenant-expansion-plan-documented", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = owner_mfa_vault_kms_production_closure_queries.get_closure(
            tenant_id=options["tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            monitoring_window_elapsed=options["monitoring_window_elapsed"],
            provider_health_stable=options["provider_health_stable"],
            owner_login_error_spike_absent=options["owner_login_error_spike_absent"],
            support_incidents_absent=options["support_incidents_absent"],
            rollback_signal_absent=options["rollback_signal_absent"],
            evidence_redacted=options["evidence_redacted"],
            rollback_runbook_confirmed=options["rollback_runbook_confirmed"],
            residual_risks_accepted=options["residual_risks_accepted"],
            tenant_expansion_plan_documented=options["tenant_expansion_plan_documented"],
        )
        self.stdout.write(
            f"[{str(closure['status']).upper()}] result={closure['result']} tenant_id={closure['tenant_id']} "
            f"target_provider={closure['target_provider']}"
        )
        for key, value in closure["closure_signals"].items():
            self.stdout.write(f"closure_signal key={key} value={value}")
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in closure["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for guardrail in closure["expansion_guardrails"]:
            self.stdout.write(f"expansion_guardrail={guardrail}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not closure["ready"]:
            raise CommandError("Owner MFA Vault/KMS production closure is not ready.")
