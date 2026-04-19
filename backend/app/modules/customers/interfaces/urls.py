from django.urls import path

from .views import AdminCustomerActionView, AdminCustomerDetailView, AdminCustomersListView


app_name = "customers"


urlpatterns = [
    path("", AdminCustomersListView.as_view(), name="admin-customers-list"),
    path("<slug:customer_slug>/", AdminCustomerDetailView.as_view(), name="admin-customers-detail"),
    path("<slug:customer_slug>/actions/update/", AdminCustomerActionView.as_view(), name="admin-customer-update"),
]
