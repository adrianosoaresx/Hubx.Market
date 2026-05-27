from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries import (
    owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries,
)


class Command(BaseCommand):
    help = "Captura evidência do skeleton de adapter Vault/KMS para segredos TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/skeleton-probe")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
            probe_reference=options["probe_reference"],
        )
        status = str(result["status"]).upper()
        probe = result["probe"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"current_provider={result['current_provider']} target_provider={result['target_provider']} "
            f"probe_result={probe['result']} probe_ready={probe['ready']} secret_returned={probe['secret_returned']}"
        )
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
