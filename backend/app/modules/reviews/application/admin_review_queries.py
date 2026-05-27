from __future__ import annotations

from dataclasses import dataclass


STATUS_OPTIONS = [
    {"value": "", "label": "Todos"},
    {"value": "pending", "label": "Pendentes"},
    {"value": "approved", "label": "Aprovadas"},
    {"value": "rejected", "label": "Rejeitadas"},
]


STATUS_LABELS = {
    "pending": "Pendente",
    "approved": "Aprovada",
    "rejected": "Rejeitada",
}


def _string(value: object) -> str:
    return str(value or "").strip()


class DjangoOrmAdminReviewRepository:
    def __init__(self) -> None:
        try:
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.product_review_model = None
            return
        self.product_review_model = ProductReview

    def list_reviews(self, *, tenant_id: int | None, status: str = "", search: str = "") -> list[object]:
        if self.product_review_model is None or not tenant_id:
            return []
        queryset = self.product_review_model._default_manager.select_related("product", "customer").filter(
            tenant_id=tenant_id,
        )
        normalized_status = _string(status)
        if normalized_status in STATUS_LABELS:
            queryset = queryset.filter(status=normalized_status)
        normalized_search = _string(search).lower()
        reviews = list(queryset.order_by("-created_at", "-id")[:100])
        if normalized_search:
            reviews = [
                review
                for review in reviews
                if normalized_search in _string(getattr(getattr(review, "product", None), "name", "")).lower()
                or normalized_search in _string(getattr(review, "title", "")).lower()
                or normalized_search in _string(getattr(review, "body", "")).lower()
                or normalized_search in _string(getattr(review, "author_name", "")).lower()
            ]
        return reviews


@dataclass
class AdminReviewQueryService:
    repository: DjangoOrmAdminReviewRepository

    def list_reviews(self, *, tenant_id: int | None, status: str = "", search: str = "") -> list[dict[str, object]]:
        return [
            {
                "id": review.id,
                "product_name": _string(getattr(getattr(review, "product", None), "name", "")) or "Produto indisponível",
                "rating": int(getattr(review, "rating", 0) or 0),
                "author_name": _string(getattr(review, "author_name", "")) or "Cliente",
                "title": _string(getattr(review, "title", "")) or "Sem título",
                "body": _string(getattr(review, "body", "")),
                "status": _string(getattr(review, "status", "")),
                "status_label": STATUS_LABELS.get(_string(getattr(review, "status", "")), "Desconhecido"),
                "created_at": review.created_at.strftime("%d/%m/%Y %H:%M") if getattr(review, "created_at", None) else "-",
            }
            for review in self.repository.list_reviews(tenant_id=tenant_id, status=status, search=search)
        ]


admin_review_queries = AdminReviewQueryService(repository=DjangoOrmAdminReviewRepository())
