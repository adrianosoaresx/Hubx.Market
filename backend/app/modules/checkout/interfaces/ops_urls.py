from django.urls import path

from .views import CheckoutMetricsView


app_name = "checkout_ops"


urlpatterns = [
    path("metrics/session-issues/", CheckoutMetricsView.as_view(), name="checkout-metrics"),
]
