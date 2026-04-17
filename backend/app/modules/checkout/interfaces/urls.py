from django.urls import path

from .views import CheckoutPageView


app_name = "checkout"


urlpatterns = [
    path("", CheckoutPageView.as_view(), name="checkout-page"),
]
