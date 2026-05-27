from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.payments.application.refund_sandbox_evidence_commands import (
    ALLOWED_DECISIONS,
    payment_refund_sandbox_evidence_commands,
)


class Command(BaseCommand):
    help = "Anexa evidência sandbox ao ledger de refund sem chamar provider ou alterar status."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, required=True, help="Tenant do refund.")
        parser.add_argument("--refund-key", dest="refund_key", required=True, help="UUID do PaymentRefund.")
        parser.add_argument("--captured-by", dest="captured_by", required=True, help="Operador que capturou a evidência.")
        parser.add_argument(
            "--decision",
            dest="decision",
            required=True,
            choices=sorted(ALLOWED_DECISIONS),
            help="Decisão operacional da evidência.",
        )
        parser.add_argument("--environment", dest="environment", default="sandbox", help="Ambiente da evidência.")
        parser.add_argument("--dry-run-output", dest="dry_run_output", default="", help="Resumo seguro do dry-run.")
        parser.add_argument("--execution-output", dest="execution_output", default="", help="Resumo seguro da execução.")
        parser.add_argument(
            "--provider-dashboard-reference",
            dest="provider_dashboard_reference",
            default="",
            help="Referência externa segura do dashboard do provider.",
        )
        parser.add_argument(
            "--reconciliation-reference",
            dest="reconciliation_reference",
            default="",
            help="Referência segura da revisão de conciliação.",
        )
        parser.add_argument("--notes", dest="notes", default="", help="Notas operacionais sem dados sensíveis.")

    def handle(self, *args, **options):
        result, refund = payment_refund_sandbox_evidence_commands.capture_evidence(
            tenant_id=int(options["tenant_id"]),
            refund_key=options["refund_key"],
            captured_by=options["captured_by"],
            decision=options["decision"],
            environment=options.get("environment") or "sandbox",
            dry_run_output=options.get("dry_run_output") or "",
            execution_output=options.get("execution_output") or "",
            provider_dashboard_reference=options.get("provider_dashboard_reference") or "",
            reconciliation_reference=options.get("reconciliation_reference") or "",
            notes=options.get("notes") or "",
        )
        if refund is None:
            self.stdout.write(self.style.WARNING(f"payment_refund_sandbox_evidence={result}"))
            return

        evidence = dict((getattr(refund, "metadata", {}) or {}).get("sandbox_evidence") or {})
        self.stdout.write(
            "payment_refund_sandbox_evidence "
            f"result={result} "
            f"tenant_id={refund.tenant_id} "
            f"refund_key={refund.refund_key} "
            f"status={refund.status} "
            f"decision={evidence.get('decision', '-') or '-'} "
            f"captured_by={evidence.get('captured_by', '-') or '-'}"
        )
