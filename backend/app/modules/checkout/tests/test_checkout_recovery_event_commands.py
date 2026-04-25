from django.test import TestCase

from app.modules.checkout.application.checkout_recovery_event_commands import record_checkout_recovery_event
from app.modules.checkout.models import CheckoutRecoveryEvent
from app.modules.checkout.models import CheckoutSession
from app.modules.tenants.models import Tenant


class CheckoutRecoveryEventCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Recovery Events",
            slug="hubx-recovery-events",
            subdomain="hubx-recovery-events",
        )
        self.other_tenant = Tenant.objects.create(
            name="Other Recovery Events",
            slug="other-recovery-events",
            subdomain="other-recovery-events",
        )

    def test_records_known_result_with_taxonomy(self):
        session = CheckoutSession.objects.create(tenant=self.tenant)

        event = record_checkout_recovery_event(
            tenant_id=self.tenant.id,
            result="checkout-completion-stock-conflict",
            session_key=str(session.session_key),
            stage="review",
        )

        self.assertIsNotNone(event)
        stored = CheckoutRecoveryEvent.objects.get()
        self.assertEqual(stored.tenant, self.tenant)
        self.assertEqual(stored.checkout_session, session)
        self.assertEqual(stored.result_code, "checkout-completion-stock-conflict")
        self.assertEqual(stored.family, "inventory")
        self.assertEqual(stored.severity, "warning")
        self.assertEqual(stored.recovery_action, "restart_from_product")
        self.assertEqual(stored.stage, "review")

    def test_does_not_record_without_tenant_or_known_result(self):
        self.assertIsNone(
            record_checkout_recovery_event(
                tenant_id=None,
                result="checkout-completion-stock-conflict",
            )
        )
        self.assertIsNone(
            record_checkout_recovery_event(
                tenant_id=self.tenant.id,
                result="unknown-result",
            )
        )

        self.assertEqual(CheckoutRecoveryEvent.objects.count(), 0)

    def test_does_not_attach_session_from_another_tenant(self):
        foreign_session = CheckoutSession.objects.create(tenant=self.other_tenant)

        event = record_checkout_recovery_event(
            tenant_id=self.tenant.id,
            result="checkout-completion-snapshot-conflict",
            session_key=str(foreign_session.session_key),
            stage="review",
        )

        self.assertIsNotNone(event)
        stored = CheckoutRecoveryEvent.objects.get()
        self.assertEqual(stored.tenant, self.tenant)
        self.assertIsNone(stored.checkout_session)
        self.assertEqual(stored.family, "snapshot")
