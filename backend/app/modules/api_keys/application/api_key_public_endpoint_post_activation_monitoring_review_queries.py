from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointPostActivationMonitoringDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointPostActivationMonitoringRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointPostActivationMonitoringReviewQueryService:
    def get_review(
        self,
        *,
        activation_evidence_ready: bool = False,
        monitoring_window_observed: bool = False,
        dashboard_reviewed: bool = False,
        auth_failure_rate_acceptable: bool = False,
        rate_limit_rate_acceptable: bool = False,
        endpoint_enabled_stable: bool = False,
        alert_noise_acceptable: bool = False,
        threshold_tuning_needed_logged: bool = False,
        rollback_not_required: bool = False,
        expansion_decision_deferred: bool = False,
        no_sensitive_data_observed: bool = False,
    ) -> dict[str, object]:
        signals = {
            "activation_evidence_ready": bool(activation_evidence_ready),
            "monitoring_window_observed": bool(monitoring_window_observed),
            "dashboard_reviewed": bool(dashboard_reviewed),
            "auth_failure_rate_acceptable": bool(auth_failure_rate_acceptable),
            "rate_limit_rate_acceptable": bool(rate_limit_rate_acceptable),
            "endpoint_enabled_stable": bool(endpoint_enabled_stable),
            "alert_noise_acceptable": bool(alert_noise_acceptable),
            "threshold_tuning_needed_logged": bool(threshold_tuning_needed_logged),
            "rollback_not_required": bool(rollback_not_required),
            "expansion_decision_deferred": bool(expansion_decision_deferred),
            "no_sensitive_data_observed": bool(no_sensitive_data_observed),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-post-activation-monitoring-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "requirements": self._requirements(),
            "blockers": blockers,
            "monitoring_checks": self._monitoring_checks(),
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        for key, value in signals.items():
            if not value:
                blockers.append(f"public-endpoint-post-activation-monitoring:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointPostActivationMonitoringDecision, ...]:
        return (
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="activation",
                status="ready" if signals["activation_evidence_ready"] else "blocked",
                summary="monitoramento pós-ativação depende de evidência produtiva pronta",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="window",
                status="observed" if signals["monitoring_window_observed"] and signals["dashboard_reviewed"] else "blocked",
                summary="janela inicial deve ser observada no dashboard antes de expandir endpoints",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="traffic-health",
                status="acceptable"
                if signals["auth_failure_rate_acceptable"]
                and signals["rate_limit_rate_acceptable"]
                and signals["endpoint_enabled_stable"]
                else "blocked",
                summary="auth failures, rate limit e endpoint enabled precisam ficar dentro do esperado",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="alerts",
                status="acceptable"
                if signals["alert_noise_acceptable"] and signals["threshold_tuning_needed_logged"]
                else "blocked",
                summary="ruído de alertas deve ser aceitável e ajustes de threshold precisam ficar registrados",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="rollback",
                status="not-required" if signals["rollback_not_required"] else "blocked",
                summary="não deve haver sinal operacional exigindo rollback imediato",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="expansion",
                status="deferred" if signals["expansion_decision_deferred"] else "blocked",
                summary="expansão de novos endpoints públicos deve ser decisão separada após estabilização",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="sensitive-data",
                status="guarded" if signals["no_sensitive_data_observed"] else "blocked",
                summary="monitoramento não deve mostrar token, header, hash ou API key em claro",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringDecision(
                key="classification",
                status=status,
                summary="classificação decide se pós-ativação está estável para encerrar ou seguir expansão",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointPostActivationMonitoringRequirement, ...]:
        return (
            ApiKeyPublicEndpointPostActivationMonitoringRequirement(
                key="window",
                summary="observar janela inicial de 24h ou janela operacional equivalente definida pelo time",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringRequirement(
                key="dashboard",
                summary="revisar dashboard `Hubx API Key Public Endpoints` para request, auth failure, rate limit e endpoint enabled",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringRequirement(
                key="alerts",
                summary="avaliar alertas `HubxApiKeyPublic*` como warning e registrar necessidade de tuning",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringRequirement(
                key="rollback",
                summary="confirmar que não há evidência exigindo remover scrape/alerts/dashboard ou desabilitar endpoint público",
            ),
            ApiKeyPublicEndpointPostActivationMonitoringRequirement(
                key="security",
                summary="confirmar ausência de token, header, hash ou API key em claro nas superfícies de observabilidade",
            ),
        )

    def _monitoring_checks(self) -> tuple[str, ...]:
        return (
            "validar `hubx_api_key_public_endpoint_enabled` estável por endpoint",
            "comparar auth failures por tenant/endpoint/reason contra baseline inicial",
            "comparar rate limit por tenant/endpoint/prefix contra expectativa de rollout",
            "verificar se alertas warning geraram ruído acionável ou falso positivo",
            "registrar qualquer necessidade de tuning antes de habilitar novos endpoints públicos",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não alterar thresholds nesta review",
            "não expandir endpoints públicos nesta review",
            "não alterar token ou scrape real nesta review",
            "não alterar billing/quotas comerciais",
            "não armazenar evidência com segredo, hash, header ou API key em claro",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Expansion Review",
                "API Key Governance Closure Review",
            )
        return (
            "API Key Public Endpoint Post-Activation Follow-Up",
            "API Key Public Endpoint Production Rollback Review",
        )


api_key_public_endpoint_post_activation_monitoring_review_queries = (
    ApiKeyPublicEndpointPostActivationMonitoringReviewQueryService()
)
