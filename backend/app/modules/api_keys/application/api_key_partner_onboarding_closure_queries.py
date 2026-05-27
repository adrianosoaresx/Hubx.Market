from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_partner_documentation_publication_evidence_queries import (
    api_key_partner_documentation_publication_evidence_queries,
)


@dataclass(frozen=True)
class ApiKeyPartnerOnboardingClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerOnboardingClosureQueryService:
    def get_closure(
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
    ) -> dict[str, object]:
        publication_evidence = api_key_partner_documentation_publication_evidence_queries.get_review(
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
        )
        blockers = self._blockers(
            publication_evidence=publication_evidence,
            onboarding_scope_closed=onboarding_scope_closed,
            residual_risks_accepted=residual_risks_accepted,
            next_roi_decision_recorded=next_roi_decision_recorded,
            partner_activation_deferred=partner_activation_deferred,
            commercial_quotas_deferred=commercial_quotas_deferred,
            new_endpoint_expansion_deferred=new_endpoint_expansion_deferred,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-onboarding-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "publication_evidence": self._publication_summary(publication_evidence=publication_evidence),
            "decisions": self._decisions(
                publication_evidence=publication_evidence,
                onboarding_scope_closed=onboarding_scope_closed,
                residual_risks_accepted=residual_risks_accepted,
                next_roi_decision_recorded=next_roi_decision_recorded,
                partner_activation_deferred=partner_activation_deferred,
                commercial_quotas_deferred=commercial_quotas_deferred,
                new_endpoint_expansion_deferred=new_endpoint_expansion_deferred,
            ),
            "blockers": blockers,
            "closed_scope": self._closed_scope(),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(
        self,
        *,
        publication_evidence: dict[str, object],
        onboarding_scope_closed: bool,
        residual_risks_accepted: bool,
        next_roi_decision_recorded: bool,
        partner_activation_deferred: bool,
        commercial_quotas_deferred: bool,
        new_endpoint_expansion_deferred: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not publication_evidence["ready"]:
            blockers.append(f"publication:{publication_evidence['result']}")
            blockers.extend(f"publication:{blocker}" for blocker in publication_evidence["blockers"])
        checks = {
            "onboarding-scope-closed": onboarding_scope_closed,
            "residual-risks-accepted": residual_risks_accepted,
            "next-roi-decision-recorded": next_roi_decision_recorded,
            "partner-activation-deferred": partner_activation_deferred,
            "commercial-quotas-deferred": commercial_quotas_deferred,
            "new-endpoint-expansion-deferred": new_endpoint_expansion_deferred,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        publication_evidence: dict[str, object],
        onboarding_scope_closed: bool,
        residual_risks_accepted: bool,
        next_roi_decision_recorded: bool,
        partner_activation_deferred: bool,
        commercial_quotas_deferred: bool,
        new_endpoint_expansion_deferred: bool,
    ) -> tuple[ApiKeyPartnerOnboardingClosureDecision, ...]:
        return (
            ApiKeyPartnerOnboardingClosureDecision(
                key="publication-evidence",
                status="ready" if publication_evidence["ready"] else "blocked",
                summary="closure só segue quando publicação/entrega da documentação está evidenciada e sanitizada",
            ),
            ApiKeyPartnerOnboardingClosureDecision(
                key="scope",
                status="closed" if onboarding_scope_closed else "blocked",
                summary="escopo de onboarding fica restrito a documentação, pacote, evidência e handoff",
            ),
            ApiKeyPartnerOnboardingClosureDecision(
                key="residual-risks",
                status="accepted" if residual_risks_accepted else "blocked",
                summary="riscos residuais são aceitos antes de nova seleção ROI",
            ),
            ApiKeyPartnerOnboardingClosureDecision(
                key="deferrals",
                status="deferred"
                if partner_activation_deferred and commercial_quotas_deferred and new_endpoint_expansion_deferred
                else "blocked",
                summary="ativação real por parceiro, quotas comerciais e novos endpoints ficam fora desta closure",
            ),
            ApiKeyPartnerOnboardingClosureDecision(
                key="next-roi",
                status="recorded" if next_roi_decision_recorded else "blocked",
                summary="próxima decisão de ROI deve ser registrada fora da trilha de onboarding",
            ),
        )

    def _closed_scope(self) -> tuple[str, ...]:
        return (
            "partner onboarding documentation review",
            "partner documentation execution review",
            "partner documentation publication evidence",
            "public catalog onboarding guide",
            "delivery package",
            "publication evidence",
            "safe examples and redaction guardrails",
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "ativação real por parceiro ainda exige smoke operacional separado",
            "quotas comerciais e billing continuam fora do contrato",
            "novos endpoints públicos exigem nova seleção ROI e contrato próprio",
            "documentação precisa ser versionada novamente se payload ou erro mudar",
            "canal de entrega deve continuar restrito para evitar exposição acidental",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "System ROI Re-Selection Review",
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Partner Onboarding Closure Follow-Up",
            "API Key Partner Documentation Publication Evidence Review",
        )

    def _publication_summary(self, *, publication_evidence: dict[str, object]) -> dict[str, object]:
        return {
            "result": publication_evidence["result"],
            "ready": bool(publication_evidence["ready"]),
            "version": publication_evidence["evidence"].version,
            "channel": publication_evidence["evidence"].channel,
            "evidence_scope_count": len(publication_evidence["evidence_scope"]),
        }


api_key_partner_onboarding_closure_queries = ApiKeyPartnerOnboardingClosureQueryService()
