from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_governance_closure_queries import api_key_governance_closure_queries


class Command(BaseCommand):
    help = "Fecha a trilha de governança de API keys com artefatos, decisões e riscos residuais."

    def add_arguments(self, parser):
        parser.add_argument("--model-ready", action="store_true")
        parser.add_argument("--runtime-auth-ready", action="store_true")
        parser.add_argument("--drf-adapter-ready", action="store_true")
        parser.add_argument("--public-endpoints-ready", action="store_true")
        parser.add_argument("--observability-ready", action="store_true")
        parser.add_argument("--expansion-closed", action="store_true")
        parser.add_argument("--no-billing-or-quotas-required", action="store_true")
        parser.add_argument("--no-secret-exposure-confirmed", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = api_key_governance_closure_queries.get_closure(
            model_ready=options["model_ready"],
            runtime_auth_ready=options["runtime_auth_ready"],
            drf_adapter_ready=options["drf_adapter_ready"],
            public_endpoints_ready=options["public_endpoints_ready"],
            observability_ready=options["observability_ready"],
            expansion_closed=options["expansion_closed"],
            no_billing_or_quotas_required=options["no_billing_or_quotas_required"],
            no_secret_exposure_confirmed=options["no_secret_exposure_confirmed"],
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
            raise CommandError("API key governance closure is blocked.")
