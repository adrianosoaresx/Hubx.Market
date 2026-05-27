from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_commercial_quotas_closure_queries import (
    api_key_commercial_quotas_closure_queries,
)


@dataclass(frozen=True)
class SystemRoiPostQuotaCandidate:
    key: str
    score: int
    recommended_track: str
    rationale: str


@dataclass(frozen=True)
class SystemRoiPostQuotaDecision:
    key: str
    status: str
    summary: str


@dataclass
class SystemRoiPostQuotaReselectionQueryService:
    def get_review(
        self,
        *,
        quota_contract_ready: bool = False,
        quota_model_ready: bool = False,
        quota_enforcement_review_ready: bool = False,
        quota_enforcement_ready: bool = False,
        quota_admin_visibility_review_ready: bool = False,
        quota_admin_visibility_ready: bool = False,
        quota_metrics_ready: bool = False,
        quota_audit_ready: bool = False,
        quota_no_billing_charge_created: bool = False,
        quota_no_plan_enforcement_created: bool = False,
        quota_no_sensitive_material_recorded: bool = False,
        quota_docs_updated: bool = False,
        quota_decision_recorded: bool = False,
        payments_provider_production_blocker: bool = False,
        payments_refund_reconciliation_blocker: bool = False,
        shipping_quote_conversion_blocker: bool = False,
        shipping_carrier_contract_ready: bool = False,
        cross_module_runbook_gap_confirmed: bool = False,
        production_closure_requested: bool = False,
        storefront_conversion_pressure_confirmed: bool = False,
    ) -> dict[str, object]:
        quota_closure = api_key_commercial_quotas_closure_queries.get_review(
            contract_ready=quota_contract_ready,
            model_ready=quota_model_ready,
            enforcement_review_ready=quota_enforcement_review_ready,
            enforcement_ready=quota_enforcement_ready,
            admin_visibility_review_ready=quota_admin_visibility_review_ready,
            admin_visibility_ready=quota_admin_visibility_ready,
            metrics_ready=quota_metrics_ready,
            audit_ready=quota_audit_ready,
            no_billing_charge_created=quota_no_billing_charge_created,
            no_plan_enforcement_created=quota_no_plan_enforcement_created,
            no_sensitive_material_recorded=quota_no_sensitive_material_recorded,
            docs_updated=quota_docs_updated,
            decision_recorded=quota_decision_recorded,
        )
        candidates = self._candidates(
            payments_provider_production_blocker=payments_provider_production_blocker,
            payments_refund_reconciliation_blocker=payments_refund_reconciliation_blocker,
            shipping_quote_conversion_blocker=shipping_quote_conversion_blocker,
            shipping_carrier_contract_ready=shipping_carrier_contract_ready,
            cross_module_runbook_gap_confirmed=cross_module_runbook_gap_confirmed,
            production_closure_requested=production_closure_requested,
            storefront_conversion_pressure_confirmed=storefront_conversion_pressure_confirmed,
        )
        recommendation = max(candidates, key=lambda candidate: candidate.score)
        blockers = self._blockers(quota_closure=quota_closure, candidates=candidates)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-roi-post-quota-reselection-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "system",
            "quota_closure": self._closure_summary(quota_closure=quota_closure),
            "candidates": candidates,
            "recommendation": recommendation,
            "decisions": self._decisions(
                quota_closure=quota_closure,
                recommendation=recommendation,
                status=status,
            ),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status, recommendation=recommendation),
            "out_of_scope": self._out_of_scope(),
        }

    def _candidates(
        self,
        *,
        payments_provider_production_blocker: bool,
        payments_refund_reconciliation_blocker: bool,
        shipping_quote_conversion_blocker: bool,
        shipping_carrier_contract_ready: bool,
        cross_module_runbook_gap_confirmed: bool,
        production_closure_requested: bool,
        storefront_conversion_pressure_confirmed: bool,
    ) -> tuple[SystemRoiPostQuotaCandidate, ...]:
        return (
            SystemRoiPostQuotaCandidate(
                key="payments-production-readiness",
                score=92
                if payments_provider_production_blocker and payments_refund_reconciliation_blocker
                else 74
                if payments_provider_production_blocker or payments_refund_reconciliation_blocker
                else 42,
                recommended_track="Payments Production Readiness Review",
                rationale="pagamentos concentram risco de receita real, provider, refund e conciliação antes de crescimento",
            ),
            SystemRoiPostQuotaCandidate(
                key="shipping-real-quotes",
                score=88 if shipping_quote_conversion_blocker and shipping_carrier_contract_ready else 58 if shipping_quote_conversion_blocker else 36,
                recommended_track="Shipping Real Quote & SLA Activation Review",
                rationale="cotação real destrava conversão quando há contrato de transportadora e blocker explícito de checkout",
            ),
            SystemRoiPostQuotaCandidate(
                key="cross-module-runbooks",
                score=84 if cross_module_runbook_gap_confirmed and production_closure_requested else 52 if cross_module_runbook_gap_confirmed else 34,
                recommended_track="Cross-Module Production Runbook Closure Review",
                rationale="runbooks cross-module reduzem risco de ativação, mas devem seguir blockers financeiros/logísticos reais",
            ),
            SystemRoiPostQuotaCandidate(
                key="storefront-conversion",
                score=70 if storefront_conversion_pressure_confirmed else 28,
                recommended_track="Storefront Conversion Experimentation Review",
                rationale="otimização de conversão só deve furar fila quando houver tráfego/dados reais suficientes",
            ),
        )

    def _blockers(
        self,
        *,
        quota_closure: dict[str, object],
        candidates: tuple[SystemRoiPostQuotaCandidate, ...],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not quota_closure["ready"]:
            blockers.append(f"quota-closure:{quota_closure['result']}")
            blockers.extend(f"quota-closure:{blocker}" for blocker in quota_closure["blockers"])
        if max(candidate.score for candidate in candidates) < 50:
            blockers.append("roi:no-post-quota-candidate-above-threshold")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        quota_closure: dict[str, object],
        recommendation: SystemRoiPostQuotaCandidate,
        status: str,
    ) -> tuple[SystemRoiPostQuotaDecision, ...]:
        return (
            SystemRoiPostQuotaDecision(
                key="quota-closure",
                status="ready" if quota_closure["ready"] else "blocked",
                summary="re-seleção só segue após Battery B fechada sem billing/plano/segredo pendente",
            ),
            SystemRoiPostQuotaDecision(
                key="recommended-track",
                status=recommendation.key,
                summary=recommendation.rationale,
            ),
            SystemRoiPostQuotaDecision(
                key="classification",
                status=status,
                summary="classificação escolhe a próxima bateria após ativação de parceiro e quotas comerciais",
            ),
        )

    def _closure_summary(self, *, quota_closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": quota_closure["result"],
            "ready": bool(quota_closure["ready"]),
            "closed_scope_count": len(quota_closure["closure_scope"]),
        }

    def _next_tracks(
        self,
        *,
        status: str,
        recommendation: SystemRoiPostQuotaCandidate,
    ) -> tuple[str, ...]:
        if status == "ready":
            return (
                recommendation.recommended_track,
                "System Production Closure Review",
            )
        return (
            "API Key Commercial Quotas Closure Review",
            "System ROI Re-Selection Follow-Up",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar provider de pagamento nesta review",
            "não ativar transportadora real nesta review",
            "não alterar billing, quota ou API pública",
            "não executar runbook produtivo",
        )


system_roi_post_quota_reselection_queries = SystemRoiPostQuotaReselectionQueryService()
