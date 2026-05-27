from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointProductionRolloutDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointProductionRolloutRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointProductionRolloutReviewQueryService:
    def get_review(
        self,
        *,
        observability_closure_ready: bool = False,
        production_token_configured: bool = False,
        prometheus_scrape_planned: bool = False,
        dashboard_import_planned: bool = False,
        alert_rules_load_planned: bool = False,
        smoke_metrics_planned: bool = False,
        rollback_plan_available: bool = False,
        evidence_capture_required: bool = False,
        owner_approval_required: bool = False,
        no_secret_exposure_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "observability_closure_ready": bool(observability_closure_ready),
            "production_token_configured": bool(production_token_configured),
            "prometheus_scrape_planned": bool(prometheus_scrape_planned),
            "dashboard_import_planned": bool(dashboard_import_planned),
            "alert_rules_load_planned": bool(alert_rules_load_planned),
            "smoke_metrics_planned": bool(smoke_metrics_planned),
            "rollback_plan_available": bool(rollback_plan_available),
            "evidence_capture_required": bool(evidence_capture_required),
            "owner_approval_required": bool(owner_approval_required),
            "no_secret_exposure_required": bool(no_secret_exposure_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-production-rollout-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "requirements": self._requirements(),
            "blockers": blockers,
            "runbook_steps": self._runbook_steps(),
            "rollback_steps": self._rollback_steps(),
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        for key, value in signals.items():
            if not value:
                blockers.append(f"public-endpoint-production-rollout:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointProductionRolloutDecision, ...]:
        return (
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="closure",
                status="ready" if signals["observability_closure_ready"] else "blocked",
                summary="rollout produtivo depende da closure de observabilidade pronta",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="token",
                status="required" if signals["production_token_configured"] else "blocked",
                summary="`API_KEYS_OBSERVABILITY_TOKEN` precisa existir no ambiente sem ser registrado em logs/evidências",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="observability",
                status="required"
                if signals["prometheus_scrape_planned"]
                and signals["dashboard_import_planned"]
                and signals["alert_rules_load_planned"]
                else "blocked",
                summary="scrape, dashboard e alert rules devem ser ativados como pacote operacional mínimo",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="evidence",
                status="required"
                if signals["smoke_metrics_planned"] and signals["evidence_capture_required"]
                else "blocked",
                summary="rollout precisa capturar evidência de scrape/smoke sem expor material sensível",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="rollback",
                status="required" if signals["rollback_plan_available"] else "blocked",
                summary="rollback deve remover scrape/alertas/dashboard ou desabilitar flag pública conforme incidente",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="approval",
                status="required" if signals["owner_approval_required"] else "blocked",
                summary="ativação produtiva exige aceite operacional explícito",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="sensitive-data",
                status="guarded" if signals["no_secret_exposure_required"] else "blocked",
                summary="evidências e logs não podem incluir segredo, hash, header ou valor claro de API key",
            ),
            ApiKeyPublicEndpointProductionRolloutDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro executar rollout produtivo limitado",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointProductionRolloutRequirement, ...]:
        return (
            ApiKeyPublicEndpointProductionRolloutRequirement(
                key="token",
                summary="configurar `API_KEYS_OBSERVABILITY_TOKEN` no ambiente e validar 403 sem token, 200 com token",
            ),
            ApiKeyPublicEndpointProductionRolloutRequirement(
                key="scrape",
                summary="carregar scrape para `/api-keys/metrics/public-endpoints/` usando token de observabilidade",
            ),
            ApiKeyPublicEndpointProductionRolloutRequirement(
                key="dashboard",
                summary="importar `infra/observability/grafana/api-key-public-endpoints-dashboard.json` com `DS_PROMETHEUS`",
            ),
            ApiKeyPublicEndpointProductionRolloutRequirement(
                key="alerts",
                summary="carregar `infra/observability/prometheus/api-keys-alert-rules.yml` como warning inicial",
            ),
            ApiKeyPublicEndpointProductionRolloutRequirement(
                key="smoke",
                summary="capturar scrape com métricas enabled/request/auth/rate limit sem segredo/hash/header",
            ),
        )

    def _runbook_steps(self) -> tuple[str, ...]:
        return (
            "definir `API_KEYS_OBSERVABILITY_TOKEN` no ambiente",
            "validar `/api-keys/metrics/public-endpoints/` sem token retornando bloqueio",
            "validar scrape com token de observabilidade retornando Prometheus text format",
            "carregar scrape no Prometheus",
            "importar dashboard Grafana com `DS_PROMETHEUS`",
            "carregar alert rules Prometheus como warning",
            "capturar evidências sem segredo/hash/header/API key em claro",
        )

    def _rollback_steps(self) -> tuple[str, ...]:
        return (
            "remover scrape job de API keys públicas do Prometheus",
            "desabilitar alert rules `HubxApiKeyPublic*`",
            "remover ou pausar dashboard Grafana importado",
            "rotacionar `API_KEYS_OBSERVABILITY_TOKEN` se houver suspeita de exposição",
            "desabilitar flag pública do endpoint se o problema estiver no tráfego externo",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não ativar produção nesta review",
            "não executar curl contra ambiente real",
            "não criar token ou segredo real",
            "não alterar Prometheus/Grafana/Alertmanager reais",
            "não criar billing/quotas comerciais",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Production Activation Evidence",
                "API Key Public Endpoint Post-Activation Monitoring Review",
            )
        return (
            "API Key Public Endpoint Production Rollout Follow-Up",
            "API Key Governance Closure Review",
        )


api_key_public_endpoint_production_rollout_review_queries = ApiKeyPublicEndpointProductionRolloutReviewQueryService()
