from django.core.management.base import BaseCommand

from app.modules.payments.application.refund_reversal_queries import payment_refund_readiness_queries


class Command(BaseCommand):
    help = "Lista pedidos candidatos ou bloqueados para refund/reversal financeiro, sem executar estorno."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, default=0, help="Tenant obrigatório para auditoria.")
        parser.add_argument("--ready-only", dest="ready_only", action="store_true", help="Mostra somente candidatos prontos.")
        parser.add_argument("--limit", dest="limit", type=int, default=250, help="Número máximo de pedidos auditados.")

    def handle(self, *args, **options):
        tenant_id = int(options.get("tenant_id") or 0) or None
        if not tenant_id:
            self.stdout.write(self.style.WARNING("payment_refund_candidates=blocked reason=tenant-required"))
            return

        limit = min(max(1, int(options.get("limit") or 250)), 1000)
        ready_only = bool(options.get("ready_only"))
        candidates = payment_refund_readiness_queries.list_refund_candidates(tenant_id=tenant_id, limit=limit)
        if ready_only:
            candidates = [candidate for candidate in candidates if candidate["readiness"] == "ready"]

        if not candidates:
            self.stdout.write("payment_refund_candidates=0")
            return

        for candidate in candidates:
            blockers = ",".join(candidate["blockers"]) if candidate["blockers"] else "-"
            self.stdout.write(
                "payment_refund_candidate "
                f"tenant_id={candidate['tenant_id']} "
                f"order_number={candidate['order_number']} "
                f"readiness={candidate['readiness']} "
                f"amount={candidate['amount']} "
                f"attempt_key={candidate['attempt_key'] or '-'} "
                f"external_reference={candidate['external_reference'] or '-'} "
                f"blockers={blockers}"
            )
        self.stdout.write(self.style.SUCCESS(f"payment_refund_candidates={len(candidates)} limit={limit}"))
