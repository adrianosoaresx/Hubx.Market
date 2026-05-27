from django.urls import path

from .views import (
    AdminConversionAnalyticsView,
    AdminProductDetailView,
    AdminProductFormView,
    AdminProductsListView,
    CatalogMetricsView,
)


app_name = "catalog"


urlpatterns = [
    path("analytics/", AdminConversionAnalyticsView.as_view(), name="admin-conversion-analytics"),
    path("metrics/publication-issues/", CatalogMetricsView.as_view(), name="catalog-metrics"),
    path("products/", AdminProductsListView.as_view(), name="admin-products-list"),
    path("products/new/", AdminProductFormView.as_view(), name="admin-products-create"),
    path("products/<slug:product_slug>/", AdminProductDetailView.as_view(), name="admin-products-detail"),
    path("products/<slug:product_slug>/edit/", AdminProductFormView.as_view(), name="admin-products-edit"),
]
