from django.urls import path

from .views import (
    AdminProductDetailView,
    AdminProductFormView,
    AdminProductsListView,
)


app_name = "catalog"


urlpatterns = [
    path("products/", AdminProductsListView.as_view(), name="admin-products-list"),
    path("products/new/", AdminProductFormView.as_view(), name="admin-products-create"),
    path("products/<slug:product_slug>/", AdminProductDetailView.as_view(), name="admin-products-detail"),
    path("products/<slug:product_slug>/edit/", AdminProductFormView.as_view(), name="admin-products-edit"),
]
