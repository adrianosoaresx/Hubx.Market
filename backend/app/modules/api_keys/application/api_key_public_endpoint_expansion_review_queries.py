from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPublicEndpointExpansionDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPublicEndpointExpansionRequirement:
    key: str
    summary: str


@dataclass
class ApiKeyPublicEndpointExpansionReviewQueryService:
    def get_review(
        self,
        *,
        post_activation_monitoring_ready: bool = False,
        candidate_endpoint_identified: bool = False,
        read_only_required: bool = False,
        tenant_context_required: bool = False,
        explicit_scope_required: bool = False,
        rate_limit_required: bool = False,
        observability_required: bool = False,
        payload_contract_required: bool = False,
        no_pii_required: bool = False,
        no_cross_module_leak_required: bool = False,
        rollout_flag_required: bool = False,
        expansion_deferred_until_contract: bool = False,
    ) -> dict[str, object]:
        signals = {
            "post_activation_monitoring_ready": bool(post_activation_monitoring_ready),
            "candidate_endpoint_identified": bool(candidate_endpoint_identified),
            "read_only_required": bool(read_only_required),
            "tenant_context_required": bool(tenant_context_required),
            "explicit_scope_required": bool(explicit_scope_required),
            "rate_limit_required": bool(rate_limit_required),
            "observability_required": bool(observability_required),
            "payload_contract_required": bool(payload_contract_required),
            "no_pii_required": bool(no_pii_required),
            "no_cross_module_leak_required": bool(no_cross_module_leak_required),
            "rollout_flag_required": bool(rollout_flag_required),
            "expansion_deferred_until_contract": bool(expansion_deferred_until_contract),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-public-endpoint-expansion-review-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "recommended_candidate": self._recommended_candidate(),
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
                blockers.append(f"public-endpoint-expansion:{key}:missing")
        return tuple(blockers)

    def _recommended_candidate(self) -> dict[str, str]:
        return {
            "endpoint": "GET /api/v1/catalog/products/<slug>/",
            "owner_module": "catalog",
            "scope": "read:catalog",
            "reason": "detalhe público de produto reaproveita domínio já exposto no piloto sem abrir pedidos, clientes ou pagamentos",
        }

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPublicEndpointExpansionDecision, ...]:
        return (
            ApiKeyPublicEndpointExpansionDecision(
                key="post-activation",
                status="ready" if signals["post_activation_monitoring_ready"] else "blocked",
                summary="expansão só deve começar após monitoramento pós-ativação estável",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="candidate",
                status="recommended" if signals["candidate_endpoint_identified"] else "blocked",
                summary="primeiro candidato recomendado é detalhe público read-only de produto por slug",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="contract",
                status="required"
                if signals["read_only_required"]
                and signals["tenant_context_required"]
                and signals["explicit_scope_required"]
                and signals["payload_contract_required"]
                else "blocked",
                summary="novo endpoint exige contrato read-only, tenant-context, escopo explícito e payload seguro",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="operations",
                status="required"
                if signals["rate_limit_required"] and signals["observability_required"] and signals["rollout_flag_required"]
                else "blocked",
                summary="rate limit, métricas e flag de rollout devem nascer junto com qualquer endpoint novo",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="privacy",
                status="guarded" if signals["no_pii_required"] and signals["no_cross_module_leak_required"] else "blocked",
                summary="payload não deve expor PII, estoque bruto, tenant_id ou dados de pedidos/clientes/pagamentos",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="execution",
                status="deferred" if signals["expansion_deferred_until_contract"] else "blocked",
                summary="esta review decide o próximo recorte; execução fica para wave própria",
            ),
            ApiKeyPublicEndpointExpansionDecision(
                key="classification",
                status=status,
                summary="classificação decide se já é seguro planejar a execução do próximo endpoint público",
            ),
        )

    def _requirements(self) -> tuple[ApiKeyPublicEndpointExpansionRequirement, ...]:
        return (
            ApiKeyPublicEndpointExpansionRequirement(
                key="endpoint",
                summary="preferir `GET /api/v1/catalog/products/<slug>/` como próxima leitura pública",
            ),
            ApiKeyPublicEndpointExpansionRequirement(
                key="scope",
                summary="usar escopo explícito `read:catalog`, negando request sem tenant ou sem escopo",
            ),
            ApiKeyPublicEndpointExpansionRequirement(
                key="payload",
                summary="retornar apenas dados públicos de PDP: produto, variantes públicas, preço público e disponibilidade segura",
            ),
            ApiKeyPublicEndpointExpansionRequirement(
                key="operations",
                summary="integrar rate limit, métricas existentes e flag de rollout desde a primeira execução",
            ),
            ApiKeyPublicEndpointExpansionRequirement(
                key="boundaries",
                summary="implementação pertence a `catalog` na query/view pública, usando auth/permissions de `api_keys`",
            ),
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não implementar endpoint nesta review",
            "não abrir pedidos, clientes, pagamentos ou operações admin",
            "não expor tenant_id, estoque bruto, custo, margem ou PII",
            "não criar escopo amplo como `read:*`",
            "não criar billing/quotas comerciais nesta review",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Public Product Detail Endpoint Contract Review",
                "API Key Governance Closure Review",
            )
        return (
            "API Key Public Endpoint Expansion Follow-Up",
            "API Key Public Endpoint Post-Activation Monitoring Review",
        )


api_key_public_endpoint_expansion_review_queries = ApiKeyPublicEndpointExpansionReviewQueryService()
