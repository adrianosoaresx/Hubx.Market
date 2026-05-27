from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_production_activation_evidence_queries import (
    owner_mfa_vault_kms_provider_production_activation_evidence_queries,
)


class Command(BaseCommand):
    help = "Captura evidência declarativa da ativação production Vault/KMS MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--deployment-completed", action="store_true")
        parser.add_argument("--flags-enabled-for-tenant", action="store_true")
        parser.add_argument("--post-deploy-probe-passed", action="store_true")
        parser.add_argument("--owner-login-challenge-passed", action="store_true")
        parser.add_argument("--provider-health-ready", action="store_true")
        parser.add_argument("--rollback-not-required", action="store_true")
        parser.add_argument("--evidence-redacted", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_production_activation_evidence_queries.get_evidence(
            tenant_id=options["tenant_id"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            deployment_completed=options["deployment_completed"],
            flags_enabled_for_tenant=options["flags_enabled_for_tenant"],
            post_deploy_probe_passed=options["post_deploy_probe_passed"],
            owner_login_challenge_passed=options["owner_login_challenge_passed"],
            provider_health_ready=options["provider_health_ready"],
            rollback_not_required=options["rollback_not_required"],
            evidence_redacted=options["evidence_redacted"],
        )
        status = str(result["status"]).upper()
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']}"
        )
        for evidence in result["evidence_pack"]:
            self.stdout.write(f"evidence={evidence}")
        for key, confirmed in result["confirmations"].items():
            self.stdout.write(f"confirmation key={key} confirmed={confirmed}")
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
