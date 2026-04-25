from django.urls import path

from .views import NotificationMetricsView


app_name = "notifications"


urlpatterns = [
    path("metrics/email-logs/", NotificationMetricsView.as_view(), name="email-log-metrics"),
]
