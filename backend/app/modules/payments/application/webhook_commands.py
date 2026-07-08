from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from app.modules.orders.application.customer_order_payment_commands import customer_order_payment_commands
from app.modules.payments.application.payment_attempt_commands import payment_attempt_commands
from app.modules.payments.application.platform_billing_commands import platform_billing_commands
from app.modules.payments.application.platform_fee_ledger_commands import platform_fee_ledger_commands
from app.modules.payments.domain.webhook_normalization import (
    looks_like_asaas_webhook,
    looks_like_pagarme_webhook,
    normalize_payment_webhook,
)
from app.modules.payments.domain.webhook_security import is_valid_hmac_sha1_signature
from app.modules.payments.infrastructure.alert_signal_metrics import record_payment_alert_signal
from app.modules.notifications.application.notification_event_handlers import notification_event_handlers


logger = logging.getLogger(__name__)


class PaymentWebhookRepository(Protocol):
    def resolve_tenant_id(self, *, tenant_slug: str, tenant_subdomain: str) -> int | None:
        ...


class DjangoOrmPaymentWebhookRepository:
    def __init__(self) -> None:
        try:
            from app.modules.tenants.models import Tenant
        except Exception:
            self.tenant_model = None
            return
        self.tenant_model = Tenant

    def resolve_tenant_id(self, *, tenant_slug: str, tenant_subdomain: str) -> int | None:
        if self.tenant_model is None:
            return None
        slug = str(tenant_slug or "").strip()
        subdomain = str(tenant_subdomain or "").strip()
        filters: dict[str, object] = {"is_active": True}
        if slug:
            filters["slug"] = slug
        elif subdomain:
            filters["subdomain"] = subdomain
        else:
            return None
        try:
            tenant = self.tenant_model._default_manager.filter(**filters).only("id").first()
        except Exception:
            return None
        return int(tenant.id) if tenant is not None else None

