from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_sdk_dependency_review_queries import (
    owner_mfa_vault_kms_provider_sdk_dependency_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato de dependência SDK para provider Vault/KMS TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/real-adapter-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--dependency-pinned-confirmed", action="store_true")
        parser.add_argument("--import-optional-confirmed", action="store_true")
        parser.add_argument("--deploy-rollback-confirmed", action="store_true")
        parser.add_argument("--license-review-confirmed", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_sdk_dependency_review_queries.get_review(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            dependency_pinned_confirmed=options["dependency_pinned_confirmed"],
            import_optional_confirmed=options["import_optional_confirmed"],
            deploy_rollback_confirmed=options["deploy_rollback_confirmed"],
            license_review_confirmed=options["license_review_confirmed"],
        )
        status = str(result["status"]).upper()
        dependency_contract = result["dependency_contract"]
        import_contract = result["import_contract"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} packages={','.join(dependency_contract['packages']) or 'none'} "
            f"imports={','.join(import_contract['imports']) or 'none'}"
        )
        for key, confirmed in result["confirmations"].items():
            self.stdout.write(f"confirmation key={key} confirmed={confirmed}")
        self.stdout.write(f"dependency_contract={dependency_contract['pinning']}")
        self.stdout.write(f"import_contract={import_contract['strategy']}")
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
