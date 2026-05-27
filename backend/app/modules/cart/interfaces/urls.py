from django.urls import path

from .views import CartPageView


app_name = "cart"


urlpatterns = [
    path("", CartPageView.as_view(), name="cart-page"),
]
