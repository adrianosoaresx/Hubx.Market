from __future__ import annotations

from dataclasses import dataclass


PRE_CHECKOUT_DELIVERY_OPTIONS = [
    {
        "label": "Entrega padrão",
        "description": "Estimativa exibida no checkout: até 5 dias úteis após confirmação.",
        "price_hint": "A partir de R$ 24,90",
    },
    {
        "label": "Entrega expressa",
        "description": "Estimativa exibida no checkout: até 2 dias úteis após confirmação.",
        "price_hint": "A partir de R$ 39,90",
    },
]


@dataclass
class DeliveryPromiseQueryService:
    def get_pre_checkout_promise(self, *, tenant_id: int | str | None) -> dict[str, object]:
        if not tenant_id:
            return {}
        return {
            "title": "Entrega no próximo passo",
            "description": "Você escolhe frete e prazo no checkout antes de qualquer pedido ser criado.",
            "items": PRE_CHECKOUT_DELIVERY_OPTIONS,
            "note": "Valores e prazos finais dependem do endereço informado no checkout.",
        }


delivery_promise_queries = DeliveryPromiseQueryService()
