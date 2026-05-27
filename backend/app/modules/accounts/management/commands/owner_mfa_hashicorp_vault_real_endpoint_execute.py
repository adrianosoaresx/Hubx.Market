from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_hashicorp_vault_real_endpoint_execution_queries import (
    owner_mfa_hashicorp_vault_real_endpoint_execution_queries,
)


class Command(BaseCommand):
    help = "Captura evidência do endpoint real Hashicorp Vault para TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_hashicorp_vault_real_endpoint_execution_queries.get_evidence(
            tenant_id=options["tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
        )
        status = str(result["status"]).upper()
        probe = result["probe"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} endpoint_enabled={result['endpoint_enabled']} "
            f"probe_result={probe['result']} probe_ready={probe['ready']} secret_returned={probe['secret_returned']}"
        )
        for setting in result["settings_contract"]:
            self.stdout.write(f"setting_contract={setting}")
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
