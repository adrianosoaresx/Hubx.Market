from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.newsletter.application.newsletter_campaign_commands import newsletter_campaign_commands
from app.modules.newsletter.application.admin_newsletter_queries import admin_newsletter_queries
from app.modules.newsletter.application.newsletter_subscription_commands import newsletter_subscription_commands
from app.modules.newsletter.models import NewsletterCampaign, NewsletterSubscriber
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class NewsletterContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Newsletter", slug="loja-newsletter", subdomain="loja-newsletter")
        self.other_tenant = Tenant.objects.create(name="Outra Newsletter", slug="outra-newsletter", subdomain="outra-newsletter")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"
        self.user = get_user_model().objects.create_user(
            username="marketing@hubx.market",
            email="marketing@hubx.market",
            password="secret",
        )

    def _login_owner(self, *, role: str = "owner"):
        OwnerUser.objects.update_or_create(
            tenant=self.tenant,
            email=self.user.email,
            defaults={"role": role, "is_active": True},
        )
        self.client.force_login(self.user)
        self.client.defaults["HTTP_HOST"] = self.host

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

    def test_campaign_command_creates_tenant_scoped_draft(self):
        result = newsletter_campaign_commands.create_campaign(
            tenant_id=self.tenant.id,
            title="Lançamento",
            subject="Novidades da loja",
            body_text="Confira a nova coleção.",
            actor_label="marketing@hubx.market",
        )

        self.assertEqual(result["result"], "newsletter-campaign-created")
        campaign = NewsletterCampaign.objects.get()
        self.assertEqual(campaign.tenant, self.tenant)
        self.assertEqual(campaign.status, NewsletterCampaign.Status.DRAFT)
        self.assertEqual(campaign.created_by_label, "marketing@hubx.market")

    def test_send_campaign_creates_email_logs_for_active_subscribers_only(self):
        active = NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@email.com", name="Ativo")
        NewsletterSubscriber.objects.create(
            tenant=self.tenant,
            email="off@email.com",
            status=NewsletterSubscriber.Status.UNSUBSCRIBED,
        )
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="outro@email.com")
        campaign = NewsletterCampaign.objects.create(
            tenant=self.tenant,
            title="Lançamento",
            subject="Novidades da loja",
            body_text="Confira a nova coleção.",
        )

        result = newsletter_campaign_commands.send_campaign(
            tenant_id=self.tenant.id,
            campaign_id=campaign.id,
            actor_label="marketing@hubx.market",
        )

        self.assertEqual(result["result"], "newsletter-campaign-sent")
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, NewsletterCampaign.Status.SENT)
        self.assertEqual(campaign.recipient_count, 1)
        log = EmailLog.objects.get()
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.recipient_email, active.email)
        self.assertEqual(log.source_event, "newsletter.campaign.sent")
        self.assertEqual(log.status, EmailLog.Status.PLANNED)

    def test_send_campaign_is_idempotent_after_sent(self):
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@email.com")
        campaign = NewsletterCampaign.objects.create(
            tenant=self.tenant,
            title="Lançamento",
            subject="Novidades da loja",
            body_text="Confira a nova coleção.",
        )

        first = newsletter_campaign_commands.send_campaign(tenant_id=self.tenant.id, campaign_id=campaign.id)
        second = newsletter_campaign_commands.send_campaign(tenant_id=self.tenant.id, campaign_id=campaign.id)

        self.assertEqual(first["result"], "newsletter-campaign-sent")
        self.assertEqual(second["result"], "newsletter-campaign-already-sent")
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_campaign_send_is_tenant_scoped(self):
        NewsletterSubscriber.objects.create(tenant=self.other_tenant, email="outro@email.com")
        campaign = NewsletterCampaign.objects.create(
            tenant=self.tenant,
            title="Lançamento",
            subject="Novidades da loja",
            body_text="Confira a nova coleção.",
        )

        result = newsletter_campaign_commands.send_campaign(
            tenant_id=self.other_tenant.id,
            campaign_id=campaign.id,
        )

        self.assertEqual(result["result"], "newsletter-campaign-not-found")
        self.assertEqual(EmailLog.objects.count(), 0)

    def test_admin_campaign_create_and_send_views_require_manage_permission(self):
        self._login_owner(role="marketing")
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@email.com")

        create_response = self.client.post(
            reverse("newsletter:admin-newsletter-campaign-create"),
            {
                "title": "Lançamento",
                "subject": "Novidades da loja",
                "body_text": "Confira a nova coleção.",
            },
        )
        campaign = NewsletterCampaign.objects.get()
        send_response = self.client.post(
            reverse("newsletter:admin-newsletter-campaign-send", kwargs={"campaign_id": campaign.id}),
        )

        self.assertEqual(create_response.status_code, 302)
        self.assertIn("status=created", create_response["Location"])
        self.assertEqual(send_response.status_code, 302)
        self.assertIn("status=sent", send_response["Location"])
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_viewer_cannot_read_or_manage_newsletter_campaigns(self):
        self._login_owner(role="viewer")
        NewsletterSubscriber.objects.create(tenant=self.tenant, email="ativo@email.com")
        campaign = NewsletterCampaign.objects.create(
            tenant=self.tenant,
            title="Lançamento",
            subject="Novidades da loja",
            body_text="Confira a nova coleção.",
        )

        list_response = self.client.get(reverse("newsletter:admin-newsletter-list"))
        create_response = self.client.post(
            reverse("newsletter:admin-newsletter-campaign-create"),
            {
                "title": "Bloqueada",
                "subject": "Bloqueada",
                "body_text": "Bloqueada",
            },
        )
        send_response = self.client.post(
            reverse("newsletter:admin-newsletter-campaign-send", kwargs={"campaign_id": campaign.id}),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Permissão necessária")
        self.assertNotContains(list_response, "ativo@email.com")
        self.assertNotContains(list_response, "Criar campanha")
        self.assertNotContains(list_response, "Enviar")
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(send_response.status_code, 302)
        self.assertEqual(EmailLog.objects.count(), 0)
