from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object) -> str:
    return str(value or "").strip()


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


class DjangoOrmPaymentRefundApprovalRepository:
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
            self.payment_refund_model._default_manager.select_related("order", "payment_attempt")
            .filter(tenant_id=tenant_id, refund_key=_string(refund_key))
            .first()
        )

    def save_refund(self, refund) -> None:
        refund.save(
            update_fields=[
                "status",
                "metadata",
                "updated_at",
            ]
        )


@dataclass
class PaymentRefundApprovalCommandService:
    repository: DjangoOrmPaymentRefundApprovalRepository

    def approve_refund(
        self,
        *,
        tenant_id: int | None,
        refund_key: str,
        actor_label: str,
        approval_note: str = "",
    ) -> tuple[str, object | None]:
        if not tenant_id or not _string(refund_key):
            return "refund-approval-unavailable", None

        refund = self.repository.get_refund(tenant_id=tenant_id, refund_key=refund_key)
        if refund is None:
            return "refund-approval-unavailable", None

        blockers = self._approval_blockers(refund=refund, actor_label=actor_label)
        if blockers:
            metadata = dict(getattr(refund, "metadata", {}) or {})
            metadata["approval_blockers"] = blockers
            metadata["approval_checked_at"] = timezone.now().isoformat()
            metadata["provider_call"] = "not-executed"
            refund.metadata = metadata
            self.repository.save_refund(refund)
            return "refund-approval-blocked", refund

        with transaction.atomic():
            refund = self.repository.get_refund(tenant_id=tenant_id, refund_key=refund_key)
            if refund is None:
                return "refund-approval-unavailable", None
            blockers = self._approval_blockers(refund=refund, actor_label=actor_label)
            if blockers:
                metadata = dict(getattr(refund, "metadata", {}) or {})
                metadata["approval_blockers"] = blockers
                metadata["approval_checked_at"] = timezone.now().isoformat()
                metadata["provider_call"] = "not-executed"
                refund.metadata = metadata
                self.repository.save_refund(refund)
                return "refund-approval-blocked", refund

            metadata = dict(getattr(refund, "metadata", {}) or {})
            metadata["approved_by"] = _string(actor_label)
            metadata["approved_at"] = timezone.now().isoformat()
            metadata["approval_note"] = _string(approval_note)
            metadata["approval_contract_version"] = "refund-approval-v1"
            metadata["provider_call"] = "not-executed"
            metadata.pop("approval_blockers", None)
            refund.metadata = metadata
            refund.status = self.repository.payment_refund_model.Status.PROCESSING
            self.repository.save_refund(refund)
            audit_log_commands.record_event(
                tenant_id=tenant_id,
                module="payments",
                action="refund.approved",
                entity_type="PaymentRefund",
                entity_id=str(refund.id),
                actor_label=_string(actor_label),
                summary=f"Refund {refund.refund_key} aprovado para execução",
                metadata={
                    "refund_key": str(refund.refund_key),
                    "order_id": getattr(refund, "order_id", None),
                    "amount": f"{_money(getattr(refund, 'amount', '0.00')):.2f}",
                    "currency_code": _string(getattr(refund, "currency_code", "")),
                    "provider_code": _string(getattr(refund, "provider_code", "")),
                    "provider_call": "not-executed",
                    "approval_contract_version": "refund-approval-v1",
                },
            )
            return "refund-approval-ready", refund

    def _approval_blockers(self, *, refund, actor_label: str) -> list[str]:
        blockers: list[str] = []
        status = _string(getattr(refund, "status", "")).lower()
        amount = _money(getattr(refund, "amount", "0.00"))
        payment_attempt = getattr(refund, "payment_attempt", None)

        if status != self.repository.payment_refund_model.Status.REQUESTED:
            blockers.append("refund-status-not-requested")
        if list(getattr(refund, "blockers", []) or []):
            blockers.append("refund-has-blockers")
        if not _string(actor_label):
            blockers.append("approval-actor-missing")
        if payment_attempt is None:
            blockers.append("paid-attempt-missing")
        elif _string(getattr(payment_attempt, "status", "")).lower() != self.repository.payment_attempt_model.Status.PAID:
            blockers.append("paid-attempt-missing")
        if not _string(getattr(refund, "external_reference", "")):
            blockers.append("external-reference-missing")
        if amount <= Decimal("0.00"):
            blockers.append("refund-amount-invalid")
        return blockers


payment_refund_approval_commands = PaymentRefundApprovalCommandService(
    repository=DjangoOrmPaymentRefundApprovalRepository(),
)
