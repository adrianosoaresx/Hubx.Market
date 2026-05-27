from __future__ import annotations

from dataclasses import dataclass


STATUS_LABELS = {
    "pending": "Avaliação em moderação",
    "approved": "Avaliação publicada",
    "rejected": "Avaliação não publicada",
}


def _empty() -> dict[str, object]:
    return {
        "found": False,
        "status": "",
        "status_label": "",
        "moderated_at": None,
        "created_at": None,
    }


class DjangoOrmCustomerReviewStatusRepository:
    def __init__(self) -> None:
        try:
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.product_review_model = None
            return
        self.product_review_model = ProductReview

    def get_customer_product_review(self, *, tenant_id: int | None, customer_id: int | None, product_id: int | None):
        if self.product_review_model is None or not tenant_id or not customer_id or not product_id:
            return None
        return (
            self.product_review_model._default_manager.filter(
                tenant_id=tenant_id,
                customer_id=customer_id,
                product_id=product_id,
            )
            .order_by("-created_at", "-id")
            .first()
        )


@dataclass
class CustomerReviewStatusQueryService:
    repository: DjangoOrmCustomerReviewStatusRepository

    def get_customer_product_review_status(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        product_id: int | None,
    ) -> dict[str, object]:
        review = self.repository.get_customer_product_review(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        )
        if review is None:
            return _empty()

        status = str(getattr(review, "status", "") or "").strip()
        return {
            "found": True,
            "status": status,
            "status_label": STATUS_LABELS.get(status, "Avaliação registrada"),
            "moderated_at": getattr(review, "moderated_at", None),
            "created_at": getattr(review, "created_at", None),
        }


customer_review_status_queries = CustomerReviewStatusQueryService(
    repository=DjangoOrmCustomerReviewStatusRepository(),
)
