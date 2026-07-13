from django.contrib import admin

from app.modules.assistant.models import AssistantConversation, AssistantFeedback, AssistantMessage


@admin.register(AssistantConversation)
class AssistantConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "owner_email", "title", "created_at", "updated_at")
    list_filter = ("tenant", "created_at")
    search_fields = ("title", "owner_email")


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "source", "created_at")
    list_filter = ("role", "source", "created_at")
    search_fields = ("content",)


@admin.register(AssistantFeedback)
class AssistantFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "value", "created_at")
    list_filter = ("value", "created_at")

