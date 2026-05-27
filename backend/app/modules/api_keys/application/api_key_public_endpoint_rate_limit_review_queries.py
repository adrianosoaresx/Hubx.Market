from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointRateLimitDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointRateLimitRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointRateLimitReviewQueryService:
    def get_review(
        self,
        *,
        public_endpoint_active: bool = False,
        rate_limit_key_available: bool = False,
        per_tenant_and_key_required: bool = False,
        cache_backend_required: bool = False,
        fixed_window_acceptable: bool = False,
        default_limit_config_required: bool = False,
        endpoint_override_config_required: bool = False,
        retry_after_required: bool = False,
        audit_event_required: bool = False,
        fail_closed_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "public_endpoint_active": bool(public_endpoint_active),
            "rate_limit_key_available": bool(rate_limit_key_available),
            "per_tenant_and_key_required": bool(per_tenant_and_key_required),
            "cache_backend_required": bool(cache_backend_required),
            "fixed_window_acceptable": bool(fixed_window_acceptable),
            "default_limit_config_required": bool(default_limit_config_required),
            "endpoint_override_config_required": bool(endpoint_override_config_required),
            "retry_after_required": bool(retry_after_required),
            "audit_event_required": bool(audit_event_required),
            "fail_closed_required": bool(fail_closed_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-rate-limit-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "recommended_policy": self._recommended_policy(),
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
                blockers.append(f"public-endpoint-rate-limit:{key}:missing")
        return tuple(blockers)

    def _recommended_policy(self) -> dict[str, object]:
        return {
            "algorithm": "fixed-window",
            "scope": "tenant+api_key+endpoint",
            "default_limit": 120,
            "default_window_seconds": 60,
            "event": "api_key.rate_limited",
        }

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointRateLimitDecision, ...]:
        return (
            ApiKeyPublicEndpointRateLimitDecision(
                key="algorithm",
                status="fixed-window" if signals["fixed_window_acceptable"] else "blocked",
                summary="primeira versão deve usar fixed-window simples via cache Django",
            ),
            ApiKeyPublicEndpointRateLimitDecision(
                key="identity",
                status="tenant+key" if signals["per_tenant_and_key_required"] else "blocked",
                summary="limite deve ser por tenant e API key, usando `rate_limit_key` do adapter",
            ),
            ApiKeyPublicEndpointRateLimitDecision(
                key="response",
                status="required" if signals["retry_after_required"] else "blocked",
                summary="resposta 429 deve incluir `Retry-After` e payload estável",
            ),
            ApiKeyPublicEndpointRateLimitDecision(
                key="audit",
                status="required" if signals["audit_event_required"] else "blocked",
                summary="estouro de limite deve registrar `api_key.rate_limited` sem segredo/header/hash",
            ),
            ApiKeyPublicEndpointRateLimitDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro implementar throttle mínimo",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointRateLimitRequirement, ...]:
        return (
            ApiKeyPublicEndpointRateLimitRequirement(
                key="service",
                summary="criar service em `api_keys.application` para avaliar `rate_limit_key + endpoint` no cache",
            ),
            ApiKeyPublicEndpointRateLimitRequirement(
                key="permission-or-throttle",
                summary="integrar no DRF como throttle/permission opt-in, não em settings globais",
            ),
            ApiKeyPublicEndpointRateLimitRequirement(
                key="config",
                summary="expor limite/janela default e override do catálogo por settings/env",
            ),
            ApiKeyPublicEndpointRateLimitRequirement(
                key="response",
                summary="retornar 429 com `Retry-After` quando limite for excedido",
            ),
            ApiKeyPublicEndpointRateLimitRequirement(
                key="observability",
                summary="registrar `api_key.rate_limited` com tenant, key_id/prefix, endpoint, limit e window",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar throttle nesta review",
            "não alterar DEFAULT_THROTTLE_CLASSES nesta review",
            "não criar limite por IP como substituto do tenant+key",
            "não aplicar rate limit em endpoints HTML/storefront",
            "não criar plano pago/quotas comerciais nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Endpoint Rate Limit Execution",
                "API Key Public Endpoint Observability Review",
            )
        return (
            "API Key Public Endpoint Rate Limit Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_public_endpoint_rate_limit_review_queries = ApiKeyPublicEndpointRateLimitReviewQueryService()
