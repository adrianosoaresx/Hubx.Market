from django.urls import path

from .views import AdminNewsletterListView


app_name = "newsletter"


urlpatterns = [
    path("", AdminNewsletterListView.as_view(), name="admin-newsletter-list"),
]