@dataclass
class PaymentWebhookCommandService:
    repository: PaymentWebhookRepository

    def process_webhook(
        self,
        *,
        payload: dict[str, object],
        provided_token: str,
        raw_body: bytes,
        provided_signature: str,
    ) -> tuple[str, int]:
        if looks_like_asaas_webhook(payload):
            configured_token = str(getattr(settings, "ASAAS_WEBHOOK_TOKEN", "") or "").strip()
            fallback_token = str(getattr(settings, "PAYMENTS_WEBHOOK_TOKEN", "") or "").strip()
            if configured_token:
                if provided_token != configured_token:
                    logger.warning("payments.webhook.forbidden_token", extra={"provider": "asaas"})
                    return "payment-webhook-forbidden", 403
            elif not fallback_token or provided_token != fallback_token:
                logger.warning("payments.webhook.forbidden_fallback_token", extra={"provider": "asaas"})
                return "payment-webhook-forbidden", 403
        elif looks_like_pagarme_webhook(payload):
            secret_key = str(getattr(settings, "PAGARME_SECRET_KEY", "") or "").strip()
            if secret_key:
                if not is_valid_hmac_sha1_signature(
                    secret_key=secret_key,
                    body=raw_body,
                    provided_signature=provided_signature,
                ):
                    record_payment_alert_signal(
                        "webhook.invalid_signature",
                        provider_code="pagarme",
                    )
                    logger.warning(
                        "payments.webhook.invalid_signature",
                        extra={
                            "provider": "pagarme",
                        },
                    )
                    return "payment-webhook-invalid-signature", 403
            else:
                configured_token = str(getattr(settings, "PAYMENTS_WEBHOOK_TOKEN", "") or "").strip()
                if not configured_token or provided_token != configured_token:
                    logger.warning("payments.webhook.forbidden_fallback_token", extra={"provider": "pagarme"})
                    return "payment-webhook-forbidden", 403
        else:
            configured_token = str(getattr(settings, "PAYMENTS_WEBHOOK_TOKEN", "") or "").strip()
            if not configured_token or provided_token != configured_token:
                logger.warning("payments.webhook.forbidden_token", extra={"provider": "generic"})
                return "payment-webhook-forbidden", 403

        platform_billing_result = platform_billing_commands.process_platform_fee_webhook(payload=payload)
        if platform_billing_result is not None:
            return platform_billing_result

        normalized = normalize_payment_webhook(payload)
        if normalized is None:
            logger.warning("payments.webhook.unsupported_event", extra={"payload_type": str(payload.get("type") or payload.get("event_type") or "")})
            return "payment-webhook-unsupported-event", 400
        if normalized.event_type not in {"payment.paid", "payment.failed"}:
            logger.warning("payments.webhook.event_blocked", extra={"event_type": normalized.event_type})
            return "payment-webhook-unsupported-event", 400

        if not normalized.order_number or not (normalized.tenant_slug or normalized.tenant_subdomain):
            logger.warning("payments.webhook.invalid_payload", extra={"event_type": normalized.event_type})
            return "payment-webhook-invalid-payload", 400

        tenant_id = self.repository.resolve_tenant_id(
            tenant_slug=normalized.tenant_slug,
            tenant_subdomain=normalized.tenant_subdomain,
        )
        if not tenant_id:
            record_payment_alert_signal(
                "webhook.tenant_unavailable",
                order_number=normalized.order_number,
                provider_code=normalized.payment_source_label,
                reason_code=normalized.event_type,
                metadata={
                    "tenant_slug": normalized.tenant_slug,
                    "tenant_subdomain": normalized.tenant_subdomain,
                },
            )
            logger.warning(
                "payments.webhook.tenant_unavailable",
                extra={
                    "event_type": normalized.event_type,
                    "tenant_slug": normalized.tenant_slug,
                    "tenant_subdomain": normalized.tenant_subdomain,
                },
            )
            return "payment-webhook-tenant-unavailable", 404

        if normalized.event_type == "payment.paid":
            result = customer_order_payment_commands.confirm_external_payment(
                tenant_id=tenant_id,
                order_number=normalized.order_number,
                payment_reference=normalized.payment_reference,
                payment_source_label=normalized.payment_source_label,
            )
            if result in {"payment-confirmed", "payment-already-confirmed"}:
                payment_attempt = payment_attempt_commands.reconcile_external_event(
                    tenant_id=tenant_id,
                    order_number=normalized.order_number,
                    event_type=normalized.event_type,
                    external_reference=normalized.payment_reference,
                    provider_label=normalized.payment_source_label,
                )
                platform_fee_ledger_commands.record_paid_order_fee(
                    tenant_id=tenant_id,
                    order_number=normalized.order_number,
                    payment_attempt=payment_attempt,
                )
                if result == "payment-confirmed":
                    notification_event_handlers.record_customer_order_event_email_logs(
                        tenant_id=tenant_id,
                        source_event=normalized.event_type,
                        order_number=normalized.order_number,
                    )
        else:
            result = customer_order_payment_commands.fail_external_payment(
                tenant_id=tenant_id,
                order_number=normalized.order_number,
                payment_reference=normalized.payment_reference,
                payment_source_label=normalized.payment_source_label,
            )
            if result == "payment-failure-blocked":
                platform_fee_ledger_commands.mark_order_adjustment_required(
                    tenant_id=tenant_id,
                    order_number=normalized.order_number,
                    reason_code=normalized.event_type,
                )
            if result == "payment-failed":
                payment_attempt_commands.reconcile_external_event(
                    tenant_id=tenant_id,
                    order_number=normalized.order_number,
                    event_type=normalized.event_type,
                    external_reference=normalized.payment_reference,
                    provider_label=normalized.payment_source_label,
                )
                notification_event_handlers.record_customer_order_event_email_logs(
                    tenant_id=tenant_id,
                    source_event=normalized.event_type,
                    order_number=normalized.order_number,
                )
                notification_event_handlers.record_owner_order_event_email_logs(
                    tenant_id=tenant_id,
                    source_event=normalized.event_type,
                    order_number=normalized.order_number,
                )
        if result == "payment-confirmation-stock-conflict":
            record_payment_alert_signal(
                "payment_confirmation.stock_conflict",
                tenant_id=tenant_id,
                order_number=normalized.order_number,
                provider_code=normalized.payment_source_label,
                reason_code=result,
            )
        logger.info(
            "payments.webhook.processed",
            extra={
                "tenant_id": tenant_id,
                "order_number": normalized.order_number,
                "event_type": normalized.event_type,
                "provider_label": normalized.payment_source_label,
                "result": result,
            },
        )
        status_map = {
            "payment-confirmed": 200,
            "payment-already-confirmed": 200,
            "payment-failed": 200,
            "payment-failure-blocked": 409,
            "payment-confirmation-unavailable": 404,
            "payment-confirmation-blocked": 409,
            "payment-confirmation-inventory-link-missing": 409,
            "payment-confirmation-inventory-unavailable": 409,
            "payment-confirmation-stock-conflict": 409,
        }
        return result, status_map.get(result, 400)


payment_webhook_commands = PaymentWebhookCommandService(
    repository=DjangoOrmPaymentWebhookRepository(),
)
