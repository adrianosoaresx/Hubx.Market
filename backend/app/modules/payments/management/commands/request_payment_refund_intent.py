from django.core.management.base import BaseCommand

from app.modules.payments.application.refund_ledger_commands import payment_refund_ledger_commands


class Command(BaseCommand):
    help = "Registra uma intenção idempotente de refund no ledger, sem chamar provider."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, required=True, help="Tenant do pedido.")
        parser.add_argument("--order-number", dest="order_number", required=True, help="Número do pedido.")
        parser.add_argument("--idempotency-key", dest="idempotency_key", required=True, help="Chave idempotente da solicitação.")
        parser.add_argument("--amount", dest="amount", default="", help="Valor do refund. Se vazio, usa total do pedido.")
        parser.add_argument("--reason-code", dest="reason_code", default="", help="Motivo operacional do refund.")

    def handle(self, *args, **options):
        result, refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=int(options["tenant_id"]),
            order_number=options["order_number"],
            idempotency_key=options["idempotency_key"],
            amount=options.get("amount") or None,
            reason_code=options.get("reason_code") or "",
        )
        if refund is None:
            self.stdout.write(self.style.WARNING(f"payment_refund_intent={result}"))
            return

        blockers = ",".join(refund.blockers or []) if refund.blockers else "-"
        self.stdout.write(
            "payment_refund_intent "
            f"result={result} "
            f"tenant_id={refund.tenant_id} "
            f"order_number={getattr(refund.order, 'number', '')} "
            f"refund_key={refund.refund_key} "
            f"status={refund.status} "
            f"amount={refund.amount:.2f} "
            f"idempotency_key={refund.idempotency_key} "
            f"external_reference={refund.external_reference or '-'} "
            f"blockers={blockers}"
        )
