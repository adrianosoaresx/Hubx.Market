from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.payments.application.refund_execution_commands import payment_refund_execution_commands


def _string(value: object) -> str:
    return str(value or "").strip()


class Command(BaseCommand):
    help = "Valida um refund sandbox específico, com dry-run seguro e sem efeitos cross-module."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, required=True, help="Tenant do refund.")
        parser.add_argument("--refund-key", dest="refund_key", required=True, help="UUID do PaymentRefund.")
        parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Valida sem chamar adapter/provider.")
        parser.add_argument(
            "--require-processing",
            dest="require_processing",
            action="store_true",
            default=True,
            help="Exige status processing antes de validar.",
        )

    def handle(self, *args, **options):
        tenant_id = int(options["tenant_id"])
        refund_key = _string(options["refund_key"])
        dry_run = bool(options.get("dry_run"))
        require_processing = bool(options.get("require_processing"))

        from app.modules.payments.models import PaymentRefund

        refund = (
            PaymentRefund.objects.select_related("order", "payment_attempt")
            .filter(tenant_id=tenant_id, refund_key=refund_key)
            .first()
        )
        if refund is None:
            self.stdout.write(self.style.WARNING("payment_sandbox_refund_validation=unavailable reason=refund-not-found"))
            return

        order_number = _string(getattr(getattr(refund, "order", None), "number", ""))
        blockers = list(getattr(refund, "blockers", []) or [])
        self.stdout.write(
            "payment_sandbox_refund_candidate "
            f"tenant_id={refund.tenant_id} "
            f"order_number={order_number or '-'} "
            f"refund_key={refund.refund_key} "
            f"status={refund.status} "
            f"amount={refund.amount:.2f} "
            f"external_reference={refund.external_reference or '-'} "
            f"idempotency_key={refund.idempotency_key or '-'} "
            f"blockers={','.join(blockers) if blockers else '-'}"
        )

        if require_processing and refund.status != PaymentRefund.Status.PROCESSING:
            self.stdout.write(self.style.WARNING("payment_sandbox_refund_validation=blocked reason=refund-not-processing"))
            return
        if dry_run:
            self.stdout.write(self.style.SUCCESS("payment_sandbox_refund_validation=dry-run result=ready"))
            return

        result, executed_refund = payment_refund_execution_commands.execute_refund(
            tenant_id=tenant_id,
            refund_key=refund_key,
        )
        if executed_refund is None:
            self.stdout.write(self.style.WARNING(f"payment_sandbox_refund_validation={result}"))
            return
        self.stdout.write(
            self.style.SUCCESS(
                "payment_sandbox_refund_validation "
                f"result={result} "
                f"status={executed_refund.status} "
                f"provider_refund_reference={executed_refund.provider_refund_reference or '-'}"
            )
        )
