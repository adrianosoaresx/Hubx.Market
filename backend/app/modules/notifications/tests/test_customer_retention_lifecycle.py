from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.newsletter.application.newsletter_segment_queries import newsletter_segment_queries
from app.modules.newsletter.models import NewsletterSubscriber
from app.modules.notifications.application.customer_retention_lifecycle_commands import customer_retention_lifecycle_commands
from app.modules.notifications.application.customer_retention_lifecycle_queries import customer_retention_lifecycle_closure_queries
from app.modules.notifications.application.notification_intent_catalog import get_notification_intent
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class CustomerRetentionLifecycleTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Retention Tenant", slug="retention-tenant", subdomain="retention-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Retention", slug="other-retention", subdomain="other-retention")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="RET-1001",
            status=Order.Status.PAID,
            customer_name="Cliente Retention",
            customer_email="cliente@example.com",
            total="150.00",
        )

    def test_newsletter_segment_returns_only_subscribed_tenant_records(self):
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@example.com", status=NewsletterSubscriber.Status.SUBSCRIBED)
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="optout@example.com", status=NewsletterSubscriber.Status.UNSUBSCRIBED)
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="outro@example.com", status=NewsletterSubscriber.Status.SUBSCRIBED)

        segment = newsletter_segment_queries.list_subscribed_segment(tenant_id=self.tenant.id)

        self.assertEqual([item["email"] for item in segment], ["ativo@example.com"])

    def test_post_purchase_intent_exists_in_catalog(self):
        intent = get_notification_intent("customer.post_purchase.follow_up")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.source_event, "retention.post_purchase_eligible")
        self.assertEqual(intent.audience, "customer")

    def test_plan_post_purchase_follow_up_creates_email_log_for_subscribed_customer(self):
        subscriber = NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="cliente@example.com",
            name="Cliente Retention",
            status=NewsletterSubscriber.Status.SUBSCRIBED,
        )

        result = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
            tenant_id=self.tenant.id,
            order_id=self.order.id,
        )

        self.assertEqual(result["result"], "retention-lifecycle-planned")
        log = EmailLog.objects.get()
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.intent_key, "customer.post_purchase.follow_up")
        self.assertEqual(log.source_event, "retention.post_purchase_eligible")
        self.assertEqual(log.recipient_type, "newsletter_subscriber")
        self.assertEqual(log.recipient_id, str(subscriber.id))
        self.assertEqual(log.recipient_email, "cliente@example.com")

    def test_plan_post_purchase_follow_up_is_idempotent(self):
        NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="cliente@example.com",
            status=NewsletterSubscriber.Status.SUBSCRIBED,
        )

        first = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
            tenant_id=self.tenant.id,
            order_id=self.order.id,
        )
        second = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
            tenant_id=self.tenant.id,
            order_id=self.order.id,
        )

        self.assertEqual(first["result"], "retention-lifecycle-planned")
        self.assertEqual(second["result"], "retention-lifecycle-already-planned")
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_plan_post_purchase_follow_up_respects_opt_out(self):
        NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="cliente@example.com",
            status=NewsletterSubscriber.Status.UNSUBSCRIBED,
        )

        result = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
            tenant_id=self.tenant.id,
            order_id=self.order.id,
        )

        self.assertEqual(result["result"], "retention-lifecycle-opted-out")
        self.assertFalse(EmailLog.objects.exists())

    def test_plan_post_purchase_follow_up_blocks_cross_tenant_order(self):
        NewsletterSubscriber.objects.create(
            tenant=self.other_tenant,
            email="cliente@example.com",
            status=NewsletterSubscriber.Status.SUBSCRIBED,
        )

        result = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
            tenant_id=self.other_tenant.id,
            order_id=self.order.id,
        )

        self.assertEqual(result["result"], "retention-lifecycle-order-not-found")
        self.assertFalse(EmailLog.objects.exists())

    def test_closure_recommends_battery_i(self):
        review = customer_retention_lifecycle_closure_queries.get_review(
            lifecycle_contract_ready=True,
            newsletter_segment_ready=True,
            post_purchase_intent_ready=True,
            notification_integration_ready=True,
            opt_out_boundary_ready=True,
            no_complex_automation=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertTrue(review["ready"])
        self.assertIn("Battery I — Storefront Data-Driven Conversion", review["next_tracks"])

    def test_management_command_closure_reports_ready(self):
        output = StringIO()
        call_command(
            "customer_retention_lifecycle",
            review="closure",
            lifecycle_contract_ready=True,
            newsletter_segment_ready=True,
            post_purchase_intent_ready=True,
            notification_integration_ready=True,
            opt_out_boundary_ready=True,
            no_complex_automation=True,
            docs_updated=True,
            decision_recorded=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=customer-retention-lifecycle-ready", value)
        self.assertIn("next_track=Battery I — Storefront Data-Driven Conversion", value)
