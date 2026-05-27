import json
from urllib.error import URLError
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test import override_settings

from app.modules.payments.infrastructure.provider_adapters import (
    PagarmeProviderAdapter,
    ProviderAdapterError,
    ProviderAdapterLite,
    RefundProviderContract,
)


class ProviderRefundAdapterTests(SimpleTestCase):
    def _contract(self) -> RefundProviderContract:
        return RefundProviderContract(
            tenant_id=1,
            refund_key="refund-key-1",
            idempotency_key="refund-idem-1",
            provider_code="pagarme",
            external_reference="ch_123",
            amount="120.00",
            currency_code="BRL",
            reason_code="customer-request",
            metadata={"order_number": "1001"},
        )

    def test_lite_refund_adapter_returns_accepted_contract_without_real_provider_call(self):
        response = ProviderAdapterLite().create_refund(contract=self._contract())

        self.assertEqual(response.provider_code, "pagarme")
        self.assertEqual(response.provider_refund_reference, "refund-refund-key-1")
        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.payload_snapshot["provider_call"], "lite")
        self.assertEqual(response.payload_snapshot["external_reference"], "ch_123")
        self.assertEqual(response.payload_snapshot["amount"], "120.00")

    @override_settings(PAGARME_SECRET_KEY="sk_test_refund", PAGARME_API_BASE_URL="https://api.pagar.me/core/v5")
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_pagarme_refund_adapter_calls_charge_cancel_endpoint_conservatively(self, mocked_urlopen):
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.read.return_value = json.dumps({"id": "ch_123", "status": "canceled"}).encode("utf-8")

        response = PagarmeProviderAdapter().create_refund(contract=self._contract())

        request = mocked_urlopen.call_args.args[0]
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.pagar.me/core/v5/charges/ch_123")
        self.assertEqual(request.get_method(), "DELETE")
        self.assertEqual(request_payload["amount"], 12000)
        self.assertEqual(request.headers["Idempotency-key"], "refund-idem-1")
        self.assertEqual(response.provider_code, "pagarme")
        self.assertEqual(response.provider_refund_reference, "ch_123")
        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.payload_snapshot["response"]["status"], "canceled")

    @override_settings(PAGARME_SECRET_KEY="", PAGARME_API_BASE_URL="https://api.pagar.me/core/v5")
    def test_pagarme_refund_adapter_requires_secret_key(self):
        with self.assertRaises(ProviderAdapterError) as context:
            PagarmeProviderAdapter().create_refund(contract=self._contract())

        self.assertEqual(str(context.exception), "pagarme-secret-key-missing")

    @override_settings(PAGARME_SECRET_KEY="sk_test_refund", PAGARME_API_BASE_URL="https://api.pagar.me/core/v5")
    def test_pagarme_refund_adapter_requires_charge_id(self):
        contract = RefundProviderContract(
            tenant_id=1,
            refund_key="refund-key-1",
            idempotency_key="refund-idem-1",
            provider_code="pagarme",
            external_reference="",
            amount="120.00",
            currency_code="BRL",
            reason_code="customer-request",
            metadata={},
        )

        with self.assertRaises(ProviderAdapterError) as context:
            PagarmeProviderAdapter().create_refund(contract=contract)

        self.assertEqual(str(context.exception), "pagarme-refund-charge-id-missing")

    @override_settings(PAGARME_SECRET_KEY="sk_test_refund", PAGARME_API_BASE_URL="https://api.pagar.me/core/v5")
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_pagarme_refund_adapter_reports_network_failure(self, mocked_urlopen):
        mocked_urlopen.side_effect = URLError("offline")

        with self.assertRaises(ProviderAdapterError) as context:
            PagarmeProviderAdapter().create_refund(contract=self._contract())

        self.assertEqual(str(context.exception), "pagarme-network-unavailable")
