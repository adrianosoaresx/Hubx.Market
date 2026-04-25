from django.urls import path

from .views import AdminOrderActionView, AdminOrderDetailView, AdminOrdersListView, InventoryExceptionMetricsView


app_name = "orders"


urlpatterns = [
    path("", AdminOrdersListView.as_view(), name="admin-orders-list"),
    path("metrics/inventory-exceptions/", InventoryExceptionMetricsView.as_view(), name="inventory-exception-metrics"),
    path("<slug:order_number>/actions/update/", AdminOrderActionView.as_view(), name="admin-order-update"),
    path("<slug:order_number>/", AdminOrderDetailView.as_view(), name="admin-orders-detail"),
]
