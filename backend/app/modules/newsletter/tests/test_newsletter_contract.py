from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.newsletter.application.admin_newsletter_queries import admin_newsletter_queries
from app.modules.newsletter.application.newsletter_subscription_commands import newsletter_subscription_commands
from app.modules.newsletter.models import NewsletterSubscriber
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class NewsletterContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Newsletter", slug="loja-newsletter", subdomain="loja-newsletter")
        self.other_tenant = Tenant.objects.create(name="Outra Newsletter", slug="outra-newsletter", subdomain="outra-newsletter")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"

    def test_subscribe_creates_tenant_scoped_opt_in(self):
        result = newsletter_subscription_commands.subscribe(
            tenant_id=self.tenant.id,
            email=" CLIENTE@EMAIL.COM ",
            name="Cliente",
            source="storefront_test",
        )

        self.assertEqual(result["result"], "newsletter-subscribed")
        subscriber = NewsletterSubscriber.objects.get()
        self.assertEqual(subscriber.tenant, self.tenant)
        self.assertEqual(subscriber.email, "cliente@email.com")
        self.assertEqual(subscriber.name, "Cliente")
        self.assertEqual(subscriber.status, NewsletterSubscriber.Status.SUBSCRIBED)
        self.assertIsNotNone(subscriber.consented_at)

    def test_subscribe_is_idempotent_per_tenant(self):
        NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="cliente@email.com",
            status=NewsletterSubscriber.Status.UNSUBSCRIBED,
        )

        result = newsletter_subscription_commands.subscribe(
            tenant_id=self.tenant.id,
            email="cliente@email.com",
            name="Cliente reativado",
        )

        self.assertEqual(result["result"], "newsletter-resubscribed")
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)
        subscriber = NewsletterSubscriber.objects.get()
        self.assertEqual(subscriber.status, NewsletterSubscriber.Status.SUBSCRIBED)
        self.assertEqual(subscriber.name, "Cliente reativado")
        self.assertIsNone(subscriber.unsubscribed_at)

    def test_same_email_can_subscribe_in_different_tenants(self):
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="cliente@email.com")

        result = newsletter_subscription_commands.subscribe(tenant_id=self.tenant.id, email="cliente@email.com")

        self.assertEqual(result["result"], "newsletter-subscribed")
        self.assertEqual(NewsletterSubscriber.objects.filter(email="cliente@email.com").count(), 2)

    def test_unsubscribe_only_affects_current_tenant(self):
        current = NewsletterSubscriber.objects.create(tenant=self.tenant, email="cliente@email.com")
        other = NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="cliente@email.com")

        result = newsletter_subscription_commands.unsubscribe(tenant_id=self.tenant.id, email="cliente@email.com")

        self.assertEqual(result["result"], "newsletter-unsubscribed")
        current.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(current.status, NewsletterSubscriber.Status.UNSUBSCRIBED)
        self.assertEqual(other.status, NewsletterSubscriber.Status.SUBSCRIBED)

    def test_admin_query_lists_only_current_tenant_subscribers(self):
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="cliente@email.com")
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="outro@email.com")

        subscribers = admin_newsletter_queries.list_subscribers(tenant_id=self.tenant.id)

        self.assertEqual([subscriber["email"] for subscriber in subscribers], ["cliente@email.com"])

    def test_storefront_subscribe_view_creates_opt_in(self):
        response = self.client.post(
            reverse("storefront_newsletter:newsletter-subscribe"),
            {
                "name": "Cliente",
                "email": "cliente@email.com",
                "consent_label": "Aceito receber novidades.",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=subscribed", response["Location"])
        subscriber = NewsletterSubscriber.objects.get()
        self.assertEqual(subscriber.tenant, self.tenant)
        self.assertEqual(subscriber.source, "storefront_newsletter_page")

    def test_storefront_subscribe_view_rejects_invalid_email(self):
        response = self.client.post(
            reverse("storefront_newsletter:newsletter-subscribe"),
            {"email": "invalido", "consent_label": "Aceito receber novidades."},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Informe um e-mail válido.", status_code=400)
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_admin_list_view_renders_current_tenant_subscribers(self):
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="cliente@email.com", name="Cliente")
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="outro@email.com")

        response = self.client.get(reverse("newsletter:admin-newsletter-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_newsletter_list_page.html")
        self.assertContains(response, "cliente@email.com")
        self.assertNotContains(response, "outro@email.com")

    def test_admin_list_view_filters_status(self):
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@email.com")
        NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="off@email.com",
            status=NewsletterSubscriber.Status.UNSUBSCRIBED,
        )

        response = self.client.get(
            reverse("newsletter:admin-newsletter-list"),
            {"status": NewsletterSubscriber.Status.UNSUBSCRIBED},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "off@email.com")
        self.assertNotContains(response, "ativo@email.com")
