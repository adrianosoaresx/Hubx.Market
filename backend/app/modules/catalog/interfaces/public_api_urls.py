from django.urls import path

from .public_api_views import PublicCatalogProductDetailApiView, PublicCatalogProductsApiView


app_name = "catalog_public_api"


urlpatterns = [
    path("products/", PublicCatalogProductsApiView.as_view(), name="products-list"),
    path("products/<slug:slug>/", PublicCatalogProductDetailApiView.as_view(), name="products-detail"),
]
