from django.urls import path

from .views import AdminCustomerActionView, AdminCustomerDetailView, AdminCustomersListView, CustomerMetricsView


app_name = "customers"


urlpatterns = [
    path("metrics/data-issues/", CustomerMetricsView.as_view(), name="customer-metrics"),
    path("", AdminCustomersListView.as_view(), name="admin-customers-list"),
    path("<slug:customer_slug>/", AdminCustomerDetailView.as_view(), name="admin-customers-detail"),
    path("<slug:customer_slug>/actions/update/", AdminCustomerActionView.as_view(), name="admin-customer-update"),
]
