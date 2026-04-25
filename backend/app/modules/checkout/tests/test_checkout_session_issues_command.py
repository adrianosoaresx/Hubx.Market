from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.checkout.application.checkout_metrics_queries import checkout_metrics_queries
from app.modules.checkout.application.checkout_session_issues import checkout_session_issues
from app.modules.checkout.models import CheckoutRecoveryEvent, CheckoutSession, CheckoutSessionItem
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class CheckoutSessionIssueTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Checkout Ops",
            slug="hubx-checkout-ops",
            subdomain="hubx-checkout-ops",
        )
        self.other_tenant = Tenant.objects.create(
            name="Hubx Checkout Ops Other",
            slug="hubx-checkout-ops-other",
            subdomain="hubx-checkout-ops-other",
        )

    def _create_session_with_item(self, **overrides) -> CheckoutSession:
        payload = {
            "tenant": self.tenant,
            "status": CheckoutSession.Status.OPEN,
            "first_name": "Ana",
            "email": "ana@hubx.market",
            "address_line_1": "Rua A, 100",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01000-000",
            "shipping_method_selected": "standard",
            "payment_method_selected": "credit_card",
            "accept_terms": True,
            "subtotal": Decimal("100.00"),
            "shipping_total": Decimal("10.00"),
            "discount_total": Decimal("0.00"),
            "grand_total": Decimal("110.00"),
        }
        payload.update(overrides)
        session = CheckoutSession.objects.create(**payload)
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto operacional",
            price=Decimal("100.00"),
            quantity=1,
            sort_order=1,
        )
        return session

    def test_lists_tenant_scoped_checkout_session_issues(self):
        empty_session = CheckoutSession.objects.create(tenant=self.tenant)
        missing_contact = self._create_session_with_item(first_name="", email="")
        missing_delivery = self._create_session_with_item(address_line_1="", shipping_method_selected="")
        missing_payment = self._create_session_with_item(payment_method_selected="", accept_terms=False)
        stale = self._create_session_with_item()
        CheckoutSession.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timezone.timedelta(days=2))
        completed_missing = self._create_session_with_item(status=CheckoutSession.Status.COMPLETED, completed_order_number="9001")
        total_mismatch = self._create_session_with_item(subtotal=Decimal("90.00"), grand_total=Decimal("100.00"))
        self._create_session_with_item(tenant=self.other_tenant, first_name="", email="")

        issues = checkout_session_issues.list_issues(tenant_id=self.tenant.id, limit=50)
        issue_codes = [issue.issue_code for issue in issues]

        self.assertIn("open_empty", issue_codes)
        self.assertIn("open_missing_contact", issue_codes)
        self.assertIn("open_missing_delivery", issue_codes)
        self.assertIn("open_missing_payment", issue_codes)
        self.assertIn("open_stale", issue_codes)
        self.assertIn("completed_order_missing", issue_codes)
        self.assertIn("total_mismatch", issue_codes)
        self.assertNotIn(str(self.other_tenant.id), {issue.tenant_id for issue in issues})
        self.assertIn(str(empty_session.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(missing_contact.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(missing_delivery.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(missing_payment.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(stale.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(completed_missing.session_key), {issue.session_key for issue in issues})
        self.assertIn(str(total_mismatch.session_key), {issue.session_key for issue in issues})

    def test_completed_session_with_existing_order_is_not_reported(self):
        session = self._create_session_with_item(status=CheckoutSession.Status.COMPLETED, completed_order_number="1001")
        Order.objects.create(tenant=self.tenant, number="1001", customer_email="ana@hubx.market", total=Decimal("110.00"))

        issues = checkout_session_issues.list_issues(tenant_id=self.tenant.id, limit=50)

        self.assertNotIn(("completed_order_missing", str(session.session_key)), {(issue.issue_code, issue.session_key) for issue in issues})

    def test_management_command_filters_issue(self):
        session = self._create_session_with_item(payment_method_selected="", accept_terms=False)
        output = StringIO()

        call_command(
            "list_checkout_session_issues",
            "--tenant-id",
            str(self.tenant.id),
            "--issue",
            "open_missing_payment",
            stdout=output,
        )

        payload = output.getvalue()
        self.assertIn("checkout_session_issue", payload)
        self.assertIn("issue=open_missing_payment", payload)
        self.assertIn(str(session.session_key), payload)
        self.assertIn("checkout_session_issues=1", payload)

    @override_settings(CHECKOUT_OBSERVABILITY_TOKEN="checkout-token")
    def test_metrics_export_and_view(self):
        self._create_session_with_item(payment_method_selected="", accept_terms=False)
        self._create_session_with_item(status=CheckoutSession.Status.EXPIRED)
        CheckoutRecoveryEvent.objects.create(
            tenant=self.tenant,
            result_code="checkout-completion-stock-conflict",
            family="inventory",
            severity="warning",
            recovery_action="restart_from_product",
            stage="review",
        )
        CheckoutRecoveryEvent.objects.create(
            tenant=self.tenant,
            result_code="checkout-completion-stock-conflict",
            family="inventory",
            severity="warning",
            recovery_action="restart_from_product",
            stage="review",
        )

        payload = checkout_metrics_queries.export_prometheus_metrics()
        self.assertIn("hubx_checkout_session_issue_total", payload)
        self.assertIn('issue="open_missing_payment"', payload)
        self.assertIn("hubx_checkout_session_status_total", payload)
        self.assertIn('status="expired"', payload)
        self.assertIn("hubx_checkout_recovery_result_info", payload)
        self.assertIn('code="checkout-completion-stock-conflict"', payload)
        self.assertIn('family="inventory"', payload)
        self.assertIn('recovery_action="restart_from_product"', payload)
        self.assertIn("hubx_checkout_recovery_event_total", payload)
        self.assertIn(
            f'hubx_checkout_recovery_event_total{{tenant_id="{self.tenant.id}",code="checkout-completion-stock-conflict",family="inventory",severity="warning",recovery_action="restart_from_product"}} 2',
            payload,
        )

        response = self.client.get(
            reverse("checkout_ops:checkout-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="checkout-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hubx_checkout_session_issue_total")
        self.assertContains(response, "hubx_checkout_session_status_total")
        self.assertContains(response, "hubx_checkout_recovery_result_info")
        self.assertContains(response, "hubx_checkout_recovery_event_total")

    @override_settings(CHECKOUT_OBSERVABILITY_TOKEN="checkout-token")
    def test_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("checkout_ops:checkout-metrics"), HTTP_X_HUBX_OBSERVABILITY_TOKEN="wrong")

        self.assertEqual(response.status_code, 403)

    @override_settings(CHECKOUT_OBSERVABILITY_TOKEN="")
    def test_metrics_view_returns_not_found_when_disabled(self):
        response = self.client.get(reverse("checkout_ops:checkout-metrics"))

        self.assertEqual(response.status_code, 404)
