from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationMetricsViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Metrics View", slug="loja-metrics-view", subdomain="loja-metrics-view")
        EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.failed",
            intent_key="customer.payment.failed",
            audience="customer",
            entity_type="order",
            entity_id="1",
            idempotency_key=f"{self.tenant.id}:customer.payment.failed:order:1:email",
            recipient_delivery_key=f"{self.tenant.id}:customer.payment.failed:order:1:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento falhou",
            status=EmailLog.Status.FAILED,
        )

    @override_settings(NOTIFICATIONS_OBSERVABILITY_TOKEN="ops-token")
    def test_metrics_view_returns_prometheus_payload_with_token(self):
        response = self.client.get(
            reverse("notifications:email-log-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="ops-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])
        self.assertContains(response, "hubx_notifications_email_log_total")

    @override_settings(NOTIFICATIONS_OBSERVABILITY_TOKEN="ops-token")
    def test_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("notifications:email-log-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(NOTIFICATIONS_OBSERVABILITY_TOKEN="")
    def test_metrics_view_is_not_found_without_configured_token(self):
        response = self.client.get(reverse("notifications:email-log-metrics"))

        self.assertEqual(response.status_code, 404)
