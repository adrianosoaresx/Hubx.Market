from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_sso_readiness_queries import owner_mfa_sso_readiness_queries


class Command(BaseCommand):
    help = "Revisa o contrato/readiness de MFA/SSO para owners/admins."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando readiness estiver bloqueado.")

    def handle(self, *args, **options):
        readiness = owner_mfa_sso_readiness_queries.get_readiness()
        status = "READY" if readiness["ready"] else "BLOCKED"
        blockers = ",".join(readiness["blockers"]) if readiness["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] mode={readiness['mode']} mfa_required={str(readiness['mfa_required']).lower()} "
                f"mfa_provider={readiness['mfa_provider'] or 'none'} sso_enabled={str(readiness['sso_enabled']).lower()} "
                f"sso_provider={readiness['sso_provider'] or 'none'} blockers={blockers}"
            )
        )
        for contract in readiness["contracts"]:
            self.stdout.write(f"contract key={contract.key} status={contract.status} summary={contract.summary}")
        for risk in readiness["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in readiness["next_tracks"]:
            self.stdout.write(f"next_track={track}")

        if options.get("fail_on_blockers") and not readiness["ready"]:
            raise CommandError("Owner MFA/SSO readiness blocked.")
