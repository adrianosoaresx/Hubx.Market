from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.accounts.application.owner_mfa_enrollment_closure_queries import owner_mfa_enrollment_closure_queries


class Command(BaseCommand):
    help = "Fecha a trilha de enrollment MFA owner/admin."

    def handle(self, *args, **options):
        closure = owner_mfa_enrollment_closure_queries.get_closure()
        self.stdout.write(self.style.SUCCESS(f"[READY] mfa_sso_mode={closure['mfa_sso_mode']}"))
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
