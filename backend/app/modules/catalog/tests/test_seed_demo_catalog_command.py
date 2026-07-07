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
        tenant.refresh_from_db()
        self.assertEqual(tenant.name, "Seed Demo Store")
        self.assertEqual(tenant.storefront_hero_image_url, "")
        self.assertEqual(products.filter(status=Product.Status.ACTIVE, is_active=True).count(), 2)
        self.assertEqual(ProductVariant.objects.filter(product__in=products).count(), 6)
        self.assertEqual(ProductImage.objects.filter(product__in=products).count(), 4)
        self.assertTrue(all(image.image_url.endswith(".jpg") for image in ProductImage.objects.filter(product__in=products)))
        self.assertFalse(ProductImage.objects.filter(product__in=products, image_url__endswith=".svg").exists())

    def test_seed_demo_catalog_can_reset_entire_demo_catalog_and_brand_name(self):
        tenant = Tenant.objects.create(
            name="Old Demo",
            slug="hubx-demo",
            subdomain="hubx-demo",
        )
        Product.objects.create(
            tenant=tenant,
            name="Produto antigo",
            slug="legacy-product",
            status=Product.Status.ACTIVE,
            is_active=True,
        )

        call_command(
            "seed_demo_catalog",
            tenant_subdomain=tenant.subdomain,
            count=1,
            images_per_product=1,
            reset_seed=True,
            reset_tenant_catalog=True,
            clear_discovery_events=True,
            store_name="Hubx Market Demo",
        )

        tenant.refresh_from_db()
        self.assertEqual(tenant.name, "Hubx Market Demo")
        self.assertEqual(
            tenant.storefront_hero_image_url,
            "http://hubx-demo.localhost:8002/static/img/brand/hubx-public-hero.jpg",
        )
        self.assertFalse(Product.objects.filter(tenant=tenant, slug="legacy-product").exists())
        self.assertEqual(Product.objects.filter(tenant=tenant, slug__startswith="demo-").count(), 1)
        self.assertFalse(ProductImage.objects.filter(product__tenant=tenant, image_url__endswith=".svg").exists())
