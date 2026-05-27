from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_hashicorp_vault_post_activation_monitoring_queries import (
    owner_mfa_hashicorp_vault_post_activation_monitoring_queries,
)


class Command(BaseCommand):
    help = "Classifica monitoramento pós-ativação Hashicorp Vault MFA owner/admin."

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
        parser.add_argument("--fail-on-rollback", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_hashicorp_vault_post_activation_monitoring_queries.get_review(
            tenant_id=options["tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            monitoring_window_elapsed=options["monitoring_window_elapsed"],
            provider_health_stable=options["provider_health_stable"],
            owner_login_error_spike_absent=options["owner_login_error_spike_absent"],
            support_incidents_absent=options["support_incidents_absent"],
            rollback_signal_absent=options["rollback_signal_absent"],
            evidence_redacted=options["evidence_redacted"],
        )
        self.stdout.write(
            f"[{str(result['status']).upper()}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} classification={result['classification']}"
        )
        for key, value in result["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for item in result["watch_items"]:
            self.stdout.write(f"watch_item={item}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_rollback"] and result["status"] == "rollback":
            raise CommandError("Owner MFA Hashicorp Vault post-activation monitoring requires rollback.")
