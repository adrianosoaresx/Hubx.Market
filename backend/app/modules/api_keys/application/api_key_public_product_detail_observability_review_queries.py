from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicProductDetailObservabilityDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicProductDetailObservabilityRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicProductDetailObservabilityReviewQueryService:
    def get_review(
        self,
        *,
        detail_endpoint_executed: bool = False,
        metrics_endpoint_label_present: bool = False,
        enabled_gauge_present: bool = False,
        dashboard_endpoint_filter_covers_detail: bool = False,
        alert_rules_endpoint_label_covers_detail: bool = False,
        rate_limit_metrics_reused: bool = False,
        auth_failure_metrics_reused: bool = False,
        no_new_dashboard_required: bool = False,
        no_new_alert_rules_required: bool = False,
        no_sensitive_labels_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "detail_endpoint_executed": bool(detail_endpoint_executed),
            "metrics_endpoint_label_present": bool(metrics_endpoint_label_present),
            "enabled_gauge_present": bool(enabled_gauge_present),
            "dashboard_endpoint_filter_covers_detail": bool(dashboard_endpoint_filter_covers_detail),
            "alert_rules_endpoint_label_covers_detail": bool(alert_rules_endpoint_label_covers_detail),
            "rate_limit_metrics_reused": bool(rate_limit_metrics_reused),
            "auth_failure_metrics_reused": bool(auth_failure_metrics_reused),
            "no_new_dashboard_required": bool(no_new_dashboard_required),
            "no_new_alert_rules_required": bool(no_new_alert_rules_required),
            "no_sensitive_labels_required": bool(no_sensitive_labels_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-product-detail-observability-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "endpoint": "catalog.products.detail",
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
                blockers.append(f"public-product-detail-observability:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicProductDetailObservabilityDecision, ...]:
        return (
            ApiKeyPublicProductDetailObservabilityDecision(
                key="metrics",
                status="covered"
                if signals["metrics_endpoint_label_present"] and signals["enabled_gauge_present"]
                else "blocked",
                summary="detalhe usa endpoint label `catalog.products.detail` e gauge enabled dedicado",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="dashboard",
                status="covered" if signals["dashboard_endpoint_filter_covers_detail"] else "blocked",
                summary="dashboard existente filtra por endpoint e cobre list/detail sem JSON novo",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="alerts",
                status="covered" if signals["alert_rules_endpoint_label_covers_detail"] else "blocked",
                summary="alert rules existentes agregam por endpoint e cobrem detail sem YAML novo",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="auth-rate-limit",
                status="covered"
                if signals["rate_limit_metrics_reused"] and signals["auth_failure_metrics_reused"]
                else "blocked",
                summary="auth failure e rate limit reutilizam métricas públicas existentes",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="artifacts",
                status="no-new-artifact"
                if signals["no_new_dashboard_required"] and signals["no_new_alert_rules_required"]
                else "blocked",
                summary="não há necessidade de dashboard ou alert rules dedicados nesta fase",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="sensitive-data",
                status="guarded" if signals["no_sensitive_labels_required"] else "blocked",
                summary="labels continuam limitadas a tenant, endpoint, result/reason/prefix sem slug, token, hash ou header",
            ),
            ApiKeyPublicProductDetailObservabilityDecision(
                key="classification",
                status=status,
                summary="classificação decide se observabilidade do detalhe está suficiente para fechar a expansão inicial",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicProductDetailObservabilityRequirement, ...]:
        return (
            ApiKeyPublicProductDetailObservabilityRequirement(
                key="success",
                summary="sucesso do detalhe deve registrar `hubx_api_key_public_request_total` com endpoint `catalog.products.detail`",
            ),
            ApiKeyPublicProductDetailObservabilityRequirement(
                key="enabled",
                summary="gauge `hubx_api_key_public_endpoint_enabled` deve expor `catalog.products.detail`",
            ),
            ApiKeyPublicProductDetailObservabilityRequirement(
                key="dashboard",
                summary="dashboard `Hubx API Key Public Endpoints` deve permitir filtro por endpoint para list/detail",
            ),
            ApiKeyPublicProductDetailObservabilityRequirement(
                key="alerts",
                summary="alertas `HubxApiKeyPublic*` devem continuar usando label endpoint para cobrir detalhe",
            ),
            ApiKeyPublicProductDetailObservabilityRequirement(
                key="privacy",
                summary="não adicionar slug, SKU, token, hash, header ou API key em labels de métrica",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não criar dashboard Grafana novo nesta review",
            "não criar alert rules Prometheus novas nesta review",
            "não adicionar labels por slug ou SKU",
            "não alterar thresholds",
            "não expandir para novos endpoints nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Expansion Closure Review",
                "API Key Governance Closure Review",
            )
        return (
            "API Key Public Product Detail Observability Follow-Up",
            "API Key Public Product Detail Endpoint Execution",
        )


api_key_public_product_detail_observability_review_queries = (
    ApiKeyPublicProductDetailObservabilityReviewQueryService()
)
