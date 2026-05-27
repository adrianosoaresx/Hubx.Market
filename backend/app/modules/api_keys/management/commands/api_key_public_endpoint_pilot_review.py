from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_pilot_review_queries import (
    api_key_public_endpoint_pilot_review_queries,
)


class Command(BaseCommand):
    help = "Revisa o primeiro endpoint público piloto para autenticação por API key."

    def add_arguments(self, parser):
        for name in (
            "drf-adapter-available",
            "pilot-endpoint-read-only",
            "tenant-context-required",
            "explicit-scope-required",
            "rate-limit-plan-required",
            "safe-payload-required",
            "no-pii-required",
            "no-admin-ops-reuse-required",
            "versioned-url-required",
            "rollout-flag-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_pilot_review_queries.get_review(
            drf_adapter_available=options["drf_adapter_available"],
            pilot_endpoint_read_only=options["pilot_endpoint_read_only"],
            tenant_context_required=options["tenant_context_required"],
            explicit_scope_required=options["explicit_scope_required"],
            rate_limit_plan_required=options["rate_limit_plan_required"],
            safe_payload_required=options["safe_payload_required"],
            no_pii_required=options["no_pii_required"],
            no_admin_ops_reuse_required=options["no_admin_ops_reuse_required"],
            versioned_url_required=options["versioned_url_required"],
            rollout_flag_required=options["rollout_flag_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        pilot = review["recommended_pilot"]
        self.stdout.write(
            f"recommended_pilot module={pilot['module']} method={pilot['method']} endpoint={pilot['endpoint']} scope={pilot['scope']}"
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
            raise CommandError("API key public endpoint pilot review is blocked.")
