from django.urls import path

from .views import (
    AccountAddressesView,
    AccountAddressCreateReadyView,
    AccountAddressDeleteReadyView,
    AccountAddressEditReadyView,
    AccountOrderDetailView,
    AccountOrdersView,
    AccountOverviewView,
    AccountProfileView,
    ForgotPasswordView,
    LoginView,
    RegisterView,
    ResetPasswordView,
)


app_name = "accounts"


urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("account/", AccountOverviewView.as_view(), name="account-overview"),
    path("account/orders/", AccountOrdersView.as_view(), name="account-orders"),
    path("account/orders/<str:order_number>/", AccountOrderDetailView.as_view(), name="account-order-detail"),
    path("account/addresses/", AccountAddressesView.as_view(), name="account-addresses"),
    path("account/addresses/new/", AccountAddressCreateReadyView.as_view(), name="account-address-create"),
    path("account/addresses/<int:address_id>/edit/", AccountAddressEditReadyView.as_view(), name="account-address-edit"),
    path("account/addresses/<int:address_id>/remove/", AccountAddressDeleteReadyView.as_view(), name="account-address-delete"),
    path("account/profile/", AccountProfileView.as_view(), name="account-profile"),
]
