from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_governance_foundation_queries import (
    api_key_governance_foundation_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato mínimo de governança para API keys tenant-scoped."

    def add_arguments(self, parser):
        for name in (
            "public-api-surface-confirmed",
            "tenant-scoped-model-required",
            "hashed-secret-storage-required",
            "scoped-permissions-required",
            "revocation-required",
            "audit-events-required",
            "last-used-tracking-required",
            "rate-limit-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_governance_foundation_queries.get_review(
            public_api_surface_confirmed=options["public_api_surface_confirmed"],
            tenant_scoped_model_required=options["tenant_scoped_model_required"],
            hashed_secret_storage_required=options["hashed_secret_storage_required"],
            scoped_permissions_required=options["scoped_permissions_required"],
            revocation_required=options["revocation_required"],
            audit_events_required=options["audit_events_required"],
            last_used_tracking_required=options["last_used_tracking_required"],
            rate_limit_required=options["rate_limit_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for key, value in review["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for requirement in review["requirements"]:
            self.stdout.write(f"requirement key={requirement.key} summary={requirement.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key governance foundation is blocked.")
