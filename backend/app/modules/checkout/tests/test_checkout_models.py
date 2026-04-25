from django.test import TestCase

from app.modules.checkout.models import CheckoutRecoveryEvent, CheckoutSession, CheckoutSessionItem
from app.modules.tenants.models import Tenant


class CheckoutReadinessModelTests(TestCase):
    def test_checkout_session_persists_snapshot_fields_and_items(self):
        tenant = Tenant.objects.create(
            name="Hubx Demo Store",
            slug="hubx-demo-checkout",
            subdomain="hubx-demo-checkout",
        )

        session = CheckoutSession.objects.create(
            tenant=tenant,
            first_name="Ana",
            last_name="Souza",
            email="ana@hubx.market",
            phone="(11) 99999-0000",
            address_line_1="Rua das Laranjeiras, 100",
            city="São Paulo",
            state="SP",
            zip_code="01310-100",
            shipping_methods=[{"value": "standard", "label": "Entrega padrão"}],
            shipping_method_selected="standard",
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            payment_method_selected="credit_card",
            subtotal="359.80",
            shipping_total="24.90",
            discount_total="20.00",
            grand_total="364.70",
            installments_summary="3x de R$ 121,56 sem juros",
            installments_selected="3x",
            installments_options=[{"value": "3x", "label": "3x de R$ 121,56"}],
            accept_terms=True,
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Tênis Hubx Runner",
            subtitle="Preto · 42",
            meta="SKU RUNNER-001-BLK-42",
            price="299.90",
            compare_price="349.90",
            quantity=1,
            sort_order=1,
        )

        stored = CheckoutSession.objects.prefetch_related("items").get(pk=session.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.shipping_method_selected, "standard")
        self.assertEqual(stored.payment_method_selected, "credit_card")
        self.assertEqual(stored.items.count(), 1)
        self.assertEqual(stored.items.first().title, "Tênis Hubx Runner")

    def test_checkout_recovery_event_persists_tenant_scope_and_taxonomy(self):
        tenant = Tenant.objects.create(
            name="Hubx Recovery Store",
            slug="hubx-recovery-checkout",
            subdomain="hubx-recovery-checkout",
        )
        session = CheckoutSession.objects.create(tenant=tenant)

        event = CheckoutRecoveryEvent.objects.create(
            tenant=tenant,
            checkout_session=session,
            result_code="checkout-completion-stock-conflict",
            family="inventory",
            severity="warning",
            recovery_action="restart_from_product",
            stage="review",
        )

        stored = CheckoutRecoveryEvent.objects.get(pk=event.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.checkout_session, session)
        self.assertEqual(stored.family, "inventory")
        self.assertEqual(stored.recovery_action, "restart_from_product")
