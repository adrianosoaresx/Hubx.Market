from django.urls import path

from .views import CatalogListView, ProductDetailView


app_name = "storefront"


urlpatterns = [
    path("", CatalogListView.as_view(), name="catalog-list"),
    path("<slug:product_slug>/", ProductDetailView.as_view(), name="product-detail"),
]
