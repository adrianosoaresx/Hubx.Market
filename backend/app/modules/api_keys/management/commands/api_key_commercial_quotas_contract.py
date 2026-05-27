from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_commercial_quotas_contract_queries import (
    api_key_commercial_quotas_contract_queries,
)


class Command(BaseCommand):
    help = "Revisa o contrato mínimo de quotas comerciais para API keys públicas."

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
            "battery-b-selected-by-operator",
            "battery-a-remaining-deferred",
            "commercial-quota-pressure-confirmed",
            "quota-dimensions-documented",
            "quota-window-documented",
            "quota-default-limits-documented",
            "quota-overage-behavior-documented",
            "quota-error-contract-documented",
            "quota-observability-documented",
            "quota-admin-visibility-documented",
            "no-billing-charge-in-contract",
            "no-plan-enforcement-in-contract",
            "no-runtime-enforcement-in-contract",
            "no-new-endpoint-in-contract",
            "no-sensitive-material-in-contract",
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
        ignored_options = {
            "fail_on_blockers",
            "verbosity",
            "settings",
            "pythonpath",
            "traceback",
            "no_color",
            "force_color",
            "skip_checks",
            "stdout",
            "stderr",
        }
        review = api_key_commercial_quotas_contract_queries.get_review(
            **{key: value for key, value in options.items() if key not in ignored_options}
        )
        contract = review["contract"]
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} "
            f"scope={contract.scope} window={contract.default_window_seconds} limit={contract.default_limit}"
        )
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["closed_scope"]:
            self.stdout.write(f"closed_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key commercial quotas contract is blocked.")
