from django.urls import path

from .owner_views import AdminOwnerActionView, AdminOwnersListView


app_name = "owners"


urlpatterns = [
    path("", AdminOwnersListView.as_view(), name="admin-owners-list"),
    path("<int:owner_id>/actions/update/", AdminOwnerActionView.as_view(), name="admin-owner-update"),
]
