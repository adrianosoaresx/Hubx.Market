from django.urls import path

from .views import AdminSubscriptionBillingMethodView, AdminSubscriptionsListView


app_name = "subscriptions"


urlpatterns = [
    path("", AdminSubscriptionsListView.as_view(), name="admin-subscriptions-list"),
    path("billing-method/", AdminSubscriptionBillingMethodView.as_view(), name="admin-subscriptions-billing-method"),
]
