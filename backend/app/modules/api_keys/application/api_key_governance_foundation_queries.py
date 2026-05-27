from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyGovernanceDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyGovernanceRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyGovernanceFoundationQueryService:
    def get_review(
        self,
        *,
        public_api_surface_confirmed: bool = False,
        tenant_scoped_model_required: bool = False,
        hashed_secret_storage_required: bool = False,
        scoped_permissions_required: bool = False,
        revocation_required: bool = False,
        audit_events_required: bool = False,
        last_used_tracking_required: bool = False,
        rate_limit_required: bool = False,
    ) -> dict[str, object]:
        signals = {
            "public_api_surface_confirmed": bool(public_api_surface_confirmed),
            "tenant_scoped_model_required": bool(tenant_scoped_model_required),
            "hashed_secret_storage_required": bool(hashed_secret_storage_required),
            "scoped_permissions_required": bool(scoped_permissions_required),
            "revocation_required": bool(revocation_required),
            "audit_events_required": bool(audit_events_required),
            "last_used_tracking_required": bool(last_used_tracking_required),
            "rate_limit_required": bool(rate_limit_required),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-governance-foundation-{status}",
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
                blockers.append(f"governance:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyGovernanceDecision, ...]:
        return (
            ApiKeyGovernanceDecision(
                key="surface",
                status="ready" if signals["public_api_surface_confirmed"] else "blocked",
                summary="API keys só avançam se existir superfície programática pública/integração confirmada",
            ),
            ApiKeyGovernanceDecision(
                key="tenant-scope",
                status="required" if signals["tenant_scoped_model_required"] else "blocked",
                summary="toda chave deve pertencer a um tenant explícito",
            ),
            ApiKeyGovernanceDecision(
                key="secret-storage",
                status="required" if signals["hashed_secret_storage_required"] else "blocked",
                summary="segredo de API key deve ser armazenado apenas como hash; valor claro só aparece na criação",
            ),
            ApiKeyGovernanceDecision(
                key="permissions",
                status="required" if signals["scoped_permissions_required"] else "blocked",
                summary="chaves precisam de escopos declarativos, não acesso global implícito",
            ),
            ApiKeyGovernanceDecision(
                key="classification",
                status=status,
                summary="classificação decide se modelo mínimo pode ser implementado",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyGovernanceRequirement, ...]:
        return (
            ApiKeyGovernanceRequirement(
                key="model",
                summary="ApiKey tenant-scoped com nome, prefixo, hash, scopes, status, timestamps e owner opcional",
            ),
            ApiKeyGovernanceRequirement(
                key="creation",
                summary="command service gera segredo uma vez, persiste hash e retorna valor claro apenas no resultado inicial",
            ),
            ApiKeyGovernanceRequirement(
                key="revocation",
                summary="revogar chave por tenant_id + key_id sem deletar histórico",
            ),
            ApiKeyGovernanceRequirement(
                key="audit",
                summary="registrar api_key.created, api_key.revoked e api_key.auth_failed quando aplicável",
            ),
            ApiKeyGovernanceRequirement(
                key="runtime",
                summary="validação runtime deve exigir tenant, hash match, status ativo, escopo e rate limit",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não criar API pública nesta review",
            "não criar modelo/migration nesta review",
            "não gerar segredo real nesta review",
            "não implementar autenticação DRF nesta review",
            "não criar UI admin nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Model Minimal Contract Execution",
                "API Key Runtime Authentication Contract Review",
            )
        return (
            "API Key Public Surface Demand Review",
            "Security ROI Re-Selection Review",
        )


api_key_governance_foundation_queries = ApiKeyGovernanceFoundationQueryService()
