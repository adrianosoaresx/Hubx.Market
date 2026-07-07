from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedPaymentWebhook:
    event_type: str
    tenant_slug: str
    tenant_subdomain: str
    order_number: str
    payment_reference: str
    payment_source_label: str


def _string(value: object) -> str:
    return str(value or "").strip()


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _extract_pagarme_metadata(data: dict[str, object]) -> dict[str, object]:
    direct_metadata = _dict(data.get("metadata"))
    if direct_metadata:
        return direct_metadata
    for charge in _list(data.get("charges")):
        charge_metadata = _dict(_dict(charge).get("metadata"))
        if charge_metadata:
            return charge_metadata
    return {}


def _extract_pagarme_reference(data: dict[str, object]) -> str:
    for charge in _list(data.get("charges")):
        normalized_charge = _dict(charge)
        charge_reference = _string(normalized_charge.get("id") or normalized_charge.get("code"))
        if charge_reference:
            return charge_reference
    direct_reference = _string(data.get("id") or data.get("code"))
    if direct_reference:
        return direct_reference
    return ""


def _normalize_generic(payload: dict[str, object]) -> NormalizedPaymentWebhook | None:
    event_type = _string(payload.get("event_type") or payload.get("event")).lower()
    if not event_type:
        return None
    return NormalizedPaymentWebhook(
        event_type=event_type,
        tenant_slug=_string(payload.get("tenant_slug")),
        tenant_subdomain=_string(payload.get("tenant_subdomain")),
        order_number=_string(payload.get("order_number")),
        payment_reference=_string(payload.get("payment_reference") or payload.get("transaction_id")),
        payment_source_label=_string(payload.get("payment_source_label") or payload.get("provider") or "Gateway externo"),
    )


def _normalize_pagarme(payload: dict[str, object]) -> NormalizedPaymentWebhook | None:
    provider = _string(payload.get("provider")).lower()
    event_type = _string(payload.get("type") or payload.get("event")).lower()
    if provider != "pagarme" and not event_type.startswith(("charge.", "order.")):
        return None
    if event_type not in {
        "charge.paid",
        "charge.failed",
        "charge.payment_failed",
        "order.paid",
        "order.payment_failed",
    }:
        return None
    data = _dict(payload.get("data"))
    metadata = _extract_pagarme_metadata(data)
    payment_source_label = _string(payload.get("payment_source_label"))
    if not payment_source_label:
        payment_source_label = "Pagar.me"
    return NormalizedPaymentWebhook(
        event_type="payment.paid" if event_type in {"charge.paid", "order.paid"} else "payment.failed",
        tenant_slug=_string(metadata.get("tenant_slug")),
        tenant_subdomain=_string(metadata.get("tenant_subdomain")),
        order_number=_string(metadata.get("order_number")),
        payment_reference=_extract_pagarme_reference(data),
        payment_source_label=payment_source_label,
    )


def _parse_hubx_external_reference(value: object) -> tuple[str, str]:
    normalized = _string(value)
    if not normalized.startswith("hubx-market:"):
        return "", ""
    parts = normalized.split(":", 3)
    if len(parts) < 3:
        return "", ""
    tenant_subdomain = _string(parts[1])
    order_number = _string(parts[2])
    return tenant_subdomain, order_number


def _normalize_asaas(payload: dict[str, object]) -> NormalizedPaymentWebhook | None:
    provider = _string(payload.get("provider")).lower()
    event_type = _string(payload.get("event") or payload.get("type")).upper()
    if provider != "asaas" and not event_type.startswith("PAYMENT_"):
        return None
    paid_events = {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"}
    failed_events = {"PAYMENT_OVERDUE", "PAYMENT_DELETED", "PAYMENT_REFUNDED", "PAYMENT_CHARGEBACK_REQUESTED"}
    if event_type not in paid_events | failed_events:
        return None
    payment = _dict(payload.get("payment"))
    tenant_subdomain, order_number = _parse_hubx_external_reference(payment.get("externalReference"))
    return NormalizedPaymentWebhook(
        event_type="payment.paid" if event_type in paid_events else "payment.failed",
        tenant_slug="",
        tenant_subdomain=tenant_subdomain,
        order_number=order_number,
        payment_reference=_string(payment.get("id")),
        payment_source_label=_string(payload.get("payment_source_label") or "Asaas"),
    )


def _normalize_stripe(payload: dict[str, object]) -> NormalizedPaymentWebhook | None:
    provider = _string(payload.get("provider")).lower()
    event_type = _string(payload.get("type") or payload.get("event")).lower()
    if provider != "stripe" and not event_type.startswith("payment_intent."):
        return None
    if event_type not in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
        return None
    data = _dict(payload.get("data"))
    data_object = _dict(data.get("object"))
    metadata = _dict(data_object.get("metadata"))
    return NormalizedPaymentWebhook(
        event_type="payment.paid" if event_type == "payment_intent.succeeded" else "payment.failed",
        tenant_slug=_string(metadata.get("tenant_slug")),
        tenant_subdomain=_string(metadata.get("tenant_subdomain")),
        order_number=_string(metadata.get("order_number")),
        payment_reference=_string(data_object.get("id")),
        payment_source_label=_string(payload.get("payment_source_label") or payload.get("provider") or "Gateway Stripe"),
    )


def normalize_payment_webhook(payload: dict[str, object]) -> NormalizedPaymentWebhook | None:
    for normalizer in (_normalize_asaas, _normalize_generic, _normalize_pagarme, _normalize_stripe):
        normalized = normalizer(payload)
        if normalized is not None:
            return normalized
    return None


def looks_like_asaas_webhook(payload: dict[str, object]) -> bool:
    provider = _string(payload.get("provider")).lower()
    event_type = _string(payload.get("event") or payload.get("type")).upper()
    return provider == "asaas" or event_type.startswith("PAYMENT_")


def looks_like_pagarme_webhook(payload: dict[str, object]) -> bool:
    provider = _string(payload.get("provider")).lower()
    event_type = _string(payload.get("type") or payload.get("event")).lower()
    return provider == "pagarme" or event_type.startswith(("charge.", "order."))
