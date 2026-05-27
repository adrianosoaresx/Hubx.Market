from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_adapter_contract_queries,
)


class Command(BaseCommand):
    help = "Revisa o contrato técnico do adapter Vault/KMS para segredos TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_adapter_contract_queries.get_contract(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
        )
        status = str(result["status"]).upper()
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']}"
        )
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in result["settings_contract"]:
            self.stdout.write(f"settings_contract={item}")
        for item in result["adapter_interface"]:
            self.stdout.write(f"adapter_interface={item}")
        for item in result["recoverable_errors"]:
            self.stdout.write(f"recoverable_error={item}")
        for item in result["security_controls"]:
            self.stdout.write(f"security_control={item}")
        for item in result["test_contract"]:
            self.stdout.write(f"test_contract={item}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
