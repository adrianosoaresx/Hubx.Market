from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app.modules.checkout.application.checkout_activation_commands import checkout_activation_commands
from app.modules.checkout.models import CheckoutSession, CheckoutSessionItem
from app.modules.tenants.models import Tenant


class CheckoutActivationCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Checkout Activation",
            slug="hubx-checkout-activation",
            subdomain="hubx-checkout-activation",
        )

    def _product(self, *, sku: str = "ACT-001") -> dict[str, object]:
        return {
            "tenant_id": self.tenant.id,
            "name": "Produto Activation",
            "effective_variant_label": "Preto · 42",
            "sku": sku,
            "price": "100.00",
            "compare_price": "120.00",
            "main_image_url": "https://cdn.hubx.market/demo/product.jpg",
            "main_image_alt": "Produto Activation",
        }

    def _open_session(self) -> CheckoutSession:
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            status=CheckoutSession.Status.OPEN,
            shipping_methods=[{"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"}],
            shipping_method_selected="standard",
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            payment_method_selected="credit_card",
            subtotal=Decimal("100.00"),
            shipping_total=Decimal("24.90"),
            grand_total=Decimal("124.90"),
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto anterior",
            variant_sku="OLD-001",
            price=Decimal("100.00"),
            quantity=1,
        )
        return session

    def test_activate_from_product_reuses_recent_open_session(self):
        session = self._open_session()

        session_key = checkout_activation_commands.activate_from_product(self._product(sku="ACT-002"))

        self.assertEqual(str(session.session_key), session_key)
        self.assertEqual(CheckoutSession.objects.count(), 1)
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.OPEN)
        self.assertEqual(session.items.count(), 2)

    def test_activate_from_product_does_not_reuse_stale_open_session(self):
        stale = self._open_session()
        CheckoutSession.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timezone.timedelta(hours=30))

        session_key = checkout_activation_commands.activate_from_product(self._product(sku="ACT-003"))

        stale.refresh_from_db()
        self.assertEqual(stale.status, CheckoutSession.Status.EXPIRED)
        self.assertNotEqual(str(stale.session_key), session_key)
        self.assertEqual(CheckoutSession.objects.count(), 2)
        new_session = CheckoutSession.objects.get(session_key=session_key)
        self.assertEqual(new_session.status, CheckoutSession.Status.OPEN)
        self.assertEqual(new_session.items.count(), 1)
        self.assertEqual(new_session.items.first().variant_sku, "ACT-003")

    def test_activate_from_product_does_not_reuse_expired_at_open_session(self):
        expired_by_timestamp = self._open_session()
        CheckoutSession.objects.filter(pk=expired_by_timestamp.pk).update(expires_at=timezone.now() - timezone.timedelta(minutes=5))

        session_key = checkout_activation_commands.activate_from_product(self._product(sku="ACT-004"))

        expired_by_timestamp.refresh_from_db()
        self.assertEqual(expired_by_timestamp.status, CheckoutSession.Status.EXPIRED)
        self.assertNotEqual(str(expired_by_timestamp.session_key), session_key)
        self.assertEqual(CheckoutSession.objects.count(), 2)
