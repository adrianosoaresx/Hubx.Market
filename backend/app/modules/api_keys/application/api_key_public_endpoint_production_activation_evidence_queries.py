from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointProductionActivationEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointProductionActivationEvidenceRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointProductionActivationEvidenceQueryService:
    def get_evidence(
        self,
        *,
        environment: str = "",
        rollout_review_ready: bool = False,
        token_redacted: bool = False,
        metrics_endpoint_reachable: bool = False,
        metrics_payload_valid: bool = False,
        prometheus_scrape_active: bool = False,
        dashboard_imported: bool = False,
        alert_rules_loaded: bool = False,
        endpoint_enabled_metric_present: bool = False,
        request_metric_present: bool = False,
        auth_failure_metric_present: bool = False,
        rate_limit_metric_present: bool = False,
        rollback_rehearsed: bool = False,
        evidence_reference: str = "",
    ) -> dict[str, object]:
        normalized_environment = environment.strip().lower()
        safe_reference = self._sanitize_reference(evidence_reference)
        signals = {
            "environment_production": normalized_environment == "production",
            "rollout_review_ready": bool(rollout_review_ready),
            "token_redacted": bool(token_redacted),
            "metrics_endpoint_reachable": bool(metrics_endpoint_reachable),
            "metrics_payload_valid": bool(metrics_payload_valid),
            "prometheus_scrape_active": bool(prometheus_scrape_active),
            "dashboard_imported": bool(dashboard_imported),
            "alert_rules_loaded": bool(alert_rules_loaded),
            "endpoint_enabled_metric_present": bool(endpoint_enabled_metric_present),
            "request_metric_present": bool(request_metric_present),
            "auth_failure_metric_present": bool(auth_failure_metric_present),
            "rate_limit_metric_present": bool(rate_limit_metric_present),
            "rollback_rehearsed": bool(rollback_rehearsed),
            "evidence_reference_present": bool(safe_reference),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-production-activation-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "environment": normalized_environment,
            "evidence_reference": safe_reference,
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "requirements": self._requirements(),
            "blockers": blockers,
            "captured_evidence": self._captured_evidence(signals=signals, evidence_reference=safe_reference),
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        for key, value in signals.items():
            if not value:
                blockers.append(f"public-endpoint-production-activation-evidence:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointProductionActivationEvidenceDecision, ...]:
        return (
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="environment",
                status="production" if signals["environment_production"] else "blocked",
                summary="evidência desta etapa deve representar ativação produtiva, não staging ou sandbox",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="rollout-review",
                status="ready" if signals["rollout_review_ready"] else "blocked",
                summary="activation evidence depende do Production Rollout Review pronto",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="scrape",
                status="ready"
                if signals["metrics_endpoint_reachable"]
                and signals["metrics_payload_valid"]
                and signals["prometheus_scrape_active"]
                else "blocked",
                summary="endpoint de métricas, payload Prometheus e scrape ativo precisam estar evidenciados",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="grafana-alerts",
                status="ready" if signals["dashboard_imported"] and signals["alert_rules_loaded"] else "blocked",
                summary="dashboard e alert rules precisam estar carregados no ambiente",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="metrics-coverage",
                status="ready"
                if signals["endpoint_enabled_metric_present"]
                and signals["request_metric_present"]
                and signals["auth_failure_metric_present"]
                and signals["rate_limit_metric_present"]
                else "blocked",
                summary="evidência deve conter as quatro métricas públicas sem material sensível",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="sensitive-data",
                status="guarded" if signals["token_redacted"] else "blocked",
                summary="token, header, hash e API key em claro devem permanecer redigidos",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="rollback",
                status="ready" if signals["rollback_rehearsed"] else "blocked",
                summary="rollback operacional precisa ser ensaiado ou confirmado antes de fechar ativação",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceDecision(
                key="classification",
                status=status,
                summary="classificação decide se a ativação produtiva tem evidência mínima suficiente",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointProductionActivationEvidenceRequirement, ...]:
        return (
            ApiKeyPublicEndpointProductionActivationEvidenceRequirement(
                key="scrape",
                summary="capturar evidência sanitizada de `/api-keys/metrics/public-endpoints/` com token redigido",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceRequirement(
                key="metrics",
                summary="confirmar `hubx_api_key_public_request_total`, `hubx_api_key_auth_failure_total`, `hubx_api_key_rate_limited_total` e `hubx_api_key_public_endpoint_enabled`",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceRequirement(
                key="dashboard",
                summary="registrar referência externa do dashboard importado sem credenciais",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceRequirement(
                key="alerts",
                summary="registrar referência externa das alert rules carregadas sem segredo",
            ),
            ApiKeyPublicEndpointProductionActivationEvidenceRequirement(
                key="rollback",
                summary="confirmar rollback de scrape, dashboard, alert rules e token rotation",
            ),
        )

    def _captured_evidence(
        self,
        *,
        signals: dict[str, bool],
        evidence_reference: str,
    ) -> tuple[str, ...]:
        captured: list[str] = [f"reference={evidence_reference}"] if evidence_reference else []
        for key, value in signals.items():
            captured.append(f"{key}={value}")
        return tuple(captured)

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não executar chamada real nesta command",
            "não armazenar token ou header de observabilidade",
            "não armazenar API key pública, hash ou segredo",
            "não alterar Prometheus/Grafana/Alertmanager",
            "não calibrar thresholds produtivos nesta etapa",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Post-Activation Monitoring Review",
                "API Key Public Endpoint Expansion Review",
            )
        return (
            "API Key Public Endpoint Production Activation Follow-Up",
            "API Key Public Endpoint Production Rollout Review",
        )

    def _sanitize_reference(self, value: str) -> str:
        sanitized = value.strip()
        forbidden_fragments = ("secret", "token=", "key_hash", "authorization", "x-hubx-api-key", "api_key=")
        lowered = sanitized.lower()
        if any(fragment in lowered for fragment in forbidden_fragments):
            return ""
        return sanitized


api_key_public_endpoint_production_activation_evidence_queries = (
    ApiKeyPublicEndpointProductionActivationEvidenceQueryService()
)
