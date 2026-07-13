from __future__ import annotations

from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView, View

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    PERMISSION_PLATFORM_TENANTS_VIEW,
)
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role
from app.modules.tenants.application.platform_tenant_admin_commands import platform_tenant_admin_commands
from app.modules.tenants.application.platform_tenant_admin_queries import platform_tenant_admin_queries
from app.modules.tenants.application.tenant_onboarding_commands import tenant_onboarding_commands
from app.modules.tenants.application.tenant_onboarding_queries import tenant_onboarding_queries


def _status_badge(tenant: dict[str, object]) -> str:
    variant_classes = {
        "success": "ds-badge-success",
        "warning": "ds-badge-warning",
        "danger": "ds-badge-danger",
    }
    return format_html(
        '<span class="ds-badge ds-badge-xs {}">{}</span>',
        variant_classes.get(str(tenant["status_variant"]), "ds-badge-neutral"),
        tenant["status_label"],
    )


def _can_manage_platform_tenants(request) -> bool:
    return bool(request_owner_role(request)) and request_admin_can(request, PERMISSION_PLATFORM_TENANTS_MANAGE)


def _tenant_state_actions(tenant: dict[str, object]) -> list[dict[str, str]]:
    actions = []
    if tenant["is_active"]:
        actions.append({"label": "Desativar loja", "action": "deactivate", "variant": "secondary"})
    else:
        actions.append({"label": "Ativar loja", "action": "activate", "variant": "primary"})
    if tenant["maintenance_mode"]:
        actions.append({"label": "Desligar manutenção", "action": "maintenance-off", "variant": "secondary"})
    else:
        actions.append({"label": "Ligar manutenção", "action": "maintenance-on", "variant": "secondary"})
    return actions


class PlatformTenantAdminListView(TemplateView):
    template_name = "pages/templates/admin_platform_tenants_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenants = platform_tenant_admin_queries.list_tenants()
        summary = platform_tenant_admin_queries.get_summary()
        can_view_platform_tenants = request_admin_can(self.request, PERMISSION_PLATFORM_TENANTS_VIEW)
        can_manage_platform_tenants = _can_manage_platform_tenants(self.request)
        if not can_view_platform_tenants:
            tenants = []

        context.update(
            {
                "page_title": "Lojas",
                "page_eyebrow": "Platform store management",
                "page_description": "Inventário read-only das lojas/tenants cadastradas na plataforma.",
                "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
                "create_href": reverse("tenants:platform-tenants-create") if can_manage_platform_tenants else "",
                "admin_nav_items": [
                    {"label": "Lojas", "href": "/ops/platform/tenants/"},
                ],
                "summary": summary,
                "table_count": f"{len(tenants)} loja(s)",
                "columns": [
                    {"label": "Loja"},
                    {"label": "Subdomínio"},
                    {"label": "Domínio customizado"},
                    {"label": "Status"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            format_html(
                                '<a class="font-medium text-[var(--color-action-primary-bg)] hover:underline" href="{}">{} · {}</a>',
                                reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant["slug"]}),
                                tenant["name"],
                                tenant["slug"],
                            ),
                            tenant["storefront_host"],
                            tenant["custom_domain"],
                            _status_badge(tenant),
                            tenant["updated_at"],
                        ]
                    }
                    for tenant in tenants
                ],
                "empty_title": "Nenhuma loja visível",
                "empty_description": (
                    "Não há tenants cadastrados ou a role atual ainda não pode visualizar a surface platform."
                ),
                "contract_notes": [
                    "Esta tela não cria, edita ou remove tenants.",
                    "custom_domain aparece como cadastro contract-only e ainda não ativa resolução HTTP.",
                    "Dados comerciais da loja continuam nas superfícies tenant-scoped existentes.",
                ],
            }
        )
        return context


def _create_form_context(*, values: dict[str, object] | None = None, errors: dict[str, str] | None = None) -> dict[str, object]:
    values = values or {}
    errors = errors or {}
    return {
        "values": {
            "name": values.get("name", ""),
            "slug": values.get("slug", ""),
            "subdomain": values.get("subdomain", ""),
            "custom_domain": values.get("custom_domain", ""),
            "is_active": values.get("is_active", "on"),
            "maintenance_mode": values.get("maintenance_mode", ""),
        },
        "errors": errors,
        "form_error": errors.get("__all__", ""),
    }


