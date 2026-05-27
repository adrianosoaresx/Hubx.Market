from django.urls import path

from .owner_views import (
    AdminOwnerActionView,
    AdminOwnerFormView,
    AdminOwnerInviteView,
    AdminOwnerMfaDeactivateView,
    AdminOwnerMfaListView,
    AdminOwnerMfaVerifyView,
    AdminOwnersListView,
)


app_name = "owners"


urlpatterns = [
    path("", AdminOwnersListView.as_view(), name="admin-owners-list"),
    path("new/", AdminOwnerFormView.as_view(), name="admin-owner-create"),
    path("mfa/", AdminOwnerMfaListView.as_view(), name="admin-owner-mfa-list"),
    path("mfa/<int:factor_id>/verify/", AdminOwnerMfaVerifyView.as_view(), name="admin-owner-mfa-verify"),
    path("mfa/<int:factor_id>/deactivate/", AdminOwnerMfaDeactivateView.as_view(), name="admin-owner-mfa-deactivate"),
    path("<int:owner_id>/edit/", AdminOwnerFormView.as_view(), name="admin-owner-edit"),
    path("<int:owner_id>/actions/update/", AdminOwnerActionView.as_view(), name="admin-owner-update"),
    path("<int:owner_id>/actions/invite/", AdminOwnerInviteView.as_view(), name="admin-owner-invite"),
]
