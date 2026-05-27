from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_provider_staging_canary_evidence_queries import (
    owner_mfa_vault_kms_provider_staging_canary_evidence_queries,
)


class Command(BaseCommand):
    help = "Captura evidência declarativa pós-canário staging para provider Vault/KMS TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--target-provider", dest="target_provider", default="hashicorp-vault")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/skeleton-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        parser.add_argument("--evidence-label", dest="evidence_label", default="staging-canary")
        parser.add_argument("--valid-login-passed", action="store_true")
        parser.add_argument("--invalid-challenge-blocked", action="store_true")
        parser.add_argument("--post-health-ready", action="store_true")
        parser.add_argument("--logs-redacted", action="store_true")
        parser.add_argument("--rollback-verified", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_vault_kms_provider_staging_canary_evidence_queries.get_evidence(
            tenant_id=options["tenant_id"],
            target_provider=options["target_provider"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            valid_login_passed=options["valid_login_passed"],
            invalid_challenge_blocked=options["invalid_challenge_blocked"],
            post_health_ready=options["post_health_ready"],
            logs_redacted=options["logs_redacted"],
            rollback_verified=options["rollback_verified"],
            evidence_label=options["evidence_label"],
        )
        status = str(result["status"]).upper()
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"target_provider={result['target_provider']} canary_owner={result['canary_owner_email']} "
            f"evidence_label={result['evidence_label']}"
        )
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for evidence in result["evidence_pack"]:
            self.stdout.write(f"evidence={evidence}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
