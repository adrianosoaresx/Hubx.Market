from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorefrontConversionDecision:
    key: str
    status: str
    summary: str


@dataclass
class StorefrontConversionClosureQueryService:
    def get_review(
        self,
        *,
        baseline_ready: bool = False,
        pdp_funnel_ready: bool = False,
        search_facet_dropoff_ready: bool = False,
        experiment_contract_ready: bool = False,
        experiment_execution_ready: bool = False,
        no_full_redesign: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "baseline_ready": bool(baseline_ready),
            "pdp_funnel_ready": bool(pdp_funnel_ready),
            "search_facet_dropoff_ready": bool(search_facet_dropoff_ready),
            "experiment_contract_ready": bool(experiment_contract_ready),
            "experiment_execution_ready": bool(experiment_execution_ready),
            "no_full_redesign": bool(no_full_redesign),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = tuple(f"storefront-conversion:{key}:missing" for key, value in signals.items() if not value)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"storefront-conversion-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "catalog",
            "signals": signals,
            "decisions": (
                StorefrontConversionDecision("baseline", "ready" if signals["baseline_ready"] else "blocked", "eventos de discovery/PDP/CTA precisam gerar baseline mensurável"),
                StorefrontConversionDecision("experiment", "ready" if signals["experiment_contract_ready"] and signals["experiment_execution_ready"] else "blocked", "experimento product_card_priority_v1 precisa estar contratado e executado"),
                StorefrontConversionDecision("scope", "guarded" if signals["no_full_redesign"] else "blocked", "sem redesenhar storefront inteiro nesta bateria"),
            ),
            "closure_scope": (
                "conversion metrics baseline",
                "PDP CTA funnel evidence",
                "search/facet drop-off review",
                "product card priority experiment",
                "storefront conversion closure",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery J — System Production Closure",) if status == "ready" else ("Storefront Conversion Follow-Up",),
        }


storefront_conversion_closure_queries = StorefrontConversionClosureQueryService()
