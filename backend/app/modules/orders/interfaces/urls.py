from django.urls import path

from .views import AdminOrderActionView, AdminOrderDetailView, AdminOrdersListView


app_name = "orders"


urlpatterns = [
    path("", AdminOrdersListView.as_view(), name="admin-orders-list"),
    path("<slug:order_number>/actions/update/", AdminOrderActionView.as_view(), name="admin-order-update"),
    path("<slug:order_number>/", AdminOrderDetailView.as_view(), name="admin-orders-detail"),
]
