from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentProductionDecision:
    key: str
    status: str
    summary: str


def _blockers(prefix: str, signals: dict[str, bool]) -> tuple[str, ...]:
    return tuple(f"{prefix}:{key}:missing" for key, value in signals.items() if not value)


def _status(blockers: tuple[str, ...]) -> str:
    return "ready" if not blockers else "blocked"


@dataclass
class PaymentProviderProductionGateQueryService:
    def get_review(
        self,
        *,
        provider_credentials_configured: bool = False,
        provider_mode_production_confirmed: bool = False,
        tenant_rollout_scope_defined: bool = False,
        webhook_secret_configured: bool = False,
        hosted_return_url_configured: bool = False,
        observability_ready: bool = False,
        runbook_reviewed: bool = False,
        rollback_plan_ready: bool = False,
        finance_owner_approved: bool = False,
        no_secret_material_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "provider_credentials_configured": bool(provider_credentials_configured),
            "provider_mode_production_confirmed": bool(provider_mode_production_confirmed),
            "tenant_rollout_scope_defined": bool(tenant_rollout_scope_defined),
            "webhook_secret_configured": bool(webhook_secret_configured),
            "hosted_return_url_configured": bool(hosted_return_url_configured),
            "observability_ready": bool(observability_ready),
            "runbook_reviewed": bool(runbook_reviewed),
            "rollback_plan_ready": bool(rollback_plan_ready),
            "finance_owner_approved": bool(finance_owner_approved),
            "no_secret_material_recorded": bool(no_secret_material_recorded),
        }
        blockers = _blockers("payment-provider-production-gate", signals)
        status = _status(blockers)
        return {
            "result": f"payment-provider-production-gate-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("provider", "ready" if signals["provider_credentials_configured"] and signals["provider_mode_production_confirmed"] else "blocked", "provider precisa estar configurado em modo produção"),
                PaymentProductionDecision("tenant-rollout", "ready" if signals["tenant_rollout_scope_defined"] else "blocked", "ativação deve ser tenant-by-tenant"),
                PaymentProductionDecision("operations", "ready" if signals["observability_ready"] and signals["runbook_reviewed"] and signals["rollback_plan_ready"] else "blocked", "observabilidade, runbook e rollback precisam estar prontos"),
                PaymentProductionDecision("classification", status, "classificação decide se pode capturar evidência de ativação produtiva"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payment Provider Production Activation Evidence", "Payment Provider Production Gate Follow-Up") if status == "ready" else ("Payment Provider Production Gate Follow-Up",),
        }


@dataclass
class PaymentProviderProductionActivationEvidenceQueryService:
    def get_review(
        self,
        *,
        production_gate_ready: bool = False,
        tenant_reference_recorded: bool = False,
        provider_dashboard_reference_recorded: bool = False,
        production_payment_intent_created: bool = False,
        hosted_checkout_reached: bool = False,
        return_url_observed: bool = False,
        metrics_snapshot_attached: bool = False,
        rollback_not_required: bool = False,
        no_secret_material_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "production_gate_ready": bool(production_gate_ready),
            "tenant_reference_recorded": bool(tenant_reference_recorded),
            "provider_dashboard_reference_recorded": bool(provider_dashboard_reference_recorded),
            "production_payment_intent_created": bool(production_payment_intent_created),
            "hosted_checkout_reached": bool(hosted_checkout_reached),
            "return_url_observed": bool(return_url_observed),
            "metrics_snapshot_attached": bool(metrics_snapshot_attached),
            "rollback_not_required": bool(rollback_not_required),
            "no_secret_material_recorded": bool(no_secret_material_recorded),
        }
        blockers = _blockers("payment-provider-production-activation-evidence", signals)
        status = _status(blockers)
        return {
            "result": f"payment-provider-production-activation-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("gate", "ready" if signals["production_gate_ready"] else "blocked", "evidência depende do gate de produção pronto"),
                PaymentProductionDecision("checkout", "observed" if signals["production_payment_intent_created"] and signals["hosted_checkout_reached"] and signals["return_url_observed"] else "blocked", "intent, hosted checkout e retorno precisam ser observados"),
                PaymentProductionDecision("classification", status, "classificação decide se pode seguir para smoke de webhook"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payment Webhook Production Smoke Review", "Payment Refund Production Gate Review") if status == "ready" else ("Payment Provider Production Activation Evidence Follow-Up",),
        }


@dataclass
class PaymentWebhookProductionSmokeQueryService:
    def get_review(
        self,
        *,
        activation_evidence_ready: bool = False,
        paid_webhook_observed: bool = False,
        failed_webhook_observed_or_deferred: bool = False,
        signature_validation_confirmed: bool = False,
        idempotency_confirmed: bool = False,
        order_payment_status_confirmed: bool = False,
        inventory_side_effects_confirmed: bool = False,
        audit_log_confirmed: bool = False,
        no_sensitive_payload_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "activation_evidence_ready": bool(activation_evidence_ready),
            "paid_webhook_observed": bool(paid_webhook_observed),
            "failed_webhook_observed_or_deferred": bool(failed_webhook_observed_or_deferred),
            "signature_validation_confirmed": bool(signature_validation_confirmed),
            "idempotency_confirmed": bool(idempotency_confirmed),
            "order_payment_status_confirmed": bool(order_payment_status_confirmed),
            "inventory_side_effects_confirmed": bool(inventory_side_effects_confirmed),
            "audit_log_confirmed": bool(audit_log_confirmed),
            "no_sensitive_payload_recorded": bool(no_sensitive_payload_recorded),
        }
        blockers = _blockers("payment-webhook-production-smoke", signals)
        status = _status(blockers)
        return {
            "result": f"payment-webhook-production-smoke-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("webhook", "ready" if signals["paid_webhook_observed"] and signals["signature_validation_confirmed"] and signals["idempotency_confirmed"] else "blocked", "webhook produtivo precisa validar pagamento, assinatura e idempotência"),
                PaymentProductionDecision("side-effects", "ready" if signals["order_payment_status_confirmed"] and signals["inventory_side_effects_confirmed"] else "blocked", "efeitos em pedido/estoque precisam ser confirmados"),
                PaymentProductionDecision("classification", status, "classificação decide se provider produtivo está operacionalmente validado"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payment Refund Production Gate Review", "Payment Financial Reconciliation Production Review") if status == "ready" else ("Payment Webhook Production Smoke Follow-Up",),
        }


@dataclass
class PaymentRefundProductionGateQueryService:
    def get_review(
        self,
        *,
        webhook_smoke_ready: bool = False,
        refund_foundation_closed: bool = False,
        sandbox_evidence_captured: bool = False,
        provider_refund_reference_ready: bool = False,
        finance_approval_required: bool = False,
        single_refund_manual_scope: bool = False,
        reconciliation_reference_required: bool = False,
        rollback_plan_ready: bool = False,
        no_self_service_enabled: bool = False,
        no_batch_execution_enabled: bool = False,
    ) -> dict[str, object]:
        signals = {
            "webhook_smoke_ready": bool(webhook_smoke_ready),
            "refund_foundation_closed": bool(refund_foundation_closed),
            "sandbox_evidence_captured": bool(sandbox_evidence_captured),
            "provider_refund_reference_ready": bool(provider_refund_reference_ready),
            "finance_approval_required": bool(finance_approval_required),
            "single_refund_manual_scope": bool(single_refund_manual_scope),
            "reconciliation_reference_required": bool(reconciliation_reference_required),
            "rollback_plan_ready": bool(rollback_plan_ready),
            "no_self_service_enabled": bool(no_self_service_enabled),
            "no_batch_execution_enabled": bool(no_batch_execution_enabled),
        }
        blockers = _blockers("payment-refund-production-gate", signals)
        status = _status(blockers)
        return {
            "result": f"payment-refund-production-gate-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("scope", "manual-limited" if signals["single_refund_manual_scope"] and signals["no_self_service_enabled"] and signals["no_batch_execution_enabled"] else "blocked", "refund produtivo só pode iniciar manual e unitário"),
                PaymentProductionDecision("evidence", "ready" if signals["sandbox_evidence_captured"] and signals["provider_refund_reference_ready"] else "blocked", "refund produtivo exige evidência sandbox e referência provider"),
                PaymentProductionDecision("classification", status, "classificação decide se pode capturar smoke de refund produtivo"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payment Refund Production Smoke Evidence", "Payment Financial Reconciliation Production Review") if status == "ready" else ("Payment Refund Production Gate Follow-Up",),
        }


@dataclass
class PaymentRefundProductionSmokeEvidenceQueryService:
    def get_review(
        self,
        *,
        refund_gate_ready: bool = False,
        refund_key_recorded: bool = False,
        provider_refund_status_recorded: bool = False,
        provider_dashboard_reference_recorded: bool = False,
        internal_ledger_updated: bool = False,
        reconciliation_reference_recorded: bool = False,
        operator_recorded: bool = False,
        no_customer_self_service: bool = False,
        no_sensitive_material_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "refund_gate_ready": bool(refund_gate_ready),
            "refund_key_recorded": bool(refund_key_recorded),
            "provider_refund_status_recorded": bool(provider_refund_status_recorded),
            "provider_dashboard_reference_recorded": bool(provider_dashboard_reference_recorded),
            "internal_ledger_updated": bool(internal_ledger_updated),
            "reconciliation_reference_recorded": bool(reconciliation_reference_recorded),
            "operator_recorded": bool(operator_recorded),
            "no_customer_self_service": bool(no_customer_self_service),
            "no_sensitive_material_recorded": bool(no_sensitive_material_recorded),
        }
        blockers = _blockers("payment-refund-production-smoke-evidence", signals)
        status = _status(blockers)
        return {
            "result": f"payment-refund-production-smoke-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("refund", "observed" if signals["refund_key_recorded"] and signals["provider_refund_status_recorded"] and signals["internal_ledger_updated"] else "blocked", "refund produtivo precisa referência interna/provider/ledger"),
                PaymentProductionDecision("classification", status, "classificação decide se refund pode entrar na closure produtiva"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payment Financial Reconciliation Production Review", "Payments Production Closure Review") if status == "ready" else ("Payment Refund Production Smoke Evidence Follow-Up",),
        }


@dataclass
class PaymentFinancialReconciliationProductionQueryService:
    def get_review(
        self,
        *,
        provider_activation_evidence_ready: bool = False,
        webhook_smoke_ready: bool = False,
        refund_evidence_ready_or_no_go_recorded: bool = False,
        reconciliation_report_exported: bool = False,
        paid_attempts_matched: bool = False,
        amount_mismatches_reviewed: bool = False,
        pending_attempts_triaged: bool = False,
        refund_entries_reconciled_or_deferred: bool = False,
        finance_owner_signed_off: bool = False,
        no_auto_correction_enabled: bool = False,
    ) -> dict[str, object]:
        signals = {
            "provider_activation_evidence_ready": bool(provider_activation_evidence_ready),
            "webhook_smoke_ready": bool(webhook_smoke_ready),
            "refund_evidence_ready_or_no_go_recorded": bool(refund_evidence_ready_or_no_go_recorded),
            "reconciliation_report_exported": bool(reconciliation_report_exported),
            "paid_attempts_matched": bool(paid_attempts_matched),
            "amount_mismatches_reviewed": bool(amount_mismatches_reviewed),
            "pending_attempts_triaged": bool(pending_attempts_triaged),
            "refund_entries_reconciled_or_deferred": bool(refund_entries_reconciled_or_deferred),
            "finance_owner_signed_off": bool(finance_owner_signed_off),
            "no_auto_correction_enabled": bool(no_auto_correction_enabled),
        }
        blockers = _blockers("payment-financial-reconciliation-production", signals)
        status = _status(blockers)
        return {
            "result": f"payment-financial-reconciliation-production-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("finance", "signed-off" if signals["finance_owner_signed_off"] and signals["reconciliation_report_exported"] else "blocked", "financeiro precisa relatório e aceite"),
                PaymentProductionDecision("no-auto-correction", "guarded" if signals["no_auto_correction_enabled"] else "blocked", "review não deve corrigir divergências automaticamente"),
                PaymentProductionDecision("classification", status, "classificação decide se payments pode fechar produção controlada"),
            ),
            "blockers": blockers,
            "next_tracks": ("Payments Production Closure Review", "System Production Closure Review") if status == "ready" else ("Payment Financial Reconciliation Production Follow-Up",),
        }


@dataclass
class PaymentsProductionClosureQueryService:
    def get_review(
        self,
        *,
        provider_gate_ready: bool = False,
        provider_activation_evidence_ready: bool = False,
        webhook_smoke_ready: bool = False,
        refund_gate_ready: bool = False,
        refund_smoke_evidence_ready_or_no_go_recorded: bool = False,
        financial_reconciliation_ready: bool = False,
        rollback_runbook_ready: bool = False,
        monitoring_window_defined: bool = False,
        incident_owner_defined: bool = False,
        no_unbounded_rollout: bool = False,
        no_sensitive_material_recorded: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "provider_gate_ready": bool(provider_gate_ready),
            "provider_activation_evidence_ready": bool(provider_activation_evidence_ready),
            "webhook_smoke_ready": bool(webhook_smoke_ready),
            "refund_gate_ready": bool(refund_gate_ready),
            "refund_smoke_evidence_ready_or_no_go_recorded": bool(refund_smoke_evidence_ready_or_no_go_recorded),
            "financial_reconciliation_ready": bool(financial_reconciliation_ready),
            "rollback_runbook_ready": bool(rollback_runbook_ready),
            "monitoring_window_defined": bool(monitoring_window_defined),
            "incident_owner_defined": bool(incident_owner_defined),
            "no_unbounded_rollout": bool(no_unbounded_rollout),
            "no_sensitive_material_recorded": bool(no_sensitive_material_recorded),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = _blockers("payments-production-closure", signals)
        status = _status(blockers)
        return {
            "result": f"payments-production-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "payments",
            "signals": signals,
            "decisions": (
                PaymentProductionDecision("battery-c", "complete" if status == "ready" else "blocked", "Battery C fecha provider, webhook, refund e reconciliação"),
                PaymentProductionDecision("rollout", "controlled" if signals["no_unbounded_rollout"] and signals["monitoring_window_defined"] else "blocked", "produção deve permanecer controlada e monitorada"),
                PaymentProductionDecision("classification", status, "classificação encerra ou bloqueia a Battery C"),
            ),
            "closure_scope": (
                "provider production gate",
                "provider activation evidence",
                "webhook production smoke",
                "refund production gate",
                "refund production smoke evidence or explicit No-Go",
                "financial reconciliation production review",
                "rollback/runbook/monitoring closure",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery D — Shipping Quote Productionization", "System Production Closure Review") if status == "ready" else ("Payments Production Closure Follow-Up",),
        }


payment_provider_production_gate_queries = PaymentProviderProductionGateQueryService()
payment_provider_production_activation_evidence_queries = PaymentProviderProductionActivationEvidenceQueryService()
payment_webhook_production_smoke_queries = PaymentWebhookProductionSmokeQueryService()
payment_refund_production_gate_queries = PaymentRefundProductionGateQueryService()
payment_refund_production_smoke_evidence_queries = PaymentRefundProductionSmokeEvidenceQueryService()
payment_financial_reconciliation_production_queries = PaymentFinancialReconciliationProductionQueryService()
payments_production_closure_queries = PaymentsProductionClosureQueryService()
