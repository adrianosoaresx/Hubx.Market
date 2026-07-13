from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from app.modules.audit.application.admin_audit_log_queries import admin_audit_log_queries
from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


class AdminAuditLogListView(TemplateView):
    template_name = "pages/templates/admin_audit_log_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        search_value = self.request.GET.get("q", "").strip()
        module_value = self.request.GET.get("module", "").strip()
        action_value = self.request.GET.get("action", "").strip()
        logs = admin_audit_log_queries.list_logs(
            tenant_id=tenant_id,
            module=module_value,
            action=action_value,
            search=search_value,
        )

        empty_title = "Nenhum evento auditável"
        empty_description = "Quando ações administrativas forem registradas, elas aparecerão aqui para este tenant."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar auditoria tenant-scoped."

        context.update(
            {
                "page_title": "Auditoria",
                "page_eyebrow": "Governança",
                "page_description": "Leitura tenant-scoped de eventos auditáveis administrativos.",
                "filter_action": reverse("audit:admin-audit-log-list"),
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar eventos",
                "search_placeholder": "Resumo, entidade, ator",
                "module_value": module_value,
                "action_value": action_value,
                "reset_url": reverse("audit:admin-audit-log-list"),
                "export_url": self._export_url(module=module_value, action=action_value),
                "columns": [
                    {"label": "Data"},
                    {"label": "Módulo"},
                    {"label": "Ação"},
                    {"label": "Entidade"},
                    {"label": "Ator"},
                    {"label": "Resumo"},
                ],
                "rows": [
                    {
                        "cells": [
                            log["created_at"],
                            log["module"],
                            log["action"],
                            log["entity"],
                            log["actor_label"],
                            log["summary"],
                        ]
                    }
                    for log in logs
                ],
                "table_count": f"{len(logs)} evento(s)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context

    def _export_url(self, *, module: str, action: str) -> str:
        base_url = reverse("audit:admin-audit-evidence-export")
        params = {}
        if module:
            params["module"] = module
        if action:
            params["action"] = action
        if not params:
            return base_url
        return f"{base_url}?{urlencode(params)}"


class AdminAuditEvidenceExportView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        output_format = request.GET.get("format", "jsonl").strip() or "jsonl"
        result = audit_evidence_export_queries.export(
            tenant_id=_request_tenant_id(request),
            module=request.GET.get("module", "").strip(),
            action=request.GET.get("action", "").strip(),
            since=request.GET.get("since", "").strip(),
            until=request.GET.get("until", "").strip(),
            limit=int(request.GET.get("limit", "500") or 500),
            output_format=output_format,
            include_metadata=request.GET.get("include_metadata") == "1",
        )
        if result["result"] != "audit-evidence-exported":
            return HttpResponse("Exportação de auditoria indisponível para este contexto.", status=400)
        content_type = "text/csv; charset=utf-8" if output_format == "csv" else "application/x-ndjson; charset=utf-8"
        response = HttpResponse(result["content"], content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="audit-evidence.{output_format}"'
        return response
