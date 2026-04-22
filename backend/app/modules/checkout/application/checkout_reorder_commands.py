from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection, transaction

from app.modules.checkout.application.checkout_activation_commands import (
    _default_payment_methods,
    _default_shipping_methods,
    _installments_summary,
    _safe_decimal,
    _shipping_total_from_selected_method,
)


logger = logging.getLogger(__name__)


def _variant_sku_from_order_item(item: object) -> str:
    explicit = str(getattr(item, "variant_sku", "") or "").strip()
    if explicit:
        return explicit
    meta = str(getattr(item, "meta", "") or "").strip()
    if meta.upper().startswith("SKU "):
        return meta[4:].strip()
    return ""


class CheckoutReorderRepository(Protocol):
    def bootstrap_from_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        ...


class DjangoOrmCheckoutReorderRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts import models as account_models
            from app.modules.catalog import models as catalog_models
            from app.modules.checkout import models as checkout_models
            from app.modules.customers import models as customer_models
            from app.modules.orders import models as order_models
            from app.modules.tenants import models as tenant_models
        except Exception:
            self.account_profile_model = None
            self.customer_address_model = None
            self.customer_model = None
            self.order_model = None
            self.product_variant_model = None
            self.product_image_model = None
            self.session_model = None
            self.item_model = None
            self.tenant_model = None
            return

        self.account_profile_model = getattr(account_models, "AccountProfile", None)
        self.customer_address_model = getattr(customer_models, "CustomerAddress", None)
        self.customer_model = getattr(customer_models, "Customer", None)
        self.order_model = getattr(order_models, "Order", None)
        self.product_variant_model = getattr(catalog_models, "ProductVariant", None)
        self.product_image_model = getattr(catalog_models, "ProductImage", None)
        self.session_model = getattr(checkout_models, "CheckoutSession", None)
        self.item_model = getattr(checkout_models, "CheckoutSessionItem", None)
        self.tenant_model = getattr(tenant_models, "Tenant", None)

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.order_model._meta.db_table,
                self.product_variant_model._meta.db_table,
                self.session_model._meta.db_table,
                self.item_model._meta.db_table,
                self.tenant_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_names.issubset(set(tables))

    def _profile_and_address_prefill(self, *, tenant_id: int, customer_id: int | None, email: str) -> dict[str, str]:
        profile = None
        if self.account_profile_model:
            try:
                queryset = self.account_profile_model._default_manager.select_related("customer").filter(
                    tenant_id=tenant_id,
                    is_active=True,
                )
                if customer_id:
                    profile = queryset.filter(customer_id=customer_id).order_by("-updated_at", "-id").first()
                if profile is None and email:
                    profile = queryset.filter(email__iexact=email).order_by("-updated_at", "-id").first()
                if profile is None:
                    profile = queryset.order_by("-updated_at", "-id").first()
            except Exception:
                profile = None

        customer = getattr(profile, "customer", None)
        if customer is None and customer_id and self.customer_model:
            try:
                customer = self.customer_model._default_manager.filter(
                    tenant_id=tenant_id,
                    pk=customer_id,
                ).first()
            except Exception:
                customer = None
        if customer is None and email and self.customer_model:
            try:
                customer = self.customer_model._default_manager.filter(
                    tenant_id=tenant_id,
                    email__iexact=email,
                ).order_by("-updated_at", "-id").first()
            except Exception:
                customer = None

        address = None
        if customer is not None and self.customer_address_model:
            try:
                address = (
                    self.customer_address_model._default_manager.filter(customer=customer)
                    .order_by("-is_default", "-updated_at", "-id")
                    .first()
                )
            except Exception:
                address = None

        return {
            "first_name": str(getattr(profile, "first_name", "") or ""),
            "last_name": str(getattr(profile, "last_name", "") or ""),
            "email": str(getattr(profile, "email", "") or email or ""),
            "phone": str(getattr(profile, "phone", "") or ""),
            "address_line_1": str(getattr(address, "line_1", "") or ""),
            "address_line_2": str(getattr(address, "line_2", "") or ""),
            "city": str(getattr(address, "city", "") or ""),
            "state": str(getattr(address, "state", "") or ""),
            "zip_code": str(getattr(address, "postal_code", "") or ""),
        }

    def _get_reusable_open_session(self, *, tenant_id: int):
        try:
            return (
                self.session_model._default_manager.select_for_update()
                .filter(tenant_id=tenant_id, status=self.session_model.Status.OPEN)
                .prefetch_related("items")
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None

    def _recalculate_session_totals(self, *, session) -> None:
        items = list(self.item_model._default_manager.filter(checkout_session=session).order_by("sort_order", "id"))
        subtotal = sum(
            (
                _safe_decimal(getattr(item, "price", Decimal("0.00")))
                * int(getattr(item, "quantity", 1) or 1)
                for item in items
            ),
            Decimal("0.00"),
        )
        shipping_total = _shipping_total_from_selected_method(session) if items else Decimal("0.00")
        discount_total = _safe_decimal(getattr(session, "discount_total", Decimal("0.00")))
        grand_total = subtotal + shipping_total - discount_total
        session.subtotal = subtotal
        session.shipping_total = shipping_total
        session.grand_total = grand_total
        if items:
            installments_summary, installments_selected, installments_options = _installments_summary(grand_total)
            session.installments_summary = installments_summary
            session.installments_options = installments_options
            if not any(
                option["value"] == str(getattr(session, "installments_selected", "") or "")
                for option in installments_options
            ):
                session.installments_selected = installments_selected
        else:
            session.installments_summary = ""
            session.installments_options = []
            session.installments_selected = ""

    def bootstrap_from_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        if not self.is_ready() or not tenant_id or not order_number:
            return "reorder-lite-unavailable", None

        try:
            order_queryset = self.order_model._default_manager.select_for_update().prefetch_related("items").filter(
                tenant_id=tenant_id,
                number=str(order_number).lstrip("#"),
            )
            if customer_id:
                order_queryset = order_queryset.filter(customer_id=customer_id)
            elif email:
                order_queryset = order_queryset.filter(customer_email__iexact=email)
            order = order_queryset.first()
        except Exception:
            return "reorder-lite-unavailable", None
        if order is None:
            return "reorder-lite-unavailable", None

        eligible_snapshots: list[dict[str, object]] = []
        ineligible_count = 0
        try:
            order_items = list(order.items.all())
        except Exception:
            order_items = []
        for order_item in order_items:
            variant_sku = _variant_sku_from_order_item(order_item)
            if not variant_sku:
                ineligible_count += 1
                continue
            try:
                variant = (
                    self.product_variant_model._default_manager.select_related("product")
                    .filter(
                        sku=variant_sku,
                        product__tenant_id=tenant_id,
                        product__status="active",
                        product__is_active=True,
                    )
                    .first()
                )
            except Exception:
                variant = None
            if variant is None:
                ineligible_count += 1
                continue
            image = None
            if self.product_image_model is not None:
                try:
                    image = (
                        self.product_image_model._default_manager.filter(product=variant.product)
                        .order_by("-is_primary", "position", "id")
                        .first()
                    )
                except Exception:
                    image = None
            eligible_snapshots.append(
                {
                    "title": str(getattr(variant.product, "name", "") or getattr(order_item, "title", "") or "Produto"),
                    "subtitle": str(getattr(order_item, "subtitle", "") or ""),
                    "meta": f"SKU {variant_sku}",
                    "variant_sku": variant_sku,
                    "image_url": str(getattr(image, "image_url", "") or ""),
                    "image_alt": str(getattr(image, "alt_text", "") or getattr(variant.product, "name", "") or ""),
                    "price": _safe_decimal(getattr(variant, "price", Decimal("0.00"))),
                    "compare_price": _safe_decimal(getattr(variant, "compare_price", None), default="0.00")
                    if getattr(variant, "compare_price", None) not in (None, "")
                    else None,
                    "quantity": max(1, int(getattr(order_item, "quantity", 1) or 1)),
                }
            )

        if not eligible_snapshots:
            return "reorder-lite-unavailable", None

        prefill = self._profile_and_address_prefill(tenant_id=tenant_id, customer_id=customer_id, email=email)
        tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
        if tenant is None:
            return "reorder-lite-unavailable", None

        with transaction.atomic():
            session = self._get_reusable_open_session(tenant_id=tenant_id)
            if session is None:
                session = self.session_model._default_manager.create(
                    tenant=tenant,
                    status=self.session_model.Status.OPEN,
                    shipping_methods=_default_shipping_methods(),
                    shipping_method_selected="standard",
                    payment_methods=_default_payment_methods(),
                    payment_method_selected="credit_card",
                    discount_total=Decimal("0.00"),
                    accept_terms=False,
                )
            else:
                self.item_model._default_manager.filter(checkout_session=session).delete()

            session.first_name = prefill.get("first_name", "")
            session.last_name = prefill.get("last_name", "")
            session.email = prefill.get("email", "")
            session.phone = prefill.get("phone", "")
            session.address_line_1 = prefill.get("address_line_1", "")
            session.address_line_2 = prefill.get("address_line_2", "")
            session.city = prefill.get("city", "")
            session.state = prefill.get("state", "")
            session.zip_code = prefill.get("zip_code", "")
            session.shipping_methods = _default_shipping_methods()
            session.shipping_method_selected = "standard"
            session.payment_methods = _default_payment_methods()
            session.payment_method_selected = "credit_card"
            session.discount_total = Decimal("0.00")
            session.accept_terms = False

            for index, snapshot in enumerate(eligible_snapshots, start=1):
                self.item_model._default_manager.create(
                    checkout_session=session,
                    title=str(snapshot["title"]),
                    subtitle=str(snapshot["subtitle"]),
                    meta=str(snapshot["meta"]),
                    variant_sku=str(snapshot["variant_sku"]),
                    image_url=str(snapshot["image_url"]),
                    image_alt=str(snapshot["image_alt"]),
                    price=snapshot["price"],
                    compare_price=snapshot["compare_price"],
                    quantity=int(snapshot["quantity"]),
                    quantity_readonly=True,
                    sort_order=index,
                )

            self._recalculate_session_totals(session=session)
            session.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state",
                    "zip_code",
                    "shipping_methods",
                    "shipping_method_selected",
                    "payment_methods",
                    "payment_method_selected",
                    "subtotal",
                    "shipping_total",
                    "discount_total",
                    "grand_total",
                    "installments_summary",
                    "installments_selected",
                    "installments_options",
                    "accept_terms",
                    "updated_at",
                ]
            )

        result = "reorder-lite-partial" if ineligible_count else "reorder-lite-ready"
        return result, str(session.session_key)


@dataclass
class CheckoutReorderCommandService:
    repository: CheckoutReorderRepository

    def bootstrap_from_order(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> tuple[str, str | None]:
        if not tenant_id:
            logger.warning(
                "checkout.reorder.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "order_number": str(order_number or "").lstrip("#"),
                },
            )
            return "reorder-lite-unavailable", None
        return self.repository.bootstrap_from_order(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=email,
            order_number=order_number,
        )


checkout_reorder_commands = CheckoutReorderCommandService(
    repository=DjangoOrmCheckoutReorderRepository(),
)
