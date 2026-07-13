from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.assistant.application.assistant_knowledge_service import assistant_knowledge_service
from app.modules.assistant.application.assistant_feedback_commands import assistant_feedback_commands
from app.modules.assistant.application.assistant_query_service import assistant_query_service
from app.modules.assistant.models import AssistantConversation, AssistantFeedback, AssistantMessage
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


TEST_MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "app.modules.tenants.interfaces.middleware.TenantSubdomainMiddleware",
    "app.modules.tenants.interfaces.middleware.DemoTenantReadOnlyMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "app.modules.accounts.interfaces.middleware.OwnerContextMiddleware",
    "app.modules.accounts.interfaces.middleware.PlatformOwnerContextMiddleware",
    "app.modules.accounts.interfaces.middleware.OpsAuthenticationGateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


@override_settings(
    ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
    ASSISTANT_LLM_ENABLED=False,
    MIDDLEWARE=TEST_MIDDLEWARE,
)
class AssistantContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Assistente", slug="loja-assistente", subdomain="loja-assistente")
        self.other_tenant = Tenant.objects.create(name="Outra Assistente", slug="outra-assistente", subdomain="outra-assistente")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.assistant@hubx.market",
            role="viewer",
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="owner-assistant",
            email="owner.assistant@hubx.market",
            password="secret",
        )

    def test_assistant_view_requires_authenticated_owner_when_ops_gate_enabled(self):
        with override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True):
            anonymous = self.client.get(reverse("assistant:admin-assistant"), HTTP_HOST=self.host)
            self.assertEqual(anonymous.status_code, 302)
            self.assertTrue(anonymous["Location"].startswith("/accounts/login/?next="))

            outsider = User.objects.create_user(username="outsider", email="outsider@hubx.market", password="secret")
            self.client.force_login(outsider)
            forbidden = self.client.get(reverse("assistant:admin-assistant"), HTTP_HOST=self.host)
            self.assertEqual(forbidden.status_code, 403)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_any_ops_role_can_open_assistant_page(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("assistant:admin-assistant"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_assistant_page.html")
        self.assertContains(response, "Assistente")
        self.assertContains(response, "Como cadastro um produto corretamente?")

    def test_fallback_answer_saves_sanitized_messages_and_audit_without_content(self):
        question = "Qual a diferenca entre produto e variante? token=abc1234567890"

        result = assistant_query_service.ask(
            tenant_id=self.tenant.id,
            owner_user=self.owner,
            question=question,
        )

        self.assertEqual(result["result"], "assistant-answered-fallback")
        self.assertEqual(result["source"], AssistantMessage.Source.FALLBACK)
        conversation = AssistantConversation.objects.get()
        self.assertEqual(conversation.tenant, self.tenant)
        messages = list(conversation.messages.order_by("id"))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, AssistantMessage.Role.USER)
        self.assertIn("[redigido]", messages[0].content)
        self.assertNotIn("abc1234567890", messages[0].content)
        self.assertIn("produto", messages[1].content.lower())
        self.assertIn("variante", messages[1].content.lower())
        self.assertIn("docs/assistant/catalogo.md", messages[1].content)
        self.assertEqual(messages[1].sources[0]["path"], "docs/assistant/catalogo.md")

        audit = AuditLog.objects.get(module="assistant", action="assistant.question_answered")
        self.assertEqual(audit.tenant, self.tenant)
        self.assertEqual(audit.metadata["source"], AssistantMessage.Source.FALLBACK)
        self.assertIn("source_count", audit.metadata)
        self.assertNotIn("produto", str(audit.metadata).lower())
        self.assertNotIn("abc1234567890", str(audit.metadata))

    def test_knowledge_search_prioritizes_assistant_guides(self):
        hits = assistant_knowledge_service.search(question="Como cadastrar um produto corretamente?")

        self.assertTrue(hits)
        self.assertTrue(hits[0].path.startswith("docs/assistant/"))
        self.assertIn("produto", hits[0].excerpt.lower())

    def test_knowledge_smoke_command_passes_real_questions(self):
        output = StringIO()

        call_command("assistant_knowledge_smoke", "--fail-on-error", stdout=output)

        value = output.getvalue()
        self.assertIn("result=assistant-knowledge-smoke-passed", value)
        self.assertIn("Como cadastro um produto?", value)
        self.assertIn("docs/assistant/catalogo.md", value)

    def test_conversation_cannot_be_continued_from_another_tenant(self):
        first = assistant_query_service.ask(
            tenant_id=self.tenant.id,
            owner_user=self.owner,
            question="Como configurar a marca da loja?",
        )
        other_owner = OwnerUser.objects.create(
            tenant=self.other_tenant,
            email="other.assistant@hubx.market",
            role="owner",
            is_active=True,
        )

        second = assistant_query_service.ask(
            tenant_id=self.other_tenant.id,
            owner_user=other_owner,
            conversation_id=first["conversation_id"],
            question="Como publicar uma pagina institucional?",
        )

        self.assertEqual(second["result"], "assistant-answered-fallback")
        self.assertNotEqual(first["conversation_id"], second["conversation_id"])
        self.assertEqual(AssistantConversation.objects.filter(tenant=self.tenant).count(), 1)
        self.assertEqual(AssistantConversation.objects.filter(tenant=self.other_tenant).count(), 1)

    def test_feedback_is_tenant_scoped_to_assistant_message(self):
        result = assistant_query_service.ask(
            tenant_id=self.tenant.id,
            owner_user=self.owner,
            question="Quando o estoque baixa em um pedido?",
        )

        feedback = assistant_feedback_commands.record_feedback(
            tenant_id=self.tenant.id,
            message_id=result["message_id"],
            value=AssistantFeedback.Value.USEFUL,
            comment="secret=abc123456789",
        )
        blocked = assistant_feedback_commands.record_feedback(
            tenant_id=self.other_tenant.id,
            message_id=result["message_id"],
            value=AssistantFeedback.Value.NOT_USEFUL,
        )

        self.assertEqual(feedback["result"], "assistant-feedback-recorded")
        self.assertEqual(blocked["result"], "assistant-feedback-not-found")
        saved = AssistantFeedback.objects.get()
        self.assertEqual(saved.value, AssistantFeedback.Value.USEFUL)
        self.assertIn("[redigido]", saved.comment)
        self.assertNotIn("abc123456789", saved.comment)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_post_question_through_view_redirects_to_tenant_conversation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("assistant:admin-assistant"),
            data={"question": "Como publicar uma pagina institucional?"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        conversation = AssistantConversation.objects.get(tenant=self.tenant)
        self.assertIn(f"conversation_id={conversation.id}", response["Location"])
        self.assertEqual(conversation.messages.count(), 2)

        page = self.client.get(
            f"{reverse('assistant:admin-assistant')}?conversation_id={conversation.id}",
            HTTP_HOST=self.host,
        )
        self.assertContains(page, "Fontes consultadas")
        self.assertContains(page, "docs/assistant/paginas.md")
