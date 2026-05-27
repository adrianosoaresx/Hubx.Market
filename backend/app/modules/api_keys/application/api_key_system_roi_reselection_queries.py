from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_governance_closure_queries import api_key_governance_closure_queries


@dataclass(frozen=True)
class ApiKeySystemRoiCandidate:
    key: str
    score: int
    recommended_track: str
    rationale: str


@dataclass(frozen=True)
class ApiKeySystemRoiDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeySystemRoiReselectionQueryService:
    def get_review(
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
        partner_docs_missing: bool = False,
        partner_onboarding_requested: bool = False,
        commercial_quota_pressure_confirmed: bool = False,
        new_endpoint_demand_confirmed: bool = False,
        admin_ux_gap_confirmed: bool = False,
        production_incident_pressure_confirmed: bool = False,
    ) -> dict[str, object]:
        closure = api_key_governance_closure_queries.get_closure(
            model_ready=model_ready,
            runtime_auth_ready=runtime_auth_ready,
            drf_adapter_ready=drf_adapter_ready,
            public_endpoints_ready=public_endpoints_ready,
            observability_ready=observability_ready,
            expansion_closed=expansion_closed,
            no_billing_or_quotas_required=no_billing_or_quotas_required,
            no_secret_exposure_confirmed=no_secret_exposure_confirmed,
        )
        candidates = self._candidates(
            partner_docs_missing=partner_docs_missing,
            partner_onboarding_requested=partner_onboarding_requested,
            commercial_quota_pressure_confirmed=commercial_quota_pressure_confirmed,
            new_endpoint_demand_confirmed=new_endpoint_demand_confirmed,
            admin_ux_gap_confirmed=admin_ux_gap_confirmed,
            production_incident_pressure_confirmed=production_incident_pressure_confirmed,
        )
        recommendation = max(candidates, key=lambda candidate: candidate.score)
        blockers = self._blockers(closure=closure, candidates=candidates)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-system-roi-reselection-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "governance_closure": self._closure_summary(closure=closure),
            "candidates": candidates,
            "recommendation": recommendation,
            "decisions": self._decisions(
                closure=closure,
                recommendation=recommendation,
                status=status,
                partner_docs_missing=partner_docs_missing,
            ),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status, recommendation=recommendation),
        }

    def _candidates(
        self,
        *,
        partner_docs_missing: bool,
        partner_onboarding_requested: bool,
        commercial_quota_pressure_confirmed: bool,
        new_endpoint_demand_confirmed: bool,
        admin_ux_gap_confirmed: bool,
        production_incident_pressure_confirmed: bool,
    ) -> tuple[ApiKeySystemRoiCandidate, ...]:
        return (
            ApiKeySystemRoiCandidate(
                key="partner-onboarding-docs",
                score=90 if partner_docs_missing and partner_onboarding_requested else 42,
                recommended_track="API Key Partner Onboarding Documentation Review",
                rationale="endpoints públicos já existem; documentação versionada destrava uso real com baixo risco técnico",
            ),
            ApiKeySystemRoiCandidate(
                key="commercial-quotas",
                score=78 if commercial_quota_pressure_confirmed else 35,
                recommended_track="API Key Commercial Quotas Review",
                rationale="quotas comerciais só vencem ROI quando houver pressão clara de billing, plano ou abuso comercial",
            ),
            ApiKeySystemRoiCandidate(
                key="public-endpoint-expansion",
                score=72 if new_endpoint_demand_confirmed else 30,
                recommended_track="API Key Public Endpoint Expansion Review",
                rationale="novos endpoints aumentam superfície e devem depender de demanda concreta de integração",
            ),
            ApiKeySystemRoiCandidate(
                key="admin-management-ux",
                score=65 if admin_ux_gap_confirmed else 28,
                recommended_track="API Key Admin Management UX Review",
                rationale="UX admin melhora operação, mas não bloqueia o consumo inicial via contrato já fechado",
            ),
            ApiKeySystemRoiCandidate(
                key="production-incident-hardening",
                score=82 if production_incident_pressure_confirmed else 20,
                recommended_track="API Key Production Incident Hardening Review",
                rationale="hardening operacional deve furar fila apenas quando houver pressão real de incidente ou ativação",
            ),
        )

    def _closure_summary(self, *, closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": closure["result"],
            "ready": bool(closure["ready"]),
            "module": closure["module"],
            "closed_scope_count": len(closure["closed_scope"]),
        }

    def _blockers(
        self,
        *,
        closure: dict[str, object],
        candidates: tuple[ApiKeySystemRoiCandidate, ...],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not closure["ready"]:
            blockers.append(f"governance:{closure['result']}")
            blockers.extend(f"governance:{blocker}" for blocker in closure["blockers"])
        if max(candidate.score for candidate in candidates) < 50:
            blockers.append("roi:no-system-candidate-above-threshold")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        closure: dict[str, object],
        recommendation: ApiKeySystemRoiCandidate,
        status: str,
        partner_docs_missing: bool,
    ) -> tuple[ApiKeySystemRoiDecision, ...]:
        return (
            ApiKeySystemRoiDecision(
                key="governance-closure",
                status="ready" if closure["ready"] else "blocked",
                summary="re-seleção só segue quando governança de API keys está fechada",
            ),
            ApiKeySystemRoiDecision(
                key="partner-usability-gap",
                status="confirmed" if partner_docs_missing else "unconfirmed",
                summary="o maior gap após list/detail é uso seguro por parceiros sem abrir nova superfície",
            ),
            ApiKeySystemRoiDecision(
                key="recommended-track",
                status=recommendation.key,
                summary=recommendation.rationale,
            ),
            ApiKeySystemRoiDecision(
                key="classification",
                status=status,
                summary="classificação decide o próximo ROI sistêmico depois da trilha de API keys",
            ),
        )

    def _next_tracks(
        self,
        *,
        status: str,
        recommendation: ApiKeySystemRoiCandidate,
    ) -> tuple[str, ...]:
        if status == "ready":
            return (
                recommendation.recommended_track,
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Governance Closure Review",
            "System ROI Re-Selection Review",
        )


api_key_system_roi_reselection_queries = ApiKeySystemRoiReselectionQueryService()
