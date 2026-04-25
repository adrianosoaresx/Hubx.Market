from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand


@dataclass
class BackfillStats:
    profiles_already_linked: int = 0
    profiles_linked: int = 0
    profiles_skipped: int = 0
    profiles_skipped_missing_email: int = 0
    profiles_skipped_no_match: int = 0
    profiles_skipped_ambiguous: int = 0
    orders_already_linked: int = 0
    orders_linked: int = 0
    orders_skipped: int = 0
    orders_skipped_missing_email: int = 0
    orders_skipped_no_match: int = 0
    orders_skipped_ambiguous: int = 0
    order_email_fallback_remaining: int = 0


class Command(BaseCommand):
    help = "Preenche vínculos explícitos entre AccountProfile/Order e Customer quando o match por tenant + email é inequívoco."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos vínculos seriam preenchidos sem persistir alterações.",
        )
        parser.add_argument(
            "--tenant-id",
            dest="tenant_id",
            default="",
            help="Limita o backfill a um tenant específico. Sem este filtro, mantém compatibilidade global legada.",
        )
        parser.add_argument(
            "--only",
            dest="only",
            default="all",
            choices=["all", "profiles", "orders"],
            help="Limita o backfill a profiles, orders ou ambos.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        tenant_id = str(options.get("tenant_id") or "").strip()
        only = str(options.get("only") or "all").strip()

        from app.modules.accounts.models import AccountProfile
        from app.modules.customers.application.customer_data_issues import customer_data_issues
        from app.modules.customers.models import Customer
        from app.modules.orders.models import Order

        stats = BackfillStats()

        profile_base_queryset = AccountProfile.objects.all()
        order_base_queryset = Order.objects.all()
        if tenant_id:
            profile_base_queryset = profile_base_queryset.filter(tenant_id=tenant_id)
            order_base_queryset = order_base_queryset.filter(tenant_id=tenant_id)

        if only in {"all", "profiles"}:
            stats.profiles_already_linked = profile_base_queryset.filter(customer__isnull=False).count()
            stats.profiles_skipped_missing_email = profile_base_queryset.filter(customer__isnull=True, email="").count()
            profile_queryset = profile_base_queryset.filter(customer__isnull=True).exclude(email="")
            for profile in profile_queryset.iterator():
                customer, reason = self._resolve_customer_match(
                    customer_model=Customer,
                    tenant_id=profile.tenant_id,
                    email=profile.email,
                )
                if customer is None:
                    stats.profiles_skipped += 1
                    if reason == "ambiguous":
                        stats.profiles_skipped_ambiguous += 1
                    else:
                        stats.profiles_skipped_no_match += 1
                    continue
                stats.profiles_linked += 1
                if not dry_run:
                    profile.customer = customer
                    profile.save(update_fields=["customer"])
            stats.profiles_skipped += stats.profiles_skipped_missing_email

        if only in {"all", "orders"}:
            stats.orders_already_linked = order_base_queryset.filter(customer__isnull=False).count()
            stats.orders_skipped_missing_email = order_base_queryset.filter(customer__isnull=True, customer_email="").count()
            order_queryset = order_base_queryset.filter(customer__isnull=True).exclude(customer_email="")
            for order in order_queryset.iterator():
                customer, reason = self._resolve_customer_match(
                    customer_model=Customer,
                    tenant_id=order.tenant_id,
                    email=order.customer_email,
                )
                if customer is None:
                    stats.orders_skipped += 1
                    if reason == "ambiguous":
                        stats.orders_skipped_ambiguous += 1
                    else:
                        stats.orders_skipped_no_match += 1
                    continue
                stats.orders_linked += 1
                if not dry_run:
                    order.customer = customer
                    order.save(update_fields=["customer"])
            stats.orders_skipped += stats.orders_skipped_missing_email

        stats.order_email_fallback_remaining = len(
            customer_data_issues.list_issues(
                tenant_id=tenant_id,
                issue_code="order_email_fallback",
                limit=1000,
            )
        )

        mode_label = "DRY-RUN" if dry_run else "APPLIED"
        scope_label = f"tenant_id={tenant_id}" if tenant_id else "tenant_id=global"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode_label}] {scope_label} only={only} "
                f"profiles_linked={stats.profiles_linked} "
                f"profiles_already_linked={stats.profiles_already_linked} "
                f"profiles_skipped={stats.profiles_skipped} "
                f"profiles_skipped_missing_email={stats.profiles_skipped_missing_email} "
                f"profiles_skipped_no_match={stats.profiles_skipped_no_match} "
                f"profiles_skipped_ambiguous={stats.profiles_skipped_ambiguous} "
                f"orders_linked={stats.orders_linked} "
                f"orders_already_linked={stats.orders_already_linked} "
                f"orders_skipped={stats.orders_skipped} "
                f"orders_skipped_missing_email={stats.orders_skipped_missing_email} "
                f"orders_skipped_no_match={stats.orders_skipped_no_match} "
                f"orders_skipped_ambiguous={stats.orders_skipped_ambiguous} "
                f"order_email_fallback_remaining={stats.order_email_fallback_remaining}"
            )
        )

    @staticmethod
    def _resolve_customer(*, customer_model, tenant_id: int, email: str):
        customer, _ = Command._resolve_customer_match(customer_model=customer_model, tenant_id=tenant_id, email=email)
        return customer

    @staticmethod
    def _resolve_customer_match(*, customer_model, tenant_id: int, email: str):
        normalized_email = str(email or "").strip()
        if not tenant_id or not normalized_email:
            return None, "missing_email"
        matches = list(
            customer_model.objects.filter(
                tenant_id=tenant_id,
                email__iexact=normalized_email,
            )[:2]
        )
        if not matches:
            return None, "no_match"
        if len(matches) != 1:
            return None, "ambiguous"
        return matches[0], ""
