from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from app.modules.payments.application.gateway_bootstrap_commands import GatewayBootstrapContract
from app.modules.payments.domain.provider_rollout import decide_provider_rollout
from app.modules.subscriptions.application.commercial_terms import get_tenant_commercial_terms


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


def _money_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _payment_method_list(payment_method_code: str) -> list[str]:
    normalized = _string(payment_method_code).lower()
    if normalized in {"credit_card", "pix", "boleto"}:
        return [normalized]
    return ["credit_card"]


def _asaas_billing_type(payment_method_code: str) -> str:
    normalized = _string(payment_method_code).lower()
    if normalized == "pix":
        return "PIX"
    if normalized == "boleto":
        return "BOLETO"
    if normalized == "credit_card":
        return "CREDIT_CARD"
    return "UNDEFINED"


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


def _safe_external_reference(contract: GatewayBootstrapContract) -> str:
    tenant = _string(contract.metadata.get("tenant_subdomain") or contract.metadata.get("tenant_slug"))
    order_number = _string(contract.order_number)
    if tenant and order_number:
        return f"hubx-market:{tenant}:{order_number}"[:120]
    return _string(contract.provider_request_key)[:120]


def _extract_response_value(payload: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _asaas_platform_split_payload(*, attempt=None) -> list[dict[str, object]]:
    split_enabled = bool(getattr(settings, "PAYMENTS_HUBX_SPLIT_ENABLED", False))
    wallet_id = _string(getattr(settings, "ASAAS_HUBX_WALLET_ID", ""))
    tenant_id = getattr(attempt, "tenant_id", None)
    if not split_enabled or not wallet_id or not tenant_id:
        return []
    terms = get_tenant_commercial_terms(tenant_id=tenant_id)
    if not terms.has_platform_fee:
        return []
    return [
        {
            "walletId": wallet_id,
            "percentualValue": terms.platform_fee_percent,
        }
    ]


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


@dataclass(frozen=True)
class PlatformBillingCustomerContract:
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    contact_email: str


@dataclass(frozen=True)
class PlatformBillingCustomerResponse:
    provider_code: str
    provider_label: str
    customer_reference: str
    payload_snapshot: dict[str, object]


@dataclass(frozen=True)
class PlatformBillingChargeContract:
    tenant_id: int
    tenant_slug: str
    ledger_key: str
    customer_reference: str
    amount: str
    currency_code: str
    due_date: str
    description: str
    external_reference: str
    billing_method_reference: str = ""
    remote_ip: str = ""


@dataclass(frozen=True)
class PlatformBillingChargeResponse:
    provider_code: str
    provider_label: str
    payment_reference: str
    action_url: str
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

    def create_platform_billing_customer(
        self,
        *,
        contract: PlatformBillingCustomerContract,
    ) -> PlatformBillingCustomerResponse:
        reference = f"lite-customer-{contract.tenant_id}"
        return PlatformBillingCustomerResponse(
            provider_code="lite",
            provider_label="Gateway externo",
            customer_reference=reference,
            payload_snapshot={
                "provider_call": "lite",
                "tenant_id": contract.tenant_id,
                "tenant_slug": contract.tenant_slug,
                "tenant_name": contract.tenant_name,
                "contact_email": contract.contact_email,
            },
        )

    def create_platform_billing_charge(
        self,
        *,
        contract: PlatformBillingChargeContract,
    ) -> PlatformBillingChargeResponse:
        reference = f"lite-charge-{contract.ledger_key}"
        return PlatformBillingChargeResponse(
            provider_code="lite",
            provider_label="Gateway externo",
            payment_reference=reference,
            action_url=f"https://payments.hubx.local/platform-fees/{contract.ledger_key}",
            status="pending",
            payload_snapshot={
                "provider_call": "lite",
                "ledger_key": contract.ledger_key,
                "customer_reference": contract.customer_reference,
                "amount": contract.amount,
                "external_reference": contract.external_reference,
            },
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


class AsaasProviderAdapter:
    provider_code = "asaas"
    provider_label = "Asaas"

    def create_intent(self, *, contract: GatewayBootstrapContract, attempt=None) -> ProviderIntentResponse:
        api_key = _string(getattr(settings, "ASAAS_API_KEY", ""))
        if not api_key:
            raise ProviderAdapterError("asaas-api-key-missing")

        customer_payload = self._build_customer_payload(contract=contract)
        customer_response = self._request("POST", "/customers", customer_payload)
        customer_id = _extract_response_value(customer_response, "id")
        if not customer_id:
            raise ProviderAdapterError("asaas-missing-customer-id")

        payment_payload = self._build_payment_payload(
            contract=contract,
            attempt=attempt,
            customer_id=customer_id,
        )
        payment_response = self._request("POST", "/payments", payment_payload)
        action_url = _extract_response_value(payment_response, "invoiceUrl", "bankSlipUrl", "transactionReceiptUrl")
        if not action_url:
            raise ProviderAdapterError("asaas-missing-action-url")

        external_reference = _extract_response_value(payment_response, "id")
        if not external_reference:
            external_reference = _safe_external_reference(contract)

        return ProviderIntentResponse(
            provider_code=self.provider_code,
            provider_label=self.provider_label,
            external_reference=external_reference,
            action_url=action_url,
            payload_snapshot={
                "request": {
                    "customer": _json_ready(customer_payload),
                    "payment": _json_ready(payment_payload),
                },
                "response": {
                    "customer": _json_ready(customer_response),
                    "payment": _json_ready(payment_response),
                },
            },
        )

    def create_refund(self, *, contract: RefundProviderContract) -> RefundProviderResponse:
        api_key = _string(getattr(settings, "ASAAS_API_KEY", ""))
        if not api_key:
            raise ProviderAdapterError("asaas-api-key-missing")
        payment_id = _string(contract.external_reference)
        if not payment_id:
            raise ProviderAdapterError("asaas-refund-payment-id-missing")

        payload = self._build_refund_payload(contract=contract)
        response_payload = self._request("POST", f"/payments/{payment_id}/refund", payload)
        provider_refund_reference = _extract_response_value(
            response_payload,
            "id",
            "refundId",
            "paymentId",
        )
        if not provider_refund_reference:
            provider_refund_reference = f"asaas-refund-{payment_id}-{_string(contract.refund_key)}"

        return RefundProviderResponse(
            provider_code=self.provider_code,
            provider_refund_reference=provider_refund_reference,
            status=self._refund_response_status(response_payload),
            payload_snapshot={
                "request": _json_ready(payload),
                "response": _json_ready(response_payload),
            },
        )

    def create_platform_billing_customer(
        self,
        *,
        contract: PlatformBillingCustomerContract,
    ) -> PlatformBillingCustomerResponse:
        api_key = _string(getattr(settings, "ASAAS_API_KEY", ""))
        if not api_key:
            raise ProviderAdapterError("asaas-api-key-missing")
        payload = self._build_platform_billing_customer_payload(contract=contract)
        response_payload = self._request("POST", "/customers", payload)
        customer_reference = _extract_response_value(response_payload, "id")
        if not customer_reference:
            raise ProviderAdapterError("asaas-missing-customer-id")
        return PlatformBillingCustomerResponse(
            provider_code=self.provider_code,
            provider_label=self.provider_label,
            customer_reference=customer_reference,
            payload_snapshot={
                "request": _json_ready(payload),
                "response": _json_ready(response_payload),
            },
        )

    def create_platform_billing_charge(
        self,
        *,
        contract: PlatformBillingChargeContract,
    ) -> PlatformBillingChargeResponse:
        api_key = _string(getattr(settings, "ASAAS_API_KEY", ""))
        if not api_key:
            raise ProviderAdapterError("asaas-api-key-missing")
        if not _string(contract.customer_reference):
            raise ProviderAdapterError("asaas-customer-reference-missing")
        payload = self._build_platform_billing_charge_payload(contract=contract)
        response_payload = self._request("POST", "/payments", payload)
        payment_reference = _extract_response_value(response_payload, "id")
        if not payment_reference:
            raise ProviderAdapterError("asaas-missing-payment-id")
        action_url = _extract_response_value(response_payload, "invoiceUrl", "bankSlipUrl", "transactionReceiptUrl")
        return PlatformBillingChargeResponse(
            provider_code=self.provider_code,
            provider_label=self.provider_label,
            payment_reference=payment_reference,
            action_url=action_url,
            status=_extract_response_value(response_payload, "status").lower() or "pending",
            payload_snapshot={
                "request": _redacted_json_ready(payload),
                "response": _redacted_json_ready(response_payload),
            },
        )

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        body = json.dumps(_compact(_json_ready(payload or {}))).encode("utf-8")
        request = Request(
            url=f'{_string(getattr(settings, "ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3")).rstrip("/")}{path}',
            data=body if method != "GET" else None,
            headers={
                "access_token": _string(getattr(settings, "ASAAS_API_KEY", "")),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "hubx.market/0.1",
            },
            method=method,
        )
        timeout = float(getattr(settings, "ASAAS_HTTP_TIMEOUT_SECONDS", 15) or 15)
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="ignore")
            raise ProviderAdapterError(body_text or f"asaas-http-{exc.code}") from exc
        except URLError as exc:
            raise ProviderAdapterError("asaas-network-unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderAdapterError("asaas-invalid-json-response") from exc

    def _build_customer_payload(self, *, contract: GatewayBootstrapContract) -> dict[str, object]:
        fallback_name = f"Cliente pedido {contract.order_number}" if _string(contract.order_number) else "Cliente Hubx Market"
        return {
            "name": _normalize_title(contract.customer_name, fallback=fallback_name),
            "email": _string(contract.customer_email),
            "externalReference": _safe_external_reference(contract),
        }

    def _build_platform_billing_customer_payload(
        self,
        *,
        contract: PlatformBillingCustomerContract,
    ) -> dict[str, object]:
        return {
            "name": _normalize_title(contract.tenant_name, fallback=f"Tenant {contract.tenant_id}"),
            "email": _string(contract.contact_email),
            "externalReference": f"hubx-platform-billing:{contract.tenant_id}:{_string(contract.tenant_slug)}"[:120],
        }

    def _build_payment_payload(self, *, contract: GatewayBootstrapContract, attempt=None, customer_id: str) -> dict[str, object]:
        payment_method_code = getattr(attempt, "payment_method_code", "")
        due_date = timezone.localdate()
        if _string(payment_method_code).lower() == "boleto":
            due_date = due_date + timedelta(days=3)
        payload = {
            "customer": customer_id,
            "billingType": _asaas_billing_type(str(payment_method_code or "")),
            "value": Decimal(str(contract.amount or "0.00")),
            "dueDate": due_date.isoformat(),
            "description": _normalize_title(f"Pedido #{contract.order_number} - Hubx Market", fallback="Pedido Hubx Market"),
            "externalReference": _safe_external_reference(contract),
        }
        splits = _asaas_platform_split_payload(attempt=attempt)
        if splits:
            payload["splits"] = splits
        return payload

    def _build_platform_billing_charge_payload(
        self,
        *,
        contract: PlatformBillingChargeContract,
    ) -> dict[str, object]:
        payload = {
            "customer": _string(contract.customer_reference),
            "billingType": "CREDIT_CARD",
            "value": Decimal(str(contract.amount or "0.00")),
            "dueDate": _string(contract.due_date),
            "description": _normalize_title(contract.description, fallback="Complemento mensal Hubx Market"),
            "externalReference": _string(contract.external_reference)[:120],
        }
        billing_method_reference = _string(contract.billing_method_reference)
        remote_ip = _string(contract.remote_ip)
        if billing_method_reference:
            payload["creditCardToken"] = billing_method_reference
        if remote_ip:
            payload["remoteIp"] = remote_ip
        return payload

    def _build_refund_payload(self, *, contract: RefundProviderContract) -> dict[str, object]:
        payload: dict[str, object] = {
            "description": _normalize_title(
                contract.reason_code or f"Refund {contract.refund_key}",
                fallback="Refund Hubx Market",
            ),
        }
        amount = _money_decimal(contract.amount)
        if amount > Decimal("0.00"):
            payload["value"] = amount
        return payload

    def _refund_response_status(self, payload: dict[str, object]) -> str:
        status = _extract_response_value(payload, "status", "refundStatus").upper()
        if status in {"DONE", "REFUNDED", "SUCCEEDED", "SUCCESS"}:
            return "succeeded"
        if status in {"CANCELLED", "CANCELED", "FAILED", "ERROR"}:
            return "failed"
        return "accepted"


def _compact(data: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in data.items() if value not in ("", None, [])}


def _json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


SENSITIVE_PAYLOAD_KEYS = {
    "accessToken",
    "apiKey",
    "authorization",
    "cardNumber",
    "ccv",
    "creditCard",
    "creditCardHolderInfo",
    "creditCardToken",
    "cvv",
    "number",
}


def _redacted_json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key) in SENSITIVE_PAYLOAD_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redacted_json_ready(item)
        return redacted
    if isinstance(value, list):
        return [_redacted_json_ready(item) for item in value]
    return value


def get_provider_adapter(*, provider_code: str, tenant=None):
    normalized_provider = _string(provider_code).lower()
    rollout = decide_provider_rollout(provider_code=normalized_provider, tenant=tenant)
    if (
        normalized_provider == "asaas"
        and rollout.allow_real_provider
        and _string(getattr(settings, "ASAAS_API_KEY", ""))
    ):
        return AsaasProviderAdapter()
    if (
        normalized_provider == "pagarme"
        and rollout.allow_real_provider
        and _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
    ):
        return PagarmeProviderAdapter()
    return ProviderAdapterLite()
