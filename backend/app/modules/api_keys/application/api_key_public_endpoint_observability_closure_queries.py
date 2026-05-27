from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiKeyPublicEndpointObservabilityClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPublicEndpointObservabilityClosureQueryService:
    repo_root: Path = Path(__file__).resolve().parents[5]
    metrics_service_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "application" / "api_key_public_endpoint_metrics.py"
    metrics_view_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "interfaces" / "views.py"
    dashboard_path: Path = repo_root / "infra" / "observability" / "grafana" / "api-key-public-endpoints-dashboard.json"
    alert_rules_path: Path = repo_root / "infra" / "observability" / "prometheus" / "api-keys-alert-rules.yml"
    runbook_path: Path = repo_root / "infra" / "observability" / "README.md"

    def get_closure(
        self,
        *,
        rollout_ready: bool = False,
        alertmanager_routing_deferred: bool = True,
        prometheus_activation_deferred: bool = True,
    ) -> dict[str, object]:
        artifacts = self._artifacts()
        blockers = self._blockers(artifacts=artifacts, rollout_ready=rollout_ready)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-observability-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "artifacts": artifacts,
            "decisions": self._decisions(
                artifacts=artifacts,
                rollout_ready=rollout_ready,
                alertmanager_routing_deferred=alertmanager_routing_deferred,
                prometheus_activation_deferred=prometheus_activation_deferred,
            ),
            "blockers": blockers,
            "residual_risks": self._residual_risks(
                alertmanager_routing_deferred=alertmanager_routing_deferred,
                prometheus_activation_deferred=prometheus_activation_deferred,
            ),
            "next_tracks": self._next_tracks(status=status),
        }

    def _artifacts(self) -> dict[str, bool]:
        return {
            "metrics-service": self.metrics_service_path.exists(),
            "metrics-endpoint": self._file_contains(self.metrics_view_path, "ApiKeyPublicEndpointMetricsView"),
            "grafana-dashboard": self.dashboard_path.exists(),
            "prometheus-alert-rules": self.alert_rules_path.exists(),
            "observability-runbook": self._file_contains(self.runbook_path, "api-keys-alert-rules.yml"),
        }

    def _blockers(
        self,
        *,
        artifacts: dict[str, bool],
        rollout_ready: bool,
    ) -> tuple[str, ...]:
        blockers = [f"artifact-missing:{name}" for name, present in artifacts.items() if not present]
        if not rollout_ready:
            blockers.append("rollout-ready:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        artifacts: dict[str, bool],
        rollout_ready: bool,
        alertmanager_routing_deferred: bool,
        prometheus_activation_deferred: bool,
    ) -> tuple[ApiKeyPublicEndpointObservabilityClosureDecision, ...]:
        return (
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="metrics",
                status="ready" if artifacts["metrics-service"] and artifacts["metrics-endpoint"] else "blocked",
                summary="endpoint Prometheus protegido e service de métricas existem para endpoints públicos por API key",
            ),
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="dashboard",
                status="ready" if artifacts["grafana-dashboard"] else "blocked",
                summary="dashboard Grafana versionado cobre requests, auth failures, rate limit, endpoint enabled e top tenants",
            ),
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="alert-rules",
                status="ready" if artifacts["prometheus-alert-rules"] else "blocked",
                summary="alert rules versionadas cobrem auth failures, rate limit e endpoint disabled",
            ),
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="sensitive-data",
                status="guarded",
                summary="métricas, dashboard e alert rules não devem expor segredo, hash, header ou valor claro de API key",
            ),
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="activation",
                status="deferred" if prometheus_activation_deferred and alertmanager_routing_deferred else "manual-review",
                summary="ativação real de Prometheus/Grafana/Alertmanager permanece decisão de ambiente",
            ),
            ApiKeyPublicEndpointObservabilityClosureDecision(
                key="rollout",
                status="ready" if rollout_ready else "blocked",
                summary="closure só é Go quando rollout operacional aceita carregar scrape, dashboard e alertas",
            ),
        )

    def _residual_risks(
        self,
        *,
        alertmanager_routing_deferred: bool,
        prometheus_activation_deferred: bool,
    ) -> tuple[str, ...]:
        risks = [
            "baseline produtivo de thresholds ainda precisa ser calibrado após tráfego real",
            "dashboard depende de Prometheus datasource `DS_PROMETHEUS` selecionado no ambiente",
            "alertas começam como warning para reduzir ruído de rollout",
            "novos endpoints públicos precisarão aderir explicitamente às mesmas métricas e labels",
        ]
        if prometheus_activation_deferred:
            risks.append("scrape Prometheus real ainda precisa ser ativado por ambiente")
        if alertmanager_routing_deferred:
            risks.append("roteamento Alertmanager real ainda precisa ser configurado por ambiente")
        return tuple(risks)

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Production Rollout Review",
                "API Key Public Endpoint Expansion Review",
            )
        return (
            "API Key Public Endpoint Observability Activation Review",
            "API Key Governance Closure Review",
        )

    def _file_contains(self, path: Path, text: str) -> bool:
        return path.exists() and text in path.read_text(encoding="utf-8")


api_key_public_endpoint_observability_closure_queries = ApiKeyPublicEndpointObservabilityClosureQueryService()
