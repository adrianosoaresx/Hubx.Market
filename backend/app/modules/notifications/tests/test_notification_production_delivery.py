from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.notifications.application.notification_failure_classification import classify_notification_failure
from app.modules.notifications.application.notification_production_delivery_commands import notification_production_delivery_commands
from app.modules.notifications.application.notification_production_delivery_queries import (
    notification_failure_handling_queries,
    notification_production_closure_queries,
    notification_provider_production_gate_queries,
)
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationProductionDeliveryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Notification Production",
            slug="notification-production",
            subdomain="notification-production",
        )

    @override_settings(
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="ops@hubx.test",
    )
    def test_provider_gate_is_ready_when_runtime_and_operational_signals_are_present(self):
        review = notification_provider_production_gate_queries.get_review(
            provider_credentials_confirmed=True,
            sender_domain_confirmed=True,
            rollback_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "notification-provider-production-gate-ready")

    @override_settings(
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="ops@hubx.test",
    )
    def test_transactional_smoke_sends_email_and_returns_sanitized_evidence(self):
        result = notification_production_delivery_commands.execute_transactional_smoke(
            tenant_id=self.tenant.id,
            recipient_email="customer@example.com",
            smoke_key="battery-g",
        )

        self.assertEqual(result.result, "notification-smoke-sent")
        self.assertEqual(result.log.status, EmailLog.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.com"])
        self.assertEqual(result.evidence["recipient"], "cu******@example.com")
        self.assertNotIn("customer@example.com", str(result.evidence))

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True)
    def test_transactional_smoke_blocks_when_provider_is_not_ready(self):
        result = notification_production_delivery_commands.execute_transactional_smoke(
            tenant_id=self.tenant.id,
            recipient_email="customer@example.com",
            smoke_key="battery-g",
        )

        self.assertEqual(result.result, "notification-smoke-provider-blocked")
        self.assertFalse(EmailLog.objects.exists())

    def test_failure_classification_groups_bounces_and_provider_failures(self):
        self.assertEqual(classify_notification_failure("Mailbox bounced: invalid recipient"), "bounce")
        self.assertEqual(classify_notification_failure("provider timeout"), "provider-unavailable")
        self.assertEqual(classify_notification_failure("authentication denied"), "provider-authentication")

    def test_failure_handling_review_reports_classifications(self):
        EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.failed",
            intent_key="customer.payment.failed",
            audience="customer",
            entity_type="order",
            entity_id="9001",
            idempotency_key="1:customer.payment.failed:order:9001:email",
            recipient_delivery_key="1:customer.payment.failed:order:9001:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento falhou",
            status=EmailLog.Status.FAILED,
            last_error="Mailbox bounced",
        )

        review = notification_failure_handling_queries.get_review(
            tenant_id=self.tenant.id,
            bounce_handling_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["failure_classifications"], {"bounce": 1})

    def test_production_closure_recommends_battery_h_when_all_signals_are_ready(self):
        EmailLog.objects.create(
            tenant=self.tenant,
            source_event="notification.production_smoke",
            intent_key="system.notification.production_smoke",
            audience="system",
            entity_type="notification_smoke",
            entity_id="battery-g",
            idempotency_key="1:system.notification.production_smoke:notification_smoke:battery-g:email",
            recipient_delivery_key="1:notification.production_smoke:battery-g:email:system:hash",
            recipient_type="system",
            recipient_id="hash",
            recipient_email="smoke@example.com",
            title="Smoke",
            status=EmailLog.Status.SENT,
        )

        review = notification_production_closure_queries.get_review(
            tenant_id=self.tenant.id,
            provider_gate_ready=True,
            smoke_execution_ready=True,
            evidence_capture_ready=True,
            failure_handling_ready=True,
            monitoring_ready=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertTrue(review["ready"])
        self.assertIn("Battery H — Customer Retention Lifecycle", review["next_tracks"])

    @override_settings(
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="ops@hubx.test",
    )
    def test_management_command_smoke_masks_recipient(self):
        output = StringIO()
        call_command(
            "notification_production_delivery",
            review="smoke",
            tenant_id=str(self.tenant.id),
            recipient_email="customer@example.com",
            smoke_key="battery-g-command",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=notification-smoke-sent", value)
        self.assertIn("evidence recipient=cu******@example.com", value)
        self.assertNotIn("customer@example.com", value)
