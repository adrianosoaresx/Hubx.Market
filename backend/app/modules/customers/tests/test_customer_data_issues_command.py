from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.customers.application.customer_data_issues import customer_data_issues
from app.modules.customers.application.customer_metrics_queries import customer_metrics_queries
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class CustomerDataIssueCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Customer Data Ops",
            slug="hubx-customer-data-ops",
            subdomain="hubx-customer-data-ops",
        )

    def test_customer_data_issues_detects_address_and_order_fallback(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ops-customer",
            reference="#CD-1",
            full_name="Ops Customer",
            email="ops.customer@hubx.market",
            phone="(11) 90000-0000",
        )
        Order.objects.create(
            tenant=self.tenant,
            customer=None,
            number="CD-100",
            status="paid",
            customer_name=customer.full_name,
            customer_email=customer.email,
            subtotal="100.00",
            shipping_total="0.00",
            discount_total="0.00",
            total="100.00",
        )
        Order.objects.filter(number="CD-100").update(customer=None)

        issue_codes = [issue.issue_code for issue in customer_data_issues.list_issues(tenant_id=self.tenant.id)]

        self.assertIn("missing_address", issue_codes)
        self.assertIn("order_email_fallback", issue_codes)

    def test_customer_data_issues_detects_missing_default_and_incomplete_default(self):
        missing_default = Customer.objects.create(
            tenant=self.tenant,
            slug="missing-default",
            reference="#CD-2",
            full_name="Missing Default",
            email="missing.default@hubx.market",
        )
        CustomerAddress.objects.create(
            customer=missing_default,
            label="Casa",
            line_1="Rua A, 10",
            city="São Paulo",
            state="SP",
            postal_code="01000-000",
            is_default=False,
        )
        incomplete_default = Customer.objects.create(
            tenant=self.tenant,
            slug="incomplete-default",
            reference="#CD-3",
            full_name="Incomplete Default",
            email="incomplete.default@hubx.market",
        )
        CustomerAddress.objects.create(
            customer=incomplete_default,
            label="Casa",
            line_1="Rua B, 20",
            city="",
            state="SP",
            postal_code="02000-000",
            is_default=True,
        )

        issues_by_slug = {
            issue.slug: issue.issue_code
            for issue in customer_data_issues.list_issues(tenant_id=self.tenant.id)
            if issue.slug in {"missing-default", "incomplete-default"}
        }

        self.assertEqual(issues_by_slug["missing-default"], "missing_default_address")
        self.assertEqual(issues_by_slug["incomplete-default"], "incomplete_default_address")

    def test_list_customer_data_issues_command_filters_by_issue(self):
        Customer.objects.create(
            tenant=self.tenant,
            slug="no-address",
            reference="#CD-4",
            full_name="No Address",
            email="no.address@hubx.market",
        )

        output = StringIO()
        call_command(
            "list_customer_data_issues",
            tenant_id=str(self.tenant.id),
            issue="missing_address",
            stdout=output,
        )

        payload = output.getvalue()
        self.assertIn("customer_data_issue", payload)
        self.assertIn("slug=no-address", payload)
        self.assertIn("issue=missing_address", payload)
        self.assertIn("customer_data_issues=1", payload)

    def test_customer_metrics_exports_issue_counts(self):
        Customer.objects.create(
            tenant=self.tenant,
            slug="metrics-no-address",
            reference="#CD-5",
            full_name="Metrics No Address",
            email="metrics.no.address@hubx.market",
        )

        payload = customer_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_customer_data_issue_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}"', payload)
        self.assertIn('issue="missing_address"', payload)

    @override_settings(CUSTOMERS_OBSERVABILITY_TOKEN="customers-secret")
    def test_customer_metrics_view_requires_valid_token(self):
        Customer.objects.create(
            tenant=self.tenant,
            slug="view-no-address",
            reference="#CD-6",
            full_name="View No Address",
            email="view.no.address@hubx.market",
        )

        forbidden = self.client.get(reverse("customers:customer-metrics"), HTTP_X_HUBX_OBSERVABILITY_TOKEN="wrong")
        response = self.client.get(reverse("customers:customer-metrics"), HTTP_AUTHORIZATION="Bearer customers-secret")

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(response.status_code, 200)
        self.assertIn("hubx_customer_data_issue_total", response.content.decode())

    @override_settings(CUSTOMERS_OBSERVABILITY_TOKEN="")
    def test_customer_metrics_view_returns_404_when_disabled(self):
        response = self.client.get(reverse("customers:customer-metrics"), HTTP_X_HUBX_OBSERVABILITY_TOKEN="anything")

        self.assertEqual(response.status_code, 404)
