from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_partner_activation_smoke_execution_queries import (
    api_key_partner_activation_smoke_execution_queries,
)


class Command(BaseCommand):
    help = "Revisa a execução sanitizada do smoke de ativação de parceiro para API key pública."

    def add_arguments(self, parser):
        for name in (
            "smoke-contract-ready",
            "list-endpoint-checked",
            "detail-endpoint-checked",
            "list-status-expected",
            "detail-status-expected",
            "auth-failure-negative-checked",
            "observability-signal-checked",
            "rollback-not-required",
            "redaction-confirmed",
            "no-secret-material-recorded",
            "no-runtime-change-performed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--partner-reference", default="")
        parser.add_argument("--tenant-reference", default="")
        parser.add_argument("--target-environment", default="")
        parser.add_argument("--evidence-reference", default="")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_partner_activation_smoke_execution_queries.get_review(
            **self._review_options(options=options)
        )
        identifiers = review["identifiers"]
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} "
            f"partner={identifiers['partner_reference']} tenant={identifiers['tenant_reference']} "
            f"environment={identifiers['target_environment']} evidence={identifiers['evidence_reference']}"
        )
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["executed_checks"]:
            self.stdout.write(f"executed_check={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key partner activation smoke execution is blocked.")

    def _review_options(self, *, options: dict[str, object]) -> dict[str, object]:
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
        return {key: value for key, value in options.items() if key not in ignored_options}
