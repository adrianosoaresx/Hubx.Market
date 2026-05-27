from __future__ import annotations

from dataclasses import dataclass

from app.modules.reviews.application.review_eligibility_queries import ELIGIBLE, _is_delivered_order, review_eligibility_queries
from app.modules.reviews.application.review_submission_commands import _rating, _string


SUBMITTED_PENDING = "customer-review-submitted-pending"
INELIGIBLE = "customer-review-ineligible"
DUPLICATE = "customer-review-duplicate"
INVALID_RATING = "customer-review-invalid-rating"
UNAVAILABLE = "customer-review-unavailable"


class DjangoOrmCustomerReviewSubmissionRepository:
    def __init__(self) -> None:
        try:
            from app.modules.catalog.models import Product
            from app.modules.customers.models import Customer
            from app.modules.orders.models import Order
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.customer_model = None
            self.order_model = None
            self.product_model = None
            self.product_review_model = None
            return
        self.customer_model = Customer
        self.order_model = Order
        self.product_model = Product
        self.product_review_model = ProductReview

    def get_customer(self, *, tenant_id: int | None, customer_id: int | None):
        if self.customer_model is None or not tenant_id or not customer_id:
            return None
        return self.customer_model._default_manager.filter(tenant_id=tenant_id, id=customer_id).first()

    def get_product(self, *, tenant_id: int | None, product_id: int | None):
        if self.product_model is None or not tenant_id or not product_id:
            return None
        return self.product_model._default_manager.filter(tenant_id=tenant_id, id=product_id).first()

    def get_order(self, *, tenant_id: int | None, customer_id: int | None, order_number: str):
        if self.order_model is None or not tenant_id or not customer_id or not _string(order_number):
            return None
        return (
            self.order_model._default_manager.filter(
                tenant_id=tenant_id,
                customer_id=customer_id,
                number=_string(order_number).lstrip("#"),
            )
            .prefetch_related("items")
            .first()
        )

    def order_contains_product(self, *, order, product_id: int) -> bool:
        items = list(getattr(order, "items").all())
        for item in items:
            snapshot = getattr(item, "product_id_snapshot", None)
            if snapshot and int(snapshot) == int(product_id):
                return True
        return False

    def has_customer_review(self, *, tenant_id: int, customer_id: int, product_id: int) -> bool:
        if self.product_review_model is None:
            return False
        return self.product_review_model._default_manager.filter(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        ).exists()

    def create_review(self, *, tenant, product, customer, rating: int, title: str, body: str, author_name: str):
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
class CustomerReviewSubmissionCommandService:
    repository: DjangoOrmCustomerReviewSubmissionRepository

    def submit_customer_product_review(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        order_number: str,
        product_id: int | None,
        rating: object = None,
        title: str = "",
        body: str = "",
        author_name: str = "",
        consent_display_name: bool = False,
    ) -> tuple[str, object | None]:
        normalized_rating = _rating(rating)
        if normalized_rating is None:
            return INVALID_RATING, None
        if not tenant_id or not customer_id or not product_id or not _string(order_number):
            return UNAVAILABLE, None

        customer = self.repository.get_customer(tenant_id=tenant_id, customer_id=customer_id)
        product = self.repository.get_product(tenant_id=tenant_id, product_id=product_id)
        order = self.repository.get_order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            order_number=order_number,
        )
        if customer is None or product is None or order is None:
            return INELIGIBLE, None
        if not _is_delivered_order(order):
            return INELIGIBLE, None
        if not self.repository.order_contains_product(order=order, product_id=product_id):
            return INELIGIBLE, None
        if self.repository.has_customer_review(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        ):
            return DUPLICATE, None

        eligibility = review_eligibility_queries.can_customer_review_product(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        )
        if eligibility.get("result") != ELIGIBLE:
            return DUPLICATE if eligibility.get("result") == "review-ineligible-duplicate" else INELIGIBLE, None

        display_name = _string(author_name, max_length=120)
        if not consent_display_name:
            display_name = "Cliente"
        if not display_name:
            display_name = _string(getattr(customer, "full_name", ""), max_length=120) if consent_display_name else "Cliente"
        review = self.repository.create_review(
            tenant=getattr(product, "tenant", None),
            product=product,
            customer=customer,
            rating=normalized_rating,
            title=_string(title, max_length=120),
            body=_string(body),
            author_name=display_name or "Cliente",
        )
        if review is None:
            return UNAVAILABLE, None
        return SUBMITTED_PENDING, review


customer_review_submission_commands = CustomerReviewSubmissionCommandService(
    repository=DjangoOrmCustomerReviewSubmissionRepository(),
)