class PlatformTenantAdminCreateView(TemplateView):
    template_name = "pages/templates/admin_platform_tenant_form_page.html"

    def _base_context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None) -> dict[str, object]:
        can_manage_platform_tenants = _can_manage_platform_tenants(self.request)
        return {
            "page_title": "Nova loja",
            "page_eyebrow": "Platform store management",
            "page_description": "Crie apenas o cadastro mínimo do tenant. Owner, catálogo demo, billing e domínio customizado ativo ficam fora desta ação.",
            "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
            "admin_nav_items": [
                {"label": "Lojas", "href": "/ops/platform/tenants/"},
            ],
            "can_manage_platform_tenants": can_manage_platform_tenants,
            "form_action": reverse("tenants:platform-tenants-create"),
            "cancel_href": reverse("tenants:platform-tenants-list"),
            "empty_title": "Criação indisponível",
            "empty_description": "A role atual ainda não possui permissão para criar lojas na surface platform.",
            "contract_notes": [
                "A criação registra AuditLog platform-scope obrigatório.",
                "Nenhum owner, catálogo demo, billing ou sessão será criado.",
                "custom_domain permanece contract-only e não altera resolução HTTP.",
            ],
            **_create_form_context(values=values, errors=errors),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._base_context())
        return context

    def post(self, request, *args, **kwargs):
        result = platform_tenant_admin_commands.create_tenant(
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "platform-tenant-created":
            tenant = result.get("tenant") or {}
            return HttpResponseRedirect(
                reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant["slug"]})
            )
        context = self._base_context(values=request.POST, errors=result.get("errors") or {})
        return self.render_to_response(context, status=400)


class PlatformTenantAdminDetailView(TemplateView):
    template_name = "pages/templates/admin_platform_tenant_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_view_platform_tenants = request_admin_can(self.request, PERMISSION_PLATFORM_TENANTS_VIEW)
        if not can_view_platform_tenants:
            tenant = None
        else:
            tenant = platform_tenant_admin_queries.get_tenant(slug=str(kwargs.get("tenant_slug") or ""))
            if tenant is None:
                raise Http404("Tenant not found")

        context.update(
            {
                "page_title": "Detalhe da loja",
                "page_eyebrow": "Platform store management",
                "page_description": "Leitura read-only do cadastro operacional do tenant.",
                "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
                "admin_nav_items": [
                    {"label": "Lojas", "href": "/ops/platform/tenants/"},
                ],
                "tenant": tenant,
                "back_href": reverse("tenants:platform-tenants-list"),
                "status_badge": _status_badge(tenant) if tenant else "",
                "can_manage_platform_tenants": _can_manage_platform_tenants(self.request),
                "state_action_url": (
                    reverse("tenants:platform-tenants-state", kwargs={"tenant_slug": tenant["slug"]})
                    if tenant
                    else ""
                ),
                "custom_domain_action_url": (
                    reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": tenant["slug"]})
                    if tenant
                    else ""
                ),
                "custom_domain_value": tenant["custom_domain"] if tenant and tenant["custom_domain"] != "—" else "",
                "owner_bootstrap_action_url": (
                    reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": tenant["slug"]})
                    if tenant
                    else ""
                ),
                "owner_bootstrap_available": bool(tenant) and int(tenant["active_owner_count"]) == 0,
                "state_actions": _tenant_state_actions(tenant) if tenant else [],
                "identity_rows": [
                    {"label": "Nome", "value": tenant["name"]},
                    {"label": "Slug", "value": tenant["slug"]},
                    {"label": "ID interno", "value": tenant["id"]},
                    {"label": "Criado em", "value": tenant["created_at"]},
                    {"label": "Atualizado em", "value": tenant["updated_at"]},
                ]
                if tenant
                else [],
                "routing_rows": [
                    {"label": "Subdomínio", "value": tenant["subdomain"]},
                    {"label": "Host storefront", "value": tenant["storefront_host"]},
                    {"label": "Domínio customizado", "value": tenant["custom_domain"]},
                    {
                        "label": "Custom domain runtime",
                        "value": "Contract-only; ainda não resolve HTTP",
                    },
                ]
                if tenant
                else [],
                "state_rows": [
                    {"label": "Ativo", "value": "Sim" if tenant["is_active"] else "Não"},
                    {"label": "Modo manutenção", "value": "Ligado" if tenant["maintenance_mode"] else "Desligado"},
                    {"label": "Status operacional", "value": tenant["status_label"]},
                    {"label": "Administradores ativos", "value": tenant["active_owner_count"]},
                ]
                if tenant
                else [],
                "empty_title": "Loja não visível",
                "empty_description": "A role atual ainda não pode visualizar detalhes da surface platform.",
                "contract_notes": [
                    "Esta tela edita apenas estado operacional e custom_domain contract-only para roles com manage.",
                    "O tenant alvo é parâmetro operacional explícito, não o request.tenant da loja atual.",
                    "Nenhum dado de catálogo, pedidos, clientes ou pagamentos é lido neste detalhe.",
                ],
            }
        )
        return context


