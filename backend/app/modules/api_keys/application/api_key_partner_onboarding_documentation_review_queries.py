from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.api_keys.application.api_key_system_roi_reselection_queries import (
    api_key_system_roi_reselection_queries,
)


@dataclass(frozen=True)
class ApiKeyPartnerOnboardingDocumentationDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerOnboardingDocumentationReviewQueryService:
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
    ) -> dict[str, object]:
        roi_review = api_key_system_roi_reselection_queries.get_review(
            model_ready=model_ready,
            runtime_auth_ready=runtime_auth_ready,
            drf_adapter_ready=drf_adapter_ready,
            public_endpoints_ready=public_endpoints_ready,
            observability_ready=observability_ready,
            expansion_closed=expansion_closed,
            no_billing_or_quotas_required=no_billing_or_quotas_required,
            no_secret_exposure_confirmed=no_secret_exposure_confirmed,
            partner_docs_missing=True,
            partner_onboarding_requested=True,
        )
        documentation_artifacts = self._documentation_artifacts()
        blockers = self._blockers(
            roi_review=roi_review,
            documentation_artifacts=documentation_artifacts,
            partner_docs_versioned=partner_docs_versioned,
            endpoint_examples_documented=endpoint_examples_documented,
            activation_checklist_ready=activation_checklist_ready,
            error_contract_documented=error_contract_documented,
            safe_examples_confirmed=safe_examples_confirmed,
            no_new_endpoint_required=no_new_endpoint_required,
            no_quota_or_billing_required=no_quota_or_billing_required,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-onboarding-documentation-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "roi_review": self._roi_summary(roi_review=roi_review),
            "documentation_artifacts": documentation_artifacts,
            "decisions": self._decisions(
                documentation_artifacts=documentation_artifacts,
                partner_docs_versioned=partner_docs_versioned,
                endpoint_examples_documented=endpoint_examples_documented,
                activation_checklist_ready=activation_checklist_ready,
                error_contract_documented=error_contract_documented,
                safe_examples_confirmed=safe_examples_confirmed,
                no_new_endpoint_required=no_new_endpoint_required,
                no_quota_or_billing_required=no_quota_or_billing_required,
            ),
            "blockers": blockers,
            "closed_scope": self._closed_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _documentation_artifacts(self) -> dict[str, bool]:
        return {
            "partner-onboarding-doc": self.onboarding_doc_path.exists(),
            "catalog-list-example": self._doc_contains("GET /api/v1/catalog/products/"),
            "catalog-detail-example": self._doc_contains("GET /api/v1/catalog/products/<slug>/"),
            "read-catalog-scope": self._doc_contains("read:catalog"),
            "tenant-subdomain": self._doc_contains("tenant subdomain"),
            "activation-checklist": self._doc_contains("Activation checklist"),
            "safe-auth-placeholder": self._doc_contains("Bearer <partner_api_key>"),
            "rate-limit-section": self._doc_contains("Rate limit"),
            "observability-section": self._doc_contains("Observability"),
            "error-contract-section": self._doc_contains("Error contract"),
        }

    def _blockers(
        self,
        *,
        roi_review: dict[str, object],
        documentation_artifacts: dict[str, bool],
        partner_docs_versioned: bool,
        endpoint_examples_documented: bool,
        activation_checklist_ready: bool,
        error_contract_documented: bool,
        safe_examples_confirmed: bool,
        no_new_endpoint_required: bool,
        no_quota_or_billing_required: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not roi_review["ready"]:
            blockers.append(f"roi:{roi_review['result']}")
            blockers.extend(f"roi:{blocker}" for blocker in roi_review["blockers"])
        if roi_review["recommendation"].recommended_track != "API Key Partner Onboarding Documentation Review":
            blockers.append("roi:partner-onboarding-not-recommended")
        blockers.extend(f"artifact-missing:{name}" for name, present in documentation_artifacts.items() if not present)
        checks = {
            "partner-docs-versioned": partner_docs_versioned,
            "endpoint-examples-documented": endpoint_examples_documented,
            "activation-checklist-ready": activation_checklist_ready,
            "error-contract-documented": error_contract_documented,
            "safe-examples-confirmed": safe_examples_confirmed,
            "no-new-endpoint-required": no_new_endpoint_required,
            "no-quota-or-billing-required": no_quota_or_billing_required,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        documentation_artifacts: dict[str, bool],
        partner_docs_versioned: bool,
        endpoint_examples_documented: bool,
        activation_checklist_ready: bool,
        error_contract_documented: bool,
        safe_examples_confirmed: bool,
        no_new_endpoint_required: bool,
        no_quota_or_billing_required: bool,
    ) -> tuple[ApiKeyPartnerOnboardingDocumentationDecision, ...]:
        return (
            ApiKeyPartnerOnboardingDocumentationDecision(
                key="documentation-artifact",
                status="ready" if all(documentation_artifacts.values()) and partner_docs_versioned else "blocked",
                summary="documentação versionada cobre endpoints públicos de catálogo, tenant subdomain e escopo read:catalog",
            ),
            ApiKeyPartnerOnboardingDocumentationDecision(
                key="examples",
                status="safe" if endpoint_examples_documented and safe_examples_confirmed else "blocked",
                summary="exemplos usam placeholders e payloads públicos, sem segredo ou chave real",
            ),
            ApiKeyPartnerOnboardingDocumentationDecision(
                key="activation",
                status="ready" if activation_checklist_ready and error_contract_documented else "blocked",
                summary="checklist cobre ativação, erros esperados, rate limit e observability",
            ),
            ApiKeyPartnerOnboardingDocumentationDecision(
                key="scope-control",
                status="deferred" if no_new_endpoint_required and no_quota_or_billing_required else "blocked",
                summary="review não abre novo endpoint, quota comercial, cobrança ou superfície admin",
            ),
        )

    def _closed_scope(self) -> tuple[str, ...]:
        return (
            "partner onboarding documentation artifact",
            "GET /api/v1/catalog/products/",
            "GET /api/v1/catalog/products/<slug>/",
            "scope read:catalog",
            "safe authentication placeholder",
            "activation checklist",
            "error contract",
            "rate limit and observability notes",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Documentation Execution Review",
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Partner Onboarding Documentation Follow-Up",
            "System ROI Re-Selection Review",
        )

    def _roi_summary(self, *, roi_review: dict[str, object]) -> dict[str, object]:
        return {
            "result": roi_review["result"],
            "ready": bool(roi_review["ready"]),
            "recommendation": roi_review["recommendation"].recommended_track,
        }

    def _doc_contains(self, text: str) -> bool:
        return self.onboarding_doc_path.exists() and text in self.onboarding_doc_path.read_text(encoding="utf-8")


api_key_partner_onboarding_documentation_review_queries = ApiKeyPartnerOnboardingDocumentationReviewQueryService()
