from __future__ import annotations

from dataclasses import dataclass


PRODUCTION_MODULE_MATRIX: tuple[dict[str, str], ...] = (
    {"module": "tenants", "status": "ready", "risk": "custom-domain-remains-contract-only"},
    {"module": "accounts", "status": "ready", "risk": "owner-mfa-vault-rollout-operational"},
    {"module": "catalog", "status": "ready", "risk": "conversion-experiment-needs-volume"},
    {"module": "cart", "status": "ready", "risk": "cart-session-growth-needs-monitoring"},
    {"module": "checkout", "status": "ready", "risk": "provider-dependent-payment-step"},
    {"module": "orders", "status": "ready", "risk": "fulfillment-lifecycle-still-basic"},
    {"module": "payments", "status": "watch", "risk": "provider-production-evidence-required"},
    {"module": "shipping", "status": "ready", "risk": "carrier-real-quote-rollout-required"},
    {"module": "notifications", "status": "ready", "risk": "email-provider-production-evidence-required"},
    {"module": "api_keys", "status": "ready", "risk": "partner-quota-monitoring-required"},
    {"module": "subscriptions", "status": "ready", "risk": "billing-provider-not-enabled"},
    {"module": "audit", "status": "ready", "risk": "evidence-retention-policy-future"},
)


@dataclass(frozen=True)
class SystemProductionDecision:
    key: str
    status: str
    summary: str


def _blockers(prefix: str, signals: dict[str, bool]) -> tuple[str, ...]:
    return tuple(f"{prefix}:{key}:missing" for key, value in signals.items() if not value)


@dataclass
class SystemProductionReadinessMatrixQueryService:
    def get_review(self, *, matrix_reviewed: bool = False, watch_risks_accepted: bool = False) -> dict[str, object]:
        signals = {
            "matrix_reviewed": bool(matrix_reviewed),
            "watch_risks_accepted": bool(watch_risks_accepted),
        }
        blockers = _blockers("system-production-matrix", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-production-matrix-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "signals": signals,
            "matrix": PRODUCTION_MODULE_MATRIX,
            "blockers": blockers,
        }


@dataclass
class SystemProductionRunbookGapQueryService:
    def get_review(
        self,
        *,
        payments_runbook_ready: bool = False,
        notifications_runbook_ready: bool = False,
        shipping_runbook_ready: bool = False,
        catalog_runbook_ready: bool = False,
        checkout_runbook_ready: bool = False,
        incident_owner_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "payments_runbook_ready": bool(payments_runbook_ready),
            "notifications_runbook_ready": bool(notifications_runbook_ready),
            "shipping_runbook_ready": bool(shipping_runbook_ready),
            "catalog_runbook_ready": bool(catalog_runbook_ready),
            "checkout_runbook_ready": bool(checkout_runbook_ready),
            "incident_owner_confirmed": bool(incident_owner_confirmed),
        }
        blockers = _blockers("system-production-runbooks", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-production-runbooks-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "signals": signals,
            "critical_runbooks": ("payments", "notifications", "shipping", "catalog", "checkout"),
            "blockers": blockers,
        }


@dataclass
class SystemProductionSmokeChecklistQueryService:
    def get_review(
        self,
        *,
        tenant_resolution_smoke: bool = False,
        storefront_catalog_smoke: bool = False,
        cart_checkout_smoke: bool = False,
        payment_provider_smoke: bool = False,
        notification_smoke: bool = False,
        api_key_smoke: bool = False,
        no_sensitive_output: bool = False,
    ) -> dict[str, object]:
        signals = {
            "tenant_resolution_smoke": bool(tenant_resolution_smoke),
            "storefront_catalog_smoke": bool(storefront_catalog_smoke),
            "cart_checkout_smoke": bool(cart_checkout_smoke),
            "payment_provider_smoke": bool(payment_provider_smoke),
            "notification_smoke": bool(notification_smoke),
            "api_key_smoke": bool(api_key_smoke),
            "no_sensitive_output": bool(no_sensitive_output),
        }
        blockers = _blockers("system-production-smoke", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-production-smoke-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "signals": signals,
            "smoke_scope": (
                "tenant resolution",
                "storefront catalog/PDP",
                "cart/checkout handoff",
                "payment provider",
                "notification provider",
                "api key public endpoints",
            ),
            "blockers": blockers,
        }


