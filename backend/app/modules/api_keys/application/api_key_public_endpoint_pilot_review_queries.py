from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointPilotDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointPilotRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointPilotReviewQueryService:
    def get_review(
        self,
        *,
        drf_adapter_available: bool = False,
        pilot_endpoint_read_only: bool = False,
        tenant_context_required: bool = False,
        explicit_scope_required: bool = False,
        rate_limit_plan_required: bool = False,
        safe_payload_required: bool = False,
        no_pii_required: bool = False,
        no_admin_ops_reuse_required: bool = False,
        versioned_url_required: bool = False,
        rollout_flag_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "drf_adapter_available": bool(drf_adapter_available),
            "pilot_endpoint_read_only": bool(pilot_endpoint_read_only),
            "tenant_context_required": bool(tenant_context_required),
            "explicit_scope_required": bool(explicit_scope_required),
            "rate_limit_plan_required": bool(rate_limit_plan_required),
            "safe_payload_required": bool(safe_payload_required),
            "no_pii_required": bool(no_pii_required),
            "no_admin_ops_reuse_required": bool(no_admin_ops_reuse_required),
            "versioned_url_required": bool(versioned_url_required),
            "rollout_flag_required": bool(rollout_flag_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-pilot-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "recommended_pilot": self._recommended_pilot(),
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
                blockers.append(f"public-endpoint-pilot:{key}:missing")
        return tuple(blockers)

    def _recommended_pilot(self) -> dict[str, str]:
        return {
            "module": "catalog",
            "endpoint": "/api/v1/catalog/products/",
            "method": "GET",
            "scope": "read:catalog",
            "payload": "lista paginada de produtos ativos/publicados com campos seguros",
        }

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointPilotDecision, ...]:
        return (
            ApiKeyPublicEndpointPilotDecision(
                key="pilot-surface",
                status="catalog-read-only" if signals["pilot_endpoint_read_only"] else "blocked",
                summary="primeiro endpoint público deve ser leitura de catálogo, não pedidos/clientes/pagamentos",
            ),
            ApiKeyPublicEndpointPilotDecision(
                key="tenant-boundary",
                status="required" if signals["tenant_context_required"] else "blocked",
                summary="endpoint deve depender de tenant resolvido no request e nunca aceitar tenant_id arbitrário",
            ),
            ApiKeyPublicEndpointPilotDecision(
                key="scope",
                status="required" if signals["explicit_scope_required"] else "blocked",
                summary="piloto deve exigir escopo explícito `read:catalog`",
            ),
            ApiKeyPublicEndpointPilotDecision(
                key="rollout",
                status="required" if signals["rollout_flag_required"] else "blocked",
                summary="piloto deve nascer atrás de flag/config antes de produção real",
            ),
            ApiKeyPublicEndpointPilotDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro implementar o endpoint piloto",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointPilotRequirement, ...]:
        return (
            ApiKeyPublicEndpointPilotRequirement(
                key="url",
                summary="criar URL versionada `/api/v1/catalog/products/` separada de `/ops/` e storefront HTML",
            ),
            ApiKeyPublicEndpointPilotRequirement(
                key="auth",
                summary="usar `ApiKeyAuthentication` e `HasApiKeyScope` por opt-in na view",
            ),
            ApiKeyPublicEndpointPilotRequirement(
                key="scope",
                summary="declarar `required_api_key_scope = 'read:catalog'`",
            ),
            ApiKeyPublicEndpointPilotRequirement(
                key="payload",
                summary="retornar apenas dados públicos/seguros de produtos ativos: id/slug/name/status/price summary quando já público",
            ),
            ApiKeyPublicEndpointPilotRequirement(
                key="rate-limit",
                summary="preservar `rate_limit_key` e documentar throttle futuro antes de rollout amplo",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar endpoint nesta review",
            "não expor pedidos, clientes, pagamentos ou dados pessoais",
            "não reutilizar rotas `/ops/` como API pública",
            "não aceitar tenant_id via query/body",
            "não abrir escrita programática neste piloto",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Catalog Products Endpoint Execution",
                "API Key Public Endpoint Rate Limit Review",
            )
        return (
            "API Key Public Endpoint Pilot Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_public_endpoint_pilot_review_queries = ApiKeyPublicEndpointPilotReviewQueryService()
