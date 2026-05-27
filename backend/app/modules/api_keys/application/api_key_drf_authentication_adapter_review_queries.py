from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyDrfAuthenticationAdapterDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyDrfAuthenticationAdapterRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyDrfAuthenticationAdapterReviewQueryService:
    def get_review(
        self,
        *,
        runtime_service_available: bool = False,
        tenant_middleware_required: bool = False,
        per_view_opt_in_required: bool = False,
        global_drf_auth_forbidden: bool = False,
        required_scope_mapping_required: bool = False,
        safe_principal_required: bool = False,
        permission_class_required: bool = False,
        rate_limit_hook_required: bool = False,
        failure_response_contract_required: bool = False,
        no_public_endpoint_in_adapter: bool = False,
    ) -> dict[str, object]:
        signals = {
            "runtime_service_available": bool(runtime_service_available),
            "tenant_middleware_required": bool(tenant_middleware_required),
            "per_view_opt_in_required": bool(per_view_opt_in_required),
            "global_drf_auth_forbidden": bool(global_drf_auth_forbidden),
            "required_scope_mapping_required": bool(required_scope_mapping_required),
            "safe_principal_required": bool(safe_principal_required),
            "permission_class_required": bool(permission_class_required),
            "rate_limit_hook_required": bool(rate_limit_hook_required),
            "failure_response_contract_required": bool(failure_response_contract_required),
            "no_public_endpoint_in_adapter": bool(no_public_endpoint_in_adapter),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-drf-authentication-adapter-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
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
                blockers.append(f"drf-adapter:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyDrfAuthenticationAdapterDecision, ...]:
        return (
            ApiKeyDrfAuthenticationAdapterDecision(
                key="activation",
                status="required" if signals["per_view_opt_in_required"] else "blocked",
                summary="adapter DRF de API key deve ser ativado apenas por view/API surface explícita",
            ),
            ApiKeyDrfAuthenticationAdapterDecision(
                key="global-settings",
                status="forbidden" if signals["global_drf_auth_forbidden"] else "blocked",
                summary="não adicionar API key em DEFAULT_AUTHENTICATION_CLASSES neste estágio",
            ),
            ApiKeyDrfAuthenticationAdapterDecision(
                key="tenant-context",
                status="required" if signals["tenant_middleware_required"] else "blocked",
                summary="adapter depende de request.tenant já resolvido pelo middleware",
            ),
            ApiKeyDrfAuthenticationAdapterDecision(
                key="scope-boundary",
                status="required" if signals["required_scope_mapping_required"] else "blocked",
                summary="cada view precisa declarar escopo mínimo antes de autenticar por API key",
            ),
            ApiKeyDrfAuthenticationAdapterDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro implementar adapter DRF",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyDrfAuthenticationAdapterRequirement, ...]:
        return (
            ApiKeyDrfAuthenticationAdapterRequirement(
                key="adapter",
                summary="criar authentication class fina em api_keys.interfaces que delega para api_key_runtime_authentication",
            ),
            ApiKeyDrfAuthenticationAdapterRequirement(
                key="principal",
                summary="retornar principal seguro sem segredo/hash/header e com tenant_id, api_key_id, prefix e scopes",
            ),
            ApiKeyDrfAuthenticationAdapterRequirement(
                key="scope",
                summary="ler escopo requerido de atributo explícito da view ou permission dedicada",
            ),
            ApiKeyDrfAuthenticationAdapterRequirement(
                key="failure",
                summary="converter falhas para respostas DRF estáveis sem vazar motivo sensível demais ao cliente",
            ),
            ApiKeyDrfAuthenticationAdapterRequirement(
                key="rate-limit",
                summary="preservar rate_limit_key para throttle/rate limiter futuro, sem implementar limite real no adapter",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não alterar DEFAULT_AUTHENTICATION_CLASSES nesta review",
            "não criar endpoint público nesta review",
            "não implementar authentication class nesta review",
            "não criar permission class nesta review",
            "não criar throttle/rate limiter real nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key DRF Authentication Adapter Execution",
                "API Key Public Endpoint Pilot Review",
            )
        return (
            "API Key DRF Authentication Adapter Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_drf_authentication_adapter_review_queries = ApiKeyDrfAuthenticationAdapterReviewQueryService()
