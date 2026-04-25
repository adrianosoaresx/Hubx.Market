from django.core.management.base import BaseCommand

from app.modules.orders.application.admin_order_queries import admin_order_queries


class Command(BaseCommand):
    help = "Lista exceções operacionais de estoque por tenant para suporte e triagem."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--quick-filter",
            dest="quick_filter",
            default="active",
            choices=[
                "active",
                "review",
                "resolved",
                "high_priority",
                "medium_priority",
                "low_priority",
                "unassigned",
                "assigned",
            ],
        )
        parser.add_argument("--limit", dest="limit", type=int, default=50)

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        quick_filter = str(options.get("quick_filter") or "active").strip()
        limit = min(max(1, int(options.get("limit") or 50)), 250)

        orders = admin_order_queries.list_orders(tenant_id=int(tenant_id))
        filtered_orders = admin_order_queries.filter_orders_by_inventory_exception_state(orders, quick_filter)[:limit]
        if not filtered_orders:
            self.stdout.write(f"inventory_exceptions=0 quick_filter={quick_filter} tenant_id={tenant_id}")
            return

        for order in filtered_orders:
            self.stdout.write(
                "inventory_exception "
                f"tenant_id={tenant_id} "
                f"order_number={order.get('order_number', '')} "
                f"state={order.get('inventory_exception_list_label', '') or '-'} "
                f"priority={order.get('inventory_exception_priority_label', '') or '-'} "
                f"aging={order.get('inventory_exception_aging_label', '') or '-'} "
                f"owner={order.get('inventory_exception_owner_label', '') or '-'}"
            )
        self.stdout.write(self.style.SUCCESS(f"inventory_exceptions={len(filtered_orders)} quick_filter={quick_filter} limit={limit}"))
