from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.api_keys.application.api_key_partner_onboarding_documentation_review_queries import (
    api_key_partner_onboarding_documentation_review_queries,
)


@dataclass(frozen=True)
class ApiKeyPartnerDocumentationExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerDocumentationExecutionReviewQueryService:
    repo_root: Path = Path(__file__).resolve().parents[5]
    onboarding_doc_path: Path = repo_root / "docs" / "api" / "public-catalog-partner-onboarding.md"

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
    ) -> dict[str, object]:
        onboarding_review = api_key_partner_onboarding_documentation_review_queries.get_review(
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
        )
        execution_artifacts = self._execution_artifacts()
        blockers = self._blockers(
            onboarding_review=onboarding_review,
            execution_artifacts=execution_artifacts,
            delivery_channel_documented=delivery_channel_documented,
            support_handoff_documented=support_handoff_documented,
            smoke_evidence_template_ready=smoke_evidence_template_ready,
            change_control_documented=change_control_documented,
            owner_approved=owner_approved,
            no_runtime_change_required=no_runtime_change_required,
            no_commercial_terms_included=no_commercial_terms_included,
            no_sensitive_material_included=no_sensitive_material_included,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-documentation-execution-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "onboarding_review": self._onboarding_summary(onboarding_review=onboarding_review),
            "execution_artifacts": execution_artifacts,
            "decisions": self._decisions(
                execution_artifacts=execution_artifacts,
                delivery_channel_documented=delivery_channel_documented,
                support_handoff_documented=support_handoff_documented,
                smoke_evidence_template_ready=smoke_evidence_template_ready,
                change_control_documented=change_control_documented,
                owner_approved=owner_approved,
                no_runtime_change_required=no_runtime_change_required,
                no_commercial_terms_included=no_commercial_terms_included,
                no_sensitive_material_included=no_sensitive_material_included,
            ),
            "blockers": blockers,
            "delivery_scope": self._delivery_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _execution_artifacts(self) -> dict[str, bool]:
        return {
            "delivery-package-section": self._doc_contains("## Delivery package"),
            "delivery-channel": self._doc_contains("Delivery channel"),
            "support-handoff": self._doc_contains("Support handoff"),
            "smoke-evidence-template": self._doc_contains("Smoke evidence template"),
            "change-control": self._doc_contains("Change control"),
            "documentation-owner": self._doc_contains("Documentation owner"),
            "no-commercial-terms": self._doc_contains("No commercial terms"),
            "no-runtime-change": self._doc_contains("No runtime change"),
        }

    def _blockers(
        self,
        *,
        onboarding_review: dict[str, object],
        execution_artifacts: dict[str, bool],
        delivery_channel_documented: bool,
        support_handoff_documented: bool,
        smoke_evidence_template_ready: bool,
        change_control_documented: bool,
        owner_approved: bool,
        no_runtime_change_required: bool,
        no_commercial_terms_included: bool,
        no_sensitive_material_included: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not onboarding_review["ready"]:
            blockers.append(f"onboarding:{onboarding_review['result']}")
            blockers.extend(f"onboarding:{blocker}" for blocker in onboarding_review["blockers"])
        blockers.extend(f"artifact-missing:{name}" for name, present in execution_artifacts.items() if not present)
        checks = {
            "delivery-channel-documented": delivery_channel_documented,
            "support-handoff-documented": support_handoff_documented,
            "smoke-evidence-template-ready": smoke_evidence_template_ready,
            "change-control-documented": change_control_documented,
            "owner-approved": owner_approved,
            "no-runtime-change-required": no_runtime_change_required,
            "no-commercial-terms-included": no_commercial_terms_included,
            "no-sensitive-material-included": no_sensitive_material_included,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        execution_artifacts: dict[str, bool],
        delivery_channel_documented: bool,
        support_handoff_documented: bool,
        smoke_evidence_template_ready: bool,
        change_control_documented: bool,
        owner_approved: bool,
        no_runtime_change_required: bool,
        no_commercial_terms_included: bool,
        no_sensitive_material_included: bool,
    ) -> tuple[ApiKeyPartnerDocumentationExecutionDecision, ...]:
        return (
            ApiKeyPartnerDocumentationExecutionDecision(
                key="delivery-package",
                status="ready" if all(execution_artifacts.values()) and delivery_channel_documented else "blocked",
                summary="pacote possui canal, versão, owner e escopo de entrega documentados",
            ),
            ApiKeyPartnerDocumentationExecutionDecision(
                key="operations-handoff",
                status="ready"
                if support_handoff_documented and smoke_evidence_template_ready and change_control_documented
                else "blocked",
                summary="handoff cobre suporte, evidência de smoke e controle de mudança",
            ),
            ApiKeyPartnerDocumentationExecutionDecision(
                key="approval",
                status="approved" if owner_approved else "blocked",
                summary="owner aprova o pacote antes de qualquer entrega a parceiro",
            ),
            ApiKeyPartnerDocumentationExecutionDecision(
                key="safety-boundary",
                status="guarded"
                if no_runtime_change_required and no_commercial_terms_included and no_sensitive_material_included
                else "blocked",
                summary="execution não altera runtime, não inclui termos comerciais e não contém material sensível",
            ),
        )

    def _delivery_scope(self) -> tuple[str, ...]:
        return (
            "versioned public catalog onboarding guide",
            "delivery channel decision",
            "support handoff notes",
            "smoke evidence template",
            "change control notes",
            "documentation owner approval",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Documentation Publication Evidence Review",
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Partner Documentation Execution Follow-Up",
            "API Key Partner Onboarding Documentation Review",
        )

    def _onboarding_summary(self, *, onboarding_review: dict[str, object]) -> dict[str, object]:
        return {
            "result": onboarding_review["result"],
            "ready": bool(onboarding_review["ready"]),
            "closed_scope_count": len(onboarding_review["closed_scope"]),
        }

    def _doc_contains(self, text: str) -> bool:
        return self.onboarding_doc_path.exists() and text in self.onboarding_doc_path.read_text(encoding="utf-8")


api_key_partner_documentation_execution_review_queries = ApiKeyPartnerDocumentationExecutionReviewQueryService()
