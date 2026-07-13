from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection

from app.modules.assistant.application.assistant_knowledge_service import AssistantKnowledgeService, assistant_knowledge_service
from app.modules.assistant.domain.content_safety import sanitize_answer, sanitize_question, title_from_question
from app.modules.assistant.infrastructure.llm_client import AssistantLlmClient, assistant_llm_client
from app.modules.audit.application.audit_log_commands import audit_log_commands


class AssistantRepository(Protocol):
    def ask(
        self,
        *,
        tenant_id: int | None,
        owner_user: object,
        question: str,
        conversation_id: int | None = None,
    ) -> dict[str, object]:
        ...

    def get_page_data(self, *, tenant_id: int | None, conversation_id: int | None = None) -> dict[str, object]:
        ...


def _owner_email(owner_user: object) -> str:
    return str(getattr(owner_user, "email", "") or "").strip()[:254]


def _owner_label(owner_user: object) -> str:
    email = _owner_email(owner_user)
    role = str(getattr(owner_user, "role", "") or "").strip()
    if email and role:
        return f"{email} ({role})"
    return email or role or "owner/admin"


def _fallback_answer(*, question: str, hits: list[object]) -> str:
    if not hits:
        return (
            "Ainda nao encontrei essa resposta na documentacao do Hubx Market. "
            "Posso ajudar melhor se a pergunta mencionar a area, como catalogo, pedidos, pagamentos, "
            "branding, paginas, cupons ou acesso administrativo."
        )
    lines = [
        "Nao encontrei um provedor de IA ativo agora, entao montei uma resposta direta com a documentacao local.",
        "",
        "O que a documentacao indica:",
    ]
    for hit in hits[:3]:
        excerpt = str(getattr(hit, "excerpt", "") or "").strip()
        if excerpt:
            lines.append(f"- {excerpt[:420]}")
    lines.extend(
        [
            "",
            "Fontes consultadas:",
            *[f"- {getattr(hit, 'path', '')}" for hit in hits[:5]],
        ]
    )
    return "\n".join(lines)


def _source_payload(hits: list[object]) -> list[dict[str, str]]:
    return [
        {
            "title": str(getattr(hit, "title", "") or "")[:120],
            "path": str(getattr(hit, "path", "") or "")[:240],
            "excerpt": str(getattr(hit, "excerpt", "") or "")[:500],
        }
        for hit in hits[:5]
    ]


