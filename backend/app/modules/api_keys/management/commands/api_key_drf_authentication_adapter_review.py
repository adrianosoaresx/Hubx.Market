from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_drf_authentication_adapter_review_queries import (
    api_key_drf_authentication_adapter_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato do adapter DRF para autenticação por API key."

    def add_arguments(self, parser):
        for name in (
            "runtime-service-available",
            "tenant-middleware-required",
            "per-view-opt-in-required",
            "global-drf-auth-forbidden",
            "required-scope-mapping-required",
            "safe-principal-required",
            "permission-class-required",
            "rate-limit-hook-required",
            "failure-response-contract-required",
            "no-public-endpoint-in-adapter",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_drf_authentication_adapter_review_queries.get_review(
            runtime_service_available=options["runtime_service_available"],
            tenant_middleware_required=options["tenant_middleware_required"],
            per_view_opt_in_required=options["per_view_opt_in_required"],
            global_drf_auth_forbidden=options["global_drf_auth_forbidden"],
            required_scope_mapping_required=options["required_scope_mapping_required"],
            safe_principal_required=options["safe_principal_required"],
            permission_class_required=options["permission_class_required"],
            rate_limit_hook_required=options["rate_limit_hook_required"],
            failure_response_contract_required=options["failure_response_contract_required"],
            no_public_endpoint_in_adapter=options["no_public_endpoint_in_adapter"],
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
            raise CommandError("API key DRF authentication adapter review is blocked.")
