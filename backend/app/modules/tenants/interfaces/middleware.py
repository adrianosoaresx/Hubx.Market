from __future__ import annotations
from typing import Callable

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden

from ..models import Tenant


LOCAL_HOSTS = {"localhost", "127.0.0.1"}
DEMO_READ_ONLY_ALLOWED_PATHS = (
    "/accounts/demo-session/",
    "/accounts/login/",
    "/accounts/login/mfa/",
    "/accounts/logout/",
)
MAINTENANCE_ALLOWED_PATHS = (
    "/accounts/",
    "/ops/",
    "/admin/",
    "/static/",
    "/media/",
    "/favicon.ico",
)


class TenantSubdomainMiddleware:
    """Resolve tenant by subdomain and attach it to request.tenant.

    Rules (docs):
    - Tenant resolved only by subdomain under HUBX_MARKET_ROOT_DOMAIN
    - Reserved subdomains are ignored (request.tenant = None)
    - If a non-reserved subdomain under root domain does not map to a tenant: 404
    - Local root hosts (localhost/127.0.0.1) are ignored
    - Local subdomains (*.localhost) resolve tenants for dev/demo flows
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.root_domain: str = getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market").lower()
        reserved = getattr(settings, "HUBX_MARKET_RESERVED_SUBDOMAINS", ["www", "app", "api", "docs", "cdn", "admin"])
        self.reserved = {s.lower() for s in reserved}

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        request.tenant = None  # default
        request.tenant_resolution_source = ""

        # local / test hosts: ignore
        if host in LOCAL_HOSTS:
            return self.get_response(request)

        root_domain = self._root_domain_for_host(host)

        # Exact root domain or reserved subdomain? ignore
        if host == root_domain:
            return self.get_response(request)

        suffix = "." + root_domain
        if host.endswith(suffix):
            subpart = host[: -len(suffix)]  # e.g. "lojax" or "foo.bar"
            if not subpart:
                return self.get_response(request)
            # Use left-most label as tenant id (simple, extensible later if needed)
            subdomain = subpart.split(".")[0]
            if subdomain in self.reserved:
                return self.get_response(request)

            try:
                tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                # Host looks like a store subdomain but no tenant exists -> 404
                raise Http404("Tenant not found")
            else:
                request.tenant = tenant
                request.tenant_resolution_source = "subdomain"
                if self._tenant_in_maintenance_blocks_request(tenant=tenant, request=request):
                    return self._maintenance_response(tenant=tenant)
                return self.get_response(request)

        if bool(getattr(settings, "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED", False)):
            tenant = Tenant.objects.filter(custom_domain__iexact=host, is_active=True).first()
            if tenant is not None:
                request.tenant = tenant
                request.tenant_resolution_source = "custom_domain"
                if self._tenant_in_maintenance_blocks_request(tenant=tenant, request=request):
                    return self._maintenance_response(tenant=tenant)
                return self.get_response(request)

        return self.get_response(request)

    def _root_domain_for_host(self, host: str) -> str:
        if host.endswith(".localhost"):
            return "localhost"
        return self.root_domain

    def _tenant_in_maintenance_blocks_request(self, *, tenant: Tenant, request) -> bool:
        if not bool(getattr(tenant, "maintenance_mode", False)):
            return False
        path = str(getattr(request, "path", "") or "/")
        return not any(path == allowed or path.startswith(allowed) for allowed in MAINTENANCE_ALLOWED_PATHS)

    def _maintenance_response(self, *, tenant: Tenant) -> HttpResponse:
        return HttpResponse(
            f"{tenant.name} esta em manutencao inicial. Acesse o admin para concluir a configuracao.",
            status=503,
        )


class DemoTenantReadOnlyMiddleware:
    """Block tenant-owned writes in the configured demo store.

    The demo still allows session/auth endpoints so visitors can enter and leave
    the prepared admin/customer profiles without mutating commerce data.
    """

    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        request.is_demo_read_only = self._is_demo_tenant(request)
        if (
            request.is_demo_read_only
            and str(getattr(request, "method", "") or "").upper() in self.unsafe_methods
            and not self._is_allowed_session_path(request)
        ):
            return HttpResponseForbidden("Demo somente leitura: ação bloqueada.")
        return self.get_response(request)

    def _is_demo_tenant(self, request) -> bool:
        tenant = getattr(request, "tenant", None)
        demo_subdomain = str(getattr(settings, "HUBX_MARKET_DEMO_TENANT_SUBDOMAIN", "hubx-demo") or "hubx-demo").strip().lower()
        return bool(
            tenant is not None
            and getattr(tenant, "is_active", False)
            and str(getattr(tenant, "subdomain", "") or "").strip().lower() == demo_subdomain
        )

    def _is_allowed_session_path(self, request) -> bool:
        path = str(getattr(request, "path", "") or "")
        return any(path == allowed or path.startswith(allowed) for allowed in DEMO_READ_ONLY_ALLOWED_PATHS)
