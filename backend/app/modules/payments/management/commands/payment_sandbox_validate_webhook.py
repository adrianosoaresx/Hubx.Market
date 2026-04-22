from __future__ import annotations

import hashlib
import hmac
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse


def _string(value: object) -> str:
    return str(value or "").strip()


class Command(BaseCommand):
    help = "Simula um webhook assinado do Pagar.me para validar a reconciliação de pagamento em sandbox."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", required=True, help="Slug do tenant que receberá o evento.")
        parser.add_argument("--order-number", required=True, help="Número do pedido a reconciliar.")
        parser.add_argument(
            "--event",
            default="paid",
            choices=["paid", "failed"],
            help="Evento a simular no webhook do Pagar.me.",
        )
        parser.add_argument(
            "--charge-id",
            default="",
            help="Identificador da charge no provider. Se omitido, um valor técnico será gerado.",
        )

    def handle(self, *args, **options):
        tenant_slug = _string(options.get("tenant_slug"))
        order_number = _string(options.get("order_number")).lstrip("#")
        event = _string(options.get("event")).lower() or "paid"
        charge_id = _string(options.get("charge_id")) or f"ch_sandbox_{order_number}_{event}"
        secret_key = _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
        if not secret_key:
            raise CommandError("PAGARME_SECRET_KEY não configurada.")

        from app.modules.orders.models import Order
        from app.modules.payments.models import PaymentAttempt

        order = (
            Order.objects.filter(tenant__slug=tenant_slug, number=order_number)
            .select_related("tenant")
            .first()
        )
        if order is None:
            raise CommandError(f"Pedido #{order_number} não encontrado para o tenant {tenant_slug}.")

        attempt = (
            PaymentAttempt.objects.filter(order=order)
            .order_by("-created_at", "-id")
            .first()
        )
        if attempt is None:
            raise CommandError(f"PaymentAttempt não encontrada para o pedido #{order_number}.")

        payload = {
            "provider": "pagarme",
            "type": "order.paid" if event == "paid" else "order.payment_failed",
            "data": {
                "id": f"pg_order_{order_number}",
                "metadata": {
                    "tenant_slug": tenant_slug,
                    "order_number": order_number,
                },
                "charges": [
                    {
                        "id": charge_id,
                    }
                ],
            },
        }
        body = json.dumps(payload)
        signature = hmac.new(
            secret_key.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()

        client = Client(HTTP_HOST="localhost")
        response = client.post(
            reverse("payments:webhook"),
            data=body,
            content_type="application/json",
            **{"HTTP_X_HUB_SIGNATURE": signature},
        )

        try:
            response_result = response.json().get("result", "")
        except Exception:
            response_result = ""

        order.refresh_from_db()
        attempt.refresh_from_db()

        self.stdout.write(
            self.style.SUCCESS(
                "payment_sandbox_validate_webhook "
                f"event={event} status_code={response.status_code} "
                f"result={response_result} "
                f"order_status={order.status} "
                f"order_payment_status={order.payment_status} "
                f"attempt_status={attempt.status} "
                f"charge_id={charge_id}"
            )
        )
