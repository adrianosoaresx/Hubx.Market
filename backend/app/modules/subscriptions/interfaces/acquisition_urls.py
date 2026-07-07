from django.urls import path

from .views import (
    PlatformAcquisitionConvertView,
    PlatformAcquisitionDetailView,
    PlatformAcquisitionDiscardView,
    PlatformAcquisitionListView,
)


app_name = "subscription_acquisitions"


urlpatterns = [
    path("", PlatformAcquisitionListView.as_view(), name="platform-acquisitions-list"),
    path("<int:lead_id>/", PlatformAcquisitionDetailView.as_view(), name="platform-acquisitions-detail"),
    path("<int:lead_id>/convert/", PlatformAcquisitionConvertView.as_view(), name="platform-acquisitions-convert"),
    path("<int:lead_id>/discard/", PlatformAcquisitionDiscardView.as_view(), name="platform-acquisitions-discard"),
]
