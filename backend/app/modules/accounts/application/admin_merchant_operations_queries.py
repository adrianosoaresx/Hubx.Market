from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.accounts.application.admin_owner_queries import admin_owner_queries
from app.modules.catalog.application.admin_product_queries import admin_product_queries
from app.modules.customers.application.admin_customer_queries import admin_customer_queries
from app.modules.orders.application.admin_order_queries import admin_order_queries
from app.modules.shipping.application.admin_shipment_queries import admin_shipment_queries


def _safe_int(value: object) -> int:
    try:
        return int(str(value or "0").strip())
    except Exception:
        return 0


def _is_pending_order(order: dict[str, object]) -> bool:
    status = str(order.get("status", "") or "").strip().lower()
    payment_status = str(order.get("payment_status", "") or "").strip().lower()
    fulfillment_status = str(order.get("fulfillment_status_label", "") or "").strip().lower()
    return status == "pending" or "aguard" in payment_status or "aguard" in fulfillment_status


def _has_open_inventory_exception(order: dict[str, object]) -> bool:
    return str(order.get("inventory_exception_list_label", "") or "").strip() in {"Exceção ativa", "Em revisão"}


def _is_low_stock_product(product: dict[str, object]) -> bool:
    if not bool(product.get("track_inventory", True)):
        return False
    free_stock = max(_safe_int(product.get("stock")) - _safe_int(product.get("reserved_stock")), 0)
    return free_stock <= 3


def _needs_customer_attention(customer: dict[str, object]) -> bool:
    return (
        str(customer.get("priority_label", "") or "").strip() == "Alta prioridade"
        or bool(customer.get("is_at_risk"))
        or bool(customer.get("marked_for_followup"))
        or bool(customer.get("marked_for_reengagement"))
    )


def _has_shipping_gap(shipment: object) -> bool:
    status = str(getattr(shipment, "shipping_status", "") or "").strip().lower()
    shipment_status = str(getattr(shipment, "shipment_status", "") or "").strip().lower()
    tracking_code = str(getattr(shipment, "tracking_code", "") or "").strip()
    return not tracking_code and status not in {"", "aguardando pagamento"} and shipment_status not in {"delivered", "entregue"}


def _task(
    *,
    area: str,
    signal: str,
    count: int,
    action: str,
    href: str,
    severity: str = "info",
) -> dict[str, Any]:
    return {
        "area": area,
        "signal": signal,
        "count": count,
        "action": action,
        "href": href,
        "severity": severity,
    }