class PlatformTenantAdminStateActionView(View):
    def post(self, request, *args, **kwargs):
        tenant_slug = str(kwargs.get("tenant_slug") or "")
        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=tenant_slug,
            action=request.POST.get("action", ""),
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "platform-tenant-state-updated":
            return HttpResponseRedirect(
                reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant_slug})
            )
        if result.get("result") == "platform-tenant-state-not-found":
            raise Http404("Tenant not found")
        return HttpResponseRedirect(
            f"{reverse('tenants:platform-tenants-detail', kwargs={'tenant_slug': tenant_slug})}?result={result.get('result')}"
        )


class PlatformTenantAdminCustomDomainActionView(View):
    def post(self, request, *args, **kwargs):
        tenant_slug = str(kwargs.get("tenant_slug") or "")
        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant_slug,
            custom_domain=request.POST.get("custom_domain", ""),
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "platform-tenant-custom-domain-updated":
            return HttpResponseRedirect(
                reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant_slug})
            )
        if result.get("result") == "platform-tenant-custom-domain-not-found":
            raise Http404("Tenant not found")
        return HttpResponseRedirect(
            f"{reverse('tenants:platform-tenants-detail', kwargs={'tenant_slug': tenant_slug})}?result={result.get('result')}"
        )


class PlatformTenantAdminOwnerBootstrapActionView(View):
    def post(self, request, *args, **kwargs):
        tenant_slug = str(kwargs.get("tenant_slug") or "")
        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=tenant_slug,
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "platform-tenant-owner-bootstrapped":
            return HttpResponseRedirect(
                reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant_slug})
            )
        if result.get("result") == "platform-tenant-owner-bootstrap-not-found":
            raise Http404("Tenant not found")
        return HttpResponseRedirect(
            f"{reverse('tenants:platform-tenants-detail', kwargs={'tenant_slug': tenant_slug})}?result={result.get('result')}"
        )


class TenantOnboardingListView(TemplateView):
    template_name = "pages/templates/admin_tenant_onboarding_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        onboardings = tenant_onboarding_queries.list_onboardings()
        can_view = request_admin_can(self.request, PERMISSION_PLATFORM_TENANTS_VIEW)
        can_manage = _can_manage_platform_tenants(self.request)
        if not can_view:
            onboardings = []
        context.update(
            {
                "page_title": "Onboarding de lojas",
                "page_eyebrow": "Platform self-service",
                "page_description": "Wizard operacional para criar e configurar lojas sem acoplar billing real, DNS/TLS ou commerce.",
                "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
                "create_href": reverse("tenant_onboarding:onboarding-create") if can_manage else "",
                "admin_nav_items": [
                    {"label": "Onboarding", "href": "/ops/platform/onboarding/"},
                    {"label": "Lojas", "href": "/ops/platform/tenants/"},
                ],
                "table_count": f"{len(onboardings)} jornada(s)",
                "columns": [
                    {"label": "Jornada"},
                    {"label": "Plano"},
                    {"label": "Owner"},
                    {"label": "Status"},
                    {"label": "Progresso"},
                ],
                "rows": [
                    {
                        "cells": [
                            format_html(
                                '<a class="font-medium text-[var(--color-action-primary-bg)] hover:underline" href="{}">{} · {}</a>',
                                reverse("tenant_onboarding:onboarding-detail", kwargs={"onboarding_id": onboarding["id"]}),
                                onboarding["store_name"] or "Loja sem nome",
                                onboarding["store_slug"] or f"draft-{onboarding['id']}",
                            ),
                            onboarding["plan_code"] or "—",
                            onboarding["owner_email"] or "—",
                            _status_badge({"status_variant": onboarding["status_variant"], "status_label": onboarding["status_label"]}),
                            f"{onboarding['progress']}%",
                        ]
                    }
                    for onboarding in onboardings
                ],
                "empty_title": "Nenhuma jornada de onboarding",
                "empty_description": "Crie uma jornada para guiar loja, plano, owner, branding e domínio em um fluxo único.",
                "contract_notes": [
                    "Este portal é self-service operacional para platform owners/admins.",
                    "Billing real, upload de logo, DNS/TLS automático e commerce ficam fora do MVP.",
                    "A conclusão delega writes para boundaries existentes de tenants, subscriptions e accounts.",
                ],
            }
        )
        return context


