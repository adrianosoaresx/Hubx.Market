from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.application.api_key_partner_documentation_execution_review_queries import (
    api_key_partner_documentation_execution_review_queries,
)


@dataclass(frozen=True)
class ApiKeyPartnerDocumentationPublicationEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass(frozen=True)
class ApiKeyPartnerDocumentationPublicationEvidence:
    version: str
    channel: str
    audience: str
    tenant_reference: str
    published_at: str
    evidence_reference: str


@dataclass
class ApiKeyPartnerDocumentationPublicationEvidenceQueryService:
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
    ) -> dict[str, object]:
        execution_review = api_key_partner_documentation_execution_review_queries.get_review(
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
        )
        evidence = self._evidence(
            published_version=published_version,
            approved_channel=approved_channel,
            target_audience=target_audience,
            tenant_reference=tenant_reference,
            published_at=published_at,
            evidence_reference=evidence_reference,
        )
        blockers = self._blockers(
            execution_review=execution_review,
            evidence=evidence,
            publication_confirmed=publication_confirmed,
            support_notified=support_notified,
            activation_status_recorded=activation_status_recorded,
            smoke_template_attached=smoke_template_attached,
            redaction_confirmed=redaction_confirmed,
            no_credential_shared=no_credential_shared,
            no_runtime_activation_performed=no_runtime_activation_performed,
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-documentation-publication-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "execution_review": self._execution_summary(execution_review=execution_review),
            "evidence": evidence,
            "decisions": self._decisions(
                publication_confirmed=publication_confirmed,
                support_notified=support_notified,
                activation_status_recorded=activation_status_recorded,
                smoke_template_attached=smoke_template_attached,
                redaction_confirmed=redaction_confirmed,
                no_credential_shared=no_credential_shared,
                no_runtime_activation_performed=no_runtime_activation_performed,
            ),
            "blockers": blockers,
            "evidence_scope": self._evidence_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _evidence(
        self,
        *,
        published_version: str,
        approved_channel: str,
        target_audience: str,
        tenant_reference: str,
        published_at: str,
        evidence_reference: str,
    ) -> ApiKeyPartnerDocumentationPublicationEvidence:
        return ApiKeyPartnerDocumentationPublicationEvidence(
            version=str(published_version or "").strip(),
            channel=str(approved_channel or "").strip(),
            audience=str(target_audience or "").strip(),
            tenant_reference=str(tenant_reference or "").strip(),
            published_at=str(published_at or "").strip(),
            evidence_reference=str(evidence_reference or "").strip(),
        )

    def _blockers(
        self,
        *,
        execution_review: dict[str, object],
        evidence: ApiKeyPartnerDocumentationPublicationEvidence,
        publication_confirmed: bool,
        support_notified: bool,
        activation_status_recorded: bool,
        smoke_template_attached: bool,
        redaction_confirmed: bool,
        no_credential_shared: bool,
        no_runtime_activation_performed: bool,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not execution_review["ready"]:
            blockers.append(f"execution:{execution_review['result']}")
            blockers.extend(f"execution:{blocker}" for blocker in execution_review["blockers"])
        required_fields = {
            "published-version": evidence.version,
            "approved-channel": evidence.channel,
            "target-audience": evidence.audience,
            "tenant-reference": evidence.tenant_reference,
            "published-at": evidence.published_at,
            "evidence-reference": evidence.evidence_reference,
        }
        for key, value in required_fields.items():
            if not value:
                blockers.append(f"{key}:missing")
        checks = {
            "publication-confirmed": publication_confirmed,
            "support-notified": support_notified,
            "activation-status-recorded": activation_status_recorded,
            "smoke-template-attached": smoke_template_attached,
            "redaction-confirmed": redaction_confirmed,
            "no-credential-shared": no_credential_shared,
            "no-runtime-activation-performed": no_runtime_activation_performed,
        }
        for key, value in checks.items():
            if not value:
                blockers.append(f"{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        publication_confirmed: bool,
        support_notified: bool,
        activation_status_recorded: bool,
        smoke_template_attached: bool,
        redaction_confirmed: bool,
        no_credential_shared: bool,
        no_runtime_activation_performed: bool,
    ) -> tuple[ApiKeyPartnerDocumentationPublicationEvidenceDecision, ...]:
        return (
            ApiKeyPartnerDocumentationPublicationEvidenceDecision(
                key="publication",
                status="confirmed" if publication_confirmed else "blocked",
                summary="documentação foi entregue/publicada pelo canal aprovado",
            ),
            ApiKeyPartnerDocumentationPublicationEvidenceDecision(
                key="operations",
                status="ready" if support_notified and activation_status_recorded and smoke_template_attached else "blocked",
                summary="suporte foi notificado e evidência de ativação/smoke está pronta para uso",
            ),
            ApiKeyPartnerDocumentationPublicationEvidenceDecision(
                key="redaction",
                status="guarded" if redaction_confirmed and no_credential_shared else "blocked",
                summary="evidência é sanitizada e não contém credencial, segredo ou token",
            ),
            ApiKeyPartnerDocumentationPublicationEvidenceDecision(
                key="runtime",
                status="unchanged" if no_runtime_activation_performed else "blocked",
                summary="publication evidence não executa ativação de runtime, smoke real ou feature flag",
            ),
        )

    def _evidence_scope(self) -> tuple[str, ...]:
        return (
            "published documentation version",
            "approved delivery channel",
            "target audience",
            "tenant reference",
            "publication timestamp",
            "sanitized evidence reference",
            "support notification",
            "activation status summary",
            "smoke evidence template attachment",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Onboarding Closure Review",
                "API Key Commercial Quotas Review",
            )
        return (
            "API Key Partner Documentation Publication Evidence Follow-Up",
            "API Key Partner Documentation Execution Review",
        )

    def _execution_summary(self, *, execution_review: dict[str, object]) -> dict[str, object]:
        return {
            "result": execution_review["result"],
            "ready": bool(execution_review["ready"]),
            "delivery_scope_count": len(execution_review["delivery_scope"]),
        }


api_key_partner_documentation_publication_evidence_queries = (
    ApiKeyPartnerDocumentationPublicationEvidenceQueryService()
)
