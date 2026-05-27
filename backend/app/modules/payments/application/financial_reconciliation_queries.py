from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _string(value: object) -> str:
    return str(value or "").strip()


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _order_is_confirmed(order) -> bool:
    status = _string(getattr(order, "status", "")).lower()
    payment_status = _string(getattr(order, "payment_status", "")).lower()
    return status == "paid" or "confirm" in payment_status or "pago" in payment_status


def _issue(
    *,
    tenant_id: int | None,
    order_number: str,
    attempt_key: str,
    issue_code: str,
    severity: str,
    title: str,
    description: str,
) -> dict[str, object]:
    return {
        "tenant_id": tenant_id,
        "order_number": _string(order_number),
        "attempt_key": _string(attempt_key),
        "issue_code": _string(issue_code),
        "severity": _string(severity),
        "title": _string(title),
        "description": _string(description),
    }


class DjangoOrmPaymentFinancialReconciliationRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.payment_attempt_model = None
            return
        self.payment_attempt_model = PaymentAttempt

    def list_attempts(self, *, tenant_id: int | None = None, limit: int = 250):
        if self.payment_attempt_model is None:
            return []
        queryset = self.payment_attempt_model._default_manager.select_related("order", "tenant").order_by(
            "-updated_at",
            "-id",
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return list(queryset[:limit])


@dataclass
class PaymentFinancialReconciliationQueryService:
    repository: DjangoOrmPaymentFinancialReconciliationRepository

    def list_reconciliation_issues(self, *, tenant_id: int | None = None, limit: int = 250) -> list[dict[str, object]]:
        issues: list[dict[str, object]] = []
        for attempt in self.repository.list_attempts(tenant_id=tenant_id, limit=limit):
            order = getattr(attempt, "order", None)
            if order is None:
                continue
            order_number = _string(getattr(order, "number", ""))
            attempt_key = _string(getattr(attempt, "attempt_key", ""))
            attempt_status = _string(getattr(attempt, "status", "")).lower()
            order_confirmed = _order_is_confirmed(order)

            if attempt_status == "paid" and not order_confirmed:
                issues.append(
                    _issue(
                        tenant_id=getattr(attempt, "tenant_id", None),
                        order_number=order_number,
                        attempt_key=attempt_key,
                        issue_code="attempt_paid_order_unconfirmed",
                        severity="critical",
                        title="Tentativa paga sem pedido confirmado",
                        description="A tentativa foi reconciliada como paga, mas o pedido ainda não está confirmado.",
                    )
                )
            if attempt_status in {"pending", "failed"} and order_confirmed:
                issues.append(
                    _issue(
                        tenant_id=getattr(attempt, "tenant_id", None),
                        order_number=order_number,
                        attempt_key=attempt_key,
                        issue_code="order_confirmed_attempt_not_paid",
                        severity="critical" if attempt_status == "pending" else "warning",
                        title="Pedido confirmado sem tentativa paga",
                        description="O pedido está confirmado, mas a tentativa mais recente não está reconciliada como paga.",
                    )
                )

            if _decimal(getattr(attempt, "amount", "0.00")) != _decimal(getattr(order, "total", "0.00")):
                issues.append(
                    _issue(
                        tenant_id=getattr(attempt, "tenant_id", None),
                        order_number=order_number,
                        attempt_key=attempt_key,
                        issue_code="attempt_amount_mismatch",
                        severity="warning",
                        title="Valor da tentativa diverge do pedido",
                        description="O valor registrado na tentativa de pagamento difere do total atual do pedido.",
                    )
                )

            attempt_reference = _string(getattr(attempt, "external_reference", ""))
            order_reference = _string(getattr(order, "payment_reference", ""))
            if attempt_status == "paid" and not attempt_reference:
                issues.append(
                    _issue(
                        tenant_id=getattr(attempt, "tenant_id", None),
                        order_number=order_number,
                        attempt_key=attempt_key,
                        issue_code="paid_attempt_missing_external_reference",
                        severity="warning",
                        title="Tentativa paga sem referência externa",
                        description="A tentativa está paga, mas não possui referência externa do provider.",
                    )
                )
            if attempt_reference and order_reference and attempt_reference != order_reference:
                issues.append(
                    _issue(
                        tenant_id=getattr(attempt, "tenant_id", None),
                        order_number=order_number,
                        attempt_key=attempt_key,
                        issue_code="payment_reference_mismatch",
                        severity="warning",
                        title="Referência de pagamento divergente",
                        description="A referência externa da tentativa difere da referência gravada no pedido.",
                    )
                )
        return issues


payment_financial_reconciliation_queries = PaymentFinancialReconciliationQueryService(
    repository=DjangoOrmPaymentFinancialReconciliationRepository(),
)
