from django.urls import path

from .views import ApiKeyPublicEndpointMetricsView


app_name = "api_keys"


urlpatterns = [
    path("metrics/public-endpoints/", ApiKeyPublicEndpointMetricsView.as_view(), name="public-endpoint-metrics"),
]
