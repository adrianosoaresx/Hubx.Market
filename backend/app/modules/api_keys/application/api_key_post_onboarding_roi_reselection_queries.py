from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_partner_onboarding_closure_queries import (
    api_key_partner_onboarding_closure_queries,
)


@dataclass(frozen=True)
class ApiKeyPostOnboardingRoiCandidate:
    key: str
    score: int
    recommended_track: str
    rationale: str


@dataclass(frozen=True)
class ApiKeyPostOnboardingRoiDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPostOnboardingRoiReselectionQueryService:
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
        partner_docs_versioned: bool = False,
        endpoint_examples_documented: bool = False,
        activation_checklist_ready: bool = False,
        error_contract_documented: bool = False,
        safe_examples_confirmed: bool = False,
        no_new_endpoint_required: bool = False,
        no_quota_or_billing_required: bool = False,
        delivery_channel_documented: bool = False,
        support_handoff_documented: bool = False,
        smoke_evidence_template_ready: bool = False,
        change_control_documented: bool = False,
        owner_approved: bool = False,
        no_runtime_change_required: bool = False,
        no_commercial_terms_included: bool = False,
        no_sensitive_material_included: bool = False,
        published_version: str = "",
        approved_channel: str = "",
        target_audience: str = "",
        tenant_reference: str = "",
        published_at: str = "",
        evidence_reference: str = "",
        publication_confirmed: bool = False,
        support_notified: bool = False,
        activation_status_recorded: bool = False,
        smoke_template_attached: bool = False,
        redaction_confirmed: bool = False,
        no_credential_shared: bool = False,
        no_runtime_activation_performed: bool = False,
        onboarding_scope_closed: bool = False,
        residual_risks_accepted: bool = False,
        next_roi_decision_recorded: bool = False,
        partner_activation_deferred: bool = False,
        commercial_quotas_deferred: bool = False,
        new_endpoint_expansion_deferred: bool = False,
        partner_activation_requested: bool = False,
        partner_api_key_ready: bool = False,
        commercial_quota_pressure_confirmed: bool = False,
        new_endpoint_demand_confirmed: bool = False,
        admin_support_load_confirmed: bool = False,
        api_key_track_pause_preferred: bool = False,
    ) -> dict[str, object]:
        closure = api_key_partner_onboarding_closure_queries.get_closure(
            model_ready=model_ready,
            runtime_auth_ready=runtime_auth_ready,
            drf_adapter_ready=drf_adapter_ready,
            public_endpoints_ready=public_endpoints_ready,
            observability_ready=observability_ready,
            expansion_closed=expansion_closed,
            no_billing_or_quotas_required=no_billing_or_quotas_required,
            no_secret_exposure_confirmed=no_secret_exposure_confirmed,
            partner_docs_versioned=partner_docs_versioned,
            endpoint_examples_documented=endpoint_examples_documented,
            activation_checklist_ready=activation_checklist_ready,
            error_contract_documented=error_contract_documented,
            safe_examples_confirmed=safe_examples_confirmed,
            no_new_endpoint_required=no_new_endpoint_required,
            no_quota_or_billing_required=no_quota_or_billing_required,
            delivery_channel_documented=delivery_channel_documented,
            support_handoff_documented=support_handoff_documented,
            smoke_evidence_template_ready=smoke_evidence_template_ready,
            change_control_documented=change_control_documented,
            owner_approved=owner_approved,
            no_runtime_change_required=no_runtime_change_required,
            no_commercial_terms_included=no_commercial_terms_included,
            no_sensitive_material_included=no_sensitive_material_included,
            published_version=published_version,
            approved_channel=approved_channel,
            target_audience=target_audience,
            tenant_reference=tenant_reference,
            published_at=published_at,
            evidence_reference=evidence_reference,
            publication_confirmed=publication_confirmed,
            support_notified=support_notified,
            activation_status_recorded=activation_status_recorded,
            smoke_template_attached=smoke_template_attached,
            redaction_confirmed=redaction_confirmed,
            no_credential_shared=no_credential_shared,
            no_runtime_activation_performed=no_runtime_activation_performed,
            onboarding_scope_closed=onboarding_scope_closed,
            residual_risks_accepted=residual_risks_accepted,
            next_roi_decision_recorded=next_roi_decision_recorded,
            partner_activation_deferred=partner_activation_deferred,
            commercial_quotas_deferred=commercial_quotas_deferred,
            new_endpoint_expansion_deferred=new_endpoint_expansion_deferred,
        )
        candidates = self._candidates(
            partner_activation_requested=partner_activation_requested,
            partner_api_key_ready=partner_api_key_ready,
            commercial_quota_pressure_confirmed=commercial_quota_pressure_confirmed,
            new_endpoint_demand_confirmed=new_endpoint_demand_confirmed,
            admin_support_load_confirmed=admin_support_load_confirmed,
            api_key_track_pause_preferred=api_key_track_pause_preferred,
        )
        recommendation = max(candidates, key=lambda candidate: candidate.score)
        blockers = self._blockers(closure=closure, candidates=candidates)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-post-onboarding-roi-reselection-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "onboarding_closure": self._closure_summary(closure=closure),
            "candidates": candidates,
            "recommendation": recommendation,
            "decisions": self._decisions(
                closure=closure,
                recommendation=recommendation,
                status=status,
            ),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status, recommendation=recommendation),
        }

    def _candidates(
        self,
        *,
        partner_activation_requested: bool,
        partner_api_key_ready: bool,
        commercial_quota_pressure_confirmed: bool,
        new_endpoint_demand_confirmed: bool,
        admin_support_load_confirmed: bool,
        api_key_track_pause_preferred: bool,
    ) -> tuple[ApiKeyPostOnboardingRoiCandidate, ...]:
        return (
            ApiKeyPostOnboardingRoiCandidate(
                key="partner-activation-smoke",
                score=88 if partner_activation_requested and partner_api_key_ready else 32,
                recommended_track="API Key Partner Activation Smoke Review",
                rationale="com documentação publicada, o maior ROI é validar uma ativação real controlada sem ampliar superfície",
            ),
            ApiKeyPostOnboardingRoiCandidate(
                key="commercial-quotas",
                score=82 if commercial_quota_pressure_confirmed else 36,
                recommended_track="API Key Commercial Quotas Review",
                rationale="quotas comerciais devem avançar quando houver pressão real de plano, abuso ou cobrança",
            ),
            ApiKeyPostOnboardingRoiCandidate(
                key="public-endpoint-expansion",
                score=74 if new_endpoint_demand_confirmed else 30,
                recommended_track="API Key Public Endpoint Expansion Review",
                rationale="novos endpoints só vencem ROI com demanda concreta depois do consumo de list/detail",
            ),
            ApiKeyPostOnboardingRoiCandidate(
                key="admin-management-ux",
                score=66 if admin_support_load_confirmed else 24,
                recommended_track="API Key Admin Management UX Review",
                rationale="UX admin reduz carga de suporte, mas deve depender de fricção operacional observada",
            ),
            ApiKeyPostOnboardingRoiCandidate(
                key="api-key-track-pause",
                score=70 if api_key_track_pause_preferred else 12,
                recommended_track="System ROI Re-Selection Review",
                rationale="pausar API keys é válido quando outra frente de produto/operação supera o ROI restante",
            ),
        )

    def _blockers(
        self,
        *,
        closure: dict[str, object],
        candidates: tuple[ApiKeyPostOnboardingRoiCandidate, ...],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not closure["ready"]:
            blockers.append(f"onboarding:{closure['result']}")
            blockers.extend(f"onboarding:{blocker}" for blocker in closure["blockers"])
        if max(candidate.score for candidate in candidates) < 50:
            blockers.append("roi:no-post-onboarding-candidate-above-threshold")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        closure: dict[str, object],
        recommendation: ApiKeyPostOnboardingRoiCandidate,
        status: str,
    ) -> tuple[ApiKeyPostOnboardingRoiDecision, ...]:
        return (
            ApiKeyPostOnboardingRoiDecision(
                key="onboarding-closure",
                status="ready" if closure["ready"] else "blocked",
                summary="re-seleção pós-onboarding só segue quando docs/pacote/evidência estão fechados",
            ),
            ApiKeyPostOnboardingRoiDecision(
                key="recommended-track",
                status=recommendation.key,
                summary=recommendation.rationale,
            ),
            ApiKeyPostOnboardingRoiDecision(
                key="classification",
                status=status,
                summary="classificação decide o próximo ROI depois da trilha de onboarding de parceiros",
            ),
        )

    def _next_tracks(
        self,
        *,
        status: str,
        recommendation: ApiKeyPostOnboardingRoiCandidate,
    ) -> tuple[str, ...]:
        if status == "ready":
            return (
                recommendation.recommended_track,
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Partner Onboarding Closure Review",
            "System ROI Re-Selection Review",
        )

    def _closure_summary(self, *, closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": closure["result"],
            "ready": bool(closure["ready"]),
            "closed_scope_count": len(closure["closed_scope"]),
            "residual_risk_count": len(closure["residual_risks"]),
        }


api_key_post_onboarding_roi_reselection_queries = ApiKeyPostOnboardingRoiReselectionQueryService()