class DjangoOrmAssistantRepository:
    def __init__(
        self,
        *,
        knowledge_service: AssistantKnowledgeService,
        llm_client: AssistantLlmClient,
    ) -> None:
        from app.modules.assistant.models import AssistantConversation, AssistantFeedback, AssistantMessage
        from app.modules.tenants.models import Tenant

        self.conversation_model = AssistantConversation
        self.feedback_model = AssistantFeedback
        self.message_model = AssistantMessage
        self.tenant_model = Tenant
        self.knowledge_service = knowledge_service
        self.llm_client = llm_client

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.conversation_model._meta.db_table,
                self.message_model._meta.db_table,
                self.feedback_model._meta.db_table,
                self.tenant_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _conversation(self, *, tenant_id: int, owner_user: object, question: str, conversation_id: int | None):
        if conversation_id:
            conversation = self.conversation_model._default_manager.filter(
                id=conversation_id,
                tenant_id=tenant_id,
            ).first()
            if conversation is not None:
                return conversation
        return self.conversation_model._default_manager.create(
            tenant_id=tenant_id,
            owner=getattr(owner_user, "id", None) and owner_user,
            owner_email=_owner_email(owner_user),
            title=title_from_question(question),
        )

    def ask(
        self,
        *,
        tenant_id: int | None,
        owner_user: object,
        question: str,
        conversation_id: int | None = None,
    ) -> dict[str, object]:
        if not tenant_id:
            return {"result": "assistant-tenant-required", "errors": {"__all__": "Tenant obrigatorio para o assistente."}}
        if not self.is_ready():
            return {"result": "assistant-unavailable", "errors": {"__all__": "Assistente indisponivel."}}
        if not self.tenant_model._default_manager.filter(pk=tenant_id).exists():
            return {"result": "assistant-tenant-required", "errors": {"__all__": "Tenant obrigatorio para o assistente."}}

        clean_question = sanitize_question(question)
        if not clean_question:
            return {"result": "assistant-question-required", "errors": {"question": "Digite uma pergunta."}}

        conversation = self._conversation(
            tenant_id=tenant_id,
            owner_user=owner_user,
            question=clean_question,
            conversation_id=conversation_id,
        )
        self.message_model._default_manager.create(
            conversation=conversation,
            role=self.message_model.Role.USER,
            source=self.message_model.Source.USER,
            content=clean_question,
        )

        hits = self.knowledge_service.search(question=clean_question)
        context = self.knowledge_service.context_for_llm(hits=hits)
        llm_response = self.llm_client.complete(question=clean_question, context=context)
        if llm_response.available:
            source = self.message_model.Source.LLM
            answer = llm_response.text
            result = "assistant-answered"
        else:
            source = self.message_model.Source.FALLBACK
            answer = _fallback_answer(question=clean_question, hits=hits)
            result = "assistant-answered-fallback"

        clean_answer = sanitize_answer(answer)
        sources = _source_payload(hits)
        assistant_message = self.message_model._default_manager.create(
            conversation=conversation,
            role=self.message_model.Role.ASSISTANT,
            source=source,
            content=clean_answer,
            sources=sources,
        )
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="assistant",
            action="assistant.question_answered",
            entity_type="AssistantConversation",
            entity_id=str(conversation.id),
            actor_label=_owner_label(owner_user),
            summary="Assistente operacional respondeu pergunta tenant-scoped.",
            metadata={
                "result": result,
                "source": source,
                "source_count": len(hits),
                "llm_reason": "" if llm_response.available else llm_response.reason,
            },
        )
        return {
            "result": result,
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "answer": clean_answer,
            "source": source,
            "sources": sources,
        }

    def get_page_data(self, *, tenant_id: int | None, conversation_id: int | None = None) -> dict[str, object]:
        conversations = []
        messages = []
        current_conversation = None
        if tenant_id and self.is_ready():
            queryset = self.conversation_model._default_manager.filter(tenant_id=tenant_id).order_by("-updated_at", "-id")
            conversations = [
                {
                    "id": conversation.id,
                    "title": conversation.title,
                    "updated_at": conversation.updated_at,
                }
                for conversation in queryset[:12]
            ]
            if conversation_id:
                current_conversation = queryset.filter(id=conversation_id).first()
            if current_conversation is None:
                current_conversation = queryset.first()
            if current_conversation is not None:
                messages = [
                    {
                        "id": message.id,
                        "role": message.role,
                        "source": message.source,
                        "content": message.content,
                        "sources": message.sources if isinstance(message.sources, list) else [],
                        "created_at": message.created_at,
                    }
                    for message in current_conversation.messages.all()[:40]
                ]
        return {
            "conversations": conversations,
            "current_conversation": current_conversation,
            "messages": messages,
            "suggestions": [
                "Como cadastro um produto corretamente?",
                "Qual a diferenca entre produto e variante?",
                "Quando o estoque baixa em um pedido?",
                "Como configurar a marca da loja?",
                "Como publicar uma pagina institucional?",
            ],
        }


@dataclass
class AssistantQueryService:
    repository: AssistantRepository

    def ask(
        self,
        *,
        tenant_id: int | None,
        owner_user: object,
        question: object,
        conversation_id: int | None = None,
    ) -> dict[str, object]:
        return self.repository.ask(
            tenant_id=tenant_id,
            owner_user=owner_user,
            question=str(question or ""),
            conversation_id=conversation_id,
        )

    def get_page_data(self, *, tenant_id: int | None, conversation_id: int | None = None) -> dict[str, object]:
        return self.repository.get_page_data(tenant_id=tenant_id, conversation_id=conversation_id)


assistant_query_service = AssistantQueryService(
    repository=DjangoOrmAssistantRepository(
        knowledge_service=assistant_knowledge_service,
        llm_client=assistant_llm_client,
    )
)
