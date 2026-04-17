from django.test import TestCase
from django.utils import timezone

from app.modules.customers.models import Customer, CustomerAddress
from app.modules.tenants.models import Tenant


class CustomerReadinessModelTests(TestCase):
    def test_customer_persists_minimal_admin_read_data(self):
        tenant = Tenant.objects.create(
            name="Hubx Customers Demo",
            slug="hubx-customers-demo",
            subdomain="hubx-customers-demo",
        )

        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-souza",
            reference="#8821",
            full_name="Ana Souza",
            email="ana@hubx.market",
            phone="(11) 99999-0000",
            status=Customer.Status.ACTIVE,
            account_type="Storefront",
            last_seen_at=timezone.now(),
        )

        stored = Customer.objects.get(pk=customer.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.reference, "#8821")
        self.assertEqual(stored.full_name, "Ana Souza")
        self.assertEqual(stored.email, "ana@hubx.market")
        self.assertEqual(stored.status, Customer.Status.ACTIVE)

    def test_customer_address_persists_minimal_customer_area_read_data(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Area Demo",
            slug="hubx-customer-area-demo",
            subdomain="hubx-customer-area-demo",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-endereco",
            reference="#9901",
            full_name="Ana Endereço",
            email="ana.endereco@hubx.market",
        )

        address = CustomerAddress.objects.create(
            customer=customer,
            label="Casa",
            recipient_name="Ana Endereço",
            line_1="Rua das Laranjeiras, 100",
            line_2="Apto 42",
            district="Bela Vista",
            city="São Paulo",
            state="SP",
            postal_code="01310-100",
            is_default=True,
        )

        stored = CustomerAddress.objects.select_related("customer").get(pk=address.pk)

        self.assertEqual(stored.customer, customer)
        self.assertEqual(stored.label, "Casa")
        self.assertEqual(stored.recipient_name, "Ana Endereço")
        self.assertEqual(stored.line_1, "Rua das Laranjeiras, 100")
        self.assertTrue(stored.is_default)
