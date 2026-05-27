from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuditInstrumentationDecision:
    key: str
    status: str
    summary: str


@dataclass
class AuditInstrumentationExpansionQueryService:
    def get_review(
        self,
        *,
        critical_inventory_ready: bool = False,
        payment_admin_actions_ready: bool = False,
        api_key_actions_ready: bool = False,
        catalog_admin_actions_ready: bool = False,
        evidence_review_ready: bool = False,
        metadata_redaction_ready: bool = False,
        tenant_scope_confirmed: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "critical_inventory_ready": bool(critical_inventory_ready),
            "payment_admin_actions_ready": bool(payment_admin_actions_ready),
            "api_key_actions_ready": bool(api_key_actions_ready),
            "catalog_admin_actions_ready": bool(catalog_admin_actions_ready),
            "evidence_review_ready": bool(evidence_review_ready),
            "metadata_redaction_ready": bool(metadata_redaction_ready),
            "tenant_scope_confirmed": bool(tenant_scope_confirmed),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = tuple(f"audit-instrumentation:{key}:missing" for key, value in signals.items() if not value)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"audit-instrumentation-expansion-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "audit",
            "signals": signals,
            "decisions": (
                AuditInstrumentationDecision(
                    "scope",
                    "ready" if signals["critical_inventory_ready"] else "blocked",
                    "instrumentação cobre ações críticas selecionadas, não logging genérico",
                ),
                AuditInstrumentationDecision(
                    "payments",
                    "ready" if signals["payment_admin_actions_ready"] else "blocked",
                    "aprovação e execução de refund precisam gerar trilha auditável",
                ),
                AuditInstrumentationDecision(
                    "api_keys",
                    "ready" if signals["api_key_actions_ready"] else "blocked",
                    "criação, revogação e quotas de API key permanecem auditadas",
                ),
                AuditInstrumentationDecision(
                    "catalog",
                    "ready" if signals["catalog_admin_actions_ready"] else "blocked",
                    "mudança administrativa de visibilidade de produto precisa gerar auditoria",
                ),
                AuditInstrumentationDecision(
                    "redaction",
                    "guarded" if signals["metadata_redaction_ready"] else "blocked",
                    "metadata não inclui segredo de API, payload provider ou dados sensíveis",
                ),
            ),
            "instrumented_actions": (
                "payments.refund.approved",
                "payments.refund.execution_recorded",
                "api_keys.api_key.created",
                "api_keys.api_key.revoked",
                "api_keys.api_key.quota_upserted",
                "catalog.product.visibility_updated",
            ),
            "closure_scope": (
                "critical actions inventory",
                "payment refund approval/execution audit",
                "api key audit coverage confirmation",
                "catalog admin visibility audit",
                "cross-module evidence review",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery G — Notifications Production Delivery",) if status == "ready" else ("Audit Instrumentation Follow-Up",),
        }


audit_instrumentation_expansion_queries = AuditInstrumentationExpansionQueryService()
