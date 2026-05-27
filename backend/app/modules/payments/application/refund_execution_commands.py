from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.payments.infrastructure.provider_adapters import (
    ProviderAdapterError,
    RefundProviderContract,
    get_provider_adapter,
)


def _string(value: object) -> str:
    return str(value or "").strip()


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


class DjangoOrmPaymentRefundExecutionRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt, PaymentRefund
        except Exception:
            self.payment_attempt_model = None
            self.payment_refund_model = None
            return
        self.payment_attempt_model = PaymentAttempt
        self.payment_refund_model = PaymentRefund

    def get_refund(self, *, tenant_id: int | None, refund_key: str):
        if self.payment_refund_model is None or not tenant_id or not _string(refund_key):
            return None
        return (
            self.payment_refund_model._default_manager.select_related("tenant", "order", "payment_attempt")
            .filter(tenant_id=tenant_id, refund_key=_string(refund_key))
            .first()
        )

    def save_refund(self, refund) -> None:
        refund.save(
            update_fields=[
                "status",
                "provider_refund_reference",
                "metadata",
                "completed_at",
                "failed_at",
                "updated_at",
            ]
        )


@dataclass
class PaymentRefundExecutionCommandService:
    repository: DjangoOrmPaymentRefundExecutionRepository

    def execute_refund(self, *, tenant_id: int | None, refund_key: str) -> tuple[str, object | None]:
        if not tenant_id or not _string(refund_key):
            return "refund-execution-unavailable", None

        refund = self.repository.get_refund(tenant_id=tenant_id, refund_key=refund_key)
        if refund is None:
            return "refund-execution-unavailable", None

        blockers = self._execution_blockers(refund=refund)
        if blockers:
            metadata = dict(getattr(refund, "metadata", {}) or {})
            metadata["execution_blockers"] = blockers
            metadata["execution_checked_at"] = timezone.now().isoformat()
            refund.metadata = metadata
            self.repository.save_refund(refund)
            return "refund-execution-blocked", refund

        contract = self._build_contract(refund=refund)
        adapter = get_provider_adapter(provider_code=contract.provider_code, tenant=getattr(refund, "tenant", None))
        try:
            response = adapter.create_refund(contract=contract)
        except ProviderAdapterError as exc:
            metadata = dict(getattr(refund, "metadata", {}) or {})
            metadata["provider_refund"] = {
                "status": "failed",
                "reason_code": str(exc),
                "payload_snapshot": {},
                "responded_at": timezone.now().isoformat(),
            }
            refund.metadata = metadata
            refund.status = self.repository.payment_refund_model.Status.FAILED
            refund.failed_at = timezone.now()
            self.repository.save_refund(refund)
            self._record_execution_audit(refund=refund, result="failed", reason_code=str(exc))
            return "refund-execution-failed", refund

        self._apply_provider_response(refund=refund, response=response)
        self.repository.save_refund(refund)
        self._record_execution_audit(refund=refund, result=_string(getattr(response, "status", "")) or "failed")
        if response.status == "failed":
            return "refund-execution-failed", refund
        if response.status == "succeeded":
            return "refund-execution-succeeded", refund
        return "refund-execution-accepted", refund

    def _execution_blockers(self, *, refund) -> list[str]:
        blockers: list[str] = []
        status = _string(getattr(refund, "status", "")).lower()
        amount = _money(getattr(refund, "amount", "0.00"))
        payment_attempt = getattr(refund, "payment_attempt", None)

        if status != self.repository.payment_refund_model.Status.PROCESSING:
            blockers.append("refund-status-not-processing")
        if _string(getattr(refund, "provider_refund_reference", "")):
            blockers.append("provider-refund-reference-present")
        if list(getattr(refund, "blockers", []) or []):
            blockers.append("refund-has-blockers")
        if payment_attempt is None:
            blockers.append("paid-attempt-missing")
        elif _string(getattr(payment_attempt, "status", "")).lower() != self.repository.payment_attempt_model.Status.PAID:
            blockers.append("paid-attempt-missing")
        if not _string(getattr(refund, "external_reference", "")):
            blockers.append("external-reference-missing")
        if amount <= Decimal("0.00"):
            blockers.append("refund-amount-invalid")
        return blockers

    def _build_contract(self, *, refund) -> RefundProviderContract:
        metadata = dict(getattr(refund, "metadata", {}) or {})
        metadata["order_number"] = _string(getattr(getattr(refund, "order", None), "number", ""))
        return RefundProviderContract(
            tenant_id=int(getattr(refund, "tenant_id", 0) or 0),
            refund_key=_string(getattr(refund, "refund_key", "")),
            idempotency_key=_string(getattr(refund, "idempotency_key", "")),
            provider_code=_string(getattr(refund, "provider_code", "")) or "payment",
            external_reference=_string(getattr(refund, "external_reference", "")),
            amount=f"{_money(getattr(refund, 'amount', '0.00')):.2f}",
            currency_code=_string(getattr(refund, "currency_code", "")) or "BRL",
            reason_code=_string(getattr(refund, "reason_code", "")),
            metadata=metadata,
        )

    def _apply_provider_response(self, *, refund, response) -> None:
        normalized_status = _string(getattr(response, "status", "")).lower()
        if normalized_status not in {"accepted", "succeeded", "failed"}:
            normalized_status = "failed"

        metadata = dict(getattr(refund, "metadata", {}) or {})
        metadata["provider_refund"] = {
            "provider_code": _string(getattr(response, "provider_code", "")),
            "provider_refund_reference": _string(getattr(response, "provider_refund_reference", "")),
            "status": normalized_status,
            "payload_snapshot": dict(getattr(response, "payload_snapshot", {}) or {}),
            "responded_at": timezone.now().isoformat(),
        }
        metadata.pop("execution_blockers", None)
        refund.metadata = metadata
        refund.provider_refund_reference = _string(getattr(response, "provider_refund_reference", ""))
        if normalized_status == "succeeded":
            refund.status = self.repository.payment_refund_model.Status.SUCCEEDED
            refund.completed_at = timezone.now()
        elif normalized_status == "failed":
            refund.status = self.repository.payment_refund_model.Status.FAILED
            refund.failed_at = timezone.now()

    def _record_execution_audit(self, *, refund, result: str, reason_code: str = "") -> None:
        audit_log_commands.record_event(
            tenant_id=getattr(refund, "tenant_id", None),
            module="payments",
            action="refund.execution_recorded",
            entity_type="PaymentRefund",
            entity_id=str(getattr(refund, "id", "")),
            actor_label="system",
            summary=f"Execução de refund {getattr(refund, 'refund_key', '')} registrada como {_string(result)}",
            metadata={
                "refund_key": str(getattr(refund, "refund_key", "")),
                "order_id": getattr(refund, "order_id", None),
                "amount": f"{_money(getattr(refund, 'amount', '0.00')):.2f}",
                "currency_code": _string(getattr(refund, "currency_code", "")),
                "provider_code": _string(getattr(refund, "provider_code", "")),
                "provider_result": _string(result),
                "reason_code": _string(reason_code),
                "payload_snapshot_included": False,
            },
        )


payment_refund_execution_commands = PaymentRefundExecutionCommandService(
    repository=DjangoOrmPaymentRefundExecutionRepository(),
)
