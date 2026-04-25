from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from app.modules.shipping.models import ShipmentStatusHistory


class Command(BaseCommand):
    help = "Remove histórico antigo de shipping para controlar volume operacional."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Restringe pruning a um tenant específico.")
        parser.add_argument("--days", dest="days", type=int, default=90, help="Remove eventos mais antigos que este número de dias.")
        parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Mostra quantos eventos seriam removidos sem apagar.")

    def handle(self, *args, **options):
        tenant_id = str(options.get("tenant_id") or "").strip()
        days = int(options.get("days") or 90)
        dry_run = bool(options.get("dry_run"))
        if days < 30:
            raise CommandError("--days precisa ser >= 30 para evitar remoção agressiva de histórico operacional.")

        cutoff = timezone.now() - timedelta(days=days)
        queryset = ShipmentStatusHistory.objects.filter(created_at__lt=cutoff)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        total = queryset.count()
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry-run: shipment_history_candidates={total}; days={days}; tenant_id={tenant_id or 'all'}"))
            return

        deleted, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"Shipment history pruning concluído: deleted={deleted}; days={days}; tenant_id={tenant_id or 'all'}"))
