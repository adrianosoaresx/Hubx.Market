from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiKeyGovernanceClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyGovernanceClosureQueryService:
    repo_root: Path = Path(__file__).resolve().parents[5]
    model_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "models.py"
    commands_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "application" / "api_key_commands.py"
    runtime_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "application" / "api_key_runtime_authentication.py"
    auth_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "interfaces" / "authentication.py"
    throttling_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "interfaces" / "throttling.py"
    metrics_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "application" / "api_key_public_endpoint_metrics.py"
    catalog_query_path: Path = repo_root / "backend" / "app" / "modules" / "catalog" / "application" / "public_catalog_api_queries.py"
    catalog_view_path: Path = repo_root / "backend" / "app" / "modules" / "catalog" / "interfaces" / "public_api_views.py"
    dashboard_path: Path = repo_root / "infra" / "observability" / "grafana" / "api-key-public-endpoints-dashboard.json"
    alert_rules_path: Path = repo_root / "infra" / "observability" / "prometheus" / "api-keys-alert-rules.yml"

    def get_closure(
        self,
        *,
        model_ready: bool = False,
        runtime_auth_ready: bool = False,
        drf_adapter_ready: bool = False,
        public_endpoints_ready: bool = False,
        observability_ready: bool = False,
        expansion_closed: bool = False,
        no_billing_or_quotas_required: bool = False,
        no_secret_exposure_confirmed: bool = False,
    ) -> dict[str, object]:
        artifacts = self._artifacts()
        blockers = self._blockers(
            artifacts=artifacts,
            model_ready=model_ready,
            runtime_auth_ready=runtime_auth_ready,
            drf_adapter_ready=drf_adapter_ready,
            public_endpoints_ready=public_endpoints_ready,
            observability_ready=observability_ready,
            expansion_closed=expansion_closed,
            no_billing_or_quotas_required=no_billing_or_quotas_required,
            no_secret_exposure_confirmed=no_secret_exposure_confirmed,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-governance-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "artifacts": artifacts,
            "decisions": self._decisions(
                artifacts=artifacts,
                model_ready=model_ready,
                runtime_auth_ready=runtime_auth_ready,
                drf_adapter_ready=drf_adapter_ready,
                public_endpoints_ready=public_endpoints_ready,
                observability_ready=observability_ready,
                expansion_closed=expansion_closed,
                no_billing_or_quotas_required=no_billing_or_quotas_required,
                no_secret_exposure_confirmed=no_secret_exposure_confirmed,
            ),
            "blockers": blockers,
            "closed_scope": self._closed_scope(),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _artifacts(self) -> dict[str, bool]:
        return {
            "api-key-model": self._file_contains(self.model_path, "class ApiKey"),
            "api-key-commands": self._file_contains(self.commands_path, "def create_key"),
            "runtime-authentication": self._file_contains(self.runtime_path, "authenticate"),
            "drf-authentication": self._file_contains(self.auth_path, "class ApiKeyAuthentication"),
            "scope-permission": self._file_contains(self.auth_path, "class HasApiKeyScope"),
            "rate-limit-throttle": self._file_contains(self.throttling_path, "class ApiKeyRateLimitThrottle"),
            "public-metrics": self._file_contains(self.metrics_path, "hubx_api_key_public_request_total"),
            "catalog-list-endpoint": self._file_contains(self.catalog_view_path, "PublicCatalogProductsApiView"),
            "catalog-detail-endpoint": self._file_contains(self.catalog_view_path, "PublicCatalogProductDetailApiView"),
            "catalog-detail-query": self._file_contains(self.catalog_query_path, "def get_product_detail"),
            "grafana-dashboard": self.dashboard_path.exists(),
            "prometheus-alert-rules": self.alert_rules_path.exists(),
        }

    def _blockers(
        self,
        *,
        artifacts: dict[str, bool],
        model_ready: bool,
        runtime_auth_ready: bool,
        drf_adapter_ready: bool,
        public_endpoints_ready: bool,
        observability_ready: bool,
        expansion_closed: bool,
        no_billing_or_quotas_required: bool,
        no_secret_exposure_confirmed: bool,
    ) -> tuple[str, ...]:
        blockers = [f"artifact-missing:{name}" for name, present in artifacts.items() if not present]
        checks = {
            "model-ready": model_ready,
            "runtime-auth-ready": runtime_auth_ready,
            "drf-adapter-ready": drf_adapter_ready,
            "public-endpoints-ready": public_endpoints_ready,
            "observability-ready": observability_ready,
            "expansion-closed": expansion_closed,
            "no-billing-or-quotas-required": no_billing_or_quotas_required,
            "no-secret-exposure-confirmed": no_secret_exposure_confirmed,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        artifacts: dict[str, bool],
        model_ready: bool,
        runtime_auth_ready: bool,
        drf_adapter_ready: bool,
        public_endpoints_ready: bool,
        observability_ready: bool,
        expansion_closed: bool,
        no_billing_or_quotas_required: bool,
        no_secret_exposure_confirmed: bool,
    ) -> tuple[ApiKeyGovernanceClosureDecision, ...]:
        return (
            ApiKeyGovernanceClosureDecision(
                key="model",
                status="ready" if artifacts["api-key-model"] and artifacts["api-key-commands"] and model_ready else "blocked",
                summary="modelo e command service cobrem criação/revogação/hash/prefix/escopos de API keys",
            ),
            ApiKeyGovernanceClosureDecision(
                key="runtime-auth",
                status="ready" if artifacts["runtime-authentication"] and runtime_auth_ready else "blocked",
                summary="runtime autentica API key por tenant, expiração, revogação e escopos sem expor segredo",
            ),
            ApiKeyGovernanceClosureDecision(
                key="drf-adapter",
                status="ready"
                if artifacts["drf-authentication"]
                and artifacts["scope-permission"]
                and artifacts["rate-limit-throttle"]
                and drf_adapter_ready
                else "blocked",
                summary="DRF adapter, permission e throttle estão disponíveis para endpoints públicos",
            ),
            ApiKeyGovernanceClosureDecision(
                key="public-endpoints",
                status="ready"
                if artifacts["catalog-list-endpoint"]
                and artifacts["catalog-detail-endpoint"]
                and artifacts["catalog-detail-query"]
                and public_endpoints_ready
                else "blocked",
                summary="listagem e detalhe de catálogo são endpoints públicos read-only tenant-scoped",
            ),
            ApiKeyGovernanceClosureDecision(
                key="observability",
                status="ready"
                if artifacts["public-metrics"]
                and artifacts["grafana-dashboard"]
                and artifacts["prometheus-alert-rules"]
                and observability_ready
                else "blocked",
                summary="métricas, dashboard e alert rules cobrem endpoints públicos por label endpoint",
            ),
            ApiKeyGovernanceClosureDecision(
                key="expansion",
                status="closed" if expansion_closed else "blocked",
                summary="expansão inicial está fechada em list/detail antes de nova seleção ROI",
            ),
            ApiKeyGovernanceClosureDecision(
                key="commercial-policy",
                status="deferred" if no_billing_or_quotas_required else "blocked",
                summary="billing e quotas comerciais continuam fora do ciclo atual",
            ),
            ApiKeyGovernanceClosureDecision(
                key="sensitive-data",
                status="guarded" if no_secret_exposure_confirmed else "blocked",
                summary="contrato não expõe segredo, hash, header de autenticação ou API key em claro",
            ),
        )

    def _closed_scope(self) -> tuple[str, ...]:
        return (
            "ApiKey model and command service",
            "runtime API key authentication",
            "DRF authentication/permission/throttle",
            "GET /api/v1/catalog/products/",
            "GET /api/v1/catalog/products/<slug>/",
            "Prometheus metrics endpoint",
            "Grafana dashboard artifact",
            "Prometheus alert rules artifact",
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "billing/quotas comerciais ainda não existem",
            "novos endpoints públicos exigem nova seleção ROI e contrato próprio",
            "thresholds de alertas precisam de calibração com tráfego real",
            "rotação operacional de API keys pode ganhar surface admin mais rica no futuro",
            "documentação de parceiros externos ainda pode exigir exemplos versionados de payload",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "System ROI Re-Selection Review",
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Governance Follow-Up",
            "API Key Public Endpoint Expansion Closure Review",
        )

    def _file_contains(self, path: Path, text: str) -> bool:
        return path.exists() and text in path.read_text(encoding="utf-8")


api_key_governance_closure_queries = ApiKeyGovernanceClosureQueryService()
