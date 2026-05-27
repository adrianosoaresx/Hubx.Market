from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointObservabilityDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointObservabilityRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointObservabilityReviewQueryService:
    def get_review(
        self,
        *,
        public_endpoint_active: bool = False,
        auth_events_available: bool = False,
        rate_limit_events_available: bool = False,
        prometheus_metrics_required: bool = False,
        endpoint_labels_required: bool = False,
        tenant_labels_required: bool = False,
        key_prefix_labels_allowed: bool = False,
        no_secret_material_required: bool = False,
        alert_rules_required: bool = False,
        dashboard_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "public_endpoint_active": bool(public_endpoint_active),
            "auth_events_available": bool(auth_events_available),
            "rate_limit_events_available": bool(rate_limit_events_available),
            "prometheus_metrics_required": bool(prometheus_metrics_required),
            "endpoint_labels_required": bool(endpoint_labels_required),
            "tenant_labels_required": bool(tenant_labels_required),
            "key_prefix_labels_allowed": bool(key_prefix_labels_allowed),
            "no_secret_material_required": bool(no_secret_material_required),
            "alert_rules_required": bool(alert_rules_required),
            "dashboard_required": bool(dashboard_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-observability-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "recommended_metrics": self._recommended_metrics(),
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
                blockers.append(f"public-endpoint-observability:{key}:missing")
        return tuple(blockers)

    def _recommended_metrics(self) -> tuple[str, ...]:
        return (
            "hubx_api_key_public_request_total",
            "hubx_api_key_auth_failure_total",
            "hubx_api_key_rate_limited_total",
            "hubx_api_key_public_endpoint_enabled",
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointObservabilityDecision, ...]:
        return (
            ApiKeyPublicEndpointObservabilityDecision(
                key="metrics",
                status="required" if signals["prometheus_metrics_required"] else "blocked",
                summary="API keys públicas precisam de métricas Prometheus antes de ampliar endpoints",
            ),
            ApiKeyPublicEndpointObservabilityDecision(
                key="labels",
                status="required" if signals["endpoint_labels_required"] and signals["tenant_labels_required"] else "blocked",
                summary="métricas devem ter labels de tenant e endpoint; prefixo pode ser usado com cuidado",
            ),
            ApiKeyPublicEndpointObservabilityDecision(
                key="sensitive-data",
                status="required" if signals["no_secret_material_required"] else "blocked",
                summary="observabilidade não pode exportar segredo, hash, header ou valor claro de API key",
            ),
            ApiKeyPublicEndpointObservabilityDecision(
                key="operations",
                status="required" if signals["alert_rules_required"] and signals["dashboard_required"] else "blocked",
                summary="alert rules e dashboard mínimos devem acompanhar a métrica",
            ),
            ApiKeyPublicEndpointObservabilityDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro criar métricas/scrape/dashboard",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointObservabilityRequirement, ...]:
        return (
            ApiKeyPublicEndpointObservabilityRequirement(
                key="metrics-service",
                summary="criar query service em `api_keys.application` exportando Prometheus text format",
            ),
            ApiKeyPublicEndpointObservabilityRequirement(
                key="endpoint",
                summary="criar endpoint de métricas protegido por token de observabilidade, não por API key pública",
            ),
            ApiKeyPublicEndpointObservabilityRequirement(
                key="labels",
                summary="usar labels `tenant_id`, `endpoint`, `result` e opcionalmente `prefix`, sem segredo/hash/header",
            ),
            ApiKeyPublicEndpointObservabilityRequirement(
                key="alerts",
                summary="alertar picos de `auth_failed`, `rate_limited` e endpoint público desabilitado inesperadamente",
            ),
            ApiKeyPublicEndpointObservabilityRequirement(
                key="dashboard",
                summary="painel inicial com requests, 401/403/429, rate limit e uso por tenant/endpoint",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar métricas nesta review",
            "não criar endpoint Prometheus nesta review",
            "não criar dashboard Grafana nesta review",
            "não exportar segredo, hash, header ou valor claro de API key",
            "não criar billing/quotas comerciais nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Metrics Execution",
                "API Key Public Endpoint Dashboard Review",
            )
        return (
            "API Key Public Endpoint Observability Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_public_endpoint_observability_review_queries = ApiKeyPublicEndpointObservabilityReviewQueryService()
