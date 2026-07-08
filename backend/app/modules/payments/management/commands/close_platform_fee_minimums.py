from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.modules.payments.application.platform_billing_commands import platform_billing_commands
from app.modules.payments.application.platform_fee_ledger_commands import platform_fee_ledger_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


class Command(BaseCommand):
    help = "Calcula complementos mensais de mínimo abatível para planos Pro."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", type=int, default=0)
        parser.add_argument("--actor-label", default="close-platform-fee-minimums")
        parser.add_argument(
            "--collect",
            action="store_true",
            help="Cria cobrança complementar Asaas para ledgers pendentes quando o provider estiver configurado.",
        )

    def handle(self, *args, **options):
        tenant_id = int(options.get("tenant_id") or 0)
        actor_label = str(options.get("actor_label") or "close-platform-fee-minimums")
        collect = bool(options.get("collect")) or bool(getattr(settings, "PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED", False))
        queryset = TenantSubscription.objects.select_related("tenant", "plan").filter(
            status__in=[
                TenantSubscription.Status.TRIALING,
                TenantSubscription.Status.ACTIVE,
                TenantSubscription.Status.PAST_DUE,
            ],
            plan__billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        results: dict[str, int] = {}
        for subscription in queryset.order_by("tenant_id"):
            result, ledger = platform_fee_ledger_commands.close_minimum_commitment_period(
                tenant_id=subscription.tenant_id,
                reference_at=timezone.now(),
                actor_label=actor_label,
            )
            results[result] = results.get(result, 0) + 1
            if collect and ledger is not None:
                collect_result, _collected_ledger = platform_billing_commands.create_complementary_charge_for_ledger(
                    ledger_id=ledger.id,
                    actor_label=actor_label,
                )
                results[collect_result] = results.get(collect_result, 0) + 1

        summary = " ".join(f"{key}={value}" for key, value in sorted(results.items())) or "none=0"
        self.stdout.write(self.style.SUCCESS(f"platform_fee_minimum_close {summary}"))
