from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiKeyPublicEndpointExpansionClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPublicEndpointExpansionClosureQueryService:
    repo_root: Path = Path(__file__).resolve().parents[5]
    catalog_query_path: Path = repo_root / "backend" / "app" / "modules" / "catalog" / "application" / "public_catalog_api_queries.py"
    catalog_view_path: Path = repo_root / "backend" / "app" / "modules" / "catalog" / "interfaces" / "public_api_views.py"
    catalog_urls_path: Path = repo_root / "backend" / "app" / "modules" / "catalog" / "interfaces" / "public_api_urls.py"
    metrics_path: Path = repo_root / "backend" / "app" / "modules" / "api_keys" / "application" / "api_key_public_endpoint_metrics.py"
    dashboard_path: Path = repo_root / "infra" / "observability" / "grafana" / "api-key-public-endpoints-dashboard.json"
    alert_rules_path: Path = repo_root / "infra" / "observability" / "prometheus" / "api-keys-alert-rules.yml"

    def get_closure(
        self,
        *,
        list_endpoint_ready: bool = False,
        detail_endpoint_ready: bool = False,
        observability_ready: bool = False,
        no_additional_endpoint_selected: bool = False,
    ) -> dict[str, object]:
        artifacts = self._artifacts()
        blockers = self._blockers(
            artifacts=artifacts,
            list_endpoint_ready=list_endpoint_ready,
            detail_endpoint_ready=detail_endpoint_ready,
            observability_ready=observability_ready,
            no_additional_endpoint_selected=no_additional_endpoint_selected,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-expansion-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "artifacts": artifacts,
            "decisions": self._decisions(
                artifacts=artifacts,
                list_endpoint_ready=list_endpoint_ready,
                detail_endpoint_ready=detail_endpoint_ready,
                observability_ready=observability_ready,
                no_additional_endpoint_selected=no_additional_endpoint_selected,
            ),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "closed_scope": self._closed_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _artifacts(self) -> dict[str, bool]:
        return {
            "catalog-list-query": self._file_contains(self.catalog_query_path, "def list_products"),
            "catalog-detail-query": self._file_contains(self.catalog_query_path, "def get_product_detail"),
            "catalog-detail-view": self._file_contains(self.catalog_view_path, "PublicCatalogProductDetailApiView"),
            "catalog-detail-url": self._file_contains(self.catalog_urls_path, "products/<slug:slug>/"),
            "detail-enabled-gauge": self._file_contains(self.metrics_path, "catalog.products.detail"),
            "grafana-dashboard": self.dashboard_path.exists(),
            "prometheus-alert-rules": self.alert_rules_path.exists(),
        }

    def _blockers(
        self,
        *,
        artifacts: dict[str, bool],
        list_endpoint_ready: bool,
        detail_endpoint_ready: bool,
        observability_ready: bool,
        no_additional_endpoint_selected: bool,
    ) -> tuple[str, ...]:
        blockers = [f"artifact-missing:{name}" for name, present in artifacts.items() if not present]
        if not list_endpoint_ready:
            blockers.append("list-endpoint-ready:missing")
        if not detail_endpoint_ready:
            blockers.append("detail-endpoint-ready:missing")
        if not observability_ready:
            blockers.append("observability-ready:missing")
        if not no_additional_endpoint_selected:
            blockers.append("no-additional-endpoint-selected:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        artifacts: dict[str, bool],
        list_endpoint_ready: bool,
        detail_endpoint_ready: bool,
        observability_ready: bool,
        no_additional_endpoint_selected: bool,
    ) -> tuple[ApiKeyPublicEndpointExpansionClosureDecision, ...]:
        return (
            ApiKeyPublicEndpointExpansionClosureDecision(
                key="list-endpoint",
                status="ready" if artifacts["catalog-list-query"] and list_endpoint_ready else "blocked",
                summary="endpoint público de listagem permanece o piloto read-only tenant-scoped",
            ),
            ApiKeyPublicEndpointExpansionClosureDecision(
                key="detail-endpoint",
                status="ready"
                if artifacts["catalog-detail-query"]
                and artifacts["catalog-detail-view"]
                and artifacts["catalog-detail-url"]
                and detail_endpoint_ready
                else "blocked",
                summary="endpoint público de detalhe por slug está implementado em catalog com scope read:catalog",
            ),
            ApiKeyPublicEndpointExpansionClosureDecision(
                key="observability",
                status="ready"
                if artifacts["detail-enabled-gauge"]
                and artifacts["grafana-dashboard"]
                and artifacts["prometheus-alert-rules"]
                and observability_ready
                else "blocked",
                summary="métricas, dashboard e alert rules cobrem list/detail por label endpoint",
            ),
            ApiKeyPublicEndpointExpansionClosureDecision(
                key="privacy",
                status="guarded",
                summary="escopo fechado não expõe PII, tenant_id, estoque bruto, token, hash ou header",
            ),
            ApiKeyPublicEndpointExpansionClosureDecision(
                key="expansion",
                status="closed" if no_additional_endpoint_selected else "blocked",
                summary="nenhum novo endpoint público deve ser aberto antes de nova seleção ROI",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "thresholds de alertas ainda dependem de tráfego real para calibração fina",
            "novos endpoints precisarão repetir explicitamente tenant-scope, scope, rate limit e métricas",
            "payload público de detalhe deve ser monitorado em futuras mudanças de Product/ProductVariant",
            "billing/quotas comerciais continuam fora da trilha atual de API keys públicas",
        )

    def _closed_scope(self) -> tuple[str, ...]:
        return (
            "GET /api/v1/catalog/products/",
            "GET /api/v1/catalog/products/<slug>/",
            "scope read:catalog",
            "endpoint labels catalog.products.list e catalog.products.detail",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Governance Closure Review",
                "System ROI Re-Selection Review",
            )
        return (
            "API Key Public Endpoint Expansion Follow-Up",
            "API Key Public Product Detail Endpoint Observability Review",
        )

    def _file_contains(self, path: Path, text: str) -> bool:
        return path.exists() and text in path.read_text(encoding="utf-8")


api_key_public_endpoint_expansion_closure_queries = ApiKeyPublicEndpointExpansionClosureQueryService()
