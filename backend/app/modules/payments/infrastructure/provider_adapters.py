from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from app.modules.payments.application.gateway_bootstrap_commands import GatewayBootstrapContract
from app.modules.payments.domain.provider_rollout import decide_provider_rollout


def _string(value: object) -> str:
    return str(value or "").strip()


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _normalize_title(value: object, *, fallback: str) -> str:
    normalized = _string(value)
    return normalized[:120] if normalized else fallback


def _money_to_cents(value: object) -> int:
    try:
        decimal_value = Decimal(str(value or "0"))
    except Exception:
        decimal_value = Decimal("0")
    cents = (decimal_value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(int(cents), 0)


def _payment_method_list(payment_method_code: str) -> list[str]:
    normalized = _string(payment_method_code).lower()
    if normalized in {"credit_card", "pix", "boleto"}:
        return [normalized]
    return ["credit_card"]


def _payment_settings_payload(payment_method_code: str) -> dict[str, object]:
    accepted_payment_methods = _payment_method_list(payment_method_code)
    settings: dict[str, object] = {
        "accepted_payment_methods": accepted_payment_methods,
    }
    if "pix" in accepted_payment_methods:
        settings["pix_settings"] = {
            "expires_in": 30,
        }
    if "boleto" in accepted_payment_methods:
        settings["boleto_settings"] = {
            "instructions": "Pagamento de teste Hubx Market.",
            "due_at": None,
        }
    if "credit_card" in accepted_payment_methods:
        settings["credit_card_settings"] = {
            "installments_setup": {
                "interest_type": "simple",
                "max_installments": 1,
            }
        }
    return settings


def _extract_response_value(payload: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@dataclass(frozen=True)
class ProviderIntentResponse:
    provider_code: str
    provider_label: str
    external_reference: str
    action_url: str
    payload_snapshot: dict[str, object]


@dataclass(frozen=True)
class RefundProviderContract:
    tenant_id: int
    refund_key: str
    idempotency_key: str
    provider_code: str
    external_reference: str
    amount: str
    currency_code: str
    reason_code: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class RefundProviderResponse:
    provider_code: str
    provider_refund_reference: str
    status: str
    payload_snapshot: dict[str, object]


class ProviderAdapterError(RuntimeError):
    pass


class ProviderAdapterLite:
    def create_intent(self, *, contract: GatewayBootstrapContract, attempt=None) -> ProviderIntentResponse:
        normalized_provider = _string(contract.provider_code) or "payment"
        normalized_label = _string(contract.provider_label) or "Gateway externo"
        external_reference = f"ext-{_string(contract.provider_request_key)}"
        action_url = (
            f"https://payments.hubx.local/{normalized_provider}/pay/"
            f"{_string(contract.provider_request_key)}"
        )
        payload_snapshot = {
            "provider_code": normalized_provider,
            "provider_label": normalized_label,
            "provider_request_key": contract.provider_request_key,
            "payment_attempt_key": contract.payment_attempt_key,
            "order_number": contract.order_number,
            "amount": contract.amount,
            "currency_code": contract.currency_code,
            "customer_name": contract.customer_name,
            "customer_email": contract.customer_email,
            "metadata": dict(contract.metadata),
        }
        return ProviderIntentResponse(
            provider_code=normalized_provider,
            provider_label=normalized_label,
            external_reference=external_reference,
            action_url=action_url,
            payload_snapshot=payload_snapshot,
        )

    def create_refund(self, *, contract: RefundProviderContract) -> RefundProviderResponse:
        normalized_provider = _string(contract.provider_code) or "payment"
        provider_refund_reference = f"refund-{_string(contract.refund_key)}"
        payload_snapshot = {
            "provider_code": normalized_provider,
            "refund_key": contract.refund_key,
            "idempotency_key": contract.idempotency_key,
            "external_reference": contract.external_reference,
            "amount": contract.amount,
            "currency_code": contract.currency_code,
            "reason_code": contract.reason_code,
            "metadata": dict(contract.metadata),
            "provider_call": "lite",
        }
        return RefundProviderResponse(
            provider_code=normalized_provider,
            provider_refund_reference=provider_refund_reference,
            status="accepted",
            payload_snapshot=payload_snapshot,
        )


class PagarmeProviderAdapter:
    provider_code = "pagarme"
    provider_label = "Pagar.me"

    def create_intent(self, *, contract: GatewayBootstrapContract, attempt=None) -> ProviderIntentResponse:
        secret_key = _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
        if not secret_key:
            raise ProviderAdapterError("pagarme-secret-key-missing")

        payload = self._build_payload(contract=contract, attempt=attempt)
        request = Request(
            url=f'{_string(getattr(settings, "PAGARME_API_BASE_URL", "https://api.pagar.me/core/v5")).rstrip("/")}/paymentlinks',
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self._build_auth_header(secret_key),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        timeout = float(getattr(settings, "PAGARME_HTTP_TIMEOUT_SECONDS", 15) or 15)
        try:
            with urlopen(request, timeout=timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise ProviderAdapterError(body or f"pagarme-http-{exc.code}") from exc
        except URLError as exc:
            raise ProviderAdapterError("pagarme-network-unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderAdapterError("pagarme-invalid-json-response") from exc

        action_url = _extract_response_value(
            response_payload,
            "url",
            "short_url",
            "checkout_url",
        )
        if not action_url:
            action_url = _extract_response_value(_dict(response_payload.get("checkout")), "url", "checkout_url")
        if not action_url:
            raise ProviderAdapterError("pagarme-missing-action-url")

        external_reference = _extract_response_value(response_payload, "id", "code", "order_id")
        if not external_reference:
            external_reference = f"pg-{_string(contract.provider_request_key)}"

        return ProviderIntentResponse(
            provider_code=self.provider_code,
            provider_label=self.provider_label,
            external_reference=external_reference,
            action_url=action_url,
            payload_snapshot={
                "request": payload,
                "response": response_payload,
            },
        )

    def create_refund(self, *, contract: RefundProviderContract) -> RefundProviderResponse:
        secret_key = _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
        if not secret_key:
            raise ProviderAdapterError("pagarme-secret-key-missing")
        charge_id = _string(contract.external_reference)
        if not charge_id:
            raise ProviderAdapterError("pagarme-refund-charge-id-missing")

        payload = self._build_refund_payload(contract=contract)
        request = Request(
            url=f'{_string(getattr(settings, "PAGARME_API_BASE_URL", "https://api.pagar.me/core/v5")).rstrip("/")}/charges/{charge_id}',
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self._build_auth_header(secret_key),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Idempotency-Key": _string(contract.idempotency_key),
            },
            method="DELETE",
        )
        timeout = float(getattr(settings, "PAGARME_HTTP_TIMEOUT_SECONDS", 15) or 15)
        try:
            with urlopen(request, timeout=timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise ProviderAdapterError(body or f"pagarme-http-{exc.code}") from exc
        except URLError as exc:
            raise ProviderAdapterError("pagarme-network-unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderAdapterError("pagarme-invalid-json-response") from exc

        provider_refund_reference = _extract_response_value(response_payload, "id", "code", "charge_id")
        if not provider_refund_reference:
            provider_refund_reference = f"pagarme-refund-{charge_id}-{_string(contract.refund_key)}"

        return RefundProviderResponse(
            provider_code=self.provider_code,
            provider_refund_reference=provider_refund_reference,
            status="accepted",
            payload_snapshot={
                "request": payload,
                "response": response_payload,
            },
        )

    def _build_auth_header(self, secret_key: str) -> str:
        token = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def _build_payload(self, *, contract: GatewayBootstrapContract, attempt=None) -> dict[str, object]:
        payment_method_code = getattr(attempt, "payment_method_code", "")
        order = getattr(attempt, "order", None)
        item_names = []
        if order is not None:
            for item in list(getattr(order, "items", []).all())[:3]:
                item_names.append(_normalize_title(getattr(item, "title", ""), fallback="Item"))
        summary = ", ".join(item_names) if item_names else f"Pedido #{contract.order_number}"
        total_cents = _money_to_cents(contract.amount)

        return {
            "type": "order",
            "name": f"Pedido #{contract.order_number}",
            "order_code": contract.order_number,
            "max_paid_sessions": 1,
            "max_sessions": 1,
            "payment_settings": _payment_settings_payload(str(payment_method_code or "")),
            "cart_settings": {
                "items": [
                    {
                        "name": _normalize_title(summary, fallback=f"Pedido #{contract.order_number}"),
                        "description": f"Pagamento do pedido #{contract.order_number}",
                        "amount": total_cents,
                        "default_quantity": 1,
                    }
                ],
            },
        }

    def _build_refund_payload(self, *, contract: RefundProviderContract) -> dict[str, object]:
        payload: dict[str, object] = {}
        amount_cents = _money_to_cents(contract.amount)
        if amount_cents > 0:
            payload["amount"] = amount_cents
        return payload


def get_provider_adapter(*, provider_code: str, tenant=None):
    normalized_provider = _string(provider_code).lower()
    rollout = decide_provider_rollout(provider_code=normalized_provider, tenant=tenant)
    if (
        normalized_provider == "pagarme"
        and rollout.allow_real_provider
        and _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
    ):
        return PagarmeProviderAdapter()
    return ProviderAdapterLite()
