from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyCommercialQuotasClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyCommercialQuotasClosureQueryService:
    def get_review(
        self,
        *,
        contract_ready: bool = False,
        model_ready: bool = False,
        enforcement_review_ready: bool = False,
        enforcement_ready: bool = False,
        admin_visibility_review_ready: bool = False,
        admin_visibility_ready: bool = False,
        metrics_ready: bool = False,
        audit_ready: bool = False,
        no_billing_charge_created: bool = False,
        no_plan_enforcement_created: bool = False,
        no_sensitive_material_recorded: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "contract_ready": bool(contract_ready),
            "model_ready": bool(model_ready),
            "enforcement_review_ready": bool(enforcement_review_ready),
            "enforcement_ready": bool(enforcement_ready),
            "admin_visibility_review_ready": bool(admin_visibility_review_ready),
            "admin_visibility_ready": bool(admin_visibility_ready),
            "metrics_ready": bool(metrics_ready),
            "audit_ready": bool(audit_ready),
            "no_billing_charge_created": bool(no_billing_charge_created),
            "no_plan_enforcement_created": bool(no_plan_enforcement_created),
            "no_sensitive_material_recorded": bool(no_sensitive_material_recorded),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-commercial-quotas-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "closure_scope": self._closure_scope(),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        return tuple(
            f"commercial-quotas-closure:{key}:missing"
            for key, value in signals.items()
            if not value
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyCommercialQuotasClosureDecision, ...]:
        return (
            ApiKeyCommercialQuotasClosureDecision(
                key="battery-b",
                status="complete"
                if signals["contract_ready"]
                and signals["model_ready"]
                and signals["enforcement_review_ready"]
                and signals["enforcement_ready"]
                and signals["admin_visibility_review_ready"]
                and signals["admin_visibility_ready"]
                else "blocked",
                summary="Battery B exige contrato, modelo, enforcement e visibilidade admin",
            ),
            ApiKeyCommercialQuotasClosureDecision(
                key="operability",
                status="ready" if signals["metrics_ready"] and signals["audit_ready"] else "blocked",
                summary="bloqueios por quota precisam gerar métrica e audit log",
            ),
            ApiKeyCommercialQuotasClosureDecision(
                key="boundaries",
                status="guarded"
                if signals["no_billing_charge_created"]
                and signals["no_plan_enforcement_created"]
                and signals["no_sensitive_material_recorded"]
                else "blocked",
                summary="closure confirma ausência de cobrança, plano e material sensível",
            ),
            ApiKeyCommercialQuotasClosureDecision(
                key="classification",
                status=status,
                summary="classificação encerra ou bloqueia a bateria de quotas comerciais",
            ),
        )

    def _closure_scope(self) -> tuple[str, ...]:
        return (
            "ApiKeyQuota model",
            "ApiKeyQuotaUsage model",
            "quota upsert application service",
            "runtime quota enforcement after rate-limit",
            "quota exceeded audit log",
            "quota exceeded Prometheus metric",
            "read-only admin quota visibility",
            "no billing or plan enforcement",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Payments Production Readiness",
                "System ROI Re-Selection Review",
            )
        return (
            "API Key Commercial Quotas Follow-Up",
            "API Key Quota Enforcement Execution",
        )


api_key_commercial_quotas_closure_queries = ApiKeyCommercialQuotasClosureQueryService()
