from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg, Count


def _string(value: object) -> str:
    return str(value or "").strip()


def _rating(value: object) -> str:
    try:
        return f"{Decimal(str(value or '0')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP):.1f}"
    except Exception:
        return "0.0"


class DjangoOrmProductReviewSummaryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.product_review_model = None
            return
        self.product_review_model = ProductReview

    def approved_summary(self, *, tenant_id: int | None, product_id: int | None) -> dict[str, str | int]:
        if self.product_review_model is None or not tenant_id or not product_id:
            return _empty_summary()
        aggregate = self.product_review_model._default_manager.filter(
            tenant_id=tenant_id,
            product_id=product_id,
            status=self.product_review_model.Status.APPROVED,
        ).aggregate(review_count=Count("id"), rating_average=Avg("rating"))
        review_count = int(aggregate.get("review_count") or 0)
        return {
            "review_count": review_count,
            "rating_average": _rating(aggregate.get("rating_average") if review_count else None),
            "status": "ready" if review_count else "empty",
        }

    def approved_summaries(self, *, tenant_id: int | None, product_ids: list[int]) -> dict[int, dict[str, str | int]]:
        if self.product_review_model is None or not tenant_id or not product_ids:
            return {}
        summaries = {product_id: _empty_summary() for product_id in product_ids}
        aggregates = (
            self.product_review_model._default_manager.filter(
                tenant_id=tenant_id,
                product_id__in=product_ids,
                status=self.product_review_model.Status.APPROVED,
            )
            .values("product_id")
            .annotate(review_count=Count("id"), rating_average=Avg("rating"))
        )
        for aggregate in aggregates:
            product_id = int(aggregate["product_id"])
            review_count = int(aggregate.get("review_count") or 0)
            summaries[product_id] = {
                "review_count": review_count,
                "rating_average": _rating(aggregate.get("rating_average") if review_count else None),
                "status": "ready" if review_count else "empty",
            }
        return summaries

    def approved_reviews(
        self,
        *,
        tenant_id: int | None,
        product_id: int | None,
        limit: int = 5,
    ) -> list[dict[str, str | int]]:
        if self.product_review_model is None or not tenant_id or not product_id:
            return []
        safe_limit = max(0, min(int(limit or 0), 20))
        reviews = (
            self.product_review_model._default_manager.filter(
                tenant_id=tenant_id,
                product_id=product_id,
                status=self.product_review_model.Status.APPROVED,
            )
            .order_by("-created_at", "-id")[:safe_limit]
        )
        return [
            {
                "rating": int(review.rating),
                "title": _string(review.title),
                "body": _string(review.body),
                "author_name": _string(review.author_name) or "Cliente",
                "created_at": review.created_at.isoformat() if review.created_at else "",
            }
            for review in reviews
        ]


def _empty_summary() -> dict[str, str | int]:
    return {
        "review_count": 0,
        "rating_average": "0.0",
        "status": "empty",
    }


def _product_ids(values: list[int | str] | tuple[int | str, ...] | set[int | str]) -> list[int]:
    product_ids: list[int] = []
    seen: set[int] = set()
    for value in values or []:
        try:
            product_id = int(value)
        except (TypeError, ValueError):
            continue
        if product_id <= 0 or product_id in seen:
            continue
        product_ids.append(product_id)
        seen.add(product_id)
    return product_ids


@dataclass
class ProductReviewSummaryQueryService:
    repository: DjangoOrmProductReviewSummaryRepository

    def get_product_review_summary(self, *, tenant_id: int | None, product_id: int | None) -> dict[str, str | int]:
        return self.repository.approved_summary(tenant_id=tenant_id, product_id=product_id)

    def get_product_review_summaries(
        self,
        *,
        tenant_id: int | None,
        product_ids: list[int | str] | tuple[int | str, ...] | set[int | str],
    ) -> dict[int, dict[str, str | int]]:
        normalized_ids = _product_ids(product_ids)
        if not tenant_id or not normalized_ids:
            return {}
        return self.repository.approved_summaries(tenant_id=tenant_id, product_ids=normalized_ids)

    def list_approved_product_reviews(
        self,
        *,
        tenant_id: int | None,
        product_id: int | None,
        limit: int = 5,
    ) -> list[dict[str, str | int]]:
        return self.repository.approved_reviews(tenant_id=tenant_id, product_id=product_id, limit=limit)


product_review_summary_queries = ProductReviewSummaryQueryService(
    repository=DjangoOrmProductReviewSummaryRepository(),
)
