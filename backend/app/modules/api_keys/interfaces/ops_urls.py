from django.urls import path

from .ops_views import (
    AdminApiKeyCreateView,
    AdminApiKeyListView,
    AdminApiKeyQuotaListView,
    AdminApiKeyRevokeView,
)


app_name = "api_keys_ops"


urlpatterns = [
    path("", AdminApiKeyListView.as_view(), name="admin-api-keys-list"),
    path("new/", AdminApiKeyCreateView.as_view(), name="admin-api-key-create"),
    path("<int:key_id>/revoke/", AdminApiKeyRevokeView.as_view(), name="admin-api-key-revoke"),
    path("quotas/", AdminApiKeyQuotaListView.as_view(), name="admin-api-key-quotas-list"),
]
