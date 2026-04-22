from django.urls import path

from .views import (
    HostedPaymentRedirectView,
    HostedPaymentReturnView,
    PaymentAlertMetricsView,
    PaymentWebhookView,
)


app_name = "payments"

urlpatterns = [
    path("webhook/", PaymentWebhookView.as_view(), name="webhook"),
    path("hosted/<uuid:attempt_key>/", HostedPaymentRedirectView.as_view(), name="hosted-redirect"),
    path("return/<uuid:attempt_key>/", HostedPaymentReturnView.as_view(), name="hosted-return"),
    path("metrics/alert-signals/", PaymentAlertMetricsView.as_view(), name="alert-metrics"),
]
