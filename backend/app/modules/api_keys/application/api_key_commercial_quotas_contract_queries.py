from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_partner_onboarding_closure_queries import (
    api_key_partner_onboarding_closure_queries,
)


@dataclass(frozen=True)
class ApiKeyCommercialQuotaContract:
    dimensions: tuple[str, ...]
    scope: str
    default_window_seconds: int
    default_limit: int
    overage_behavior: str
    response_status: int


@dataclass(frozen=True)
class ApiKeyCommercialQuotaContractDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyCommercialQuotasContractQueryService:
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
        battery_b_selected_by_operator: bool = False,
        battery_a_remaining_deferred: bool = False,
        commercial_quota_pressure_confirmed: bool = False,
        quota_dimensions_documented: bool = False,
        quota_window_documented: bool = False,
        quota_default_limits_documented: bool = False,
        quota_overage_behavior_documented: bool = False,
        quota_error_contract_documented: bool = False,
        quota_observability_documented: bool = False,
        quota_admin_visibility_documented: bool = False,
        no_billing_charge_in_contract: bool = False,
        no_plan_enforcement_in_contract: bool = False,
        no_runtime_enforcement_in_contract: bool = False,
        no_new_endpoint_in_contract: bool = False,
        no_sensitive_material_in_contract: bool = False,
    ) -> dict[str, object]:
        onboarding_closure = api_key_partner_onboarding_closure_queries.get_closure(
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
        contract = self._contract()
        blockers = self._blockers(
            onboarding_closure=onboarding_closure,
            battery_b_selected_by_operator=battery_b_selected_by_operator,
            battery_a_remaining_deferred=battery_a_remaining_deferred,
            commercial_quota_pressure_confirmed=commercial_quota_pressure_confirmed,
            quota_dimensions_documented=quota_dimensions_documented,
            quota_window_documented=quota_window_documented,
            quota_default_limits_documented=quota_default_limits_documented,
            quota_overage_behavior_documented=quota_overage_behavior_documented,
            quota_error_contract_documented=quota_error_contract_documented,
            quota_observability_documented=quota_observability_documented,
            quota_admin_visibility_documented=quota_admin_visibility_documented,
            no_billing_charge_in_contract=no_billing_charge_in_contract,
            no_plan_enforcement_in_contract=no_plan_enforcement_in_contract,
            no_runtime_enforcement_in_contract=no_runtime_enforcement_in_contract,
            no_new_endpoint_in_contract=no_new_endpoint_in_contract,
            no_sensitive_material_in_contract=no_sensitive_material_in_contract,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-commercial-quotas-contract-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "onboarding_closure": self._closure_summary(onboarding_closure=onboarding_closure),
            "contract": contract,
            "decisions": self._decisions(
                battery_b_selected_by_operator=battery_b_selected_by_operator,
                battery_a_remaining_deferred=battery_a_remaining_deferred,
                commercial_quota_pressure_confirmed=commercial_quota_pressure_confirmed,
                quota_dimensions_documented=quota_dimensions_documented,
                quota_window_documented=quota_window_documented,
                quota_default_limits_documented=quota_default_limits_documented,
                quota_overage_behavior_documented=quota_overage_behavior_documented,
                quota_error_contract_documented=quota_error_contract_documented,
                quota_observability_documented=quota_observability_documented,
                quota_admin_visibility_documented=quota_admin_visibility_documented,
                no_billing_charge_in_contract=no_billing_charge_in_contract,
                no_plan_enforcement_in_contract=no_plan_enforcement_in_contract,
                no_runtime_enforcement_in_contract=no_runtime_enforcement_in_contract,
                no_new_endpoint_in_contract=no_new_endpoint_in_contract,
                no_sensitive_material_in_contract=no_sensitive_material_in_contract,
            ),
            "blockers": blockers,
            "closed_scope": self._closed_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _contract(self) -> ApiKeyCommercialQuotaContract:
        return ApiKeyCommercialQuotaContract(
            dimensions=("tenant_id", "api_key_id", "endpoint", "window"),
            scope="read:catalog",
            default_window_seconds=86400,
            default_limit=10000,
            overage_behavior="hard-limit-429",
            response_status=429,
        )

    def _blockers(
        self,
        *,
        onboarding_closure: dict[str, object],
        battery_b_selected_by_operator: bool,
        battery_a_remaining_deferred: bool,
        commercial_quota_pressure_confirmed: bool,
        quota_dimensions_documented: bool,
        quota_window_documented: bool,
        quota_default_limits_documented: bool,
        quota_overage_behavior_documented: bool,
        quota_error_contract_documented: bool,
        quota_observability_documented: bool,
        quota_admin_visibility_documented: bool,
        no_billing_charge_in_contract: bool,
        no_plan_enforcement_in_contract: bool,
        no_runtime_enforcement_in_contract: bool,
        no_new_endpoint_in_contract: bool,
        no_sensitive_material_in_contract: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not onboarding_closure["ready"]:
            blockers.append(f"onboarding:{onboarding_closure['result']}")
            blockers.extend(f"onboarding:{blocker}" for blocker in onboarding_closure["blockers"])
        checks = {
            "battery-b-selected-by-operator": battery_b_selected_by_operator,
            "battery-a-remaining-deferred": battery_a_remaining_deferred,
            "commercial-quota-pressure-confirmed": commercial_quota_pressure_confirmed,
            "quota-dimensions-documented": quota_dimensions_documented,
            "quota-window-documented": quota_window_documented,
            "quota-default-limits-documented": quota_default_limits_documented,
            "quota-overage-behavior-documented": quota_overage_behavior_documented,
            "quota-error-contract-documented": quota_error_contract_documented,
            "quota-observability-documented": quota_observability_documented,
            "quota-admin-visibility-documented": quota_admin_visibility_documented,
            "no-billing-charge-in-contract": no_billing_charge_in_contract,
            "no-plan-enforcement-in-contract": no_plan_enforcement_in_contract,
            "no-runtime-enforcement-in-contract": no_runtime_enforcement_in_contract,
            "no-new-endpoint-in-contract": no_new_endpoint_in_contract,
            "no-sensitive-material-in-contract": no_sensitive_material_in_contract,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        battery_b_selected_by_operator: bool,
        battery_a_remaining_deferred: bool,
        commercial_quota_pressure_confirmed: bool,
        quota_dimensions_documented: bool,
        quota_window_documented: bool,
        quota_default_limits_documented: bool,
        quota_overage_behavior_documented: bool,
        quota_error_contract_documented: bool,
        quota_observability_documented: bool,
        quota_admin_visibility_documented: bool,
        no_billing_charge_in_contract: bool,
        no_plan_enforcement_in_contract: bool,
        no_runtime_enforcement_in_contract: bool,
        no_new_endpoint_in_contract: bool,
        no_sensitive_material_in_contract: bool,
    ) -> tuple[ApiKeyCommercialQuotaContractDecision, ...]:
        return (
            ApiKeyCommercialQuotaContractDecision(
                key="battery-selection",
                status="accepted" if battery_b_selected_by_operator and battery_a_remaining_deferred else "blocked",
                summary="Battery B foi selecionada mesmo com ondas restantes de ativação diferidas",
            ),
            ApiKeyCommercialQuotaContractDecision(
                key="commercial-pressure",
                status="confirmed" if commercial_quota_pressure_confirmed else "blocked",
                summary="quotas comerciais exigem pressão explícita de plano, abuso, custo ou governança",
            ),
            ApiKeyCommercialQuotaContractDecision(
                key="quota-shape",
                status="ready"
                if quota_dimensions_documented
                and quota_window_documented
                and quota_default_limits_documented
                and quota_overage_behavior_documented
                else "blocked",
                summary="contrato define dimensões, janela, limites padrão e comportamento de excesso",
            ),
            ApiKeyCommercialQuotaContractDecision(
                key="operability",
                status="ready"
                if quota_error_contract_documented and quota_observability_documented and quota_admin_visibility_documented
                else "blocked",
                summary="contrato cobre erro 429, observabilidade e visibilidade admin",
            ),
            ApiKeyCommercialQuotaContractDecision(
                key="boundaries",
                status="guarded"
                if no_billing_charge_in_contract
                and no_plan_enforcement_in_contract
                and no_runtime_enforcement_in_contract
                and no_new_endpoint_in_contract
                and no_sensitive_material_in_contract
                else "blocked",
                summary="review não cria cobrança, plano, enforcement runtime, endpoint novo ou material sensível",
            ),
        )

    def _closed_scope(self) -> tuple[str, ...]:
        return (
            "quota dimensions tenant_id/api_key_id/endpoint/window",
            "scope read:catalog",
            "default daily quota shape",
            "hard-limit 429 overage behavior",
            "admin read-only visibility requirement",
            "metrics/audit requirement",
            "no billing charge in this contract",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Quota Model Minimal Execution",
                "API Key Quota Enforcement Runtime Review",
            )
        return (
            "API Key Commercial Quotas Contract Follow-Up",
            "System Execution Wave Batteries Review",
        )

    def _closure_summary(self, *, onboarding_closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": onboarding_closure["result"],
            "ready": bool(onboarding_closure["ready"]),
            "closed_scope_count": len(onboarding_closure["closed_scope"]),
        }


api_key_commercial_quotas_contract_queries = ApiKeyCommercialQuotasContractQueryService()
