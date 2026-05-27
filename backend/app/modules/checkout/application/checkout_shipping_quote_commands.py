from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.shipping.application.shipping_quote_queries import shipping_quote_queries


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00"))
    except Exception:
        return Decimal("0.00")


class DjangoOrmCheckoutShippingQuoteRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout.models import CheckoutSession
        except Exception:
            self.session_model = None
            return
        self.session_model = CheckoutSession

    def get_open_session(self, *, tenant_id: int | str | None, session_key: object):
        if self.session_model is None or not tenant_id or not _string(session_key):
            return None
        return self.session_model._default_manager.filter(
            tenant_id=tenant_id,
            session_key=_string(session_key, limit=80),
            status=self.session_model.Status.OPEN,
        ).first()

    def save_quote(self, *, session, quote_result) -> None:
        session.shipping_methods = quote_result.checkout_methods()
        if quote_result.ready and session.shipping_methods:
            selected = session.shipping_methods[0]
            session.shipping_method_selected = str(selected.get("value") or "")
            raw_price = str(selected.get("price") or "0").replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            session.shipping_total = _decimal(raw_price)
            session.grand_total = _decimal(session.subtotal) + _decimal(session.shipping_total) - _decimal(session.discount_total)
        else:
            session.shipping_method_selected = ""
            session.shipping_total = Decimal("0.00")
            session.grand_total = _decimal(session.subtotal) - _decimal(session.discount_total)
        session.save(update_fields=("shipping_methods", "shipping_method_selected", "shipping_total", "grand_total", "updated_at"))


@dataclass
class CheckoutShippingQuoteCommandService:
    repository: DjangoOrmCheckoutShippingQuoteRepository

    def refresh_quote(
        self,
        *,
        tenant_id: int | str | None,
        session_key: object,
        zip_code: object = "",
    ) -> dict[str, object]:
        session = self.repository.get_open_session(tenant_id=tenant_id, session_key=session_key)
        if session is None:
            return {"result": "checkout-shipping-quote-unavailable", "ready": False, "message": "Checkout aberto não encontrado."}
        resolved_zip = _string(zip_code or getattr(session, "zip_code", ""), limit=32)
        quote = shipping_quote_queries.get_quote(
            tenant_id=tenant_id,
            zip_code=resolved_zip,
            subtotal=getattr(session, "subtotal", Decimal("0.00")),
        )
        self.repository.save_quote(session=session, quote_result=quote)
        return {
            "result": "checkout-shipping-quote-updated" if quote.ready else "checkout-shipping-quote-failed",
            "ready": quote.ready,
            "message": quote.message,
            "failure_code": quote.failure_code,
            "shipping_methods": quote.checkout_methods(),
        }


checkout_shipping_quote_commands = CheckoutShippingQuoteCommandService(
    repository=DjangoOrmCheckoutShippingQuoteRepository(),
)
