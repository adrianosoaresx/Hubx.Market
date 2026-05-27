from django.test import TestCase

from app.modules.cart.application.cart_commands import cart_commands
from app.modules.cart.models import Cart, CartItem, CartMutation
from app.modules.catalog.models import Product, ProductVariant
from app.modules.coupons.models import Coupon
from app.modules.customers.models import Customer
from app.modules.tenants.models import Tenant


class CartCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Cart", slug="loja-cart", subdomain="loja-cart")
        self.other_tenant = Tenant.objects.create(name="Outra Cart", slug="outra-cart", subdomain="outra-cart")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Cart",
            slug="produto-cart",
            brand_name="Hubx Cart",
            category_label="Calçados",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="CART-BLK-42",
            price="199.90",
            compare_price="249.90",
            stock=8,
            reserved_stock=0,
            is_default=True,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Outra Cart",
            slug="produto-outra-cart",
            brand_name="Hubx Cart",
            category_label="Calçados",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.other_variant = ProductVariant.objects.create(
            product=self.other_product,
            sku="OTHER-CART-BLK-42",
            price="199.90",
            compare_price="249.90",
            stock=8,
            reserved_stock=0,
            is_default=True,
        )

    def _product_payload(self, **overrides):
        payload = {
            "tenant_id": self.tenant.id,
            "id": self.product.id,
            "slug": self.product.slug,
            "name": self.product.name,
            "sku": self.variant.sku,
            "effective_variant_label": "Preto · 42",
            "main_image_url": "https://cdn.hubx.market/cart.jpg",
            "main_image_alt": "Produto Cart",
            "price": "199.90",
            "compare_price": "249.90",
        }
        payload.update(overrides)
        return payload

    def test_get_or_create_active_cart_requires_tenant_and_owner_context(self):
        missing_tenant = cart_commands.get_or_create_active_cart(tenant_id="", session_key="session-1")
        missing_owner = cart_commands.get_or_create_active_cart(tenant_id=self.tenant.id)

        self.assertEqual(missing_tenant["result"], "cart-tenant-required")
        self.assertEqual(missing_owner["result"], "cart-owner-required")

    def test_get_or_create_active_cart_reuses_session_cart_per_tenant(self):
        created = cart_commands.get_or_create_active_cart(tenant_id=self.tenant.id, session_key="session-1")
        reused = cart_commands.get_or_create_active_cart(tenant_id=self.tenant.id, session_key="session-1")
        other_tenant = cart_commands.get_or_create_active_cart(tenant_id=self.other_tenant.id, session_key="session-1")

        self.assertEqual(created["result"], "cart-created")
        self.assertEqual(reused["result"], "cart-found")
        self.assertNotEqual(created["cart"]["id"], other_tenant["cart"]["id"])
        self.assertEqual(Cart.objects.count(), 2)

    def test_get_or_create_active_cart_reuses_customer_cart_per_tenant(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-cart",
            full_name="Cliente Cart",
            email="cliente.cart@hubx.market",
        )

        created = cart_commands.get_or_create_active_cart(tenant_id=self.tenant.id, customer_id=customer.id)
        reused = cart_commands.get_or_create_active_cart(tenant_id=self.tenant.id, customer_id=customer.id)

        self.assertEqual(created["result"], "cart-created")
        self.assertEqual(reused["cart"]["id"], created["cart"]["id"])
        self.assertEqual(created["cart"]["customer_id"], customer.id)

    def test_add_item_creates_snapshot_and_recalculates_totals(self):
        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )

        self.assertEqual(result["result"], "cart-item-added")
        self.assertEqual(result["cart"]["subtotal"], "399.80")
        self.assertEqual(result["cart"]["total"], "399.80")
        self.assertEqual(len(result["cart"]["items"]), 1)
        self.assertEqual(result["cart"]["items"][0]["variant_sku"], "CART-BLK-42")
        self.assertEqual(result["cart"]["items"][0]["quantity"], 2)

        item = CartItem.objects.get()
        self.assertEqual(item.product, self.product)
        self.assertEqual(str(item.price_snapshot), "199.90")

    def test_add_item_increments_existing_variant(self):
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=1,
        )
        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(price="189.90"),
            quantity=2,
        )

        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(result["cart"]["items"][0]["quantity"], 3)
        self.assertEqual(result["cart"]["subtotal"], "569.70")

    def test_add_item_with_idempotency_key_does_not_replay_same_mutation(self):
        first_result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
            idempotency_key="add-1",
        )
        replay_result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
            idempotency_key="add-1",
        )
        new_result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=1,
            idempotency_key="add-2",
        )

        self.assertEqual(first_result["result"], "cart-item-added")
        self.assertEqual(replay_result["result"], "cart-item-added-idempotent")
        self.assertEqual(new_result["result"], "cart-item-added")
        self.assertEqual(CartItem.objects.get().quantity, 3)
        self.assertEqual(CartMutation.objects.count(), 2)
        self.assertEqual(replay_result["cart"]["items"][0]["quantity"], 2)

    def test_add_item_idempotency_key_is_scoped_by_tenant_and_cart(self):
        first_result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=1,
            idempotency_key="same-key",
        )
        other_result = cart_commands.add_item(
            tenant_id=self.other_tenant.id,
            session_key="session-1",
            product=self._product_payload(
                tenant_id=self.other_tenant.id,
                id=self.other_product.id,
                slug=self.other_product.slug,
                name=self.other_product.name,
                sku=self.other_variant.sku,
            ),
            quantity=1,
            idempotency_key="same-key",
        )

        self.assertEqual(first_result["result"], "cart-item-added")
        self.assertEqual(other_result["result"], "cart-item-added")
        self.assertEqual(Cart.objects.count(), 2)
        self.assertEqual(CartMutation.objects.count(), 2)

    def test_add_item_rejects_cross_tenant_product_payload(self):
        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(tenant_id=self.other_tenant.id),
        )

        self.assertEqual(result["result"], "cart-product-cross-tenant")
        self.assertFalse(CartItem.objects.exists())

    def test_add_item_rejects_quantity_above_available_stock(self):
        self.variant.stock = 3
        self.variant.reserved_stock = 1
        self.variant.save(update_fields=["stock", "reserved_stock", "updated_at"])

        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=3,
        )

        self.assertEqual(result["result"], "cart-item-stock-conflict")
        self.assertEqual(result["available_quantity"], 2)
        self.assertEqual(result["requested_quantity"], 3)
        self.assertFalse(CartItem.objects.exists())

    def test_add_item_rejects_unavailable_variant_for_tenant(self):
        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(sku="MISSING-SKU"),
            quantity=1,
        )

        self.assertEqual(result["result"], "cart-item-stock-unavailable")
        self.assertEqual(result["available_quantity"], 0)
        self.assertFalse(CartItem.objects.exists())

    def test_add_item_allows_untracked_inventory_and_backorder(self):
        self.variant.stock = 0
        self.variant.track_inventory = False
        self.variant.save(update_fields=["stock", "track_inventory", "updated_at"])

        untracked = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=5,
        )
        self.variant.track_inventory = True
        self.variant.allow_backorder = True
        self.variant.save(update_fields=["track_inventory", "allow_backorder", "updated_at"])
        backorder = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-2",
            product=self._product_payload(),
            quantity=5,
        )

        self.assertEqual(untracked["result"], "cart-item-added")
        self.assertEqual(backorder["result"], "cart-item-added")
        self.assertEqual(CartItem.objects.count(), 2)

    def test_add_item_considers_existing_quantity_before_stock_guard(self):
        self.variant.stock = 3
        self.variant.save(update_fields=["stock", "updated_at"])
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )

        result = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )

        self.assertEqual(result["result"], "cart-item-stock-conflict")
        self.assertEqual(result["available_quantity"], 3)
        self.assertEqual(result["requested_quantity"], 4)
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_update_quantity_rejects_quantity_above_available_stock(self):
        self.variant.stock = 2
        self.variant.save(update_fields=["stock", "updated_at"])
        added = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=1,
        )
        cart_id = added["cart"]["id"]
        item_id = added["cart"]["items"][0]["id"]

        result = cart_commands.update_quantity(
            tenant_id=self.tenant.id,
            cart_id=cart_id,
            item_id=item_id,
            quantity=3,
        )

        self.assertEqual(result["result"], "cart-item-stock-conflict")
        self.assertEqual(result["available_quantity"], 2)
        self.assertEqual(result["requested_quantity"], 3)
        self.assertEqual(CartItem.objects.get().quantity, 1)

    def test_update_quantity_and_remove_item_are_tenant_scoped(self):
        added = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )
        cart_id = added["cart"]["id"]
        item_id = added["cart"]["items"][0]["id"]

        cross_tenant = cart_commands.update_quantity(
            tenant_id=self.other_tenant.id,
            cart_id=cart_id,
            item_id=item_id,
            quantity=5,
        )
        updated = cart_commands.update_quantity(
            tenant_id=self.tenant.id,
            cart_id=cart_id,
            item_id=item_id,
            quantity=3,
        )
        removed = cart_commands.remove_item(
            tenant_id=self.tenant.id,
            cart_id=cart_id,
            item_id=item_id,
        )

        self.assertEqual(cross_tenant["result"], "cart-not-found")
        self.assertEqual(updated["cart"]["subtotal"], "599.70")
        self.assertEqual(removed["cart"]["total"], "0.00")
        self.assertFalse(CartItem.objects.exists())

    def test_apply_coupon_intent_persists_invalid_code_without_discount(self):
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )

        result = cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key="session-1",
            coupon_code=" promo10 ",
        )

        self.assertEqual(result["result"], "cart-coupon-validation-unavailable")
        self.assertEqual(result["cart"]["coupon_code"], "PROMO10")
        self.assertEqual(result["cart"]["discount_total"], "0.00")
        self.assertEqual(result["cart"]["subtotal"], "399.80")
        self.assertEqual(result["cart"]["total"], "399.80")
        self.assertEqual(result["coupon_validation"]["result"], "coupon-invalid")
        self.assertEqual(result["coupon_validation"]["reason"], "coupon-invalid")

        cart = Cart.objects.get()
        self.assertEqual(cart.coupon_code, "PROMO10")
        self.assertEqual(str(cart.discount_total), "0.00")

    def test_apply_coupon_intent_applies_valid_coupon_discount(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=2,
        )

        result = cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key="session-1",
            coupon_code=" promo10 ",
        )

        self.assertEqual(result["result"], "cart-coupon-applied")
        self.assertEqual(result["coupon_validation"]["result"], "coupon-valid")
        self.assertEqual(result["cart"]["coupon_code"], "PROMO10")
        self.assertEqual(result["cart"]["discount_total"], "39.98")
        self.assertEqual(result["cart"]["total"], "359.82")

    def test_remove_coupon_intent_is_tenant_scoped(self):
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key="session-1",
            product=self._product_payload(),
            quantity=1,
        )
        cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key="session-1",
            coupon_code="SAVE",
        )

        cross_tenant = cart_commands.remove_coupon_intent(
            tenant_id=self.other_tenant.id,
            session_key="session-1",
        )
        removed = cart_commands.remove_coupon_intent(
            tenant_id=self.tenant.id,
            session_key="session-1",
        )

        self.assertEqual(cross_tenant["result"], "cart-not-found")
        self.assertEqual(removed["result"], "cart-coupon-removed")
        self.assertEqual(removed["cart"]["coupon_code"], "")
        self.assertEqual(Cart.objects.get(tenant=self.tenant).coupon_code, "")
