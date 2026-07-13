from __future__ import annotations

from dataclasses import dataclass

from app.modules.assistant.domain.content_safety import sanitize_comment


class AssistantFeedbackCommandService:
    def record_feedback(
        self,
        *,
        tenant_id: int | None,
        message_id: int | None,
        value: object,
        comment: object = "",
    ) -> dict[str, object]:
        from app.modules.assistant.models import AssistantFeedback, AssistantMessage

        if not tenant_id:
            return {"result": "assistant-feedback-tenant-required", "errors": {"__all__": "Tenant obrigatorio."}}
        normalized_value = str(value or "").strip()
        if normalized_value not in {AssistantFeedback.Value.USEFUL, AssistantFeedback.Value.NOT_USEFUL}:
            return {"result": "assistant-feedback-invalid", "errors": {"value": "Feedback invalido."}}
        message = AssistantMessage._default_manager.filter(
            id=message_id,
            conversation__tenant_id=tenant_id,
            role=AssistantMessage.Role.ASSISTANT,
        ).first()
        if message is None:
            return {"result": "assistant-feedback-not-found", "errors": {"message": "Mensagem nao encontrada."}}
        feedback = AssistantFeedback._default_manager.create(
            message=message,
            value=normalized_value,
            comment=sanitize_comment(comment),
        )
        return {"result": "assistant-feedback-recorded", "feedback_id": feedback.id}


assistant_feedback_commands = AssistantFeedbackCommandService()

