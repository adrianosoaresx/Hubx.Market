from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_observability_closure_queries import (
    api_key_public_endpoint_observability_closure_queries,
)


class Command(BaseCommand):
    help = "Fecha a trilha de observabilidade de endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        parser.add_argument("--rollout-ready", action="store_true")
        parser.add_argument("--prometheus-activation-deferred", action="store_true", default=True)
        parser.add_argument("--alertmanager-routing-deferred", action="store_true", default=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = api_key_public_endpoint_observability_closure_queries.get_closure(
            rollout_ready=options["rollout_ready"],
            prometheus_activation_deferred=options["prometheus_activation_deferred"],
            alertmanager_routing_deferred=options["alertmanager_routing_deferred"],
        )
        self.stdout.write(
            f"[{str(closure['status']).upper()}] result={closure['result']} module={closure['module']}"
        )
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for name, present in closure["artifacts"].items():
            self.stdout.write(f"artifact name={name} present={present}")
        for blocker in closure["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and closure["blockers"]:
            raise CommandError(closure["blockers"])
