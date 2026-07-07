from django.urls import path

from .storefront_branding_views import StorefrontBrandingSettingsView


app_name = "tenant_branding"


urlpatterns = [
    path("", StorefrontBrandingSettingsView.as_view(), name="storefront-branding-settings"),
]
