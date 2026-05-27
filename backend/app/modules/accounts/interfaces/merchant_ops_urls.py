from django.urls import path

from .merchant_ops_views import MerchantOperationsDashboardView


app_name = "merchant_ops"


urlpatterns = [
    path("", MerchantOperationsDashboardView.as_view(), name="admin-dashboard"),
]
