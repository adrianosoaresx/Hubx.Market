from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_expansion_closure_queries import (
    api_key_public_endpoint_expansion_closure_queries,
)


class Command(BaseCommand):
    help = "Fecha a expansão inicial de endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        parser.add_argument("--list-endpoint-ready", action="store_true")
        parser.add_argument("--detail-endpoint-ready", action="store_true")
        parser.add_argument("--observability-ready", action="store_true")
        parser.add_argument("--no-additional-endpoint-selected", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = api_key_public_endpoint_expansion_closure_queries.get_closure(
            list_endpoint_ready=options["list_endpoint_ready"],
            detail_endpoint_ready=options["detail_endpoint_ready"],
            observability_ready=options["observability_ready"],
            no_additional_endpoint_selected=options["no_additional_endpoint_selected"],
        )
        self.stdout.write(
            f"[{str(closure['status']).upper()}] result={closure['result']} module={closure['module']}"
        )
        for name, present in closure["artifacts"].items():
            self.stdout.write(f"artifact name={name} present={present}")
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in closure["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in closure["closed_scope"]:
            self.stdout.write(f"closed_scope={item}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not closure["ready"]:
            raise CommandError("API key public endpoint expansion closure is blocked.")
