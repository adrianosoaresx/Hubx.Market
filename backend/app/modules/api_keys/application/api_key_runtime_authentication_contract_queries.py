from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyRuntimeAuthenticationDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyRuntimeAuthenticationRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyRuntimeAuthenticationContractQueryService:
    def get_review(
        self,
        *,
        api_key_model_available: bool = False,
        bearer_header_required: bool = False,
        tenant_context_required: bool = False,
        prefix_lookup_required: bool = False,
        hash_verification_required: bool = False,
        active_status_required: bool = False,
        scope_enforcement_required: bool = False,
        last_used_tracking_required: bool = False,
        auth_failure_audit_required: bool = False,
        rate_limit_boundary_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "api_key_model_available": bool(api_key_model_available),
            "bearer_header_required": bool(bearer_header_required),
            "tenant_context_required": bool(tenant_context_required),
            "prefix_lookup_required": bool(prefix_lookup_required),
            "hash_verification_required": bool(hash_verification_required),
            "active_status_required": bool(active_status_required),
            "scope_enforcement_required": bool(scope_enforcement_required),
            "last_used_tracking_required": bool(last_used_tracking_required),
            "auth_failure_audit_required": bool(auth_failure_audit_required),
            "rate_limit_boundary_required": bool(rate_limit_boundary_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-runtime-authentication-contract-{status}",
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
                blockers.append(f"runtime-auth:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyRuntimeAuthenticationDecision, ...]:
        return (
            ApiKeyRuntimeAuthenticationDecision(
                key="credential-shape",
                status="required" if signals["bearer_header_required"] else "blocked",
                summary="API key runtime deve aceitar credencial apenas via Authorization Bearer",
            ),
            ApiKeyRuntimeAuthenticationDecision(
                key="tenant-boundary",
                status="required" if signals["tenant_context_required"] else "blocked",
                summary="tenant resolvido no request deve bater com a chave; chave não escolhe tenant",
            ),
            ApiKeyRuntimeAuthenticationDecision(
                key="secret-verification",
                status="required" if signals["hash_verification_required"] else "blocked",
                summary="prefixo localiza candidata, mas acesso só passa com hash válido do segredo completo",
            ),
            ApiKeyRuntimeAuthenticationDecision(
                key="permissions",
                status="required" if signals["scope_enforcement_required"] else "blocked",
                summary="escopos declarativos devem autorizar ações específicas, sem acesso global implícito",
            ),
            ApiKeyRuntimeAuthenticationDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro criar skeleton runtime de autenticação",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyRuntimeAuthenticationRequirement, ...]:
        return (
            ApiKeyRuntimeAuthenticationRequirement(
                key="request-input",
                summary="ler credencial somente do header Authorization Bearer e nunca de query string",
            ),
            ApiKeyRuntimeAuthenticationRequirement(
                key="lookup",
                summary="extrair prefixo, buscar ApiKey por prefixo e tenant_id, exigir status active",
            ),
            ApiKeyRuntimeAuthenticationRequirement(
                key="verification",
                summary="validar segredo completo com check_password contra key_hash",
            ),
            ApiKeyRuntimeAuthenticationRequirement(
                key="scope",
                summary="mapear endpoint ou caso de uso para escopo mínimo requerido",
            ),
            ApiKeyRuntimeAuthenticationRequirement(
                key="observability",
                summary="atualizar last_used_at em sucesso e registrar api_key.auth_failed em falhas relevantes",
            ),
            ApiKeyRuntimeAuthenticationRequirement(
                key="rate-limit",
                summary="definir boundary de rate limit por tenant e prefixo antes de abrir endpoint público",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar autenticação DRF nesta review",
            "não criar endpoint público nesta review",
            "não alterar modelo ApiKey nesta review",
            "não criar rate limiter real nesta review",
            "não expor segredo, hash ou material sensível em logs",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Runtime Authentication Skeleton Execution",
                "API Key Public API Surface Contract Review",
            )
        return (
            "API Key Runtime Authentication Contract Follow-Up",
            "Security ROI Re-Selection Review",
        )


api_key_runtime_authentication_contract_queries = ApiKeyRuntimeAuthenticationContractQueryService()