@dataclass
class SystemProductionObservabilityClosureQueryService:
    def get_review(
        self,
        *,
        prometheus_scrape_confirmed: bool = False,
        grafana_dashboards_confirmed: bool = False,
        alertmanager_routes_confirmed: bool = False,
        audit_export_ready: bool = False,
        oncall_triage_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "prometheus_scrape_confirmed": bool(prometheus_scrape_confirmed),
            "grafana_dashboards_confirmed": bool(grafana_dashboards_confirmed),
            "alertmanager_routes_confirmed": bool(alertmanager_routes_confirmed),
            "audit_export_ready": bool(audit_export_ready),
            "oncall_triage_confirmed": bool(oncall_triage_confirmed),
        }
        blockers = _blockers("system-production-observability", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-production-observability-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "signals": signals,
            "blockers": blockers,
        }


@dataclass
class SystemProductionRollbackDrillQueryService:
    def get_review(
        self,
        *,
        feature_flags_rollback_confirmed: bool = False,
        provider_rollback_confirmed: bool = False,
        ops_gate_rollback_confirmed: bool = False,
        communication_plan_confirmed: bool = False,
        data_restore_owner_confirmed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "feature_flags_rollback_confirmed": bool(feature_flags_rollback_confirmed),
            "provider_rollback_confirmed": bool(provider_rollback_confirmed),
            "ops_gate_rollback_confirmed": bool(ops_gate_rollback_confirmed),
            "communication_plan_confirmed": bool(communication_plan_confirmed),
            "data_restore_owner_confirmed": bool(data_restore_owner_confirmed),
        }
        blockers = _blockers("system-production-rollback", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-production-rollback-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "signals": signals,
            "rollback_scope": ("feature flags", "providers", "ops gate", "customer/support communication", "data restore owner"),
            "blockers": blockers,
        }


@dataclass
class SystemProductionGoNoGoQueryService:
    def get_review(
        self,
        *,
        readiness_matrix_ready: bool = False,
        runbooks_ready: bool = False,
        smoke_checklist_ready: bool = False,
        observability_ready: bool = False,
        rollback_drill_ready: bool = False,
        residual_risks_accepted: bool = False,
        decision_owner_confirmed: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "readiness_matrix_ready": bool(readiness_matrix_ready),
            "runbooks_ready": bool(runbooks_ready),
            "smoke_checklist_ready": bool(smoke_checklist_ready),
            "observability_ready": bool(observability_ready),
            "rollback_drill_ready": bool(rollback_drill_ready),
            "residual_risks_accepted": bool(residual_risks_accepted),
            "decision_owner_confirmed": bool(decision_owner_confirmed),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = _blockers("system-production-go-nogo", signals)
        go = not blockers
        status = "go" if go else "no-go"
        return {
            "result": f"system-production-{status}",
            "ready": go,
            "status": status,
            "module": "tenants",
            "signals": signals,
            "decisions": (
                SystemProductionDecision("production", "go" if go else "no-go", "decisão objetiva de produção real"),
                SystemProductionDecision("scope", "controlled", "ativação deve ser controlada por tenant e provider"),
                SystemProductionDecision("residual-risk", "accepted" if residual_risks_accepted else "blocked", "riscos residuais precisam de aceite explícito"),
            ),
            "closure_scope": (
                "readiness matrix refresh",
                "cross-module runbook gap review",
                "production smoke checklist",
                "observability coverage closure",
                "rollback/incident drill",
                "go/no-go decision",
            ),
            "blockers": blockers,
            "next_tracks": ("Growth/Commercial Activation Track",) if go else ("Production Corrective Battery",),
        }


system_production_readiness_matrix_queries = SystemProductionReadinessMatrixQueryService()
system_production_runbook_gap_queries = SystemProductionRunbookGapQueryService()
system_production_smoke_checklist_queries = SystemProductionSmokeChecklistQueryService()
system_production_observability_closure_queries = SystemProductionObservabilityClosureQueryService()
system_production_rollback_drill_queries = SystemProductionRollbackDrillQueryService()
system_production_go_nogo_queries = SystemProductionGoNoGoQueryService()
