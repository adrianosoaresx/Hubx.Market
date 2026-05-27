from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_expansion_review_queries import (
    api_key_public_endpoint_expansion_review_queries,
)


class Command(BaseCommand):
    help = "Revisa expansão de endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "post-activation-monitoring-ready",
            "candidate-endpoint-identified",
            "read-only-required",
            "tenant-context-required",
            "explicit-scope-required",
            "rate-limit-required",
            "observability-required",
            "payload-contract-required",
            "no-pii-required",
            "no-cross-module-leak-required",
            "rollout-flag-required",
            "expansion-deferred-until-contract",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_expansion_review_queries.get_review(
            post_activation_monitoring_ready=options["post_activation_monitoring_ready"],
            candidate_endpoint_identified=options["candidate_endpoint_identified"],
            read_only_required=options["read_only_required"],
            tenant_context_required=options["tenant_context_required"],
            explicit_scope_required=options["explicit_scope_required"],
            rate_limit_required=options["rate_limit_required"],
            observability_required=options["observability_required"],
            payload_contract_required=options["payload_contract_required"],
            no_pii_required=options["no_pii_required"],
            no_cross_module_leak_required=options["no_cross_module_leak_required"],
            rollout_flag_required=options["rollout_flag_required"],
            expansion_deferred_until_contract=options["expansion_deferred_until_contract"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for key, value in review["recommended_candidate"].items():
            self.stdout.write(f"recommended_candidate {key}={value}")
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
            raise CommandError("API key public endpoint expansion review is blocked.")
