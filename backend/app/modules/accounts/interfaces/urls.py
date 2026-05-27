from django.urls import path

from .views import (
    AccountAddressesView,
    AccountAddressCreateReadyView,
    AccountAddressDeleteReadyView,
    AccountAddressEditReadyView,
    AccountOrderDetailView,
    AccountOrderReviewCreateView,
    AccountOrdersView,
    AccountOverviewView,
    AccountProfileView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    OwnerMfaChallengeView,
    OwnerAccessMetricsView,
    OwnerMfaProviderHealthMetricsView,
    RegisterView,
    ResetPasswordView,
)


app_name = "accounts"


urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("login/mfa/", OwnerMfaChallengeView.as_view(), name="owner-mfa-challenge"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("metrics/owner-access/", OwnerAccessMetricsView.as_view(), name="owner-access-metrics"),
    path("metrics/owner-mfa-provider-health/", OwnerMfaProviderHealthMetricsView.as_view(), name="owner-mfa-provider-health-metrics"),
    path("register/", RegisterView.as_view(), name="register"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/<str:uidb64>/<str:token>/", ResetPasswordView.as_view(), name="reset-password-token"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("account/", AccountOverviewView.as_view(), name="account-overview"),
    path("account/orders/", AccountOrdersView.as_view(), name="account-orders"),
    path("account/orders/<str:order_number>/", AccountOrderDetailView.as_view(), name="account-order-detail"),
    path(
        "account/orders/<str:order_number>/reviews/<int:product_id>/new/",
        AccountOrderReviewCreateView.as_view(),
        name="account-order-review-create",
    ),
    path("account/addresses/", AccountAddressesView.as_view(), name="account-addresses"),
    path("account/addresses/new/", AccountAddressCreateReadyView.as_view(), name="account-address-create"),
    path("account/addresses/<int:address_id>/edit/", AccountAddressEditReadyView.as_view(), name="account-address-edit"),
    path("account/addresses/<int:address_id>/remove/", AccountAddressDeleteReadyView.as_view(), name="account-address-delete"),
    path("account/profile/", AccountProfileView.as_view(), name="account-profile"),
]
