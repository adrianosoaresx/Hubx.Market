from django.urls import path

from .views import AdminSubscriptionsListView


app_name = "subscriptions"


urlpatterns = [
    path("", AdminSubscriptionsListView.as_view(), name="admin-subscriptions-list"),
]
