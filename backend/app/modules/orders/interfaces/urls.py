from django.urls import path

from .views import AdminOrderDetailView, AdminOrdersListView


app_name = "orders"


urlpatterns = [
    path("", AdminOrdersListView.as_view(), name="admin-orders-list"),
    path("<slug:order_number>/", AdminOrderDetailView.as_view(), name="admin-orders-detail"),
]
