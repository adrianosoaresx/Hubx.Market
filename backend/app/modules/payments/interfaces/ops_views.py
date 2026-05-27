from __future__ import annotations

from django.core.paginator import Paginator
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import TemplateView

from app.modules.payments.application.refund_approval_commands import payment_refund_approval_commands
from app.modules.payments.application.financial_reconciliation_queries import (
    payment_financial_reconciliation_queries,
)
from app.modules.payments.application.refund_ledger_queries import payment_refund_ledger_queries


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


def _severity_cell(issue: dict[str, object]) -> str:
    severity = str(issue.get("severity") or "warning")
    label = {"critical": "Crítica", "warning": "Atenção"}.get(severity, severity)
    variant = "danger" if severity == "critical" else "warning"
    return format_html(
        '<span class="ds-badge ds-badge-{}">{}</span>',
        variant,
        label,
    )


def _issue_cell(issue: dict[str, object]) -> str:
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        issue.get("title") or issue.get("issue_code") or "Divergência financeira",
        issue.get("description") or "",
    )


def _attempt_cell(issue: dict[str, object]) -> str:
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        issue.get("attempt_key") or "Sem tentativa",
        issue.get("issue_code") or "",
    )


def _refund_status_cell(refund: dict[str, object]) -> str:
    status = str(refund.get("status") or "")
    labels = {
        "requested": "Solicitado",
        "blocked": "Bloqueado",
        "processing": "Processando",
        "succeeded": "Concluído",
        "failed": "Falhou",
        "reversed": "Revertido",
    }
    variants = {
        "requested": "warning",
        "blocked": "danger",
        "processing": "warning",
        "succeeded": "success",
        "failed": "danger",
        "reversed": "neutral",
    }
    return format_html(
        '<span class="ds-badge ds-badge-{}">{}</span>',
        variants.get(status, "neutral"),
        labels.get(status, status or "Indefinido"),
    )


def _refund_attempt_cell(refund: dict[str, object]) -> str:
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        refund.get("attempt_key") or "Sem tentativa",
        refund.get("external_reference") or "Sem referência externa",
    )


def _refund_blockers_cell(refund: dict[str, object]) -> str:
    blockers = list(refund.get("blockers") or [])
    if not blockers:
        return "Sem bloqueios"
    return format_html(
        '<div class="text-sm text-[var(--color-danger)]">{}</div>',
        ", ".join(str(blocker) for blocker in blockers),
    )


def _refund_action_cell(refund: dict[str, object], *, csrf_token: str) -> str:
    if str(refund.get("status") or "") != "requested":
        return "Sem ação"
    approve_url = reverse("payments_ops:admin-refund-approve", kwargs={"refund_key": refund.get("refund_key")})
    return format_html(
        '<form method="post" action="{}" class="space-y-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="approval_note" value="Aprovado internamente via ops refunds.">'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Aprovar internamente</button>'
        '<div class="text-xs text-[var(--color-text-secondary)]">Não executa estorno</div>'
        "</form>",
        approve_url,
        csrf_token,
    )


