from django.db import models
from django.db.models import Q


class AssistantConversation(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="assistant_conversations")
    owner = models.ForeignKey(
        "accounts.OwnerUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_conversations",
    )
    owner_email = models.EmailField(blank=True)
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        indexes = [
            models.Index(fields=("tenant", "updated_at"), name="assistant_conv_tenant_upd_idx"),
            models.Index(fields=("tenant", "owner_email"), name="assistant_conv_owner_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.title}"


class AssistantMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"
        SYSTEM = "system", "Sistema"

    class Source(models.TextChoices):
        USER = "user", "Usuário"
        LLM = "llm", "LLM"
        FALLBACK = "fallback", "Fallback"
        SYSTEM = "system", "Sistema"

    conversation = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.SYSTEM)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                check=Q(role__in=("user", "assistant", "system")),
                name="assistant_message_role_valid",
            ),
            models.CheckConstraint(
                check=Q(source__in=("user", "llm", "fallback", "system")),
                name="assistant_message_source_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("conversation", "created_at"), name="assistant_msg_conv_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.conversation_id}:{self.role}"


class AssistantFeedback(models.Model):
    class Value(models.TextChoices):
        USEFUL = "useful", "Útil"
        NOT_USEFUL = "not_useful", "Não útil"

    message = models.ForeignKey(AssistantMessage, on_delete=models.CASCADE, related_name="feedback_items")
    value = models.CharField(max_length=16, choices=Value.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                check=Q(value__in=("useful", "not_useful")),
                name="assistant_feedback_value_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("message", "created_at"), name="assistant_feedback_msg_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.message_id}:{self.value}"
