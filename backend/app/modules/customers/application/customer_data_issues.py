from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db.models.functions import Lower

from app.modules.customers.models import Customer
from app.modules.orders.models import Order


@dataclass(frozen=True)
class CustomerDataIssue:
    tenant_id: str
    customer_id: int
    slug: str
    email: str
    issue_code: str


class CustomerDataIssueRepository(Protocol):
    def list_customers(self, *, tenant_id: int | str | None = None):
        ...

    def list_case_duplicate_email_keys(self, *, tenant_id: int | str | None = None) -> set[tuple[str, str]]:
        ...

    def has_order_email_fallback(self, customer) -> bool:
        ...


class DjangoOrmCustomerDataIssueRepository:
    def list_customers(self, *, tenant_id: int | str | None = None):
        queryset = Customer.objects.prefetch_related("addresses").order_by("tenant_id", "full_name", "id")
        normalized_tenant_id = str(tenant_id or "").strip()
        if normalized_tenant_id:
            queryset = queryset.filter(tenant_id=normalized_tenant_id)
        return list(queryset)

    def list_case_duplicate_email_keys(self, *, tenant_id: int | str | None = None) -> set[tuple[str, str]]:
        queryset = Customer.objects.annotate(email_key=Lower("email")).values("tenant_id", "email_key")
        normalized_tenant_id = str(tenant_id or "").strip()
        if normalized_tenant_id:
            queryset = queryset.filter(tenant_id=normalized_tenant_id)
        counts: dict[tuple[str, str], int] = {}
        for row in queryset:
            email_key = str(row["email_key"] or "").strip()
            if not email_key:
                continue
            key = (str(row["tenant_id"]), email_key)
            counts[key] = counts.get(key, 0) + 1
        return {key for key, count in counts.items() if count > 1}

    def has_order_email_fallback(self, customer) -> bool:
        email = str(getattr(customer, "email", "") or "").strip()
        tenant_id = getattr(customer, "tenant_id", None)
        if not tenant_id or not email:
            return False
        return Order.objects.filter(tenant_id=tenant_id, customer__isnull=True, customer_email__iexact=email).exists()


@dataclass
class CustomerDataIssueService:
    repository: CustomerDataIssueRepository

    def list_issues(
        self,
        *,
        tenant_id: int | str | None = None,
        issue_code: str = "",
        limit: int = 250,
    ) -> list[CustomerDataIssue]:
        safe_limit = min(max(1, int(limit or 250)), 1000)
        normalized_issue = str(issue_code or "").strip()
        duplicate_email_keys = self.repository.list_case_duplicate_email_keys(tenant_id=tenant_id)
        issues: list[CustomerDataIssue] = []
        for customer in self.repository.list_customers(tenant_id=tenant_id):
            for code in self._issue_codes(customer, duplicate_email_keys=duplicate_email_keys):
                if normalized_issue and code != normalized_issue:
                    continue
                issues.append(
                    CustomerDataIssue(
                        tenant_id=str(customer.tenant_id),
                        customer_id=int(customer.id),
                        slug=str(customer.slug or ""),
                        email=str(customer.email or ""),
                        issue_code=code,
                    )
                )
                if len(issues) >= safe_limit:
                    return issues
        return issues

    def _issue_codes(self, customer, *, duplicate_email_keys: set[tuple[str, str]]) -> list[str]:
        issues: list[str] = []
        email = str(customer.email or "").strip()
        tenant_id = str(customer.tenant_id)
        addresses = list(customer.addresses.all())
        default_addresses = [address for address in addresses if address.is_default]
        if not str(customer.full_name or "").strip():
            issues.append("missing_name")
        if not email:
            issues.append("missing_email")
        if email and (tenant_id, email.lower()) in duplicate_email_keys:
            issues.append("duplicate_email_case")
        if not addresses:
            issues.append("missing_address")
        if addresses and not default_addresses:
            issues.append("missing_default_address")
        for address in default_addresses[:1]:
            if not all(
                str(getattr(address, field_name, "") or "").strip()
                for field_name in ("line_1", "city", "state", "postal_code")
            ):
                issues.append("incomplete_default_address")
        if self.repository.has_order_email_fallback(customer):
            issues.append("order_email_fallback")
        return issues


customer_data_issues = CustomerDataIssueService(repository=DjangoOrmCustomerDataIssueRepository())
