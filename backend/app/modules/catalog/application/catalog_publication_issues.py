from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.catalog.models import Product


@dataclass(frozen=True)
class CatalogPublicationIssue:
    tenant_id: str
    product_id: int
    slug: str
    status: str
    is_active: bool
    issue_code: str


class CatalogPublicationIssueRepository(Protocol):
    def list_products(self, *, tenant_id: int | str | None = None):
        ...


class DjangoOrmCatalogPublicationIssueRepository:
    def list_products(self, *, tenant_id: int | str | None = None):
        queryset = Product.objects.prefetch_related("variants").order_by("tenant_id", "name", "id")
        normalized_tenant_id = str(tenant_id or "").strip()
        if normalized_tenant_id:
            queryset = queryset.filter(tenant_id=normalized_tenant_id)
        return list(queryset)


@dataclass
class CatalogPublicationIssueService:
    repository: CatalogPublicationIssueRepository

    def list_issues(
        self,
        *,
        tenant_id: int | str | None = None,
        issue_code: str = "",
        limit: int = 250,
    ) -> list[CatalogPublicationIssue]:
        safe_limit = min(max(1, int(limit or 250)), 1000)
        normalized_issue = str(issue_code or "").strip()
        issues: list[CatalogPublicationIssue] = []
        for product in self.repository.list_products(tenant_id=tenant_id):
            for code in self._issue_codes(product):
                if normalized_issue and code != normalized_issue:
                    continue
                issues.append(
                    CatalogPublicationIssue(
                        tenant_id=str(product.tenant_id),
                        product_id=int(product.id),
                        slug=str(product.slug or ""),
                        status=str(product.status or ""),
                        is_active=bool(product.is_active),
                        issue_code=code,
                    )
                )
                if len(issues) >= safe_limit:
                    return issues
        return issues

    def _issue_codes(self, product) -> list[str]:
        issues: list[str] = []
        variants = list(product.variants.all())
        default_variants = [variant for variant in variants if variant.is_default]
        if (product.status == Product.Status.ACTIVE) != bool(product.is_active):
            issues.append("status_mismatch")
        if not variants:
            issues.append("missing_variant")
        if variants and not default_variants:
            issues.append("missing_default_variant")
        for variant in default_variants[:1]:
            if Decimal(variant.price or 0) <= 0:
                issues.append("missing_price")
            if variant.track_inventory and not variant.allow_backorder and int(variant.stock or 0) <= 0:
                issues.append("stock_unavailable")
        return issues


catalog_publication_issues = CatalogPublicationIssueService(
    repository=DjangoOrmCatalogPublicationIssueRepository(),
)
