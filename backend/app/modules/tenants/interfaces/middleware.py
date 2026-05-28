from __future__ import annotations
from typing import Callable

from django.conf import settings
from django.http import Http404

from ..models import Tenant


LOCAL_HOSTS = {"localhost", "127.0.0.1"}


class TenantSubdomainMiddleware:
    """Resolve tenant by subdomain and attach it to request.tenant.

    Rules (docs):
    - Tenant resolved only by subdomain under HUBX_MARKET_ROOT_DOMAIN
    - Reserved subdomains are ignored (request.tenant = None)
    - If a non-reserved subdomain under root domain does not map to a tenant: 404
    - Local hosts (localhost/127.0.0.1) are ignored
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

        # Exact root domain or reserved subdomain? ignore
        if host == self.root_domain:
            return self.get_response(request)

        suffix = "." + self.root_domain
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
                return self.get_response(request)

        if bool(getattr(settings, "HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED", False)):
            tenant = Tenant.objects.filter(custom_domain__iexact=host, is_active=True).first()
            if tenant is not None:
                request.tenant = tenant
                request.tenant_resolution_source = "custom_domain"
                return self.get_response(request)

        return self.get_response(request)
