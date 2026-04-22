from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.modules.payments.application.payment_attempt_commands import payment_attempt_commands
from app.modules.checkout.application.checkout_reorder_commands import checkout_reorder_commands


logger = logging.getLogger(__name__)


class CheckoutPaymentRetryRepository(Protocol):
    def bootstrap_from_failed_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        ...


class DjangoOrmCheckoutPaymentRetryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
        except Exception:
            self.order_model = None
            return
        self.order_model = Order

    def _get_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ):
        if self.order_model is None or not tenant_id or not order_number:
            return None
        normalized_order_number = str(order_number or "").lstrip("#")
        try:
            queryset = self.order_model._default_manager.filter(
                tenant_id=tenant_id,
                number=normalized_order_number,
            ).prefetch_related("items")
            if customer_id:
                order = queryset.filter(customer_id=customer_id).first()
                if order is not None:
                    return order
            if email:
                return queryset.filter(customer_email__iexact=str(email or "").strip()).first()
            return queryset.first()
        except Exception:
            return None

    def bootstrap_from_failed_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        order = self._get_order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=email,
            order_number=order_number,
        )
        if order is None:
            return "payment-retry-unavailable", None

        order_status = str(getattr(order, "status", "") or "").lower()
        payment_status = str(getattr(order, "payment_status", "") or "").lower()
        if order_status not in {"pending", "processing"}:
            return "payment-retry-blocked", None
        if "falhou" not in payment_status and not getattr(order, "payment_failed_at", None):
            return "payment-retry-blocked", None

        result, session_key = checkout_reorder_commands.bootstrap_from_order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=email,
            order_number=order_number,
        )
        mapped_result = {
            "reorder-lite-ready": "payment-retry-ready",
            "reorder-lite-partial": "payment-retry-partial",
            "reorder-lite-unavailable": "payment-retry-unavailable",
        }.get(result, "payment-retry-unavailable")
        if mapped_result in {"payment-retry-ready", "payment-retry-partial"}:
            payment_attempt_commands.bootstrap_pending_attempt(
                tenant_id=tenant_id,
                order_number=str(getattr(order, "number", "") or order_number),
                payment_method_code="credit_card",
            )
        return mapped_result, session_key


@dataclass
class CheckoutPaymentRetryCommandService:
    repository: CheckoutPaymentRetryRepository

    def bootstrap_from_failed_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        if not tenant_id:
            logger.warning(
                "checkout.payment_retry.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "order_number": str(order_number or "").lstrip("#"),
                },
            )
            return "payment-retry-unavailable", None
        return self.repository.bootstrap_from_failed_order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=email,
            order_number=order_number,
        )


checkout_payment_retry_commands = CheckoutPaymentRetryCommandService(
    repository=DjangoOrmCheckoutPaymentRetryRepository(),
)
