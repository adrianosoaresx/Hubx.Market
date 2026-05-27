from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.cart.application.cart_commands import cart_commands
from app.modules.cart.application.cart_page_queries import cart_page_queries
from app.modules.cart.models import Cart, CartItem
from app.modules.catalog.models import Product, ProductVariant
from app.modules.checkout.models import CheckoutSession
from app.modules.coupons.models import Coupon
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class CartStorefrontViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Cart View", slug="loja-cart-view", subdomain="loja-cart-view")
        self.other_tenant = Tenant.objects.create(name="Outra Cart View", slug="outra-cart-view", subdomain="outra-cart-view")
        self.storefront_host = f"{self.tenant.subdomain}.hubx.market"
        self.other_storefront_host = f"{self.other_tenant.subdomain}.hubx.market"
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Cart View",
            slug="produto-cart-view",
            brand_name="Hubx Cart",
            category_label="Calçados",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="VIEW-BLK-42",
            price="199.90",
            compare_price="249.90",
            stock=8,
            reserved_stock=0,
            is_default=True,
        )

    def _payload(self):
        return {
            "tenant_id": self.tenant.id,
            "id": self.product.id,
            "slug": self.product.slug,
            "name": self.product.name,
            "sku": self.variant.sku,
            "effective_variant_label": "Preto · 42",
            "main_image_url": "https://cdn.hubx.market/cart-view.jpg",
            "main_image_alt": "Produto Cart View",
            "price": "199.90",
            "compare_price": "249.90",
        }

    def test_cart_page_renders_empty_state_without_active_cart(self):
        response = self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/cart_page.html")
        self.assertContains(response, "Seu carrinho está vazio")
        self.assertContains(response, "Continuar comprando")
        self.assertContains(response, reverse("storefront:catalog-list"))

    def test_cart_page_renders_active_session_cart_items(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=2,
        )

        response = self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Produto Cart View")
        self.assertContains(response, "Preto · 42")
        self.assertContains(response, "SKU VIEW-BLK-42")
        self.assertContains(response, "R$ 199,90")
        self.assertContains(response, "R$ 399,80")
        self.assertContains(response, "Frete e pagamento continuam no checkout")
        self.assertContains(response, "Entrega no próximo passo")
        self.assertContains(response, "Entrega padrão")
        self.assertContains(response, "A partir de R$ 24,90")
        self.assertContains(response, "Valores e prazos finais dependem do endereço")
        self.assertContains(response, "Próximo passo seguro")
        self.assertContains(response, "Seu carrinho está pronto para virar uma sessão de checkout")
        self.assertContains(response, "Itens revisáveis")
        self.assertContains(response, "Frete no checkout")
        self.assertContains(response, "Pedido ainda não criado")
        self.assertContains(response, "Ir para checkout")

    def test_cart_page_post_updates_and_removes_items_by_tenant_session(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        added = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=2,
        )
        cart_id = added["cart"]["id"]
        item_id = added["cart"]["items"][0]["id"]

        increment_response = self.client.post(
            reverse("cart:cart-page"),
            {
                "cart_id": cart_id,
                "item_id": item_id,
                "quantity": 2,
                "item_action": "increment",
            },
            HTTP_HOST=self.storefront_host,
        )
        self.assertEqual(increment_response.status_code, 302)
        item = CartItem.objects.get(pk=item_id)
        self.assertEqual(item.quantity, 3)

        decrement_response = self.client.post(
            reverse("cart:cart-page"),
            {
                "cart_id": cart_id,
                "item_id": item_id,
                "quantity": 3,
                "item_action": "decrement",
            },
            HTTP_HOST=self.storefront_host,
        )
        self.assertEqual(decrement_response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

        remove_response = self.client.post(
            reverse("cart:cart-page"),
            {
                "cart_id": cart_id,
                "item_id": item_id,
                "quantity": 2,
                "item_action": "remove",
            },
            HTTP_HOST=self.storefront_host,
        )
        self.assertEqual(remove_response.status_code, 302)
        self.assertFalse(CartItem.objects.exists())

    def test_cart_page_post_does_not_mutate_other_tenant_cart(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        added = cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=2,
        )
        item_id = added["cart"]["items"][0]["id"]

        self.client.post(
            reverse("cart:cart-page"),
            {
                "cart_id": added["cart"]["id"],
                "item_id": item_id,
                "quantity": 2,
                "item_action": "increment",
            },
            HTTP_HOST=self.other_storefront_host,
        )

        item = CartItem.objects.get(pk=item_id)
        self.assertEqual(item.quantity, 2)

    def test_cart_page_checkout_handoff_creates_checkout_session_and_converts_cart(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=2,
        )

        response = self.client.post(
            reverse("cart:cart-page"),
            {"cart_intent": "checkout"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("checkout:checkout-page"), response["Location"])
        self.assertIn("session_key=", response["Location"])
        self.assertEqual(CheckoutSession.objects.count(), 1)

        checkout_session = CheckoutSession.objects.get()
        self.assertEqual(checkout_session.items.count(), 1)
        self.assertEqual(checkout_session.items.first().title, "Produto Cart View")
        self.assertEqual(checkout_session.items.first().quantity, 2)
        self.assertEqual(str(checkout_session.subtotal), "399.80")
        self.assertEqual(checkout_session.coupon_code, "")
        self.assertEqual(checkout_session.promotion_snapshot, {})

        cart = Cart.objects.get()
        self.assertEqual(cart.status, Cart.Status.CONVERTED)
        self.assertEqual(cart.converted_checkout_session_key, str(checkout_session.session_key))

    def test_cart_page_checkout_handoff_carries_valid_coupon_snapshot(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=2,
        )
        cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key=session_key,
            coupon_code="promo10",
        )

        response = self.client.post(
            reverse("cart:cart-page"),
            {"cart_intent": "checkout"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 302)
        checkout_session = CheckoutSession.objects.get()
        self.assertEqual(checkout_session.coupon_code, "PROMO10")
        self.assertEqual(str(checkout_session.discount_total), "39.98")
        self.assertEqual(str(checkout_session.grand_total), "384.72")
        self.assertEqual(
            checkout_session.promotion_snapshot,
            {
                "coupon_code": "PROMO10",
                "discount_total": "39.98",
                "source": "cart",
                "validation_result": "coupon-valid",
            },
        )

    def test_cart_page_checkout_handoff_does_not_carry_invalid_coupon_snapshot(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=1,
        )
        cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key=session_key,
            coupon_code="missing",
        )

        self.client.post(
            reverse("cart:cart-page"),
            {"cart_intent": "checkout"},
            HTTP_HOST=self.storefront_host,
        )

        checkout_session = CheckoutSession.objects.get()
        self.assertEqual(checkout_session.coupon_code, "")
        self.assertEqual(str(checkout_session.discount_total), "0.00")
        self.assertEqual(checkout_session.promotion_snapshot, {})

    def test_cart_page_applies_coupon_intent_without_discount(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=1,
        )

        response = self.client.post(
            reverse("cart:cart-page"),
            {"cart_intent": "apply_coupon", "coupon_code": " promo10 "},
            HTTP_HOST=self.storefront_host,
        )
        self.assertEqual(response.status_code, 302)

        cart = Cart.objects.get()
        self.assertEqual(cart.coupon_code, "PROMO10")
        self.assertEqual(str(cart.discount_total), "0.00")
        self.assertEqual(str(cart.total), "199.90")

        page = self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        self.assertContains(page, "PROMO10")
        self.assertContains(page, "nenhum desconto foi aplicado")

    def test_cart_page_removes_coupon_intent(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=1,
        )
        cart_commands.apply_coupon_intent(
            tenant_id=self.tenant.id,
            session_key=session_key,
            coupon_code="SAVE",
        )

        response = self.client.post(
            reverse("cart:cart-page"),
            {"cart_intent": "remove_coupon"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.get()
        self.assertEqual(cart.coupon_code, "")
        self.assertEqual(str(cart.discount_total), "0.00")

    def test_cart_page_does_not_show_cart_from_other_tenant(self):
        self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.storefront_host)
        session_key = self.client.session.session_key
        cart_commands.add_item(
            tenant_id=self.tenant.id,
            session_key=session_key,
            product=self._payload(),
            quantity=1,
        )

        response = self.client.get(reverse("cart:cart-page"), HTTP_HOST=self.other_storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu carrinho está vazio")
        self.assertNotContains(response, "Produto Cart View")

    def test_cart_page_query_does_not_create_cart_on_read(self):
        payload = cart_page_queries.get_cart_page_data(tenant_id=self.tenant.id, session_key="read-only-session")

        self.assertEqual(payload["cart_state"], "empty")
        self.assertEqual(payload["cart_items"], [])
