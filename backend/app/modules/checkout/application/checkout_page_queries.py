from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection


def _fallback_checkout_steps() -> list[dict[str, object]]:
    return [
        {"label": "Carrinho", "state": "complete"},
        {"label": "Entrega", "state": "current"},
        {"label": "Pagamento", "state": "upcoming"},
        {"label": "Confirmação", "state": "upcoming"},
    ]


def _build_checkout_steps_from_session(
    *,
    has_items: bool,
    has_shipping_address: bool,
    has_shipping_method: bool,
    has_payment_method: bool,
    accepted_terms: bool,
    status: str,
) -> list[dict[str, object]]:
    if status == "completed":
        return [
            {"label": "Carrinho", "state": "complete"},
            {"label": "Entrega", "state": "complete"},
            {"label": "Pagamento", "state": "complete"},
            {"label": "Confirmação", "state": "current"},
        ]

    delivery_complete = has_items and has_shipping_address and has_shipping_method
    payment_complete = delivery_complete and has_payment_method and accepted_terms

    return [
        {"label": "Carrinho", "state": "complete" if has_items else "current"},
        {
            "label": "Entrega",
            "state": "complete" if delivery_complete else ("current" if has_items else "upcoming"),
        },
        {
            "label": "Pagamento",
            "state": "complete" if payment_complete else ("current" if delivery_complete else "upcoming"),
        },
        {"label": "Confirmação", "state": "upcoming"},
    ]


def _fallback_shipping_methods() -> list[dict[str, object]]:
    return [
        {
            "value": "standard",
            "label": "Entrega padrão",
            "description": "Receba em até 5 dias úteis.",
            "price": "R$ 24,90",
            "checked": True,
        },
        {
            "value": "express",
            "label": "Entrega expressa",
            "description": "Receba em até 2 dias úteis.",
            "price": "R$ 39,90",
        },
    ]


def _fallback_payment_methods() -> list[dict[str, object]]:
    return [
        {
            "value": "credit_card",
            "label": "Cartão de crédito",
            "description": "Pagamento imediato com confirmação online.",
            "meta": "3x sem juros",
            "checked": True,
        },
        {
            "value": "pix",
            "label": "PIX",
            "description": "Aprovação rápida após a confirmação do pagamento.",
            "meta": "5% de desconto no pagamento à vista",
        },
    ]


def _fallback_order_items() -> list[dict[str, object]]:
    return [
        {
            "image_url": "https://placehold.co/240x240?text=runner",
            "image_alt": "Tênis Hubx Runner",
            "title": "Tênis Hubx Runner",
            "subtitle": "Preto · 42",
            "meta": "SKU RUNNER-001-BLK-42",
            "price": "R$ 299,90",
            "compare_price": "R$ 349,90",
            "quantity": 1,
            "quantity_readonly": True,
        },
        {
            "image_url": "https://placehold.co/240x240?text=meia",
            "image_alt": "Meia Performance",
            "title": "Meia Performance",
            "subtitle": "Pack com 3 pares",
            "meta": "SKU MP-030",
            "price": "R$ 59,90",
            "quantity": 1,
            "quantity_readonly": True,
        },
    ]


class CheckoutReadRepository(Protocol):
    def get_checkout_page_data(self) -> dict[str, object] | None:
        ...


def _format_currency(value: object, *, negative: bool = False) -> str:
    if value in (None, ""):
        value = Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    prefix = "-R$ " if negative and value > 0 else "R$ "
    return f"{prefix}{value:.2f}".replace(".", ",")


def _mark_selected(options: list[dict[str, object]], selected_value: str) -> list[dict[str, object]]:
    normalized = []
    for option in options:
        cloned = dict(option)
        if str(cloned.get("value", "")) == selected_value:
            cloned["checked"] = True
        else:
            cloned.pop("checked", None)
        normalized.append(cloned)
    return normalized


def _build_checkout_description(*, item_count: int, shipping_label: str, payment_label: str) -> str:
    parts = [f"Revise {item_count} item(ns) antes de concluir o pedido."]
    if shipping_label:
        parts.append(f"Entrega selecionada: {shipping_label}.")
    if payment_label:
        parts.append(f"Pagamento selecionado: {payment_label}.")
    return " ".join(parts)


class FallbackCheckoutRepository:
    def get_checkout_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Finalizar compra",
            "page_description": "Revise seus itens, informe entrega e pagamento antes de concluir o pedido.",
            "checkout_steps": _fallback_checkout_steps(),
            "first_name": "Ana",
            "last_name": "Souza",
            "email": "ana@hubx.market",
            "phone": "(11) 99999-0000",
            "address_line_1": "Rua das Laranjeiras, 100",
            "address_line_2": "Apto 42",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01310-100",
            "shipping_methods": _fallback_shipping_methods(),
            "shipping_method_selected": "standard",
            "payment_methods": _fallback_payment_methods(),
            "payment_method_selected": "credit_card",
            "order_items": _fallback_order_items(),
            "subtotal": "R$ 359,80",
            "shipping_total": "R$ 24,90",
            "discount_total": "-R$ 20,00",
            "installments_summary": "3x de R$ 121,56 sem juros",
            "grand_total": "R$ 364,70",
            "installments_selected": "3x",
            "installments_options": [
                {"value": "1x", "label": "1x de R$ 364,70"},
                {"value": "2x", "label": "2x de R$ 182,35"},
                {"value": "3x", "label": "3x de R$ 121,56"},
            ],
            "accept_terms": True,
        }


class DjangoOrmCheckoutRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout import models as checkout_models
        except Exception:
            self.session_model = None
            return

        self.session_model = getattr(checkout_models, "CheckoutSession", None)

    def is_ready(self) -> bool:
        if self.session_model is None:
            return False

        try:
            table_names = {
                self.session_model._meta.db_table,
                self.session_model._meta.get_field("items").related_model._meta.db_table,
            }
        except Exception:
            return False

        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False

        return table_names.issubset(set(tables))

    def get_checkout_page_data(self) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            session = (
                self.session_model._default_manager.filter(status="open")
                .prefetch_related("items")
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None

        if not session:
            return None

        return self._serialize_session(session)

    def _serialize_session(self, session: object) -> dict[str, object]:
        shipping_selected = str(getattr(session, "shipping_method_selected", "") or "")
        payment_selected = str(getattr(session, "payment_method_selected", "") or "")

        try:
            items = list(getattr(session, "items").all())
        except Exception:
            items = []

        shipping_methods = _mark_selected(list(getattr(session, "shipping_methods", []) or []), shipping_selected)
        payment_methods = _mark_selected(list(getattr(session, "payment_methods", []) or []), payment_selected)
        selected_shipping = next((item for item in shipping_methods if item.get("checked")), {})
        selected_payment = next((item for item in payment_methods if item.get("checked")), {})
        has_shipping_address = all(
            [
                str(getattr(session, "first_name", "") or "").strip(),
                str(getattr(session, "last_name", "") or "").strip(),
                str(getattr(session, "address_line_1", "") or "").strip(),
                str(getattr(session, "city", "") or "").strip(),
                str(getattr(session, "state", "") or "").strip(),
                str(getattr(session, "zip_code", "") or "").strip(),
            ]
        )
        session_status = str(getattr(session, "status", "open") or "open")
        accepted_terms = bool(getattr(session, "accept_terms", False))
        serialized_items = [self._serialize_item(item) for item in items]

        return {
            "page_title": "Finalizar compra",
            "page_description": _build_checkout_description(
                item_count=len(serialized_items),
                shipping_label=str(selected_shipping.get("label", "") or ""),
                payment_label=str(selected_payment.get("label", "") or ""),
            ),
            "checkout_steps": _build_checkout_steps_from_session(
                has_items=bool(serialized_items),
                has_shipping_address=has_shipping_address,
                has_shipping_method=bool(shipping_selected),
                has_payment_method=bool(payment_selected),
                accepted_terms=accepted_terms,
                status=session_status,
            ),
            "first_name": str(getattr(session, "first_name", "") or ""),
            "last_name": str(getattr(session, "last_name", "") or ""),
            "email": str(getattr(session, "email", "") or ""),
            "phone": str(getattr(session, "phone", "") or ""),
            "address_line_1": str(getattr(session, "address_line_1", "") or ""),
            "address_line_2": str(getattr(session, "address_line_2", "") or ""),
            "city": str(getattr(session, "city", "") or ""),
            "state": str(getattr(session, "state", "") or ""),
            "zip_code": str(getattr(session, "zip_code", "") or ""),
            "shipping_methods": shipping_methods,
            "shipping_method_selected": shipping_selected,
            "payment_methods": payment_methods,
            "payment_method_selected": payment_selected,
            "order_items": serialized_items,
            "subtotal": _format_currency(getattr(session, "subtotal", Decimal("0.00"))),
            "shipping_total": _format_currency(getattr(session, "shipping_total", Decimal("0.00"))),
            "discount_total": _format_currency(getattr(session, "discount_total", Decimal("0.00")), negative=True),
            "installments_summary": str(getattr(session, "installments_summary", "") or ""),
            "grand_total": _format_currency(getattr(session, "grand_total", Decimal("0.00"))),
            "installments_selected": str(getattr(session, "installments_selected", "") or ""),
            "installments_options": list(getattr(session, "installments_options", []) or []),
            "accept_terms": accepted_terms,
        }

    @staticmethod
    def _serialize_item(item: object) -> dict[str, object]:
        compare_price = getattr(item, "compare_price", None)
        return {
            "image_url": str(getattr(item, "image_url", "") or ""),
            "image_alt": str(getattr(item, "image_alt", "") or ""),
            "title": str(getattr(item, "title", "") or ""),
            "subtitle": str(getattr(item, "subtitle", "") or ""),
            "meta": str(getattr(item, "meta", "") or ""),
            "price": _format_currency(getattr(item, "price", Decimal("0.00"))),
            "compare_price": _format_currency(compare_price) if compare_price else "",
            "quantity": int(getattr(item, "quantity", 1) or 1),
            "quantity_readonly": bool(getattr(item, "quantity_readonly", True)),
        }


@dataclass
class CheckoutPageQueryService:
    orm_repository: CheckoutReadRepository
    fallback_repository: CheckoutReadRepository

    def using_persisted_source(self) -> bool:
        try:
            return self.orm_repository.get_checkout_page_data() is not None
        except Exception:
            return False

    def get_checkout_page_data(self) -> dict[str, object]:
        real_payload = self.orm_repository.get_checkout_page_data()
        return real_payload or self.fallback_repository.get_checkout_page_data()


checkout_page_queries = CheckoutPageQueryService(
    orm_repository=DjangoOrmCheckoutRepository(),
    fallback_repository=FallbackCheckoutRepository(),
)
