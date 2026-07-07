from __future__ import annotations

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_STOREFRONT_BRANDING_MANAGE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.tenants.application.storefront_branding_admin_queries import storefront_branding_admin_queries
from app.modules.tenants.application.storefront_branding_commands import storefront_branding_commands
from app.modules.tenants.application.storefront_branding_queries import storefront_branding_queries


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


def _form_values_from_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "logo_url": payload.get("logo_url", ""),
        "conversion_primary_color": payload.get("conversion_primary_color", ""),
        "storefront_hero_enabled": "storefront_hero_enabled" in payload,
        "storefront_hero_title": payload.get("storefront_hero_title", ""),
        "storefront_hero_description": payload.get("storefront_hero_description", ""),
        "storefront_hero_image_url": payload.get("storefront_hero_image_url", ""),
        "storefront_hero_cta_label": payload.get("storefront_hero_cta_label", ""),
        "storefront_hero_cta_href": payload.get("storefront_hero_cta_href", ""),
    }


class StorefrontBrandingSettingsView(TemplateView):
    template_name = "pages/templates/admin_storefront_branding_page.html"

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None) -> dict[str, object]:
        tenant = getattr(self.request, "tenant", None)
        initial = storefront_branding_admin_queries.get_form_initial(tenant=tenant)
        if values:
            initial.update(values)
        can_manage = request_admin_can(self.request, PERMISSION_STOREFRONT_BRANDING_MANAGE)
        is_demo_read_only = bool(getattr(self.request, "is_demo_read_only", False))
        can_save = can_manage and not is_demo_read_only
        result = str(self.request.GET.get("result") or "")
        return {
            "page_title": "Branding da loja",
            "page_eyebrow": "Conteúdo",
            "page_description": "Configure logo, cor de conversão e hero institucional exibidos no storefront tenant-owned.",
            "page_meta": f"Escopo tenant · role: {_request_owner_role(self.request) or 'compatibilidade legada'}",
            "form_action": reverse("tenant_branding:storefront-branding-settings"),
            "cancel_href": reverse("merchant_ops:admin-dashboard"),
            "can_manage_storefront_branding": can_manage,
            "can_save_storefront_branding": can_save,
            "save_blocked_message": (
                "A loja demo está em modo somente leitura."
                if is_demo_read_only
                else "Seu perfil atual pode visualizar esta configuração, mas não pode salvar alterações."
            ),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            "success_message": "Branding salvo." if result == "storefront-branding-updated" else "",
            "storefront_hero": storefront_branding_queries.get_home_hero(tenant=tenant) if tenant else {"enabled": False},
            **initial,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        result = storefront_branding_commands.update_storefront_hero(
            tenant_id=_request_tenant_id(request),
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=_request_owner_role(request),
        )
        if result.get("result") == "storefront-branding-updated":
            return HttpResponseRedirect(f"{reverse('tenant_branding:storefront-branding-settings')}?result=storefront-branding-updated")
        context = self.get_context_data(**kwargs)
        context.update(
            self._context(
                values=_form_values_from_payload(request.POST),
                errors=result.get("errors") or {},
            )
        )
        return self.render_to_response(context, status=400)
