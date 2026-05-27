from __future__ import annotations

from dataclasses import dataclass


def _string(value: object, *, max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if max_length is not None:
        return text[:max_length]
    return text


def _rating(value: object) -> int | None:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 5:
        return None
    return rating


class DjangoOrmProductReviewSubmissionRepository:
    def __init__(self) -> None:
        try:
            from app.modules.catalog.models import Product
            from app.modules.customers.models import Customer
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.customer_model = None
            self.product_model = None
            self.product_review_model = None
            return
        self.customer_model = Customer
        self.product_model = Product
        self.product_review_model = ProductReview

    def get_product(self, *, tenant_id: int | None, product_id: int | None = None, product_slug: str = ""):
        if self.product_model is None or not tenant_id:
            return None
        queryset = self.product_model._default_manager.filter(tenant_id=tenant_id)
        if product_id:
            return queryset.filter(id=product_id).first()
        if _string(product_slug):
            return queryset.filter(slug=_string(product_slug)).first()
        return None

    def get_customer(self, *, tenant_id: int | None, customer_id: int | None = None):
        if self.customer_model is None or not tenant_id or not customer_id:
            return None
        return self.customer_model._default_manager.filter(tenant_id=tenant_id, id=customer_id).first()

    def create_review(
        self,
        *,
        tenant,
        product,
        customer,
        rating: int,
        title: str,
        body: str,
        author_name: str,
        source: str,
    ):
        if self.product_review_model is None:
            return None
        return self.product_review_model._default_manager.create(
            tenant=tenant,
            product=product,
            customer=customer,
            rating=rating,
            title=title,
            body=body,
            author_name=author_name,
            status=self.product_review_model.Status.PENDING,
        )


@dataclass
class ProductReviewSubmissionCommandService:
    repository: DjangoOrmProductReviewSubmissionRepository

    def submit_product_review(
        self,
        *,
        tenant_id: int | None,
        product_id: int | None = None,
        product_slug: str = "",
        rating: object = None,
        title: str = "",
        body: str = "",
        author_name: str = "",
        customer_id: int | None = None,
        source: str = "internal",
    ) -> tuple[str, object | None]:
        if not tenant_id:
            return "review-submission-blocked", None

        normalized_rating = _rating(rating)
        if normalized_rating is None:
            return "review-submission-blocked", None

        product = self.repository.get_product(
            tenant_id=tenant_id,
            product_id=product_id,
            product_slug=product_slug,
        )
        if product is None:
            return "review-product-not-found", None

        customer = self.repository.get_customer(tenant_id=tenant_id, customer_id=customer_id)
        review = self.repository.create_review(
            tenant=getattr(product, "tenant", None),
            product=product,
            customer=customer,
            rating=normalized_rating,
            title=_string(title, max_length=120),
            body=_string(body),
            author_name=_string(author_name, max_length=120) or "Cliente",
            source=_string(source, max_length=64) or "internal",
        )
        if review is None:
            return "review-submission-unavailable", None
        return "review-submitted-pending", review


product_review_submission_commands = ProductReviewSubmissionCommandService(
    repository=DjangoOrmProductReviewSubmissionRepository(),
)
