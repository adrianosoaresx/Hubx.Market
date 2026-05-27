from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointAlertRuleDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointAlertRuleRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointAlertRulesReviewQueryService:
    def get_review(
        self,
        *,
        metrics_endpoint_available: bool = False,
        dashboard_available: bool = False,
        auth_failure_alert_required: bool = False,
        rate_limit_alert_required: bool = False,
        endpoint_disabled_alert_required: bool = False,
        tenant_endpoint_labels_required: bool = False,
        low_cardinality_required: bool = False,
        runbook_annotations_required: bool = False,
        no_sensitive_labels_required: bool = False,
        warning_first_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "metrics_endpoint_available": bool(metrics_endpoint_available),
            "dashboard_available": bool(dashboard_available),
            "auth_failure_alert_required": bool(auth_failure_alert_required),
            "rate_limit_alert_required": bool(rate_limit_alert_required),
            "endpoint_disabled_alert_required": bool(endpoint_disabled_alert_required),
            "tenant_endpoint_labels_required": bool(tenant_endpoint_labels_required),
            "low_cardinality_required": bool(low_cardinality_required),
            "runbook_annotations_required": bool(runbook_annotations_required),
            "no_sensitive_labels_required": bool(no_sensitive_labels_required),
            "warning_first_required": bool(warning_first_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-alert-rules-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "rules": self._rules(),
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
                blockers.append(f"public-endpoint-alert-rules:{key}:missing")
        return tuple(blockers)

    def _rules(self) -> tuple[str, ...]:
        return (
            "HubxApiKeyPublicAuthFailuresHigh",
            "HubxApiKeyPublicRateLimitedHigh",
            "HubxApiKeyPublicEndpointDisabled",
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointAlertRuleDecision, ...]:
        return (
            ApiKeyPublicEndpointAlertRuleDecision(
                key="prerequisites",
                status="required" if signals["metrics_endpoint_available"] and signals["dashboard_available"] else "blocked",
                summary="alert rules devem vir depois de métricas e dashboard mínimos já versionados",
            ),
            ApiKeyPublicEndpointAlertRuleDecision(
                key="coverage",
                status="required"
                if signals["auth_failure_alert_required"]
                and signals["rate_limit_alert_required"]
                and signals["endpoint_disabled_alert_required"]
                else "blocked",
                summary="alertas mínimos cobrem auth failure, rate limit e endpoint público desabilitado",
            ),
            ApiKeyPublicEndpointAlertRuleDecision(
                key="labels",
                status="required"
                if signals["tenant_endpoint_labels_required"]
                and signals["low_cardinality_required"]
                and signals["no_sensitive_labels_required"]
                else "blocked",
                summary="labels devem apontar tenant/endpoint sem segredo, hash, header ou valor claro de API key",
            ),
            ApiKeyPublicEndpointAlertRuleDecision(
                key="severity",
                status="warning-first" if signals["warning_first_required"] else "blocked",
                summary="primeiro pacote deve preferir severity warning antes de critical para reduzir ruído de rollout",
            ),
            ApiKeyPublicEndpointAlertRuleDecision(
                key="runbook",
                status="required" if signals["runbook_annotations_required"] else "blocked",
                summary="annotations devem orientar triagem por dashboard, scrape e audit events sem expor material sensível",
            ),
            ApiKeyPublicEndpointAlertRuleDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro materializar YAML Prometheus",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointAlertRuleRequirement, ...]:
        return (
            ApiKeyPublicEndpointAlertRuleRequirement(
                key="auth-failures",
                summary="alertar aumento de `hubx_api_key_auth_failure_total` por `tenant_id`, `endpoint` e `reason`",
            ),
            ApiKeyPublicEndpointAlertRuleRequirement(
                key="rate-limit",
                summary="alertar aumento de `hubx_api_key_rate_limited_total` por `tenant_id`, `endpoint` e `prefix`",
            ),
            ApiKeyPublicEndpointAlertRuleRequirement(
                key="endpoint-disabled",
                summary="alertar `hubx_api_key_public_endpoint_enabled == 0` por endpoint público esperado",
            ),
            ApiKeyPublicEndpointAlertRuleRequirement(
                key="annotations",
                summary="incluir summary/description com ação de triagem, dashboard e token de observabilidade",
            ),
            ApiKeyPublicEndpointAlertRuleRequirement(
                key="artifact",
                summary="materializar em `infra/observability/prometheus/api-keys-alert-rules.yml` na próxima execução",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não criar YAML de alert rules nesta review",
            "não configurar Alertmanager nesta review",
            "não provisionar Prometheus real nesta review",
            "não criar métricas novas nesta review",
            "não criar alertas por API key completa ou hash",
            "não criar billing/quotas comerciais nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Alert Rules Execution",
                "API Key Public Endpoint Observability Closure Review",
            )
        return (
            "API Key Public Endpoint Alert Rules Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_public_endpoint_alert_rules_review_queries = ApiKeyPublicEndpointAlertRulesReviewQueryService()
