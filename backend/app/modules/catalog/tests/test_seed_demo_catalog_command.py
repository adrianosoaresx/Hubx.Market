from django.core.management import call_command
from django.test import TestCase

from app.modules.catalog.models import Product, ProductImage, ProductVariant
from app.modules.tenants.models import Tenant


class SeedDemoCatalogCommandTests(TestCase):
    def test_seed_demo_catalog_creates_tenant_scoped_products(self):
        tenant = Tenant.objects.create(
            name="Seed Demo Store",
            slug="seed-demo-store",
            subdomain="seed-demo-store",
        )

        call_command(
            "seed_demo_catalog",
            tenant_subdomain=tenant.subdomain,
            count=2,
            images_per_product=2,
            reset_seed=True,
            slug_prefix="seedtest",
        )

        products = Product.objects.filter(tenant=tenant, slug__startswith="seedtest-")

        self.assertEqual(products.count(), 2)
        self.assertEqual(products.filter(status=Product.Status.ACTIVE, is_active=True).count(), 2)
        self.assertEqual(ProductVariant.objects.filter(product__in=products).count(), 6)
        self.assertEqual(ProductImage.objects.filter(product__in=products).count(), 4)