class TenantOnboardingCreateView(TemplateView):
    template_name = "pages/templates/admin_tenant_onboarding_create_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        result = tenant_onboarding_commands.create_onboarding(
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "tenant-onboarding-created":
            onboarding = result.get("onboarding") or {}
            return HttpResponseRedirect(
                reverse("tenant_onboarding:onboarding-detail", kwargs={"onboarding_id": onboarding["id"]})
            )
        return self.render_to_response(self._context(values=request.POST, errors=result.get("errors") or {}), status=400)

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None) -> dict[str, object]:
        values = values or {}
        errors = errors or {}
        return {
            "page_title": "Nova jornada",
            "page_eyebrow": "Platform self-service",
            "page_description": "Inicie um wizard para criar loja, plano interno, owner, branding mínimo e domínio contract-only.",
            "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
            "admin_nav_items": [
                {"label": "Onboarding", "href": "/ops/platform/onboarding/"},
                {"label": "Lojas", "href": "/ops/platform/tenants/"},
            ],
            "form_action": reverse("tenant_onboarding:onboarding-create"),
            "cancel_href": reverse("tenant_onboarding:onboarding-list"),
            "can_manage_platform_tenants": _can_manage_platform_tenants(self.request),
            "values": {
                "store_name": values.get("store_name", ""),
                "store_display_name": values.get("store_display_name", ""),
                "primary_color": values.get("primary_color", "#9a6410"),
            },
            "errors": errors,
            "form_error": errors.get("__all__", ""),
            "empty_title": "Onboarding indisponível",
            "empty_description": "A role atual ainda não possui permissão para iniciar jornadas de loja.",
        }


class TenantOnboardingDetailView(TemplateView):
    template_name = "pages/templates/admin_tenant_onboarding_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        onboarding = tenant_onboarding_queries.get_onboarding(onboarding_id=kwargs.get("onboarding_id"))
        if onboarding is None:
            raise Http404("Onboarding not found")
        can_manage = _can_manage_platform_tenants(self.request)
        context.update(
            {
                "page_title": "Wizard de onboarding",
                "page_eyebrow": "Platform self-service",
                "page_description": "Checklist guiado para configurar a loja antes da criação final controlada.",
                "page_meta": f"Escopo platform-only · role: {request_owner_role(self.request) or 'compatibilidade legada'}",
                "admin_nav_items": [
                    {"label": "Onboarding", "href": "/ops/platform/onboarding/"},
                    {"label": "Lojas", "href": "/ops/platform/tenants/"},
                ],
                "onboarding": onboarding,
                "plans": tenant_onboarding_queries.list_active_plans(),
                "can_manage_platform_tenants": can_manage,
                "back_href": reverse("tenant_onboarding:onboarding-list"),
                "complete_action": reverse("tenant_onboarding:onboarding-complete", kwargs={"onboarding_id": onboarding["id"]}),
                "step_action_base": f"/ops/platform/onboarding/{onboarding['id']}/step/",
                "status_badge": _status_badge({"status_variant": onboarding["status_variant"], "status_label": onboarding["status_label"]}),
                "contract_notes": [
                    "O wizard salva rascunho antes de criar o Tenant.",
                    "A conclusão cria assinatura comercial, owner inicial e audit trail.",
                    "Custom domain permanece contract-only; DNS/TLS seguem evidência externa.",
                ],
            }
        )
        return context


class TenantOnboardingStepView(View):
    def post(self, request, *args, **kwargs):
        result = tenant_onboarding_commands.update_step(
            onboarding_id=kwargs.get("onboarding_id"),
            step_key=kwargs.get("step_key"),
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        onboarding = result.get("onboarding") or {"id": kwargs.get("onboarding_id")}
        status = "?result=tenant-onboarding-step-updated" if result.get("result") == "tenant-onboarding-step-updated" else f"?result={result.get('result')}"
        return HttpResponseRedirect(
            f"{reverse('tenant_onboarding:onboarding-detail', kwargs={'onboarding_id': onboarding['id']})}{status}"
        )


class TenantOnboardingCompleteView(View):
    def post(self, request, *args, **kwargs):
        result = tenant_onboarding_commands.complete_onboarding(
            onboarding_id=kwargs.get("onboarding_id"),
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=request_owner_role(request),
        )
        onboarding = result.get("onboarding") or {"id": kwargs.get("onboarding_id")}
        status = "?result=tenant-onboarding-completed" if result.get("result") == "tenant-onboarding-completed" else f"?result={result.get('result')}"
        return HttpResponseRedirect(
            f"{reverse('tenant_onboarding:onboarding-detail', kwargs={'onboarding_id': onboarding['id']})}{status}"
        )
