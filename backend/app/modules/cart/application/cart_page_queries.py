from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection

from app.modules.shipping.application.delivery_promise_queries import delivery_promise_queries


def _format_currency(value: object, *, negative: bool = False) -> str:
    try:
        numeric = Decimal(str(value or "0.00"))
    except Exception:
        numeric = Decimal("0.00")
    prefix = "-R$ " if negative and numeric > 0 else "R$ "
    return f"{prefix}{numeric:.2f}".replace(".", ",")


def _safe_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00"))
    except Exception:
        return Decimal("0.00")


def _empty_payload(*, reason: str = "empty") -> dict[str, object]:
    descriptions = {
        "missing_session": "Seu carrinho ainda não foi iniciado neste navegador. Explore o catálogo para escolher produtos.",
        "missing_tenant": "Não encontramos uma loja ativa para carregar o carrinho.",
        "empty": "Seu carrinho ainda não possui itens. Explore a vitrine e adicione produtos quando quiser continuar.",
    }
    return {
        "page_title": "Carrinho",
        "page_description": "Revise seus itens antes de seguir para o checkout.",
        "cart_items": [],
        "subtotal": "R$ 0,00",
        "discount_total": "",
        "total": "R$ 0,00",
        "summary_description": "Nenhum item selecionado ainda.",
        "summary_note": "O pedido só será criado depois do checkout.",
        "empty_title": "Seu carrinho está vazio",
        "empty_description": descriptions.get(reason, descriptions["empty"]),
        "continue_shopping_href": "/catalog/",
        "checkout_href": "",
        "coupon_code": "",
        "coupon_message": "",
        "coupon_state": "",
        "cart_state": reason,
        "conversion_readiness_items": [],
        "delivery_promise": {},
    }


class CartPageReadRepository(Protocol):
    def get_cart_page_data(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        ...


class DjangoOrmCartPageRepository:
    def __init__(self) -> None:
        try:
            from app.modules.cart.models import Cart
        except Exception:
            self.cart_model = None
            return
        self.cart_model = Cart

    def is_ready(self) -> bool:
        if self.cart_model is None:
            return False
        try:
            table_names = {
                self.cart_model._meta.db_table,
                self.cart_model._meta.get_field("items").related_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def get_cart_page_data(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        if not tenant_id:
            return _empty_payload(reason="missing_tenant")
        normalized_session_key = str(session_key or "").strip()
        if not normalized_session_key:
            return _empty_payload(reason="missing_session")
        if not self.is_ready():
            return _empty_payload(reason="empty")

        try:
            cart = (
                self.cart_model._default_manager.prefetch_related("items")
                .filter(
                    tenant_id=tenant_id,
                    session_key=normalized_session_key,
                    status=self.cart_model.Status.ACTIVE,
                )
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            cart = None
        if cart is None:
            return _empty_payload(reason="empty")

        items = list(cart.items.all())
        if not items:
            payload = _empty_payload(reason="empty")
            payload["cart_state"] = "active-empty"
            payload["coupon_code"] = str(getattr(cart, "coupon_code", "") or "")
            if payload["coupon_code"]:
                payload["coupon_message"] = (
                    "Cupom salvo como intenção, mas validação promocional ainda não está ativa para esta loja."
                )
                payload["coupon_state"] = "validation-unavailable"
            return payload

        coupon_code = str(getattr(cart, "coupon_code", "") or "")
        discount_value = _safe_decimal(getattr(cart, "discount_total", "0.00"))
        delivery_promise = delivery_promise_queries.get_pre_checkout_promise(tenant_id=tenant_id)
        return {
            "page_title": "Carrinho",
            "page_description": "Revise os produtos escolhidos antes de seguir para entrega e pagamento.",
            "cart_id": cart.id,
            "cart_items": [
                {
                    "id": item.id,
                    "cart_id": cart.id,
                    "image_url": item.image_url,
                    "image_alt": item.image_alt,
                    "title": item.product_name,
                    "subtitle": item.variant_label,
                    "meta": f"SKU {item.variant_sku}" if item.variant_sku else item.product_slug,
                    "price": _format_currency(item.price_snapshot),
                    "compare_price": _format_currency(item.compare_price_snapshot) if item.compare_price_snapshot else "",
                    "quantity": item.quantity,
                    "quantity_readonly": False,
                    "mutation_actions": [
                        {"value": "decrement", "label": "-"},
                        {"value": "increment", "label": "+"},
                        {"value": "remove", "label": "Remover", "variant": "secondary"},
                    ],
                }
                for item in items
            ],
            "subtotal": _format_currency(cart.subtotal),
            "discount_total": _format_currency(cart.discount_total, negative=True) if cart.discount_total else "",
            "total": _format_currency(cart.total),
            "summary_description": f"{len(items)} item(ns) no carrinho.",
            "summary_note": "Frete e pagamento continuam no checkout; nenhum pedido nasce nesta tela.",
            "conversion_readiness_title": "Próximo passo seguro",
            "conversion_readiness_description": "Seu carrinho está pronto para virar uma sessão de checkout sem criar pedido ainda.",
            "conversion_readiness_items": [
                {
                    "label": "Itens revisáveis",
                    "description": f"{len(items)} item(ns) podem ser ajustados antes de informar entrega e pagamento.",
                    "ready": True,
                },
                {
                    "label": "Frete no checkout",
                    "description": "O frete será escolhido na próxima etapa, antes de qualquer pedido ser criado.",
                    "ready": True,
                },
                {
                    "label": "Pedido ainda não criado",
                    "description": "A compra só nasce depois da escolha de frete, pagamento e confirmação explícita.",
                    "ready": True,
                },
            ],
            "delivery_promise": delivery_promise,
            "coupon_code": coupon_code,
            "coupon_message": (
                "Cupom aplicado ao carrinho."
                if discount_value > 0
                else "Cupom salvo, mas nenhum desconto foi aplicado para este carrinho."
                if coupon_code
                else "Digite um cupom para validar desconto neste carrinho."
            ),
            "coupon_state": "applied" if coupon_code and discount_value > 0 else "not-applied" if coupon_code else "empty",
            "empty_title": "Seu carrinho está vazio",
            "empty_description": "Adicione produtos pela vitrine para revisar o carrinho aqui.",
            "continue_shopping_href": "/catalog/",
            "checkout_href": "/cart/",
            "cart_state": "active",
        }


@dataclass
class CartPageQueryService:
    repository: CartPageReadRepository

    def get_cart_page_data(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        return self.repository.get_cart_page_data(tenant_id=tenant_id, session_key=session_key)


cart_page_queries = CartPageQueryService(repository=DjangoOrmCartPageRepository())
