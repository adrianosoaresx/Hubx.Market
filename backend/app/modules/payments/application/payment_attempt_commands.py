from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone


logger = logging.getLogger(__name__)


def _safe_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0.00")


def _normalize_payment_method_label(payment_method_code: str) -> str:
    normalized = str(payment_method_code or "").strip().lower()
    return {
        "credit_card": "Cartão de crédito",
        "pix": "PIX",
        "boleto": "Boleto",
    }.get(normalized, "Pagamento")


def _default_provider_code(payment_method_code: str) -> str:
    configured_provider = str(getattr(settings, "PAYMENTS_PROVIDER_DEFAULT", "") or "").strip().lower()
    if configured_provider:
        return configured_provider
    normalized_method = str(payment_method_code or "").strip().lower()
    return normalized_method or "payment"


def _default_provider_label(*, provider_code: str, payment_method_code: str) -> str:
    normalized_provider = str(provider_code or "").strip().lower()
    if normalized_provider == "pagarme":
        return "Pagar.me"
    return _normalize_payment_method_label(payment_method_code)


def _append_timeline_event(
    *,
    metadata: dict[str, object],
    code: str,
    title: str,
    description: str,
    level: str = "info",
) -> dict[str, object]:
    timeline = list(metadata.get("timeline") or [])
    timeline.append(
        {
            "code": str(code or "").strip(),
            "title": str(title or "").strip(),
            "description": str(description or "").strip(),
            "level": str(level or "info").strip(),
            "at": timezone.now().isoformat(),
        }
    )
    metadata["timeline"] = timeline[-12:]
    metadata["latest_event_code"] = str(code or "").strip()
    metadata["latest_event_at"] = timezone.now().isoformat()
    return metadata


class PaymentAttemptRepository(Protocol):
    def get_order(self, *, tenant_id: int | None, order_number: str):
        ...

    def get_latest_pending_attempt(self, *, order_id: int):
        ...

    def get_latest_attempt_for_order(self, *, order_id: int):
        ...

    def get_attempt_by_external_reference(self, *, tenant_id: int | None, external_reference: str):
        ...

    def create_attempt(
        self,
        *,
        tenant,
        order,
        payment_method_code: str,
        provider_code: str,
        provider_label: str,
        amount: Decimal,
        metadata: dict[str, object],
    ):
        ...

    def save_attempt(self, attempt) -> None:
        ...


class DjangoOrmPaymentAttemptRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.order_model = None
            self.payment_attempt_model = None
            return
        self.order_model = Order
        self.payment_attempt_model = PaymentAttempt

    def get_order(self, *, tenant_id: int | None, order_number: str):
        if self.order_model is None or not tenant_id:
            return None
        normalized_order_number = str(order_number or "").lstrip("#")
        try:
            return (
                self.order_model._default_manager.filter(
                    tenant_id=tenant_id,
                    number=normalized_order_number,
                )
                .select_related("tenant")
                .first()
            )
        except Exception:
            return None

    def get_latest_pending_attempt(self, *, order_id: int):
        if self.payment_attempt_model is None or not order_id:
            return None
        try:
            return (
                self.payment_attempt_model._default_manager.filter(
                    order_id=order_id,
                    status=self.payment_attempt_model.Status.PENDING,
                )
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception:
            return None

    def get_latest_attempt_for_order(self, *, order_id: int):
        if self.payment_attempt_model is None or not order_id:
            return None
        try:
            return (
                self.payment_attempt_model._default_manager.filter(order_id=order_id)
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception:
            return None

    def get_attempt_by_external_reference(self, *, tenant_id: int | None, external_reference: str):
        if self.payment_attempt_model is None or not tenant_id or not str(external_reference or "").strip():
            return None
        try:
            return (
                self.payment_attempt_model._default_manager.filter(
                    tenant_id=tenant_id,
                    external_reference=str(external_reference or "").strip(),
                )
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception:
            return None

    def create_attempt(
        self,
        *,
        tenant,
        order,
        payment_method_code: str,
        provider_code: str,
        provider_label: str,
        amount: Decimal,
        metadata: dict[str, object],
    ):
        if self.payment_attempt_model is None:
            return None
        try:
            return self.payment_attempt_model._default_manager.create(
                tenant=tenant,
                order=order,
                payment_method_code=payment_method_code,
                provider_code=provider_code,
                provider_label=provider_label,
                status=self.payment_attempt_model.Status.PENDING,
                amount=amount,
                currency_code="BRL",
                metadata=metadata,
            )
        except IntegrityError:
            raise
        except Exception:
            return None

    def save_attempt(self, attempt) -> None:
        attempt.save()


@dataclass
class PaymentAttemptCommandService:
    repository: PaymentAttemptRepository

    def bootstrap_pending_attempt(
        self,
        *,
        tenant_id: int | None,
        order_number: str,
        payment_method_code: str,
        provider_code: str = "",
        provider_label: str = "",
        source_session_key: str = "",
    ) -> tuple[str, object | None]:
        if not tenant_id:
            logger.warning(
                "payments.attempt.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "order_number": str(order_number or "").lstrip("#"),
                },
            )
            return "payment-attempt-unavailable", None

        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "payment-attempt-unavailable", None

        current_status = str(getattr(order, "status", "") or "").lower()
        current_payment_status = str(getattr(order, "payment_status", "") or "").lower()
        if current_status in {"paid", "shipped", "canceled"} or "confirm" in current_payment_status or "pago" in current_payment_status:
            return "payment-attempt-blocked", None

        normalized_method = str(payment_method_code or "").strip().lower()
        normalized_provider_code = str(provider_code or "").strip().lower() or _default_provider_code(normalized_method)
        normalized_provider_label = str(provider_label or "").strip() or _default_provider_label(
            provider_code=normalized_provider_code,
            payment_method_code=normalized_method,
        )
        try:
            with transaction.atomic():
                existing_attempt = self.repository.get_latest_pending_attempt(order_id=int(order.id))
                if existing_attempt is not None:
                    return "payment-attempt-ready", existing_attempt

                metadata = {
                    "order_number": str(getattr(order, "number", "") or ""),
                    "payment_source_type": str(getattr(order, "payment_source_type", "") or ""),
                    "checkout_session_key": str(source_session_key or "").strip(),
                }
                metadata = _append_timeline_event(
                    metadata=metadata,
                    code="attempt_created",
                    title="Tentativa de pagamento criada",
                    description=(
                        "A trilha de pagamento foi iniciada a partir do pedido pendente."
                        if not str(source_session_key or "").strip()
                        else f"A trilha de pagamento foi iniciada a partir da sessão {str(source_session_key).strip()}."
                    ),
                    level="info",
                )
                attempt = self.repository.create_attempt(
                    tenant=getattr(order, "tenant", None),
                    order=order,
                    payment_method_code=normalized_method,
                    provider_code=normalized_provider_code,
                    provider_label=normalized_provider_label,
                    amount=_safe_decimal(getattr(order, "total", Decimal("0.00"))),
                    metadata=metadata,
                )
        except IntegrityError:
            attempt = self.repository.get_latest_pending_attempt(order_id=int(order.id))
            if attempt is not None:
                return "payment-attempt-ready", attempt
            return "payment-attempt-unavailable", None

        if attempt is None:
            return "payment-attempt-unavailable", None
        return "payment-attempt-ready", attempt

    def reconcile_external_event(
        self,
        *,
        tenant_id: int | None,
        order_number: str,
        event_type: str,
        external_reference: str,
        provider_label: str,
    ) -> object | None:
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return None

        normalized_reference = str(external_reference or "").strip()
        attempt = None
        if normalized_reference:
            attempt = self.repository.get_attempt_by_external_reference(
                tenant_id=tenant_id,
                external_reference=normalized_reference,
            )
        if attempt is None:
            attempt = self.repository.get_latest_pending_attempt(order_id=int(order.id))
        if attempt is None:
            attempt = self.repository.get_latest_attempt_for_order(order_id=int(order.id))
        if attempt is None:
            return None

        normalized_provider_label = str(provider_label or "").strip() or str(getattr(attempt, "provider_label", "") or "")
        normalized_event_type = str(event_type or "").strip().lower()
        if normalized_event_type == "payment.paid":
            if str(getattr(attempt, "status", "") or "") != "paid":
                attempt.status = "paid"
                attempt.paid_at = getattr(attempt, "paid_at", None) or timezone.now()
            if normalized_reference:
                attempt.external_reference = normalized_reference
            if normalized_provider_label:
                attempt.provider_label = normalized_provider_label
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="webhook_paid",
                title="Webhook confirmou pagamento",
                description="O provider confirmou o pagamento e a tentativa foi reconciliada com sucesso.",
                level="success",
            )
            self.repository.save_attempt(attempt)
            return attempt

        if normalized_event_type == "payment.failed" and str(getattr(attempt, "status", "") or "") != "paid":
            attempt.status = "failed"
            attempt.failed_at = timezone.now()
            if normalized_reference:
                attempt.external_reference = normalized_reference
            if normalized_provider_label:
                attempt.provider_label = normalized_provider_label
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="webhook_failed",
                title="Webhook informou falha",
                description="O provider informou falha ou cancelamento no pagamento desta tentativa.",
                level="warning",
            )
            self.repository.save_attempt(attempt)
            return attempt
        return attempt


payment_attempt_commands = PaymentAttemptCommandService(
    repository=DjangoOrmPaymentAttemptRepository(),
)
