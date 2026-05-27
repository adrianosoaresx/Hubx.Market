from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _money(value: object, *, default: str = "24.90") -> Decimal:
    try:
        return Decimal(str(value or default)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(default).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ShippingQuoteOption:
    value: str
    label: str
    description: str
    price: str
    carrier: str
    service_code: str
    estimated_days: int
    provider_reference: str = ""

    def as_checkout_method(self) -> dict[str, str]:
        return {
            "value": self.value,
            "label": self.label,
            "description": self.description,
            "price": self.price,
            "carrier": self.carrier,
            "service_code": self.service_code,
            "estimated_days": str(self.estimated_days),
            "provider_reference": self.provider_reference,
        }


@dataclass(frozen=True)
class ShippingQuoteResult:
    result: str
    ready: bool
    tenant_id: int | str | None
    zip_code: str
    options: tuple[ShippingQuoteOption, ...]
    message: str
    failure_code: str = ""

    def checkout_methods(self) -> list[dict[str, str]]:
        return [option.as_checkout_method() for option in self.options]


@dataclass
class ManualShippingQuoteProvider:
    def quote(
        self,
        *,
        tenant_id: int | str | None,
        zip_code: object,
        subtotal: object = "0.00",
        weight_grams: object = 0,
    ) -> ShippingQuoteResult:
        normalized_zip = _string(zip_code, limit=32)
        if not tenant_id:
            return ShippingQuoteResult(
                result="shipping-quote-tenant-required",
                ready=False,
                tenant_id=tenant_id,
                zip_code=normalized_zip,
                options=(),
                message="Tenant não resolvido para cotação.",
                failure_code="tenant-missing",
            )
        if len("".join(character for character in normalized_zip if character.isdigit())) < 8:
            return ShippingQuoteResult(
                result="shipping-quote-address-required",
                ready=False,
                tenant_id=tenant_id,
                zip_code=normalized_zip,
                options=(),
                message="Informe um CEP válido para calcular o frete.",
                failure_code="zip-code-invalid",
            )
        base = _money("24.90")
        if _money(subtotal, default="0.00") >= Decimal("300.00"):
            base = Decimal("0.00")
        options = (
            ShippingQuoteOption(
                value="standard",
                label="Entrega padrão",
                description="Receba em até 5 dias úteis após confirmação.",
                price=self._format_price(base),
                carrier="Manual",
                service_code="standard",
                estimated_days=5,
                provider_reference="manual-standard",
            ),
            ShippingQuoteOption(
                value="express",
                label="Entrega expressa",
                description="Receba em até 2 dias úteis após confirmação.",
                price=self._format_price(base + Decimal("15.00")),
                carrier="Manual",
                service_code="express",
                estimated_days=2,
                provider_reference="manual-express",
            ),
        )
        return ShippingQuoteResult(
            result="shipping-quote-ready",
            ready=True,
            tenant_id=tenant_id,
            zip_code=normalized_zip,
            options=options,
            message="Cotação de frete disponível.",
        )

    def _format_price(self, value: Decimal) -> str:
        return f"R$ {value:.2f}".replace(".", ",")


@dataclass
class ShippingQuoteQueryService:
    provider: ManualShippingQuoteProvider

    def get_quote(
        self,
        *,
        tenant_id: int | str | None,
        zip_code: object,
        subtotal: object = "0.00",
        weight_grams: object = 0,
    ) -> ShippingQuoteResult:
        return self.provider.quote(
            tenant_id=tenant_id,
            zip_code=zip_code,
            subtotal=subtotal,
            weight_grams=weight_grams,
        )


shipping_quote_queries = ShippingQuoteQueryService(provider=ManualShippingQuoteProvider())
