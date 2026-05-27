from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_runtime_authentication_contract_queries import (
    api_key_runtime_authentication_contract_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato runtime de autenticação para API keys tenant-scoped."

    def add_arguments(self, parser):
        for name in (
            "api-key-model-available",
            "bearer-header-required",
            "tenant-context-required",
            "prefix-lookup-required",
            "hash-verification-required",
            "active-status-required",
            "scope-enforcement-required",
            "last-used-tracking-required",
            "auth-failure-audit-required",
            "rate-limit-boundary-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_runtime_authentication_contract_queries.get_review(
            api_key_model_available=options["api_key_model_available"],
            bearer_header_required=options["bearer_header_required"],
            tenant_context_required=options["tenant_context_required"],
            prefix_lookup_required=options["prefix_lookup_required"],
            hash_verification_required=options["hash_verification_required"],
            active_status_required=options["active_status_required"],
            scope_enforcement_required=options["scope_enforcement_required"],
            last_used_tracking_required=options["last_used_tracking_required"],
            auth_failure_audit_required=options["auth_failure_audit_required"],
            rate_limit_boundary_required=options["rate_limit_boundary_required"],
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
            raise CommandError("API key runtime authentication contract is blocked.")
