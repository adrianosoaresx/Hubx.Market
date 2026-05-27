from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone


ALLOWED_DECISIONS = {"no-go", "sandbox-observed", "go-production-limited"}
SENSITIVE_MARKERS = {
    "authorization:",
    "bearer ",
    "basic ",
    "secret",
    "token",
    "api_key",
    "apikey",
    "sk_",
    "card_number",
    "cvv",
    "cvc",
    "bank_account",
    "agencia",
    "agência",
    "conta",
}


def _string(value: object) -> str:
    return str(value or "").strip()


def _contains_sensitive_value(value: object) -> bool:
    text = _string(value).lower()
    if not text:
        return False
    if any(marker in text for marker in SENSITIVE_MARKERS):
        return True
    digits = "".join(character for character in text if character.isdigit())
    return len(digits) >= 13


class DjangoOrmPaymentRefundSandboxEvidenceRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentRefund
        except Exception:
            self.payment_refund_model = None
            return
        self.payment_refund_model = PaymentRefund

    def get_refund(self, *, tenant_id: int | None, refund_key: str):
        if self.payment_refund_model is None or not tenant_id or not _string(refund_key):
            return None
        return (
            self.payment_refund_model._default_manager.select_related("tenant", "order", "payment_attempt")
            .filter(tenant_id=tenant_id, refund_key=_string(refund_key))
            .first()
        )

    def save_refund_metadata(self, refund) -> None:
        refund.save(update_fields=["metadata", "updated_at"])


@dataclass
class PaymentRefundSandboxEvidenceCommandService:
    repository: DjangoOrmPaymentRefundSandboxEvidenceRepository

    def capture_evidence(
        self,
        *,
        tenant_id: int | None,
        refund_key: str,
        captured_by: str,
        decision: str,
        environment: str = "sandbox",
        dry_run_output: str = "",
        execution_output: str = "",
        provider_dashboard_reference: str = "",
        reconciliation_reference: str = "",
        notes: str = "",
    ) -> tuple[str, object | None]:
        if not tenant_id or not _string(refund_key):
            return "refund-sandbox-evidence-unavailable", None
        normalized_captured_by = _string(captured_by)
        normalized_decision = _string(decision).lower()
        if not normalized_captured_by:
            return "refund-sandbox-evidence-blocked", None
        if normalized_decision not in ALLOWED_DECISIONS:
            return "refund-sandbox-evidence-blocked", None

        evidence_payload = {
            "captured_by": normalized_captured_by,
            "decision": normalized_decision,
            "environment": _string(environment) or "sandbox",
            "dry_run_output": _string(dry_run_output),
            "execution_output": _string(execution_output),
            "provider_dashboard_reference": _string(provider_dashboard_reference),
            "reconciliation_reference": _string(reconciliation_reference),
            "notes": _string(notes),
        }
        if any(_contains_sensitive_value(value) for value in evidence_payload.values()):
            return "refund-sandbox-evidence-sensitive-blocked", None

        refund = self.repository.get_refund(tenant_id=tenant_id, refund_key=refund_key)
        if refund is None:
            return "refund-sandbox-evidence-unavailable", None

        metadata = dict(getattr(refund, "metadata", {}) or {})
        if normalized_decision == "go-production-limited":
            if not dict(metadata.get("provider_refund") or {}):
                return "refund-sandbox-evidence-blocked", refund
            if not evidence_payload["provider_dashboard_reference"] or not evidence_payload["reconciliation_reference"]:
                return "refund-sandbox-evidence-blocked", refund

        metadata["sandbox_evidence"] = {
            "captured_at": timezone.now().isoformat(),
            "captured_by": normalized_captured_by,
            "environment": evidence_payload["environment"],
            "tenant_id": int(tenant_id),
            "refund_key": _string(refund_key),
            "dry_run_output": evidence_payload["dry_run_output"],
            "execution_output": evidence_payload["execution_output"],
            "provider_dashboard_reference": evidence_payload["provider_dashboard_reference"],
            "reconciliation_reference": evidence_payload["reconciliation_reference"],
            "decision": normalized_decision,
            "notes": evidence_payload["notes"],
        }
        refund.metadata = metadata
        self.repository.save_refund_metadata(refund)
        return "refund-sandbox-evidence-captured", refund


payment_refund_sandbox_evidence_commands = PaymentRefundSandboxEvidenceCommandService(
    repository=DjangoOrmPaymentRefundSandboxEvidenceRepository(),
)
