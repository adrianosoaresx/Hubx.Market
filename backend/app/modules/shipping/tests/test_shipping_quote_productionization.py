from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.checkout.application.checkout_shipping_quote_commands import checkout_shipping_quote_commands
from app.modules.checkout.models import CheckoutSession
from app.modules.shipping.application.shipping_quote_productionization_queries import (
    shipping_quote_productionization_queries,
)
from app.modules.shipping.application.shipping_quote_queries import shipping_quote_queries
from app.modules.tenants.models import Tenant


class ShippingQuoteProductionizationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Shipping Quote Tenant", slug="shipping-quote", subdomain="shipping-quote")

    def test_quote_provider_returns_checkout_ready_methods(self):
        quote = shipping_quote_queries.get_quote(
            tenant_id=self.tenant.id,
            zip_code="01001-000",
            subtotal="120.00",
        )

        self.assertTrue(quote.ready)
        self.assertEqual(quote.result, "shipping-quote-ready")
        self.assertEqual(len(quote.options), 2)
        self.assertEqual(quote.checkout_methods()[0]["value"], "standard")
        self.assertEqual(quote.checkout_methods()[0]["price"], "R$ 24,90")

    def test_quote_provider_returns_honest_failure_for_invalid_zip(self):
        quote = shipping_quote_queries.get_quote(
            tenant_id=self.tenant.id,
            zip_code="123",
            subtotal="120.00",
        )

        self.assertFalse(quote.ready)
        self.assertEqual(quote.result, "shipping-quote-address-required")
        self.assertEqual(quote.failure_code, "zip-code-invalid")
        self.assertEqual(quote.checkout_methods(), [])

    def test_checkout_quote_command_applies_methods_and_totals(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            subtotal=Decimal("120.00"),
            discount_total=Decimal("10.00"),
            grand_total=Decimal("110.00"),
            zip_code="01001-000",
        )

        result = checkout_shipping_quote_commands.refresh_quote(
            tenant_id=self.tenant.id,
            session_key=str(session.session_key),
        )

        session.refresh_from_db()
        self.assertEqual(result["result"], "checkout-shipping-quote-updated")
        self.assertTrue(result["ready"])
        self.assertEqual(session.shipping_method_selected, "standard")
        self.assertEqual(session.shipping_total, Decimal("24.90"))
        self.assertEqual(session.grand_total, Decimal("134.90"))
        self.assertEqual(session.shipping_methods[0]["provider_reference"], "manual-standard")

    def test_checkout_quote_command_clears_delivery_choice_on_failure(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            subtotal=Decimal("120.00"),
            grand_total=Decimal("120.00"),
            zip_code="123",
            shipping_method_selected="standard",
            shipping_methods=[{"value": "standard", "price": "R$ 24,90"}],
            shipping_total=Decimal("24.90"),
        )

        result = checkout_shipping_quote_commands.refresh_quote(
            tenant_id=self.tenant.id,
            session_key=str(session.session_key),
        )

        session.refresh_from_db()
        self.assertEqual(result["result"], "checkout-shipping-quote-failed")
        self.assertFalse(result["ready"])
        self.assertEqual(result["failure_code"], "zip-code-invalid")
        self.assertEqual(session.shipping_method_selected, "")
        self.assertEqual(session.shipping_total, Decimal("0.00"))

    def test_closure_ready_when_all_battery_d_waves_are_done(self):
        review = shipping_quote_productionization_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "shipping-quote-productionization-ready")
        self.assertIn("checkout shipping quote command", review["closure_scope"])
        self.assertIn("Battery E — Subscriptions & Tenant Billing Foundation", review["next_tracks"])

    def test_closure_command_outputs_no_sensitive_material(self):
        output = StringIO()

        call_command("shipping_quote_productionization", *self._ready_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("result=shipping-quote-productionization-ready", value)
        self.assertIn("next_track=Battery E — Subscriptions & Tenant Billing Foundation", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("token=", value)

    def test_closure_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("shipping_quote_productionization", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "provider_contract_ready": True,
            "adapter_skeleton_ready": True,
            "checkout_integration_review_ready": True,
            "checkout_execution_ready": True,
            "failure_ux_ready": True,
            "observability_ready": True,
            "tenant_scope_confirmed": True,
            "no_order_without_delivery_confirmed": True,
            "no_provider_secret_recorded": True,
            "rollback_plan_ready": True,
            "docs_updated": True,
            "decision_recorded": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return tuple(f"--{key.replace('_', '-')}" for key, value in self._ready_flags().items() if value)
