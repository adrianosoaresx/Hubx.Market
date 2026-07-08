from __future__ import annotations

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from app.modules.payments.application.platform_billing_commands import platform_billing_commands
from app.modules.payments.models import PlatformFeeLedger
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


def _string(value: object) -> str:
    return str(value or "").strip()


class Command(BaseCommand):
    help = "Valida o fluxo sandbox da cobrança complementar Asaas para mínimo Pro."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", type=int, required=True)
        parser.add_argument("--ledger-key", default="", help="Ledger de complemento Pro. Se omitido, usa o mais recente pendente.")
        parser.add_argument("--local-simulate", action="store_true", help="Cria um ledger Pro local quando não houver pendência, sem chamar Asaas.")
        parser.add_argument("--execute", action="store_true", help="Cria cobrança Asaas real quando o provider estiver habilitado.")
        parser.add_argument("--simulate-paid-webhook", action="store_true", help="Simula webhook Asaas de pagamento recebido após a criação.")
        parser.add_argument("--actor-label", default="payment-sandbox-platform-billing")

    def handle(self, *args, **options):
        tenant_id = int(options["tenant_id"])
        ledger_key = _string(options.get("ledger_key"))
        local_simulate = bool(options.get("local_simulate"))
        execute = bool(options.get("execute"))
        simulate_paid_webhook = bool(options.get("simulate_paid_webhook"))
        actor_label = _string(options.get("actor_label")) or "payment-sandbox-platform-billing"

        ledger = self._resolve_ledger(tenant_id=tenant_id, ledger_key=ledger_key)
        if ledger is None and local_simulate:
            ledger = self._create_local_simulation_ledger(tenant_id=tenant_id)
            if ledger is not None:
                self.stdout.write(
                    self.style.SUCCESS(
                        "payment_sandbox_platform_billing_local_simulation "
                        f"result=ledger-created ledger_key={ledger.ledger_key}"
                    )
                )
        if ledger is None:
            self.stdout.write(self.style.WARNING("payment_sandbox_platform_billing=unavailable reason=ledger-not-found"))
            return

        self.stdout.write(
            "payment_sandbox_platform_billing_candidate "
            f"tenant_id={ledger.tenant_id} "
            f"ledger_key={ledger.ledger_key} "
            f"status={ledger.status} "
            f"amount={ledger.fee_amount:.2f} "
            f"provider_reference={ledger.provider_payment_reference or '-'}"
        )

        if not execute:
            self.stdout.write(self.style.SUCCESS("payment_sandbox_platform_billing=dry-run result=ready"))
            if local_simulate and simulate_paid_webhook:
                self._simulate_paid_webhook(ledger=ledger)
            return

        if not bool(getattr(settings, "PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED", False)):
            raise CommandError("PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED precisa estar ativo para --execute.")

        result, updated_ledger = platform_billing_commands.create_complementary_charge_for_ledger(
            ledger_id=ledger.id,
            actor_label=actor_label,
        )
        if updated_ledger is None:
            self.stdout.write(self.style.WARNING(f"payment_sandbox_platform_billing={result}"))
            return
        self.stdout.write(
            self.style.SUCCESS(
                "payment_sandbox_platform_billing "
                f"result={result} "
                f"ledger_status={updated_ledger.status} "
                f"provider_payment_reference={updated_ledger.provider_payment_reference or '-'} "
                f"billing_checkout_url={updated_ledger.metadata.get('billing_checkout_url') or '-'}"
            )
        )
        if simulate_paid_webhook:
            self._simulate_paid_webhook(ledger=updated_ledger)

    def _resolve_ledger(self, *, tenant_id: int, ledger_key: str) -> PlatformFeeLedger | None:
        queryset = PlatformFeeLedger.objects.filter(
            tenant_id=tenant_id,
            kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT,
        )
        if ledger_key:
            return queryset.filter(ledger_key=ledger_key).first()
        return (
            queryset.exclude(status__in=[PlatformFeeLedger.Status.PAID, PlatformFeeLedger.Status.CANCELED])
            .order_by("-created_at", "-id")
            .first()
        )

    def _create_local_simulation_ledger(self, *, tenant_id: int) -> PlatformFeeLedger | None:
        subscription = (
            TenantSubscription.objects.select_related("plan")
            .filter(
                tenant_id=tenant_id,
                plan__billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            )
            .first()
        )
        if subscription is None:
            return None
        now = timezone.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1)
        minimum_fee = subscription.plan.minimum_monthly_fee
        basis_amount = minimum_fee / 2
        fee_amount = minimum_fee - basis_amount
        return PlatformFeeLedger.objects.create(
            tenant_id=tenant_id,
            ledger_key=f"local-simulation:{tenant_id}:{now.strftime('%Y%m%d%H%M%S%f')}",
            kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT,
            status=PlatformFeeLedger.Status.PENDING_COLLECTION,
            plan_code_snapshot=subscription.plan.code,
            billing_model_snapshot=subscription.plan.billing_model,
            platform_fee_percent_snapshot=subscription.plan.platform_fee_percent,
            minimum_monthly_fee_snapshot=subscription.plan.minimum_monthly_fee,
            billing_period_start=period_start,
            billing_period_end=period_end,
            basis_amount=basis_amount,
            fee_amount=fee_amount,
            currency_code=subscription.plan.currency_code or "BRL",
            provider_code="asaas",
            metadata={
                "collection_mode": "local_platform_billing_simulation",
                "provider_call": "not-executed",
                "simulation": True,
            },
        )

    def _simulate_paid_webhook(self, *, ledger: PlatformFeeLedger) -> None:
        token = _string(getattr(settings, "ASAAS_WEBHOOK_TOKEN", ""))
        if not token:
            raise CommandError("ASAAS_WEBHOOK_TOKEN precisa estar configurado para simular webhook.")
        payment_reference = ledger.provider_payment_reference or f"pay_sandbox_{ledger.id}"
        payload = {
            "event": "PAYMENT_RECEIVED",
            "payment": {
                "id": payment_reference,
                "status": "RECEIVED",
                "externalReference": f"hubx-platform-fee:{ledger.ledger_key}",
            },
        }
        body = json.dumps(payload)
        response = Client(HTTP_HOST="localhost").post(
            reverse("payments:webhook"),
            data=body,
            content_type="application/json",
            HTTP_ASAAS_ACCESS_TOKEN=token,
        )
        try:
            response_result = response.json().get("result", "")
        except Exception:
            response_result = ""
        ledger.refresh_from_db()
        self.stdout.write(
            self.style.SUCCESS(
                "payment_sandbox_platform_billing_webhook "
                f"status_code={response.status_code} "
                f"result={response_result} "
                f"ledger_status={ledger.status}"
            )
        )
