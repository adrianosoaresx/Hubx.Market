from django.urls import path

from .views import AdminCustomerDetailView, AdminCustomersListView


app_name = "customers"


urlpatterns = [
    path("", AdminCustomersListView.as_view(), name="admin-customers-list"),
    path("<slug:customer_slug>/", AdminCustomerDetailView.as_view(), name="admin-customers-detail"),
]
