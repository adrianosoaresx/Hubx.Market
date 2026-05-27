from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_hashicorp_vault_production_gate_queries import (
    owner_mfa_hashicorp_vault_production_gate_queries,
)


class Command(BaseCommand):
    help = "Revisa o gate operacional de produção para Hashicorp Vault MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--tenant-scope-confirmed", action="store_true")
        parser.add_argument("--rollout-order-confirmed", action="store_true")
        parser.add_argument("--feature-flags-confirmed", action="store_true")
        parser.add_argument("--support-standby-confirmed", action="store_true")
        parser.add_argument("--rollback-window-confirmed", action="store_true")
        parser.add_argument("--post-activation-monitoring-confirmed", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_hashicorp_vault_production_gate_queries.get_gate(
            tenant_id=options["tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            tenant_scope_confirmed=options["tenant_scope_confirmed"],
            rollout_order_confirmed=options["rollout_order_confirmed"],
            feature_flags_confirmed=options["feature_flags_confirmed"],
            support_standby_confirmed=options["support_standby_confirmed"],
            rollback_window_confirmed=options["rollback_window_confirmed"],
            post_activation_monitoring_confirmed=options["post_activation_monitoring_confirmed"],
        )
        status = str(result["status"]).upper()
        go_no_go = result["go_no_go"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} decision={go_no_go['decision']} "
            f"blocker_count={go_no_go['blocker_count']}"
        )
        for key, confirmed in result["confirmations"].items():
            self.stdout.write(f"confirmation key={key} confirmed={confirmed}")
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for step in result["activation_plan"]:
            self.stdout.write(f"activation_plan={step}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
