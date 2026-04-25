from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.orders.application.admin_order_queries import admin_order_queries


def _string(value: object) -> str:
    return str(value or "").strip()


def _label(value: object, *, default: str = "none") -> str:
    normalized = _string(value).lower().replace(" ", "_")
    for source, target in (
        ("ç", "c"),
        ("ã", "a"),
        ("á", "a"),
        ("é", "e"),
        ("ê", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("õ", "o"),
    ):
        normalized = normalized.replace(source, target)
    return normalized or default


class InventoryExceptionMetricsRepository(Protocol):
    def list_tenant_ids(self) -> list[int]:
        ...

    def list_orders(self, *, tenant_id: int) -> list[dict[str, object]]:
        ...


class DjangoOrmInventoryExceptionMetricsRepository:
    def list_tenant_ids(self) -> list[int]:
        try:
            from app.modules.orders.models import Order
        except Exception:
            return []
        return list(Order.objects.values_list("tenant_id", flat=True).distinct().order_by("tenant_id"))

    def list_orders(self, *, tenant_id: int) -> list[dict[str, object]]:
        return admin_order_queries.list_orders(tenant_id=tenant_id)


@dataclass
class InventoryExceptionMetricsQueryService:
    repository: InventoryExceptionMetricsRepository

    def export_prometheus_metrics(self) -> str:
        state_counts: dict[tuple[str, str], int] = {}
        priority_counts: dict[tuple[str, str], int] = {}
        owner_counts: dict[tuple[str, str], int] = {}
        aging_counts: dict[tuple[str, str], int] = {}

        for tenant_id in self.repository.list_tenant_ids():
            for order in self.repository.list_orders(tenant_id=tenant_id):
                state = _string(order.get("inventory_exception_list_label"))
                if state not in {"Exceção ativa", "Em revisão", "Resolvida"}:
                    continue
                tenant_label = str(tenant_id)
                priority = _label(order.get("inventory_exception_priority_label"))
                owner = "assigned" if _string(order.get("inventory_exception_owner_label")) else "unassigned"
                aging = _label(order.get("inventory_exception_aging_label"))
                state_counts[(tenant_label, _label(state))] = state_counts.get((tenant_label, _label(state)), 0) + 1
                priority_counts[(tenant_label, priority)] = priority_counts.get((tenant_label, priority), 0) + 1
                owner_counts[(tenant_label, owner)] = owner_counts.get((tenant_label, owner), 0) + 1
                aging_counts[(tenant_label, aging)] = aging_counts.get((tenant_label, aging), 0) + 1

        lines = [
            "# HELP hubx_inventory_exception_total Total de exceções de estoque por tenant e estado.",
            "# TYPE hubx_inventory_exception_total gauge",
        ]
        for (tenant_id, state), count in sorted(state_counts.items()):
            lines.append(f'hubx_inventory_exception_total{{tenant_id="{tenant_id}",state="{state}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_inventory_exception_priority_total Total de exceções de estoque por tenant e prioridade.",
                "# TYPE hubx_inventory_exception_priority_total gauge",
            ]
        )
        for (tenant_id, priority), count in sorted(priority_counts.items()):
            lines.append(f'hubx_inventory_exception_priority_total{{tenant_id="{tenant_id}",priority="{priority}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_inventory_exception_owner_total Total de exceções de estoque por tenant e ownership.",
                "# TYPE hubx_inventory_exception_owner_total gauge",
            ]
        )
        for (tenant_id, owner), count in sorted(owner_counts.items()):
            lines.append(f'hubx_inventory_exception_owner_total{{tenant_id="{tenant_id}",owner_state="{owner}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_inventory_exception_aging_total Total de exceções de estoque por tenant e aging.",
                "# TYPE hubx_inventory_exception_aging_total gauge",
            ]
        )
        for (tenant_id, aging), count in sorted(aging_counts.items()):
            lines.append(f'hubx_inventory_exception_aging_total{{tenant_id="{tenant_id}",aging="{aging}"}} {count}')
        return "\n".join(lines) + "\n"


inventory_exception_metrics_queries = InventoryExceptionMetricsQueryService(
    repository=DjangoOrmInventoryExceptionMetricsRepository(),
)
