from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShippingQuoteProductionDecision:
    key: str
    status: str
    summary: str


def _blockers(prefix: str, signals: dict[str, bool]) -> tuple[str, ...]:
    return tuple(f"{prefix}:{key}:missing" for key, value in signals.items() if not value)


def _status(blockers: tuple[str, ...]) -> str:
    return "ready" if not blockers else "blocked"


@dataclass
class ShippingQuoteProductionizationQueryService:
    def get_review(
        self,
        *,
        provider_contract_ready: bool = False,
        adapter_skeleton_ready: bool = False,
        checkout_integration_review_ready: bool = False,
        checkout_execution_ready: bool = False,
        failure_ux_ready: bool = False,
        observability_ready: bool = False,
        tenant_scope_confirmed: bool = False,
        no_order_without_delivery_confirmed: bool = False,
        no_provider_secret_recorded: bool = False,
        rollback_plan_ready: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "provider_contract_ready": bool(provider_contract_ready),
            "adapter_skeleton_ready": bool(adapter_skeleton_ready),
            "checkout_integration_review_ready": bool(checkout_integration_review_ready),
            "checkout_execution_ready": bool(checkout_execution_ready),
            "failure_ux_ready": bool(failure_ux_ready),
            "observability_ready": bool(observability_ready),
            "tenant_scope_confirmed": bool(tenant_scope_confirmed),
            "no_order_without_delivery_confirmed": bool(no_order_without_delivery_confirmed),
            "no_provider_secret_recorded": bool(no_provider_secret_recorded),
            "rollback_plan_ready": bool(rollback_plan_ready),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = _blockers("shipping-quote-productionization", signals)
        status = _status(blockers)
        return {
            "result": f"shipping-quote-productionization-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "shipping",
            "signals": signals,
            "decisions": (
                ShippingQuoteProductionDecision(
                    key="provider",
                    status="ready" if signals["provider_contract_ready"] and signals["adapter_skeleton_ready"] else "blocked",
                    summary="contrato e adapter skeleton de quote precisam estar prontos",
                ),
                ShippingQuoteProductionDecision(
                    key="checkout",
                    status="ready" if signals["checkout_integration_review_ready"] and signals["checkout_execution_ready"] else "blocked",
                    summary="checkout deve consumir quote sem criar pedido sem delivery válido",
                ),
                ShippingQuoteProductionDecision(
                    key="operations",
                    status="ready" if signals["failure_ux_ready"] and signals["observability_ready"] and signals["rollback_plan_ready"] else "blocked",
                    summary="falha honesta, observabilidade e rollback fecham operação inicial",
                ),
                ShippingQuoteProductionDecision(
                    key="classification",
                    status=status,
                    summary="classificação encerra ou bloqueia Battery D",
                ),
            ),
            "closure_scope": (
                "shipping quote provider contract",
                "manual quote adapter skeleton",
                "checkout shipping quote command",
                "failure UX semantics",
                "quote observability contract",
                "tenant-scoped closure",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery E — Subscriptions & Tenant Billing Foundation", "System Production Closure Review") if status == "ready" else ("Shipping Quote Follow-Up",),
        }


shipping_quote_productionization_queries = ShippingQuoteProductionizationQueryService()
