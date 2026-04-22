from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection, transaction

from app.modules.checkout.application.checkout_activation_commands import (
    _installments_summary,
    _safe_decimal,
)


def _selected_method(methods: list[dict[str, object]], value: str) -> dict[str, object]:
    return next((method for method in methods if str(method.get("value", "")) == value), {})


def _shipping_total_from_method(method: dict[str, object]) -> Decimal:
    raw_price = str(method.get("price", "") or "").replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    return _safe_decimal(raw_price, default="0.00")


class CheckoutSessionCommandRepository(Protocol):
    def update_session(self, *, session_key: str, payload: dict[str, object]) -> str:
        ...

    def mutate_item(self, *, session_key: str, item_id: int, operation: str) -> str:
        ...


class DjangoOrmCheckoutSessionCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout import models as checkout_models
        except Exception:
            self.session_model = None
            self.item_model = None
            return
        self.session_model = getattr(checkout_models, "CheckoutSession", None)
        self.item_model = getattr(checkout_models, "CheckoutSessionItem", None)

    def is_ready(self) -> bool:
        try:
            table_name = self.session_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_name in set(tables)

    def update_session(self, *, session_key: str, payload: dict[str, object]) -> str:
        if not self.is_ready() or not session_key:
            return "checkout-save-unavailable"

        try:
            session = self.session_model._default_manager.filter(session_key=session_key, status="open").first()
        except Exception:
            return "checkout-save-unavailable"
        if session is None:
            return "checkout-save-unavailable"

        shipping_methods = list(getattr(session, "shipping_methods", []) or [])
        payment_methods = list(getattr(session, "payment_methods", []) or [])
        requested_shipping = str(payload.get("shipping_method_selected", "") or "")
        requested_payment = str(payload.get("payment_method_selected", "") or "")

        selected_shipping = _selected_method(shipping_methods, requested_shipping)
        selected_payment = _selected_method(payment_methods, requested_payment)

        subtotal = _safe_decimal(getattr(session, "subtotal", Decimal("0.00")))
        shipping_total = (
            _shipping_total_from_method(selected_shipping)
            if selected_shipping
            else _safe_decimal(getattr(session, "shipping_total", Decimal("0.00")))
        )
        discount_total = _safe_decimal(getattr(session, "discount_total", Decimal("0.00")))
        grand_total = subtotal + shipping_total - discount_total
        installments_summary, installments_selected, installments_options = _installments_summary(grand_total)

        with transaction.atomic():
            session.first_name = str(payload.get("first_name", "") or "").strip()
            session.last_name = str(payload.get("last_name", "") or "").strip()
            session.email = str(payload.get("email", "") or "").strip()
            session.phone = str(payload.get("phone", "") or "").strip()
            session.address_line_1 = str(payload.get("address_line_1", "") or "").strip()
            session.address_line_2 = str(payload.get("address_line_2", "") or "").strip()
            session.city = str(payload.get("city", "") or "").strip()
            session.state = str(payload.get("state", "") or "").strip()
            session.zip_code = str(payload.get("zip_code", "") or "").strip()
            if selected_shipping:
                session.shipping_method_selected = requested_shipping
                session.shipping_total = shipping_total
            if selected_payment:
                session.payment_method_selected = requested_payment
            requested_installments = str(payload.get("installments_selected", "") or "")
            session.installments_summary = installments_summary
            session.installments_options = installments_options
            session.installments_selected = (
                requested_installments
                if any(option["value"] == requested_installments for option in installments_options)
                else installments_selected
            )
            session.grand_total = grand_total
            session.accept_terms = bool(payload.get("accept_terms"))
            session.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state",
                    "zip_code",
                    "shipping_method_selected",
                    "payment_method_selected",
                    "shipping_total",
                    "grand_total",
                    "installments_summary",
                    "installments_selected",
                    "installments_options",
                    "accept_terms",
                    "updated_at",
                ]
            )
        return "checkout-saved"

    def _recalculate_session_totals(self, *, session) -> None:
        items = list(
            self.item_model._default_manager.filter(checkout_session=session).order_by("sort_order", "id")
        )
        subtotal = sum(
            (
                _safe_decimal(getattr(item, "price", Decimal("0.00")))
                * int(getattr(item, "quantity", 1) or 1)
                for item in items
            ),
            Decimal("0.00"),
        )
        discount_total = _safe_decimal(getattr(session, "discount_total", Decimal("0.00")))

        if items:
            shipping_methods = list(getattr(session, "shipping_methods", []) or [])
            selected_shipping = _selected_method(
                shipping_methods,
                str(getattr(session, "shipping_method_selected", "") or ""),
            )
            shipping_total = (
                _shipping_total_from_method(selected_shipping)
                if selected_shipping
                else _safe_decimal(getattr(session, "shipping_total", Decimal("0.00")))
            )
            grand_total = subtotal + shipping_total - discount_total
            installments_summary, installments_selected, installments_options = _installments_summary(grand_total)
            requested_installments = str(getattr(session, "installments_selected", "") or "")
            session.shipping_total = shipping_total
            session.installments_summary = installments_summary
            session.installments_options = installments_options
            session.installments_selected = (
                requested_installments
                if any(option["value"] == requested_installments for option in installments_options)
                else installments_selected
            )
            session.grand_total = grand_total
        else:
            session.shipping_total = Decimal("0.00")
            session.grand_total = Decimal("0.00")
            session.installments_summary = ""
            session.installments_options = []
            session.installments_selected = ""

        session.subtotal = subtotal

    def mutate_item(self, *, session_key: str, item_id: int, operation: str) -> str:
        if not self.is_ready() or not session_key or not item_id or operation not in {"increment", "decrement", "remove"}:
            return "checkout-item-mutation-unavailable"

        try:
            with transaction.atomic():
                session = (
                    self.session_model._default_manager.select_for_update()
                    .filter(session_key=session_key, status="open")
                    .first()
                )
                if session is None:
                    return "checkout-item-mutation-unavailable"

                item = (
                    self.item_model._default_manager.select_for_update()
                    .filter(checkout_session=session, pk=item_id)
                    .first()
                )
                if item is None:
                    return "checkout-item-mutation-unavailable"

                if operation == "increment":
                    item.quantity = int(getattr(item, "quantity", 1) or 1) + 1
                    item.save(update_fields=["quantity", "updated_at"])
                    result = "checkout-item-updated"
                elif operation == "decrement":
                    current_quantity = int(getattr(item, "quantity", 1) or 1)
                    if current_quantity > 1:
                        item.quantity = current_quantity - 1
                        item.save(update_fields=["quantity", "updated_at"])
                        result = "checkout-item-updated"
                    else:
                        item.delete()
                        result = "checkout-item-removed"
                else:
                    item.delete()
                    result = "checkout-item-removed"

                self._recalculate_session_totals(session=session)
                session.save(
                    update_fields=[
                        "subtotal",
                        "shipping_total",
                        "grand_total",
                        "installments_summary",
                        "installments_selected",
                        "installments_options",
                        "updated_at",
                    ]
                )

                has_items = self.item_model._default_manager.filter(checkout_session=session).exists()
                if not has_items:
                    return "checkout-item-session-empty"
                return result
        except Exception:
            return "checkout-item-mutation-unavailable"


@dataclass
class CheckoutSessionCommandService:
    repository: CheckoutSessionCommandRepository

    def update_session(self, *, session_key: str, payload: dict[str, object]) -> str:
        return self.repository.update_session(session_key=session_key, payload=payload)

    def mutate_item(self, *, session_key: str, item_id: int, operation: str) -> str:
        return self.repository.mutate_item(session_key=session_key, item_id=item_id, operation=operation)


checkout_session_commands = CheckoutSessionCommandService(
    repository=DjangoOrmCheckoutSessionCommandRepository(),
)
