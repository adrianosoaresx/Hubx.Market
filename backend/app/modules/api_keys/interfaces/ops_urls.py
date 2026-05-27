from django.urls import path

from .ops_views import AdminApiKeyQuotaListView


app_name = "api_keys_ops"


urlpatterns = [
    path("quotas/", AdminApiKeyQuotaListView.as_view(), name="admin-api-key-quotas-list"),
]
