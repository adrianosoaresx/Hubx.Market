from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_post_onboarding_roi_reselection_queries import (
    api_key_post_onboarding_roi_reselection_queries,
)


@dataclass(frozen=True)
class ApiKeyPartnerActivationSmokeContract:
    partner_reference: str
    tenant_reference: str
    target_environment: str
    product_slug_reference: str
    evidence_reference: str


@dataclass(frozen=True)
class ApiKeyPartnerActivationSmokeContractDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerActivationSmokeContractQueryService:
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
        partner_reference: str = "",
        target_environment: str = "",
        product_slug_reference: str = "",
        smoke_evidence_reference: str = "",
        smoke_scope_documented: bool = False,
        list_endpoint_in_scope: bool = False,
        detail_endpoint_in_scope: bool = False,
        expected_status_codes_documented: bool = False,
        observability_check_documented: bool = False,
        rollback_plan_documented: bool = False,
        redaction_plan_documented: bool = False,
        no_new_endpoint_in_smoke: bool = False,
        no_commercial_terms_in_smoke: bool = False,
        no_runtime_change_in_smoke: bool = False,
        no_credential_material_in_smoke: bool = False,
    ) -> dict[str, object]:
        roi_review = api_key_post_onboarding_roi_reselection_queries.get_review(
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
            partner_activation_requested=partner_activation_requested,
            partner_api_key_ready=partner_api_key_ready,
        )
        contract = self._contract(
            partner_reference=partner_reference,
            tenant_reference=tenant_reference,
            target_environment=target_environment,
            product_slug_reference=product_slug_reference,
            evidence_reference=smoke_evidence_reference,
        )
        blockers = self._blockers(
            roi_review=roi_review,
            contract=contract,
            smoke_scope_documented=smoke_scope_documented,
            list_endpoint_in_scope=list_endpoint_in_scope,
            detail_endpoint_in_scope=detail_endpoint_in_scope,
            expected_status_codes_documented=expected_status_codes_documented,
            observability_check_documented=observability_check_documented,
            rollback_plan_documented=rollback_plan_documented,
            redaction_plan_documented=redaction_plan_documented,
            no_new_endpoint_in_smoke=no_new_endpoint_in_smoke,
            no_commercial_terms_in_smoke=no_commercial_terms_in_smoke,
            no_runtime_change_in_smoke=no_runtime_change_in_smoke,
            no_credential_material_in_smoke=no_credential_material_in_smoke,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-activation-smoke-contract-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "roi_review": self._roi_summary(roi_review=roi_review),
            "contract": contract,
            "decisions": self._decisions(
                smoke_scope_documented=smoke_scope_documented,
                list_endpoint_in_scope=list_endpoint_in_scope,
                detail_endpoint_in_scope=detail_endpoint_in_scope,
                expected_status_codes_documented=expected_status_codes_documented,
                observability_check_documented=observability_check_documented,
                rollback_plan_documented=rollback_plan_documented,
                redaction_plan_documented=redaction_plan_documented,
                no_new_endpoint_in_smoke=no_new_endpoint_in_smoke,
                no_commercial_terms_in_smoke=no_commercial_terms_in_smoke,
                no_runtime_change_in_smoke=no_runtime_change_in_smoke,
                no_credential_material_in_smoke=no_credential_material_in_smoke,
            ),
            "blockers": blockers,
            "smoke_scope": self._smoke_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _contract(
        self,
        *,
        partner_reference: str,
        tenant_reference: str,
        target_environment: str,
        product_slug_reference: str,
        evidence_reference: str,
    ) -> ApiKeyPartnerActivationSmokeContract:
        return ApiKeyPartnerActivationSmokeContract(
            partner_reference=str(partner_reference or "").strip(),
            tenant_reference=str(tenant_reference or "").strip(),
            target_environment=str(target_environment or "").strip(),
            product_slug_reference=str(product_slug_reference or "").strip(),
            evidence_reference=str(evidence_reference or "").strip(),
        )

    def _blockers(
        self,
        *,
        roi_review: dict[str, object],
        contract: ApiKeyPartnerActivationSmokeContract,
        smoke_scope_documented: bool,
        list_endpoint_in_scope: bool,
        detail_endpoint_in_scope: bool,
        expected_status_codes_documented: bool,
        observability_check_documented: bool,
        rollback_plan_documented: bool,
        redaction_plan_documented: bool,
        no_new_endpoint_in_smoke: bool,
        no_commercial_terms_in_smoke: bool,
        no_runtime_change_in_smoke: bool,
        no_credential_material_in_smoke: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not roi_review["ready"]:
            blockers.append(f"roi:{roi_review['result']}")
            blockers.extend(f"roi:{blocker}" for blocker in roi_review["blockers"])
        if roi_review["recommendation"].recommended_track != "API Key Partner Activation Smoke Review":
            blockers.append("roi:partner-activation-smoke-not-recommended")
        required_fields = {
            "partner-reference": contract.partner_reference,
            "tenant-reference": contract.tenant_reference,
            "target-environment": contract.target_environment,
            "product-slug-reference": contract.product_slug_reference,
            "smoke-evidence-reference": contract.evidence_reference,
        }
        for key, value in required_fields.items():
            if not value:
                blockers.append(f"{key}:missing")
        checks = {
            "smoke-scope-documented": smoke_scope_documented,
            "list-endpoint-in-scope": list_endpoint_in_scope,
            "detail-endpoint-in-scope": detail_endpoint_in_scope,
            "expected-status-codes-documented": expected_status_codes_documented,
            "observability-check-documented": observability_check_documented,
            "rollback-plan-documented": rollback_plan_documented,
            "redaction-plan-documented": redaction_plan_documented,
            "no-new-endpoint-in-smoke": no_new_endpoint_in_smoke,
            "no-commercial-terms-in-smoke": no_commercial_terms_in_smoke,
            "no-runtime-change-in-smoke": no_runtime_change_in_smoke,
            "no-credential-material-in-smoke": no_credential_material_in_smoke,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        smoke_scope_documented: bool,
        list_endpoint_in_scope: bool,
        detail_endpoint_in_scope: bool,
        expected_status_codes_documented: bool,
        observability_check_documented: bool,
        rollback_plan_documented: bool,
        redaction_plan_documented: bool,
        no_new_endpoint_in_smoke: bool,
        no_commercial_terms_in_smoke: bool,
        no_runtime_change_in_smoke: bool,
        no_credential_material_in_smoke: bool,
    ) -> tuple[ApiKeyPartnerActivationSmokeContractDecision, ...]:
        return (
            ApiKeyPartnerActivationSmokeContractDecision(
                key="scope",
                status="ready" if smoke_scope_documented and list_endpoint_in_scope and detail_endpoint_in_scope else "blocked",
                summary="smoke cobre apenas listagem e detalhe públicos de catálogo",
            ),
            ApiKeyPartnerActivationSmokeContractDecision(
                key="operations",
                status="ready"
                if expected_status_codes_documented and observability_check_documented and rollback_plan_documented
                else "blocked",
                summary="contrato define status esperados, observabilidade e rollback",
            ),
            ApiKeyPartnerActivationSmokeContractDecision(
                key="redaction",
                status="guarded" if redaction_plan_documented and no_credential_material_in_smoke else "blocked",
                summary="evidência deve ser sanitizada e sem credencial ou header de autenticação",
            ),
            ApiKeyPartnerActivationSmokeContractDecision(
                key="boundaries",
                status="guarded"
                if no_new_endpoint_in_smoke and no_commercial_terms_in_smoke and no_runtime_change_in_smoke
                else "blocked",
                summary="contrato não cria endpoint, termo comercial, quota, billing ou mudança de runtime",
            ),
        )

    def _smoke_scope(self) -> tuple[str, ...]:
        return (
            "GET /api/v1/catalog/products/",
            "GET /api/v1/catalog/products/<slug>/",
            "read:catalog scope",
            "tenant subdomain",
            "sanitized evidence reference",
            "observability check",
            "rollback plan",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Activation Smoke Execution",
                "API Key Partner Activation Evidence Capture",
            )
        return (
            "API Key Partner Activation Smoke Contract Follow-Up",
            "System ROI Re-Selection Review",
        )

    def _roi_summary(self, *, roi_review: dict[str, object]) -> dict[str, object]:
        return {
            "result": roi_review["result"],
            "ready": bool(roi_review["ready"]),
            "recommendation": roi_review["recommendation"].recommended_track,
        }


api_key_partner_activation_smoke_contract_queries = ApiKeyPartnerActivationSmokeContractQueryService()