class AdminPaymentFinanceView(TemplateView):
    template_name = "pages/templates/admin_orders_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        issues = (
            payment_financial_reconciliation_queries.list_reconciliation_issues(tenant_id=tenant_id)
            if tenant_id
            else []
        )
        paginator = Paginator(issues, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("payments_ops:admin-finance")
        context.update(
            {
                "page_title": "Financeiro de pagamentos",
                "page_eyebrow": "Payments",
                "page_description": "Auditoria read-only de divergências financeiras entre tentativas de pagamento e pedidos do tenant.",
                "page_meta": "Nenhuma correção automática é aplicada nesta tela.",
                "page_note": "Use esta surface para triagem antes de qualquer ajuste manual.",
                "showcase_mode": False,
                "reset_url": base_url,
                "columns": [
                    {"label": "Severidade"},
                    {"label": "Pedido"},
                    {"label": "Tentativa"},
                    {"label": "Divergência"},
                ],
                "rows": [
                    {
                        "cells": [
                            _severity_cell(issue),
                            f"#{issue.get('order_number') or '-'}",
                            _attempt_cell(issue),
                            _issue_cell(issue),
                        ]
                    }
                    for issue in page_obj.object_list
                ],
                "table_title": "Divergências financeiras",
                "table_description": "Sinais derivados de PaymentAttempt e Order. A tela é somente leitura.",
                "table_count": f"{len(issues)} divergência(s)",
                "table_id": "admin-payment-finance-table",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "page_items": [{"number": number, "url": f"{base_url}?page={number}"} for number in page_obj.paginator.page_range],
                "prev_url": f"{base_url}?page={page_obj.previous_page_number()}" if page_obj.has_previous() else "",
                "next_url": f"{base_url}?page={page_obj.next_page_number()}" if page_obj.has_next() else "",
                "empty_title": "Nenhuma divergência financeira",
                "empty_description": "Não encontramos divergências entre tentativas de pagamento e pedidos neste tenant.",
            }
        )
        return context


class AdminPaymentRefundsView(TemplateView):
    template_name = "pages/templates/admin_orders_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        selected_status = str(self.request.GET.get("status") or "").strip().lower()
        refunds = (
            payment_refund_ledger_queries.list_refunds(tenant_id=tenant_id, status=selected_status)
            if tenant_id
            else []
        )
        paginator = Paginator(refunds, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("payments_ops:admin-refunds")
        status_query = f"status={selected_status}&" if selected_status else ""
        csrf_token = get_token(self.request)
        context.update(
            {
                "page_title": "Refunds de pagamentos",
                "page_eyebrow": "Payments",
                "page_description": "Triagem read-only do ledger de refunds antes de qualquer aprovação ou chamada ao provider.",
                "page_meta": "Nenhum estorno é executado nesta tela.",
                "page_note": "Use esta surface para revisar status, bloqueios e referências antes de aprovar uma ação futura.",
                "showcase_mode": False,
                "filter_title": "Filtros de refund",
                "filter_description": "Filtre o ledger por status operacional.",
                "status_name": "status",
                "status_label": "Status",
                "status_selected": selected_status,
                "status_options": [
                    {"value": "", "label": "Todos"},
                    {"value": "requested", "label": "Solicitado"},
                    {"value": "blocked", "label": "Bloqueado"},
                    {"value": "processing", "label": "Processando"},
                    {"value": "succeeded", "label": "Concluído"},
                    {"value": "failed", "label": "Falhou"},
                    {"value": "reversed", "label": "Revertido"},
                ],
                "reset_url": base_url,
                "columns": [
                    {"label": "Status"},
                    {"label": "Pedido"},
                    {"label": "Valor"},
                    {"label": "Tentativa"},
                    {"label": "Bloqueios"},
                    {"label": "Idempotência"},
                    {"label": "Ação"},
                ],
                "rows": [
                    {
                        "cells": [
                            _refund_status_cell(refund),
                            f"#{refund.get('order_number') or '-'}",
                            f"{refund.get('currency_code') or 'BRL'} {refund.get('amount') or '0.00'}",
                            _refund_attempt_cell(refund),
                            _refund_blockers_cell(refund),
                            refund.get("idempotency_key") or "-",
                            _refund_action_cell(refund, csrf_token=csrf_token),
                        ]
                    }
                    for refund in page_obj.object_list
                ],
                "table_title": "Ledger de refunds",
                "table_description": "Registros derivados de PaymentRefund. A tela é somente leitura e não aprova estorno.",
                "table_count": f"{len(refunds)} refund(s)",
                "table_id": "admin-payment-refunds-table",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "page_items": [
                    {"number": number, "url": f"{base_url}?{status_query}page={number}"}
                    for number in page_obj.paginator.page_range
                ],
                "prev_url": f"{base_url}?{status_query}page={page_obj.previous_page_number()}" if page_obj.has_previous() else "",
                "next_url": f"{base_url}?{status_query}page={page_obj.next_page_number()}" if page_obj.has_next() else "",
                "empty_title": "Nenhum refund registrado",
                "empty_description": "Não há intenções ou bloqueios de refund registrados neste tenant para o filtro atual.",
            }
        )
        return context


class AdminPaymentRefundApproveView(View):
    def post(self, request, refund_key):
        tenant_id = _request_tenant_id(request)
        user = getattr(request, "user", None)
        actor_label = ""
        if getattr(user, "is_authenticated", False):
            actor_label = str(getattr(user, "email", "") or getattr(user, "username", "") or user).strip()
        actor_label = actor_label or "Ops interno"
        payment_refund_approval_commands.approve_refund(
            tenant_id=tenant_id,
            refund_key=str(refund_key),
            actor_label=actor_label,
            approval_note=str(request.POST.get("approval_note") or "").strip(),
        )
        return redirect("payments_ops:admin-refunds")