@dataclass
class AdminMerchantOperationsQueryService:
    def get_dashboard(self, *, tenant_id: int | None) -> dict[str, Any]:
        orders = admin_order_queries.list_orders(tenant_id=tenant_id)
        products = admin_product_queries.list_products(tenant_id=tenant_id)
        customers = admin_customer_queries.list_customers(tenant_id=tenant_id)
        shipments = admin_shipment_queries.list_shipments(tenant_id=tenant_id or "")
        owners = admin_owner_queries.list_owners(tenant_id=tenant_id or "")

        pending_orders = sum(1 for order in orders if _is_pending_order(order))
        open_inventory_exceptions = sum(1 for order in orders if _has_open_inventory_exception(order))
        active_products = sum(1 for product in products if bool(product.get("is_active")) or str(product.get("status", "")) == "active")
        low_stock_products = sum(1 for product in products if _is_low_stock_product(product))
        draft_or_inactive_products = sum(1 for product in products if str(product.get("status", "") or "") in {"draft", "inactive"})
        attention_customers = sum(1 for customer in customers if _needs_customer_attention(customer))
        shipping_gaps = sum(1 for shipment in shipments if _has_shipping_gap(shipment))
        owners_without_notifications = sum(1 for owner in owners if not owner.is_active or not owner.receives_notifications)

        tasks = [
            _task(
                area="Pedidos",
                signal="Pedidos pendentes de confirmação ou avanço operacional",
                count=pending_orders,
                action="Revisar pedidos pendentes",
                href="/ops/orders/?status=pending",
                severity="warning" if pending_orders else "success",
            ),
            _task(
                area="Estoque",
                signal="Exceções abertas ou em revisão na fila de pedidos",
                count=open_inventory_exceptions,
                action="Tratar exceções de estoque",
                href="/ops/orders/?quick_filter=active",
                severity="warning" if open_inventory_exceptions else "success",
            ),
            _task(
                area="Catálogo",
                signal="Produtos com baixo saldo livre, rascunho ou inativos",
                count=low_stock_products + draft_or_inactive_products,
                action="Revisar catálogo",
                href="/ops/catalog/products/",
                severity="warning" if low_stock_products or draft_or_inactive_products else "success",
            ),
            _task(
                area="Clientes",
                signal="Clientes em risco, prioridade alta ou follow-up",
                count=attention_customers,
                action="Priorizar clientes",
                href="/ops/customers/?quick_filter=high_priority",
                severity="warning" if attention_customers else "success",
            ),
            _task(
                area="Entregas",
                signal="Pedidos com entrega sem rastreio operacional visível",
                count=shipping_gaps,
                action="Revisar entregas",
                href="/ops/shipping/",
                severity="warning" if shipping_gaps else "success",
            ),
            _task(
                area="Administradores",
                signal="Administradores inativos ou com notificações administrativas pausadas",
                count=owners_without_notifications,
                action="Revisar administradores",
                href="/ops/owners/",
                severity="warning" if owners_without_notifications else "success",
            ),
        ]

        return {
            "kpis": [
                {
                    "title": "Pedidos pendentes",
                    "description": "Precisam de confirmação ou avanço",
                    "value": str(pending_orders),
                    "meta": f"{len(orders)} pedido(s) no recorte",
                },
                {
                    "title": "Exceções de estoque",
                    "description": "Abertas ou em revisão",
                    "value": str(open_inventory_exceptions),
                    "meta": "Fila operacional de pedidos",
                },
                {
                    "title": "Produtos ativos",
                    "description": "Publicados ou elegíveis na loja",
                    "value": str(active_products),
                    "meta": f"{low_stock_products} com estoque sensível",
                },
                {
                    "title": "Clientes em atenção",
                    "description": "Risco, prioridade ou follow-up",
                    "value": str(attention_customers),
                    "meta": f"{len(customers)} cliente(s) analisado(s)",
                },
            ],
            "tasks": tasks,
            "activity_items": self._build_activity_items(tasks),
            "recent_activity_items": self._build_recent_activity_items(tasks),
            "summary": self._summary(tasks),
        }

    @staticmethod
    def _build_activity_items(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
        active_tasks = [task for task in tasks if int(task["count"]) > 0]
        if not active_tasks:
            return [
                {
                    "title": "Operação sem bloqueio crítico",
                    "description": "Nenhuma pendência prioritária apareceu no recorte atual.",
                    "timestamp": "agora",
                    "badge_label": "OK",
                    "badge_variant": "success",
                    "meta": "Atualizado agora",
                }
            ]
        return [
            {
                "title": task["action"],
                "description": f"{task['count']} pendência(s): {task['signal']}.",
                "timestamp": "agora",
                "badge_label": task["area"],
                "badge_variant": "warning" if task["severity"] == "warning" else "info",
                "meta": str(task["href"]),
            }
            for task in active_tasks[:3]
        ]

    @staticmethod
    def _build_recent_activity_items(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
        active_tasks = [task for task in tasks if int(task["count"]) > 0]
        if not active_tasks:
            return [
                {
                    "title": "Nenhuma ação crítica pendente",
                    "description": "A operação não tem pendências prioritárias no recorte atual.",
                    "timestamp": "agora",
                    "badge_label": "OK",
                    "badge_variant": "success",
                    "meta": "Painel da loja",
                }
            ]
        return [
            {
                "title": task["action"],
                "description": f"{task['count']} pendência(s): {task['signal']}.",
                "timestamp": "agora",
                "badge_label": task["area"],
                "badge_variant": "warning" if task["severity"] == "warning" else "info",
                "meta": str(task["href"]),
                "href": str(task["href"]),
            }
            for task in active_tasks[:4]
        ]

    @staticmethod
    def _summary(tasks: list[dict[str, Any]]) -> str:
        active_count = sum(1 for task in tasks if int(task["count"]) > 0)
        if not active_count:
            return "Nenhum bloqueio crítico visível no recorte atual."
        return f"{active_count} frente(s) operacional(is) exigem atenção antes de ampliar a loja."


admin_merchant_operations_queries = AdminMerchantOperationsQueryService()
