from django.urls import path

from .views import AdminAssistantFeedbackView, AdminAssistantView


app_name = "assistant"


urlpatterns = [
    path("", AdminAssistantView.as_view(), name="admin-assistant"),
    path("feedback/", AdminAssistantFeedbackView.as_view(), name="admin-assistant-feedback"),
]

