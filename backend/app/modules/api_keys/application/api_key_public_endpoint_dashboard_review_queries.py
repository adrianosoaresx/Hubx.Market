from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointDashboardDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointDashboardRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointDashboardReviewQueryService:
    def get_review(
        self,
        *,
        metrics_endpoint_available: bool = False,
        observability_token_required: bool = False,
        requests_panel_required: bool = False,
        auth_failure_panel_required: bool = False,
        rate_limit_panel_required: bool = False,
        endpoint_enabled_panel_required: bool = False,
        tenant_endpoint_filters_required: bool = False,
        low_cardinality_required: bool = False,
        no_sensitive_labels_required: bool = False,
        alert_rules_plan_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "metrics_endpoint_available": bool(metrics_endpoint_available),
            "observability_token_required": bool(observability_token_required),
            "requests_panel_required": bool(requests_panel_required),
            "auth_failure_panel_required": bool(auth_failure_panel_required),
            "rate_limit_panel_required": bool(rate_limit_panel_required),
            "endpoint_enabled_panel_required": bool(endpoint_enabled_panel_required),
            "tenant_endpoint_filters_required": bool(tenant_endpoint_filters_required),
            "low_cardinality_required": bool(low_cardinality_required),
            "no_sensitive_labels_required": bool(no_sensitive_labels_required),
            "alert_rules_plan_required": bool(alert_rules_plan_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-dashboard-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "dashboard": self._dashboard(),
            "panels": self._panels(),
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "requirements": self._requirements(),
            "blockers": blockers,
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        for key, value in signals.items():
            if not value:
                blockers.append(f"public-endpoint-dashboard:{key}:missing")
        return tuple(blockers)

    def _dashboard(self) -> dict[str, str]:
        return {
            "title": "Hubx API Key Public Endpoints",
            "slug": "api-key-public-endpoints",
            "datasource": "DS_PROMETHEUS",
            "owner": "api_keys",
        }

    def _panels(self) -> tuple[str, ...]:
        return (
            "public_request_rate_by_tenant_endpoint_result",
            "auth_failure_rate_by_tenant_endpoint_reason",
            "rate_limited_rate_by_tenant_endpoint_prefix",
            "public_endpoint_enabled_state",
            "top_tenants_by_public_request_volume",
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointDashboardDecision, ...]:
        return (
            ApiKeyPublicEndpointDashboardDecision(
                key="scope",
                status="required" if signals["metrics_endpoint_available"] else "blocked",
                summary="dashboard deve consumir apenas métricas Prometheus já exportadas pelo módulo api_keys",
            ),
            ApiKeyPublicEndpointDashboardDecision(
                key="security",
                status="required"
                if signals["observability_token_required"] and signals["no_sensitive_labels_required"]
                else "blocked",
                summary="dashboard não pode depender de API key pública nem mostrar segredo, hash ou header",
            ),
            ApiKeyPublicEndpointDashboardDecision(
                key="panels",
                status="required"
                if signals["requests_panel_required"]
                and signals["auth_failure_panel_required"]
                and signals["rate_limit_panel_required"]
                and signals["endpoint_enabled_panel_required"]
                else "blocked",
                summary="painel mínimo precisa cobrir volume, autenticação, rate limit e estado do endpoint",
            ),
            ApiKeyPublicEndpointDashboardDecision(
                key="labels",
                status="required"
                if signals["tenant_endpoint_filters_required"] and signals["low_cardinality_required"]
                else "blocked",
                summary="filtros por tenant/endpoint são úteis, mas devem manter cardinalidade baixa",
            ),
            ApiKeyPublicEndpointDashboardDecision(
                key="alerts",
                status="planned" if signals["alert_rules_plan_required"] else "blocked",
                summary="dashboard não substitui alert rules para 401/403/429 e endpoint disabled",
            ),
            ApiKeyPublicEndpointDashboardDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro materializar JSON Grafana",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointDashboardRequirement, ...]:
        return (
            ApiKeyPublicEndpointDashboardRequirement(
                key="requests",
                summary="painel de taxa por `tenant_id`, `endpoint` e `result` usando `hubx_api_key_public_request_total`",
            ),
            ApiKeyPublicEndpointDashboardRequirement(
                key="auth-failures",
                summary="painel de falhas por `tenant_id`, `endpoint` e `reason` usando `hubx_api_key_auth_failure_total`",
            ),
            ApiKeyPublicEndpointDashboardRequirement(
                key="rate-limit",
                summary="painel de rate limit por `tenant_id`, `endpoint` e `prefix` usando `hubx_api_key_rate_limited_total`",
            ),
            ApiKeyPublicEndpointDashboardRequirement(
                key="endpoint-enabled",
                summary="stat para `hubx_api_key_public_endpoint_enabled` por endpoint público",
            ),
            ApiKeyPublicEndpointDashboardRequirement(
                key="filters",
                summary="variáveis Grafana para Prometheus datasource, tenant e endpoint, sem expor segredo de API key",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não criar dashboard JSON nesta review",
            "não provisionar Grafana real nesta review",
            "não criar alert rules Prometheus nesta review",
            "não criar métricas novas nesta review",
            "não exportar segredo, hash, header ou valor claro de API key",
            "não criar billing/quotas comerciais nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Dashboard Execution",
                "API Key Public Endpoint Alert Rules Review",
            )
        return (
            "API Key Public Endpoint Dashboard Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_public_endpoint_dashboard_review_queries = ApiKeyPublicEndpointDashboardReviewQueryService()
