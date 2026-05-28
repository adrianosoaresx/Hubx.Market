from __future__ import annotations

from dataclasses import dataclass

from app.modules.tenants.application.platform_store_management_queries import (
    platform_store_management_track_closure_queries,
)


@dataclass(frozen=True)
class SystemRoiCandidate:
    key: str
    score: int
    recommended_track: str
    rationale: str


@dataclass(frozen=True)
class SystemRoiDecision:
    key: str
    status: str
    summary: str


@dataclass
class SystemRoiReselectionQueryService:
    def get_review(
        self,
        *,
        tenant_ops_closed_confirmed: bool = False,
        owner_bootstrap_closed_confirmed: bool = False,
        custom_domain_runtime_closed_confirmed: bool = False,
        production_evidence_confirmed: bool = False,
        docs_tests_confirmed: bool = False,
        remaining_risks_accepted: bool = False,
        production_validation_preferred: bool = False,
        storefront_regression_pressure_confirmed: bool = False,
        payments_provider_blocker_confirmed: bool = False,
        shipping_provider_blocker_confirmed: bool = False,
        platform_ops_support_pressure_confirmed: bool = False,
        cross_module_runbook_pressure_confirmed: bool = False,
    ) -> dict[str, object]:
        store_management_closure = platform_store_management_track_closure_queries.get_review(
            tenant_ops_closed_confirmed=tenant_ops_closed_confirmed,
            owner_bootstrap_closed_confirmed=owner_bootstrap_closed_confirmed,
            custom_domain_runtime_closed_confirmed=custom_domain_runtime_closed_confirmed,
            production_evidence_confirmed=production_evidence_confirmed,
            docs_tests_confirmed=docs_tests_confirmed,
            remaining_risks_accepted=remaining_risks_accepted,
        )
        candidates = self._candidates(
            production_validation_preferred=production_validation_preferred,
            storefront_regression_pressure_confirmed=storefront_regression_pressure_confirmed,
            payments_provider_blocker_confirmed=payments_provider_blocker_confirmed,
            shipping_provider_blocker_confirmed=shipping_provider_blocker_confirmed,
            platform_ops_support_pressure_confirmed=platform_ops_support_pressure_confirmed,
            cross_module_runbook_pressure_confirmed=cross_module_runbook_pressure_confirmed,
        )
        recommendation = max(candidates, key=lambda candidate: candidate.score)
        blockers = self._blockers(store_management_closure=store_management_closure, candidates=candidates)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-roi-reselection-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "store_management_closure": self._closure_summary(closure=store_management_closure),
            "candidates": candidates,
            "recommendation": recommendation,
            "decisions": self._decisions(
                store_management_closure=store_management_closure,
                recommendation=recommendation,
                status=status,
                storefront_regression_pressure_confirmed=storefront_regression_pressure_confirmed,
            ),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status, recommendation=recommendation),
        }

    def _candidates(
        self,
        *,
        production_validation_preferred: bool,
        storefront_regression_pressure_confirmed: bool,
        payments_provider_blocker_confirmed: bool,
        shipping_provider_blocker_confirmed: bool,
        platform_ops_support_pressure_confirmed: bool,
        cross_module_runbook_pressure_confirmed: bool,
    ) -> tuple[SystemRoiCandidate, ...]:
        return (
            SystemRoiCandidate(
                key="storefront-admin-smoke-regression",
                score=self._storefront_validation_score(
                    production_validation_preferred=production_validation_preferred,
                    storefront_regression_pressure_confirmed=storefront_regression_pressure_confirmed,
                ),
                recommended_track="System Validation Pass 2 — Storefront/Admin Smoke & Template Regression",
                rationale="antes de nova expansão, validar home/loja/PDP/login/admin reduz risco real percebido e corrige quebras visíveis",
            ),
            SystemRoiCandidate(
                key="payments-production-readiness",
                score=86 if payments_provider_blocker_confirmed else 58,
                recommended_track="Payments Production Readiness Review",
                rationale="pagamentos ainda concentram maior risco produtivo quando provider/webhook/refund/conciliação bloqueiam venda real",
            ),
            SystemRoiCandidate(
                key="shipping-real-provider",
                score=78 if shipping_provider_blocker_confirmed else 34,
                recommended_track="Shipping Real Provider Activation Review",
                rationale="frete real destrava checkout mais fiel, mas deve esperar pressão clara de cotação/transportadora",
            ),
            SystemRoiCandidate(
                key="platform-ops-support-hardening",
                score=72 if platform_ops_support_pressure_confirmed else 30,
                recommended_track="Platform Ops Support Hardening Review",
                rationale="melhora operação de tenants quando suporte/ativação estão gerando fricção concreta",
            ),
            SystemRoiCandidate(
                key="cross-module-runbook-closure",
                score=68 if cross_module_runbook_pressure_confirmed else 28,
                recommended_track="Cross-Module Production Runbook Closure Review",
                rationale="runbooks aumentam segurança operacional, mas não devem substituir validação funcional visível",
            ),
        )

    def _storefront_validation_score(
        self,
        *,
        production_validation_preferred: bool,
        storefront_regression_pressure_confirmed: bool,
    ) -> int:
        if production_validation_preferred and storefront_regression_pressure_confirmed:
            return 92
        if production_validation_preferred:
            return 64
        return 38

    def _closure_summary(self, *, closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": closure["result"],
            "ready": bool(closure["ready"]),
            "module": closure["module"],
            "deliverable_count": len(closure["deliverables"]),
        }

    def _blockers(
        self,
        *,
        store_management_closure: dict[str, object],
        candidates: tuple[SystemRoiCandidate, ...],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not store_management_closure["ready"]:
            blockers.append(f"store-management:{store_management_closure['result']}")
            blockers.extend(f"store-management:{blocker}" for blocker in store_management_closure["blockers"])
        if max(candidate.score for candidate in candidates) < 50:
            blockers.append("roi:no-system-candidate-above-threshold")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        store_management_closure: dict[str, object],
        recommendation: SystemRoiCandidate,
        status: str,
        storefront_regression_pressure_confirmed: bool,
    ) -> tuple[SystemRoiDecision, ...]:
        return (
            SystemRoiDecision(
                key="store-management-closure",
                status="ready" if store_management_closure["ready"] else "blocked",
                summary="re-seleção só segue quando Platform Store Management está fechado",
            ),
            SystemRoiDecision(
                key="visible-regression-pressure",
                status="confirmed" if storefront_regression_pressure_confirmed else "unconfirmed",
                summary="quebras visíveis em templates/navegação elevam ROI de validação funcional antes de novas features",
            ),
            SystemRoiDecision(
                key="recommended-track",
                status=recommendation.key,
                summary=recommendation.rationale,
            ),
            SystemRoiDecision(
                key="classification",
                status=status,
                summary="classificação escolhe a próxima trilha sistêmica sem alterar runtime, tenants ou providers",
            ),
        )

    def _next_tracks(self, *, status: str, recommendation: SystemRoiCandidate) -> tuple[str, ...]:
        if status == "ready":
            return (
                recommendation.recommended_track,
                "Payments Production Readiness Review",
            )
        return (
            "Platform Store Management — Store Management Track Closure",
            "System ROI Re-Selection Review",
        )


system_roi_reselection_queries = SystemRoiReselectionQueryService()
