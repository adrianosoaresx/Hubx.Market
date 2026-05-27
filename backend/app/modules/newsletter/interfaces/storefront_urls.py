from django.urls import path

from .views import StorefrontNewsletterSubscribeView


app_name = "storefront_newsletter"


urlpatterns = [
    path("", StorefrontNewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]
