from django.urls import path

from .views import (
    PlatformTenantAdminCreateView,
    PlatformTenantAdminCustomDomainActionView,
    PlatformTenantAdminDetailView,
    PlatformTenantAdminListView,
    PlatformTenantAdminOwnerBootstrapActionView,
    PlatformTenantAdminStateActionView,
)


app_name = "tenants"


urlpatterns = [
    path("", PlatformTenantAdminListView.as_view(), name="platform-tenants-list"),
    path("new/", PlatformTenantAdminCreateView.as_view(), name="platform-tenants-create"),
    path("<slug:tenant_slug>/state/", PlatformTenantAdminStateActionView.as_view(), name="platform-tenants-state"),
    path(
        "<slug:tenant_slug>/custom-domain/",
        PlatformTenantAdminCustomDomainActionView.as_view(),
        name="platform-tenants-custom-domain",
    ),
    path(
        "<slug:tenant_slug>/owner-bootstrap/",
        PlatformTenantAdminOwnerBootstrapActionView.as_view(),
        name="platform-tenants-owner-bootstrap",
    ),
    path("<slug:tenant_slug>/", PlatformTenantAdminDetailView.as_view(), name="platform-tenants-detail"),
]
