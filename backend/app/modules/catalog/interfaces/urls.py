from django.urls import path

from .views import (
    AdminConversionAnalyticsView,
    AdminProductDeactivateView,
    AdminProductDetailView,
    AdminProductFormView,
    AdminProductVariantCreateView,
    AdminProductVariantDeactivateView,
    AdminProductVariantDefaultView,
    AdminProductsListView,
    CatalogMetricsView,
)


app_name = "catalog"


urlpatterns = [
    path("analytics/", AdminConversionAnalyticsView.as_view(), name="admin-conversion-analytics"),
    path("metrics/publication-issues/", CatalogMetricsView.as_view(), name="catalog-metrics"),
    path("products/", AdminProductsListView.as_view(), name="admin-products-list"),
    path("products/new/", AdminProductFormView.as_view(), name="admin-products-create"),
    path("products/<slug:product_slug>/variants/new/", AdminProductVariantCreateView.as_view(), name="admin-product-variant-create"),
    path(
        "products/<slug:product_slug>/variants/<int:variant_id>/default/",
        AdminProductVariantDefaultView.as_view(),
        name="admin-product-variant-default",
    ),
    path(
        "products/<slug:product_slug>/variants/<int:variant_id>/deactivate/",
        AdminProductVariantDeactivateView.as_view(),
        name="admin-product-variant-deactivate",
    ),
    path("products/<slug:product_slug>/actions/deactivate/", AdminProductDeactivateView.as_view(), name="admin-products-deactivate"),
    path("products/<slug:product_slug>/", AdminProductDetailView.as_view(), name="admin-products-detail"),
    path("products/<slug:product_slug>/edit/", AdminProductFormView.as_view(), name="admin-products-edit"),
]
