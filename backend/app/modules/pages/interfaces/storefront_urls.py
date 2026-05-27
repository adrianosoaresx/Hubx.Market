from django.urls import path

from .views import StorefrontPageDetailView


app_name = "storefront_pages"


urlpatterns = [
    path("<slug:page_slug>/", StorefrontPageDetailView.as_view(), name="page-detail"),
]
