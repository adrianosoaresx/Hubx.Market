from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_partner_documentation_execution_review_queries import (
    api_key_partner_documentation_execution_review_queries,
)


class Command(BaseCommand):
    help = "Revisa o pacote operacional/publicável de documentação de parceiros para API pública."

    def add_arguments(self, parser):
        for name in (
            "model-ready",
            "runtime-auth-ready",
            "drf-adapter-ready",
            "public-endpoints-ready",
            "observability-ready",
            "expansion-closed",
            "no-billing-or-quotas-required",
            "no-secret-exposure-confirmed",
            "partner-docs-versioned",
            "endpoint-examples-documented",
            "activation-checklist-ready",
            "error-contract-documented",
            "safe-examples-confirmed",
            "no-new-endpoint-required",
            "no-quota-or-billing-required",
            "delivery-channel-documented",
            "support-handoff-documented",
            "smoke-evidence-template-ready",
            "change-control-documented",
            "owner-approved",
            "no-runtime-change-required",
            "no-commercial-terms-included",
            "no-sensitive-material-included",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_partner_documentation_execution_review_queries.get_review(
            model_ready=options["model_ready"],
            runtime_auth_ready=options["runtime_auth_ready"],
            drf_adapter_ready=options["drf_adapter_ready"],
            public_endpoints_ready=options["public_endpoints_ready"],
            observability_ready=options["observability_ready"],
            expansion_closed=options["expansion_closed"],
            no_billing_or_quotas_required=options["no_billing_or_quotas_required"],
            no_secret_exposure_confirmed=options["no_secret_exposure_confirmed"],
            partner_docs_versioned=options["partner_docs_versioned"],
            endpoint_examples_documented=options["endpoint_examples_documented"],
            activation_checklist_ready=options["activation_checklist_ready"],
            error_contract_documented=options["error_contract_documented"],
            safe_examples_confirmed=options["safe_examples_confirmed"],
            no_new_endpoint_required=options["no_new_endpoint_required"],
            no_quota_or_billing_required=options["no_quota_or_billing_required"],
            delivery_channel_documented=options["delivery_channel_documented"],
            support_handoff_documented=options["support_handoff_documented"],
            smoke_evidence_template_ready=options["smoke_evidence_template_ready"],
            change_control_documented=options["change_control_documented"],
            owner_approved=options["owner_approved"],
            no_runtime_change_required=options["no_runtime_change_required"],
            no_commercial_terms_included=options["no_commercial_terms_included"],
            no_sensitive_material_included=options["no_sensitive_material_included"],
        )
        self.stdout.write(f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}")
        for name, present in review["execution_artifacts"].items():
            self.stdout.write(f"artifact name={name} present={present}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["delivery_scope"]:
            self.stdout.write(f"delivery_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key partner documentation execution review is blocked.")
