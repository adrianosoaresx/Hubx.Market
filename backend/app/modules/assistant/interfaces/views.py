from __future__ import annotations

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from app.modules.accounts.interfaces.admin_rbac import request_tenant_id
from app.modules.assistant.application.assistant_feedback_commands import assistant_feedback_commands
from app.modules.assistant.application.assistant_query_service import assistant_query_service


def _conversation_id(value: object) -> int | None:
    try:
        parsed = int(str(value or "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


class AdminAssistantView(TemplateView):
    template_name = "pages/templates/admin_assistant_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation_id = _conversation_id(self.request.GET.get("conversation_id"))
        page_data = assistant_query_service.get_page_data(
            tenant_id=request_tenant_id(self.request),
            conversation_id=conversation_id,
        )
        context.update(
            {
                "page_title": "Assistente",
                "page_eyebrow": "Ajuda operacional",
                "page_description": "Pergunte como usar melhor o Hubx Market com base na documentacao interna.",
                "form_action": reverse("assistant:admin-assistant"),
                "feedback_action": reverse("assistant:admin-assistant-feedback"),
                "question_value": "",
                "form_error": "",
                **page_data,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        conversation_id = _conversation_id(request.POST.get("conversation_id"))
        result = assistant_query_service.ask(
            tenant_id=request_tenant_id(request),
            owner_user=getattr(request, "owner_user", None),
            question=request.POST.get("question", ""),
            conversation_id=conversation_id,
        )
        if str(result.get("result", "")).startswith("assistant-answered"):
            return HttpResponseRedirect(
                f"{reverse('assistant:admin-assistant')}?conversation_id={result['conversation_id']}"
            )
        context = self.get_context_data(**kwargs)
        context.update(
            {
                "question_value": request.POST.get("question", ""),
                "form_error": (result.get("errors") or {}).get("__all__", "Nao foi possivel responder agora."),
            }
        )
        return self.render_to_response(context, status=400)


class AdminAssistantFeedbackView(View):
    def post(self, request, *args, **kwargs):
        conversation_id = _conversation_id(request.POST.get("conversation_id"))
        assistant_feedback_commands.record_feedback(
            tenant_id=request_tenant_id(request),
            message_id=_conversation_id(request.POST.get("message_id")),
            value=request.POST.get("value", ""),
            comment=request.POST.get("comment", ""),
        )
        target = reverse("assistant:admin-assistant")
        if conversation_id:
            target = f"{target}?conversation_id={conversation_id}"
        return HttpResponseRedirect(target)

