from django.core.management.base import BaseCommand

from app.modules.shipping.application.shipment_tracking_sync import shipment_tracking_sync
from app.modules.shipping.application.shipping_provider_settings import shipping_provider_settings
from app.modules.shipping.models import Shipment


class Command(BaseCommand):
    help = "Sincroniza snapshots de tracking para shipments não terminais."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Restringe o sync a um tenant específico.")
        parser.add_argument("--limit", dest="limit", type=int, default=100, help="Número máximo de shipments para sincronizar.")

    def handle(self, *args, **options):
        tenant_id = str(options.get("tenant_id") or "").strip()
        limit = max(1, int(options.get("limit") or 100))
        queryset = (
            Shipment.objects.select_related("order", "tenant")
            .filter(status__in=[Shipment.Status.CREATED, Shipment.Status.SENT])
            .order_by("tenant_id", "id")
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        results: dict[str, int] = {}
        processed = 0
        for shipment in queryset[:limit]:
            provider_gateway = shipping_provider_settings.get_gateway_for_tenant(tenant_id=shipment.tenant_id)
            result = shipment_tracking_sync.sync_tracking_snapshot(
                tenant_id=shipment.tenant_id,
                order_number=shipment.order.number,
                provider_gateway=provider_gateway,
            )
            results[result] = results.get(result, 0) + 1
            processed += 1

        summary = ", ".join(f"{key}={value}" for key, value in sorted(results.items())) or "sem resultados"
        self.stdout.write(self.style.SUCCESS(f"Tracking sync concluído: processed={processed}; {summary}"))
