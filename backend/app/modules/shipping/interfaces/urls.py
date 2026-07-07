from django.urls import path

from .views import (
    AdminShippingActionView,
    AdminShippingLabelView,
    AdminShippingListView,
    AdminShippingProviderSettingsActionView,
    AdminShippingProviderSettingsView,
    ShippingMetricsView,
)


app_name = "shipping"


urlpatterns = [
    path("", AdminShippingListView.as_view(), name="admin-shipping-list"),
    path("metrics/", ShippingMetricsView.as_view(), name="shipping-metrics"),
    path("provider/", AdminShippingProviderSettingsView.as_view(), name="admin-shipping-provider"),
    path("provider/actions/update/", AdminShippingProviderSettingsActionView.as_view(), name="admin-shipping-provider-update"),
    path("<str:order_number>/label/", AdminShippingLabelView.as_view(), name="admin-shipping-label"),
    path("<str:order_number>/actions/", AdminShippingActionView.as_view(), name="admin-shipping-action"),
]
