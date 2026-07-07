from django.urls import path

from .views import PublicPlansView, PublicSignupView


app_name = "subscription_public"


urlpatterns = [
    path("signup/", PublicSignupView.as_view(), name="plans-signup"),
    path("", PublicPlansView.as_view(), name="plans"),
]
