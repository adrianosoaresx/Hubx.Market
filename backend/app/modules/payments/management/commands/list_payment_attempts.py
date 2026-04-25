from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from app.modules.payments.models import PaymentAttempt


class Command(BaseCommand):
    help = "Lista tentativas de pagamento para suporte, retenção e conciliação operacional."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Restringe a listagem a um tenant específico.")
        parser.add_argument("--status", dest="status", default="", choices=["", "pending", "paid", "failed"], help="Filtra por status da tentativa.")
        parser.add_argument("--stale-hours", dest="stale_hours", type=int, default=0, help="Filtra tentativas pendentes sem atualização há N horas.")
        parser.add_argument("--limit", dest="limit", type=int, default=50, help="Número máximo de tentativas retornadas.")

    def handle(self, *args, **options):
        tenant_id = str(options.get("tenant_id") or "").strip()
        status = str(options.get("status") or "").strip().lower()
        stale_hours = max(0, int(options.get("stale_hours") or 0))
        limit = min(max(1, int(options.get("limit") or 50)), 250)

        queryset = PaymentAttempt.objects.select_related("tenant", "order").order_by("-updated_at", "-id")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        if status:
            queryset = queryset.filter(status=status)
        if stale_hours:
            cutoff = timezone.now() - timedelta(hours=stale_hours)
            queryset = queryset.filter(status=PaymentAttempt.Status.PENDING, updated_at__lt=cutoff)

        attempts = list(queryset[:limit])
        if not attempts:
            self.stdout.write("payment_attempts=0")
            return

        for attempt in attempts:
            self.stdout.write(
                "payment_attempt "
                f"tenant_id={attempt.tenant_id} "
                f"order_number={getattr(attempt.order, 'number', '')} "
                f"status={attempt.status} "
                f"provider={attempt.provider_code or attempt.provider_label or '-'} "
                f"external_reference={attempt.external_reference or '-'} "
                f"updated_at={attempt.updated_at.isoformat()}"
            )
        self.stdout.write(self.style.SUCCESS(f"payment_attempts={len(attempts)} limit={limit}"))
