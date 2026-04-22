from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from django.db import connection, transaction


def _safe_decimal(value: object, default: str = "0.00") -> Decimal:
    try:
        return Decimal(str(value or default))
    except Exception:
        return Decimal(default)


def _default_shipping_methods() -> list[dict[str, str]]:
    return [
        {
            "value": "standard",
            "label": "Entrega padrão",
            "description": "Receba em até 5 dias úteis.",
            "price": "R$ 24,90",
        },
        {
            "value": "express",
            "label": "Entrega expressa",
            "description": "Receba em até 2 dias úteis.",
            "price": "R$ 39,90",
        },
    ]


def _default_payment_methods() -> list[dict[str, str]]:
    return [
        {
            "value": "credit_card",
            "label": "Cartão de crédito",
            "description": "Pagamento imediato com confirmação online.",
            "meta": "3x sem juros",
        },
        {
            "value": "pix",
            "label": "PIX",
            "description": "Aprovação rápida após a confirmação do pagamento.",
            "meta": "5% de desconto no pagamento à vista",
        },
    ]


def _installments_summary(total: Decimal) -> tuple[str, str, list[dict[str, str]]]:
    third = (total / Decimal("3")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (
        f"3x de R$ {third:.2f}".replace(".", ",") + " sem juros",
        "3x",
        [
            {"value": "1x", "label": f"1x de R$ {total:.2f}".replace(".", ",")},
            {"value": "2x", "label": f"2x de R$ {(total / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}".replace(".", ",")},
            {"value": "3x", "label": f"3x de R$ {third:.2f}".replace(".", ",")},
        ],
    )


def _shipping_total_from_selected_method(session) -> Decimal:
    selected_value = str(getattr(session, "shipping_method_selected", "") or "").strip()
    methods = list(getattr(session, "shipping_methods", []) or [])
    selected = next((method for method in methods if str(method.get("value", "") or "").strip() == selected_value), None)
    if not selected:
        return _safe_decimal(getattr(session, "shipping_total", Decimal("0.00")))
    raw_price = str(selected.get("price", "") or "").replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    return _safe_decimal(raw_price, default="0.00")


class CheckoutActivationRepository(Protocol):
    def activate_from_product(self, product: dict[str, object], *, quantity: int = 1) -> str | None:
        ...


class DjangoOrmCheckoutActivationRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout import models as checkout_models
            from app.modules.tenants import models as tenant_models
            from app.modules.accounts import models as account_models
            from app.modules.customers import models as customer_models
        except Exception:
            self.session_model = None
            self.item_model = None
            self.tenant_model = None
            self.account_profile_model = None
            self.customer_model = None
            self.customer_address_model = None
            return

        self.session_model = getattr(checkout_models, "CheckoutSession", None)
        self.item_model = getattr(checkout_models, "CheckoutSessionItem", None)
        self.tenant_model = getattr(tenant_models, "Tenant", None)
        self.account_profile_model = getattr(account_models, "AccountProfile", None)
        self.customer_model = getattr(customer_models, "Customer", None)
        self.customer_address_model = getattr(customer_models, "CustomerAddress", None)

    def is_ready(self) -> bool:
        try:
            table_names = {
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

    def _profile_and_address_prefill(self, *, tenant_id: int) -> dict[str, str]:
        if not self.account_profile_model:
            return {}
        try:
            profile = (
                self.account_profile_model._default_manager.select_related("customer")
                .filter(tenant_id=tenant_id, is_active=True)
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return {}
        if profile is None:
            return {}

        customer = getattr(profile, "customer", None)
        if customer is None and self.customer_model:
            email = str(getattr(profile, "email", "") or "").strip()
            if email:
                try:
                    customer = (
                        self.customer_model._default_manager.filter(tenant_id=tenant_id, email=email)
                        .order_by("-updated_at", "-id")
                        .first()
                    )
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
            "email": str(getattr(profile, "email", "") or ""),
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
                self.session_model._default_manager.filter(
                    tenant_id=tenant_id,
                    status=self.session_model.Status.OPEN,
                )
                .prefetch_related("items")
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None

    def _recalculate_session_totals(self, *, session) -> None:
        items = list(
            self.item_model._default_manager.filter(checkout_session=session).order_by("sort_order", "id")
        )
        subtotal = sum((_safe_decimal(getattr(item, "price", 0)) * int(getattr(item, "quantity", 1) or 1) for item in items), Decimal("0.00"))
        shipping_total = _shipping_total_from_selected_method(session)
        discount_total = _safe_decimal(getattr(session, "discount_total", Decimal("0.00")))
        grand_total = (subtotal + shipping_total - discount_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        installments_summary, installments_selected, installments_options = _installments_summary(grand_total)
        session.subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        session.shipping_total = shipping_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        session.grand_total = grand_total
        session.installments_summary = installments_summary
        session.installments_options = installments_options
        if not any(option["value"] == str(getattr(session, "installments_selected", "") or "") for option in installments_options):
            session.installments_selected = installments_selected

    def activate_from_product(self, product: dict[str, object], *, quantity: int = 1) -> str | None:
        if not self.is_ready():
            return None

        tenant_id = product.get("tenant_id")
        if not tenant_id:
            return None

        tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
        if tenant is None:
            return None

        quantity = max(1, int(quantity or 1))
        price = _safe_decimal(product.get("price"))
        compare_price = _safe_decimal(product.get("compare_price"), default="0.00")
        prefill = self._profile_and_address_prefill(tenant_id=tenant_id)
        variant_sku = str(product.get("sku") or "").strip()

        with transaction.atomic():
            session = self._get_reusable_open_session(tenant_id=tenant_id)
            if session is None:
                shipping_total = Decimal("24.90")
                subtotal = (price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                grand_total = (subtotal + shipping_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                installments_summary, installments_selected, installments_options = _installments_summary(grand_total)
                session = self.session_model._default_manager.create(
                    tenant=tenant,
                    status=self.session_model.Status.OPEN,
                    first_name=prefill.get("first_name", ""),
                    last_name=prefill.get("last_name", ""),
                    email=prefill.get("email", ""),
                    phone=prefill.get("phone", ""),
                    address_line_1=prefill.get("address_line_1", ""),
                    address_line_2=prefill.get("address_line_2", ""),
                    city=prefill.get("city", ""),
                    state=prefill.get("state", ""),
                    zip_code=prefill.get("zip_code", ""),
                    shipping_methods=_default_shipping_methods(),
                    shipping_method_selected="standard",
                    payment_methods=_default_payment_methods(),
                    payment_method_selected="credit_card",
                    subtotal=subtotal,
                    shipping_total=shipping_total,
                    discount_total=Decimal("0.00"),
                    grand_total=grand_total,
                    installments_summary=installments_summary,
                    installments_selected=installments_selected,
                    installments_options=installments_options,
                    accept_terms=False,
                )

            existing_item = next(
                (
                    item
                    for item in getattr(session, "items").all()
                    if str(getattr(item, "variant_sku", "") or "").strip() == variant_sku and variant_sku
                ),
                None,
            )
            if existing_item is not None:
                existing_item.title = str(product.get("name") or "Produto")
                existing_item.subtitle = str(product.get("effective_variant_label") or "")
                existing_item.meta = f"SKU {variant_sku}".strip()
                existing_item.image_url = str(product.get("main_image_url") or "")
                existing_item.image_alt = str(product.get("main_image_alt") or product.get("name") or "")
                existing_item.price = price
                existing_item.compare_price = compare_price if compare_price > 0 else None
                existing_item.quantity = int(getattr(existing_item, "quantity", 1) or 1) + quantity
                existing_item.save(
                    update_fields=[
                        "title",
                        "subtitle",
                        "meta",
                        "image_url",
                        "image_alt",
                        "price",
                        "compare_price",
                        "quantity",
                        "updated_at",
                    ]
                )
            else:
                next_sort = max((int(getattr(item, "sort_order", 0) or 0) for item in getattr(session, "items").all()), default=0) + 1
                self.item_model._default_manager.create(
                    checkout_session=session,
                    title=str(product.get("name") or "Produto"),
                    subtitle=str(product.get("effective_variant_label") or ""),
                    meta=f"SKU {variant_sku}".strip(),
                    variant_sku=variant_sku,
                    image_url=str(product.get("main_image_url") or ""),
                    image_alt=str(product.get("main_image_alt") or product.get("name") or ""),
                    price=price,
                    compare_price=compare_price if compare_price > 0 else None,
                    quantity=quantity,
                    quantity_readonly=True,
                    sort_order=next_sort,
                )

            self._recalculate_session_totals(session=session)
            session.save(
                update_fields=[
                    "subtotal",
                    "shipping_total",
                    "grand_total",
                    "installments_summary",
                    "installments_selected",
                    "installments_options",
                    "updated_at",
                ]
            )
        return str(session.session_key)


@dataclass
class CheckoutActivationCommandService:
    repository: CheckoutActivationRepository

    def activate_from_product(self, product: dict[str, object], *, quantity: int = 1) -> str | None:
        return self.repository.activate_from_product(product, quantity=quantity)


checkout_activation_commands = CheckoutActivationCommandService(
    repository=DjangoOrmCheckoutActivationRepository(),
)
