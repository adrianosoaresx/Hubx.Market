from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_real_adapter_contract_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato do adapter real Vault/KMS para segredos TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/skeleton-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--sdk-dependency-confirmed", action="store_true")
        parser.add_argument("--credential-strategy-confirmed", action="store_true")
        parser.add_argument("--network-timeout-confirmed", action="store_true")
        parser.add_argument("--rollout-owner-confirmed", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_real_adapter_contract_queries.get_contract(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            sdk_dependency_confirmed=options["sdk_dependency_confirmed"],
            credential_strategy_confirmed=options["credential_strategy_confirmed"],
            network_timeout_confirmed=options["network_timeout_confirmed"],
            rollout_owner_confirmed=options["rollout_owner_confirmed"],
        )
        status = str(result["status"]).upper()
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} canary_owner={result['canary_owner_email']}"
        )
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for item in result["real_adapter_contract"]:
            self.stdout.write(f"real_adapter_contract={item}")
        for item in result["settings_contract"]:
            self.stdout.write(f"settings_contract={item}")
        for item in result["error_contract"]:
            self.stdout.write(f"error_contract={item}")
        for item in result["test_contract"]:
            self.stdout.write(f"test_contract={item}")
        for item in result["implementation_plan"]:
            self.stdout.write(f"implementation_plan={item}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
