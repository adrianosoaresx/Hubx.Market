from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PAYMENTS_MANAGE,
    PERMISSION_PAYMENTS_VIEW,
)
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role
from app.modules.payments.application.refund_approval_commands import payment_refund_approval_commands
from app.modules.payments.application.financial_reconciliation_queries import (
    payment_financial_reconciliation_queries,
)
from app.modules.payments.application.refund_execution_commands import payment_refund_execution_commands
from app.modules.payments.application.refund_ledger_queries import payment_refund_ledger_queries


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


def _actor_label(request) -> str:
    owner = getattr(request, "owner_user", None)
    owner_email = str(getattr(owner, "email", "") or "").strip()
    if owner_email:
        return owner_email
    user = getattr(request, "user", None)
    return str(getattr(user, "email", "") or getattr(user, "username", "") or "ops-admin").strip()


def _can_manage_payments(request) -> bool:
    return bool(request_owner_role(request)) and request_admin_can(request, PERMISSION_PAYMENTS_MANAGE)


def _refund_feedback(value: object) -> dict[str, str]:
    status = str(value or "").strip()
    mapping = {
        "refund-approved": ("success", "Refund aprovado", "A intenção foi preparada para execução no provider."),
        "refund-approval-blocked": ("warning", "Aprovação bloqueada", "O ledger registrou bloqueios para esta intenção de refund."),
        "refund-execution-accepted": ("info", "Execução aceita", "O provider recebeu a solicitação e a referência foi registrada."),
        "refund-execution-succeeded": ("success", "Refund concluído", "O provider confirmou o refund e o ledger foi atualizado."),
        "refund-execution-failed": ("danger", "Refund falhou", "A resposta do provider foi registrada no ledger para investigação."),
        "refund-execution-blocked": ("warning", "Execução bloqueada", "O refund ainda não atende aos requisitos para chamada ao provider."),
        "refund-permission-denied": ("danger", "Permissão necessária", "Seu perfil pode visualizar refunds, mas não aprovar ou executar estornos."),
        "refund-tenant-required": ("warning", "Tenant não resolvido", "Acesse pelo subdomínio da loja para operar refunds."),
        "refund-unavailable": ("warning", "Refund indisponível", "O refund não existe neste tenant ou não pode ser alterado neste estado."),
    }
    variant, title, description = mapping.get(status, ("info", "", ""))
    return {"variant": variant, "title": title, "description": description} if title else {}


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


def _refund_provider_cell(refund: dict[str, object]) -> str:
    provider_code = str(refund.get("provider_code") or "payment")
    provider_refund_reference = str(refund.get("provider_refund_reference") or "").strip()
    if not provider_refund_reference:
        provider_refund_reference = "Sem refund externo"
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        provider_code,
        provider_refund_reference,
    )


def _refund_blockers_cell(refund: dict[str, object]) -> str:
    blockers = list(refund.get("blockers") or [])
    if not blockers:
        return "Sem bloqueios"
    return format_html(
        '<div class="text-sm text-[var(--color-danger)]">{}</div>',
        ", ".join(str(blocker) for blocker in blockers),
    )


def _refund_action_cell(refund: dict[str, object], *, csrf_token: str, can_manage: bool) -> str:
    if not can_manage:
        return "Sem permissão para alterar"

    status = str(refund.get("status") or "")
    if status == "processing" and str(refund.get("provider_refund_reference") or "").strip():
        return "Execução registrada"

    if status == "processing":
        execute_url = reverse("payments_ops:admin-refund-execute", kwargs={"refund_key": refund.get("refund_key")})
        return format_html(
            '<form method="post" action="{}" class="space-y-2">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<button type="submit" class="ds-btn ds-btn-danger ds-btn-sm">Executar no provider</button>'
            '<div class="text-xs text-[var(--color-text-secondary)]">Usa idempotência do ledger</div>'
            "</form>",
            execute_url,
            csrf_token,
        )

    if status != "requested":
        return "Sem ação"
    approve_url = reverse("payments_ops:admin-refund-approve", kwargs={"refund_key": refund.get("refund_key")})
    return format_html(
        '<form method="post" action="{}" class="space-y-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="approval_note" value="Aprovado internamente via ops refunds.">'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Aprovar para execução</button>'
        '<div class="text-xs text-[var(--color-text-secondary)]">Não chama provider ainda</div>'
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
        can_view_payments = request_admin_can(self.request, PERMISSION_PAYMENTS_VIEW)
        can_manage_payments = _can_manage_payments(self.request)
        refunds = (
            payment_refund_ledger_queries.list_refunds(tenant_id=tenant_id, status=selected_status)
            if tenant_id and can_view_payments
            else []
        )
        paginator = Paginator(refunds, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("payments_ops:admin-refunds")
        status_query = f"status={selected_status}&" if selected_status else ""
        csrf_token = get_token(self.request)
        feedback = _refund_feedback(self.request.GET.get("result"))
        context.update(
            {
                "page_title": "Reembolsos de pagamentos",
                "page_eyebrow": "Pagamentos",
                "page_description": "Aprovação e execução controlada de reembolsos tenant-scoped com registro no ledger.",
                "page_meta": "A execução chama o provider somente para refunds em processamento e sem referência externa.",
                "page_note": feedback.get("description")
                or "Revise bloqueios, idempotência e referência do provider antes de operar um refund.",
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
                    {"label": "Provider refund"},
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
                            _refund_provider_cell(refund),
                            _refund_blockers_cell(refund),
                            refund.get("idempotency_key") or "-",
                            _refund_action_cell(refund, csrf_token=csrf_token, can_manage=can_manage_payments),
                        ]
                    }
                    for refund in page_obj.object_list
                ],
                "table_title": "Ledger de refunds",
                "table_description": "Registros derivados de PaymentRefund com aprovação interna, execução idempotente e resposta do provider.",
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
        if not tenant_id:
            return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result=refund-tenant-required')
        if not _can_manage_payments(request):
            return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result=refund-permission-denied')
        result, _refund = payment_refund_approval_commands.approve_refund(
            tenant_id=tenant_id,
            refund_key=str(refund_key),
            actor_label=_actor_label(request),
            approval_note=str(request.POST.get("approval_note") or "").strip(),
        )
        result_status = {
            "refund-approval-ready": "refund-approved",
            "refund-approval-blocked": "refund-approval-blocked",
            "refund-approval-unavailable": "refund-unavailable",
        }.get(str(result or ""), "refund-unavailable")
        return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result={result_status}')


class AdminPaymentRefundExecuteView(View):
    def post(self, request, refund_key):
        tenant_id = _request_tenant_id(request)
        if not tenant_id:
            return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result=refund-tenant-required')
        if not _can_manage_payments(request):
            return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result=refund-permission-denied')
        result, _refund = payment_refund_execution_commands.execute_refund(
            tenant_id=tenant_id,
            refund_key=str(refund_key),
            actor_label=_actor_label(request),
        )
        result_status = {
            "refund-execution-accepted": "refund-execution-accepted",
            "refund-execution-succeeded": "refund-execution-succeeded",
            "refund-execution-failed": "refund-execution-failed",
            "refund-execution-blocked": "refund-execution-blocked",
            "refund-execution-unavailable": "refund-unavailable",
        }.get(str(result or ""), "refund-unavailable")
        return HttpResponseRedirect(f'{reverse("payments_ops:admin-refunds")}?result={result_status}')
