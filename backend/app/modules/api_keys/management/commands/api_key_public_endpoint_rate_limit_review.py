from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_rate_limit_review_queries import (
    api_key_public_endpoint_rate_limit_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato de rate limit para endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "public-endpoint-active",
            "rate-limit-key-available",
            "per-tenant-and-key-required",
            "cache-backend-required",
            "fixed-window-acceptable",
            "default-limit-config-required",
            "endpoint-override-config-required",
            "retry-after-required",
            "audit-event-required",
            "fail-closed-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_rate_limit_review_queries.get_review(
            public_endpoint_active=options["public_endpoint_active"],
            rate_limit_key_available=options["rate_limit_key_available"],
            per_tenant_and_key_required=options["per_tenant_and_key_required"],
            cache_backend_required=options["cache_backend_required"],
            fixed_window_acceptable=options["fixed_window_acceptable"],
            default_limit_config_required=options["default_limit_config_required"],
            endpoint_override_config_required=options["endpoint_override_config_required"],
            retry_after_required=options["retry_after_required"],
            audit_event_required=options["audit_event_required"],
            fail_closed_required=options["fail_closed_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        policy = review["recommended_policy"]
        self.stdout.write(
            "recommended_policy "
            f"algorithm={policy['algorithm']} scope={policy['scope']} "
            f"default_limit={policy['default_limit']} window={policy['default_window_seconds']} event={policy['event']}"
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
            raise CommandError("API key public endpoint rate limit review is blocked.")
