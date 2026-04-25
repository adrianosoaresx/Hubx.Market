from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.utils import timezone

from app.modules.checkout.models import CheckoutSession
from app.modules.orders.models import Order


CHECKOUT_SESSION_ISSUE_CODES = [
    "open_empty",
    "open_missing_contact",
    "open_missing_delivery",
    "open_missing_payment",
    "open_stale",
    "completed_order_missing",
    "total_mismatch",
]


@dataclass(frozen=True)
class CheckoutSessionIssue:
    tenant_id: str
    session_id: int
    session_key: str
    status: str
    issue_code: str


class CheckoutSessionIssueRepository(Protocol):
    def list_sessions(self, *, tenant_id: int | str | None = None):
        ...

    def has_order(self, *, tenant_id: int | str | None, order_number: str) -> bool:
        ...


class DjangoOrmCheckoutSessionIssueRepository:
    def list_sessions(self, *, tenant_id: int | str | None = None):
        queryset = CheckoutSession.objects.prefetch_related("items").order_by("tenant_id", "-updated_at", "id")
        normalized_tenant_id = str(tenant_id or "").strip()
        if normalized_tenant_id:
            queryset = queryset.filter(tenant_id=normalized_tenant_id)
        return list(queryset)

    def has_order(self, *, tenant_id: int | str | None, order_number: str) -> bool:
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").strip().lstrip("#")
        if not normalized_tenant_id or not normalized_order_number:
            return False
        return Order.objects.filter(tenant_id=normalized_tenant_id, number=normalized_order_number).exists()


@dataclass
class CheckoutSessionIssueService:
    repository: CheckoutSessionIssueRepository

    def list_issues(
        self,
        *,
        tenant_id: int | str | None = None,
        issue_code: str = "",
        limit: int = 250,
    ) -> list[CheckoutSessionIssue]:
        safe_limit = min(max(1, int(limit or 250)), 1000)
        normalized_issue = str(issue_code or "").strip()
        issues: list[CheckoutSessionIssue] = []
        for session in self.repository.list_sessions(tenant_id=tenant_id):
            for code in self._issue_codes(session):
                if normalized_issue and code != normalized_issue:
                    continue
                issues.append(
                    CheckoutSessionIssue(
                        tenant_id=str(session.tenant_id),
                        session_id=int(session.id),
                        session_key=str(session.session_key),
                        status=str(session.status or ""),
                        issue_code=code,
                    )
                )
                if len(issues) >= safe_limit:
                    return issues
        return issues

    def _issue_codes(self, session) -> list[str]:
        issues: list[str] = []
        items = list(session.items.all())
        if str(session.status or "") == CheckoutSession.Status.OPEN:
            if not items:
                issues.append("open_empty")
            else:
                if not str(session.email or "").strip() or not str(session.first_name or "").strip():
                    issues.append("open_missing_contact")
                if not all(
                    str(getattr(session, field_name, "") or "").strip()
                    for field_name in ("address_line_1", "city", "state", "zip_code", "shipping_method_selected")
                ):
                    issues.append("open_missing_delivery")
                if not str(session.payment_method_selected or "").strip() or not bool(session.accept_terms):
                    issues.append("open_missing_payment")
            if self._is_stale(session):
                issues.append("open_stale")
        if str(session.status or "") == CheckoutSession.Status.COMPLETED:
            order_number = str(session.completed_order_number or "").strip()
            if not order_number or not self.repository.has_order(tenant_id=session.tenant_id, order_number=order_number):
                issues.append("completed_order_missing")
        if items and self._has_total_mismatch(session, items):
            issues.append("total_mismatch")
        return issues

    def _is_stale(self, session) -> bool:
        now = timezone.now()
        expires_at = getattr(session, "expires_at", None)
        if expires_at and expires_at <= now:
            return True
        updated_at = getattr(session, "updated_at", None)
        if not updated_at:
            return False
        return updated_at <= now - timezone.timedelta(hours=24)

    def _has_total_mismatch(self, session, items: list[object]) -> bool:
        computed_subtotal = Decimal("0.00")
        for item in items:
            price = Decimal(str(getattr(item, "price", Decimal("0.00")) or Decimal("0.00")))
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            computed_subtotal += price * quantity
        session_subtotal = Decimal(str(getattr(session, "subtotal", Decimal("0.00")) or Decimal("0.00")))
        shipping_total = Decimal(str(getattr(session, "shipping_total", Decimal("0.00")) or Decimal("0.00")))
        discount_total = Decimal(str(getattr(session, "discount_total", Decimal("0.00")) or Decimal("0.00")))
        grand_total = Decimal(str(getattr(session, "grand_total", Decimal("0.00")) or Decimal("0.00")))
        expected_total = computed_subtotal + shipping_total - discount_total
        return abs(session_subtotal - computed_subtotal) > Decimal("0.01") or abs(grand_total - expected_total) > Decimal("0.01")


checkout_session_issues = CheckoutSessionIssueService(repository=DjangoOrmCheckoutSessionIssueRepository())
