from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views import View

from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics


class ApiKeyPublicEndpointMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(getattr(settings, "API_KEYS_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de chaves de API indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        return HttpResponse(
            api_key_public_endpoint_metrics.export_prometheus_metrics(),
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )
