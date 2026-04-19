from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand


@dataclass
class BackfillStats:
    profiles_already_linked: int = 0
    profiles_linked: int = 0
    profiles_skipped: int = 0
    orders_already_linked: int = 0
    orders_linked: int = 0
    orders_skipped: int = 0


class Command(BaseCommand):
    help = "Preenche vínculos explícitos entre AccountProfile/Order e Customer quando o match por tenant + email é inequívoco."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos vínculos seriam preenchidos sem persistir alterações.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        from app.modules.accounts.models import AccountProfile
        from app.modules.customers.models import Customer
        from app.modules.orders.models import Order

        stats = BackfillStats()

        stats.profiles_already_linked = AccountProfile.objects.filter(customer__isnull=False).count()
        profile_queryset = AccountProfile.objects.filter(customer__isnull=True).exclude(email="")
        for profile in profile_queryset.iterator():
            customer = self._resolve_customer(
                customer_model=Customer,
                tenant_id=profile.tenant_id,
                email=profile.email,
            )
            if customer is None:
                stats.profiles_skipped += 1
                continue
            stats.profiles_linked += 1
            if not dry_run:
                profile.customer = customer
                profile.save(update_fields=["customer"])

        stats.orders_already_linked = Order.objects.filter(customer__isnull=False).count()
        order_queryset = Order.objects.filter(customer__isnull=True).exclude(customer_email="")
        for order in order_queryset.iterator():
            customer = self._resolve_customer(
                customer_model=Customer,
                tenant_id=order.tenant_id,
                email=order.customer_email,
            )
            if customer is None:
                stats.orders_skipped += 1
                continue
            stats.orders_linked += 1
            if not dry_run:
                order.customer = customer
                order.save(update_fields=["customer"])

        mode_label = "DRY-RUN" if dry_run else "APPLIED"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode_label}] profiles_linked={stats.profiles_linked} "
                f"profiles_already_linked={stats.profiles_already_linked} "
                f"profiles_skipped={stats.profiles_skipped} "
                f"orders_linked={stats.orders_linked} "
                f"orders_already_linked={stats.orders_already_linked} "
                f"orders_skipped={stats.orders_skipped}"
            )
        )

    @staticmethod
    def _resolve_customer(*, customer_model, tenant_id: int, email: str):
        normalized_email = str(email or "").strip()
        if not tenant_id or not normalized_email:
            return None
        matches = list(
            customer_model.objects.filter(
                tenant_id=tenant_id,
                email__iexact=normalized_email,
            )[:2]
        )
        if len(matches) != 1:
            return None
        return matches[0]
