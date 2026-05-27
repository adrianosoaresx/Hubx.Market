from __future__ import annotations

from dataclasses import dataclass


ELIGIBLE = "review-eligible"
NO_PURCHASE = "review-ineligible-no-purchase"
NOT_DELIVERED = "review-ineligible-not-delivered"
DUPLICATE = "review-ineligible-duplicate"
CUSTOMER_NOT_FOUND = "review-ineligible-customer-not-found"
PRODUCT_NOT_FOUND = "review-ineligible-product-not-found"
UNAVAILABLE = "review-ineligible-unavailable"


def _result(code: str, *, order_number: str = "") -> dict[str, object]:
    return {
        "result": code,
        "eligible": code == ELIGIBLE,
        "order_number": order_number,
    }


def _is_delivered_order(order: object) -> bool:
    status = str(getattr(order, "status", "") or "").strip()
    fulfillment_label = str(getattr(order, "fulfillment_status_label", "") or "").strip().lower()
    shipping_status = str(getattr(order, "shipping_status", "") or "").strip().lower()
    if status == "canceled":
        return False
    return status == "shipped" and ("concluído" in fulfillment_label or "entregue" in shipping_status)


class DjangoOrmReviewEligibilityRepository:
    def __init__(self) -> None:
        try:
            from app.modules.catalog.models import Product, ProductVariant
            from app.modules.customers.models import Customer
            from app.modules.orders.models import Order
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.customer_model = None
            self.order_model = None
            self.product_model = None
            self.product_review_model = None
            self.variant_model = None
            return
        self.customer_model = Customer
        self.order_model = Order
        self.product_model = Product
        self.product_review_model = ProductReview
        self.variant_model = ProductVariant

    def get_customer(self, *, tenant_id: int | None, customer_id: int | None):
        if self.customer_model is None or not tenant_id or not customer_id:
            return None
        return self.customer_model._default_manager.filter(tenant_id=tenant_id, id=customer_id).first()

    def get_product(self, *, tenant_id: int | None, product_id: int | None):
        if self.product_model is None or not tenant_id or not product_id:
            return None
        return self.product_model._default_manager.filter(tenant_id=tenant_id, id=product_id).first()

    def has_customer_review(self, *, tenant_id: int, customer_id: int, product_id: int) -> bool:
        if self.product_review_model is None:
            return False
        return self.product_review_model._default_manager.filter(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        ).exists()

    def product_variant_skus(self, *, tenant_id: int, product_id: int) -> list[str]:
        if self.variant_model is None:
            return []
        return list(
            self.variant_model._default_manager.filter(
                product_id=product_id,
                product__tenant_id=tenant_id,
            ).values_list("sku", flat=True)
        )

    def list_customer_orders_for_product(self, *, tenant_id: int, customer_id: int, product_id: int, variant_skus: list[str]) -> list[object]:
        if self.order_model is None:
            return []
        snapshot_orders = list(
            self.order_model._default_manager.filter(
                tenant_id=tenant_id,
                customer_id=customer_id,
                items__product_id_snapshot=product_id,
            )
            .distinct()
            .order_by("-updated_at", "-id")
        )
        if snapshot_orders:
            return snapshot_orders
        if not variant_skus:
            return []
        return list(
            self.order_model._default_manager.filter(
                tenant_id=tenant_id,
                customer_id=customer_id,
                items__variant_sku__in=variant_skus,
                items__product_id_snapshot__isnull=True,
            )
            .distinct()
            .order_by("-updated_at", "-id")
        )


@dataclass
class ReviewEligibilityQueryService:
    repository: DjangoOrmReviewEligibilityRepository

    def can_customer_review_product(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        product_id: int | None,
    ) -> dict[str, object]:
        if not tenant_id or not customer_id or not product_id:
            return _result(UNAVAILABLE)

        customer = self.repository.get_customer(tenant_id=tenant_id, customer_id=customer_id)
        if customer is None:
            return _result(CUSTOMER_NOT_FOUND)

        product = self.repository.get_product(tenant_id=tenant_id, product_id=product_id)
        if product is None:
            return _result(PRODUCT_NOT_FOUND)

        if self.repository.has_customer_review(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
        ):
            return _result(DUPLICATE)

        variant_skus = self.repository.product_variant_skus(tenant_id=tenant_id, product_id=product_id)
        orders = self.repository.list_customer_orders_for_product(
            tenant_id=tenant_id,
            customer_id=customer_id,
            product_id=product_id,
            variant_skus=variant_skus,
        )
        if not orders:
            return _result(NO_PURCHASE)

        delivered_order = next((order for order in orders if _is_delivered_order(order)), None)
        if delivered_order is None:
            return _result(NOT_DELIVERED)

        return _result(ELIGIBLE, order_number=str(getattr(delivered_order, "number", "") or ""))


review_eligibility_queries = ReviewEligibilityQueryService(
    repository=DjangoOrmReviewEligibilityRepository(),
)
