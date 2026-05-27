from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_endpoint_review_queries import (
    owner_mfa_vault_kms_provider_real_endpoint_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato do primeiro endpoint real Vault/KMS para TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/sdk-adapter-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--endpoint-url-confirmed", action="store_true")
        parser.add_argument("--auth-strategy-confirmed", action="store_true")
        parser.add_argument("--secret-path-contract-confirmed", action="store_true")
        parser.add_argument("--timeout-budget-confirmed", action="store_true")
        parser.add_argument("--rollback-confirmed", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_real_endpoint_review_queries.get_review(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            endpoint_url_confirmed=options["endpoint_url_confirmed"],
            auth_strategy_confirmed=options["auth_strategy_confirmed"],
            secret_path_contract_confirmed=options["secret_path_contract_confirmed"],
            timeout_budget_confirmed=options["timeout_budget_confirmed"],
            rollback_confirmed=options["rollback_confirmed"],
        )
        status = str(result["status"]).upper()
        endpoint_contract = result["endpoint_contract"]
        secret_contract = result["secret_contract"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} endpoint_provider={endpoint_contract['provider']}"
        )
        self.stdout.write(f"endpoint_contract={endpoint_contract['summary']}")
        self.stdout.write(f"endpoint_settings={','.join(endpoint_contract['settings']) or 'none'}")
        self.stdout.write(f"secret_contract={secret_contract['redaction']}")
        for key, confirmed in result["confirmations"].items():
            self.stdout.write(f"confirmation key={key} confirmed={confirmed}")
        for failure in result["failure_contract"]:
            self.stdout.write(f"failure_contract={failure}")
        for test in result["test_contract"]:
            self.stdout.write(f"test_contract={test}")
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
