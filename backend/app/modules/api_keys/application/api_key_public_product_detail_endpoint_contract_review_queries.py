from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicProductDetailEndpointContractDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicProductDetailEndpointContractRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicProductDetailEndpointContractReviewQueryService:
    def get_review(
        self,
        *,
        expansion_review_ready: bool = False,
        catalog_owner_confirmed: bool = False,
        slug_lookup_required: bool = False,
        tenant_scope_required: bool = False,
        active_product_only_required: bool = False,
        read_catalog_scope_required: bool = False,
        safe_payload_required: bool = False,
        public_variant_summary_required: bool = False,
        rate_limit_endpoint_required: bool = False,
        metrics_endpoint_label_required: bool = False,
        rollout_flag_required: bool = False,
        no_pii_or_stock_raw_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "expansion_review_ready": bool(expansion_review_ready),
            "catalog_owner_confirmed": bool(catalog_owner_confirmed),
            "slug_lookup_required": bool(slug_lookup_required),
            "tenant_scope_required": bool(tenant_scope_required),
            "active_product_only_required": bool(active_product_only_required),
            "read_catalog_scope_required": bool(read_catalog_scope_required),
            "safe_payload_required": bool(safe_payload_required),
            "public_variant_summary_required": bool(public_variant_summary_required),
            "rate_limit_endpoint_required": bool(rate_limit_endpoint_required),
            "metrics_endpoint_label_required": bool(metrics_endpoint_label_required),
            "rollout_flag_required": bool(rollout_flag_required),
            "no_pii_or_stock_raw_required": bool(no_pii_or_stock_raw_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-product-detail-endpoint-contract-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "endpoint_contract": self._endpoint_contract(),
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
                blockers.append(f"public-product-detail-contract:{key}:missing")
        return tuple(blockers)

    def _endpoint_contract(self) -> dict[str, str]:
        return {
            "method": "GET",
            "path": "/api/v1/catalog/products/<slug>/",
            "owner_module": "catalog",
            "scope": "read:catalog",
            "rate_limit_endpoint": "catalog.products.detail",
            "rollout_flag": "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED",
        }

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicProductDetailEndpointContractDecision, ...]:
        return (
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="ownership",
                status="catalog" if signals["catalog_owner_confirmed"] else "blocked",
                summary="execução do detalhe público pertence ao módulo catalog, usando auth/rate-limit de api_keys",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="routing",
                status="required" if signals["slug_lookup_required"] else "blocked",
                summary="endpoint deve resolver produto por slug público dentro do tenant atual",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="tenant-scope",
                status="required"
                if signals["tenant_scope_required"] and signals["active_product_only_required"]
                else "blocked",
                summary="query deve filtrar tenant, status ativo e is_active, sem fallback global",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="authorization",
                status="required" if signals["read_catalog_scope_required"] else "blocked",
                summary="endpoint exige API key válida com escopo `read:catalog`",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="payload",
                status="required"
                if signals["safe_payload_required"]
                and signals["public_variant_summary_required"]
                and signals["no_pii_or_stock_raw_required"]
                else "blocked",
                summary="payload deve ser público, com resumo seguro de variantes e sem PII/estoque bruto",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="operations",
                status="required"
                if signals["rate_limit_endpoint_required"]
                and signals["metrics_endpoint_label_required"]
                and signals["rollout_flag_required"]
                else "blocked",
                summary="rate limit, métricas e flag própria são obrigatórios desde a execução inicial",
            ),
            ApiKeyPublicProductDetailEndpointContractDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro implementar o endpoint no catalog",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicProductDetailEndpointContractRequirement, ...]:
        return (
            ApiKeyPublicProductDetailEndpointContractRequirement(
                key="query",
                summary="adicionar query em `catalog.application.public_catalog_api_queries` para buscar produto ativo por slug e tenant",
            ),
            ApiKeyPublicProductDetailEndpointContractRequirement(
                key="view",
                summary="adicionar `PublicCatalogProductDetailApiView` com `ApiKeyAuthentication`, `HasApiKeyScope` e `ApiKeyRateLimitThrottle`",
            ),
            ApiKeyPublicProductDetailEndpointContractRequirement(
                key="payload",
                summary="retornar campos públicos de PDP, imagens públicas e variantes com preço/disponibilidade segura, sem estoque bruto",
            ),
            ApiKeyPublicProductDetailEndpointContractRequirement(
                key="observability",
                summary="registrar métrica `success` com endpoint label `catalog.products.detail`",
            ),
            ApiKeyPublicProductDetailEndpointContractRequirement(
                key="settings",
                summary="criar flag e rate-limit settings específicos para detalhe público",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar endpoint nesta review",
            "não expor estoque bruto, custo, margem, tenant_id ou PII",
            "não abrir carrinho, checkout, pedidos, clientes ou pagamentos",
            "não criar escrita pública ou admin API",
            "não criar escopo diferente de `read:catalog` nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Product Detail Endpoint Execution",
                "API Key Public Endpoint Expansion Closure Review",
            )
        return (
            "API Key Public Product Detail Endpoint Contract Follow-Up",
            "API Key Public Endpoint Expansion Review",
        )


api_key_public_product_detail_endpoint_contract_review_queries = (
    ApiKeyPublicProductDetailEndpointContractReviewQueryService()
)
