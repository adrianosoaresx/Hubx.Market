from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_partner_onboarding_closure_queries import (
    api_key_partner_onboarding_closure_queries,
)


class Command(BaseCommand):
    help = "Fecha a trilha de onboarding/documentação de parceiros da API pública."

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
            "publication-confirmed",
            "support-notified",
            "activation-status-recorded",
            "smoke-template-attached",
            "redaction-confirmed",
            "no-credential-shared",
            "no-runtime-activation-performed",
            "onboarding-scope-closed",
            "residual-risks-accepted",
            "next-roi-decision-recorded",
            "partner-activation-deferred",
            "commercial-quotas-deferred",
            "new-endpoint-expansion-deferred",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--published-version", default="")
        parser.add_argument("--approved-channel", default="")
        parser.add_argument("--target-audience", default="")
        parser.add_argument("--tenant-reference", default="")
        parser.add_argument("--published-at", default="")
        parser.add_argument("--evidence-reference", default="")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = api_key_partner_onboarding_closure_queries.get_closure(
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
            published_version=options["published_version"],
            approved_channel=options["approved_channel"],
            target_audience=options["target_audience"],
            tenant_reference=options["tenant_reference"],
            published_at=options["published_at"],
            evidence_reference=options["evidence_reference"],
            publication_confirmed=options["publication_confirmed"],
            support_notified=options["support_notified"],
            activation_status_recorded=options["activation_status_recorded"],
            smoke_template_attached=options["smoke_template_attached"],
            redaction_confirmed=options["redaction_confirmed"],
            no_credential_shared=options["no_credential_shared"],
            no_runtime_activation_performed=options["no_runtime_activation_performed"],
            onboarding_scope_closed=options["onboarding_scope_closed"],
            residual_risks_accepted=options["residual_risks_accepted"],
            next_roi_decision_recorded=options["next_roi_decision_recorded"],
            partner_activation_deferred=options["partner_activation_deferred"],
            commercial_quotas_deferred=options["commercial_quotas_deferred"],
            new_endpoint_expansion_deferred=options["new_endpoint_expansion_deferred"],
        )
        self.stdout.write(f"[{str(closure['status']).upper()}] result={closure['result']} module={closure['module']}")
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
            raise CommandError("API key partner onboarding closure is blocked.")
