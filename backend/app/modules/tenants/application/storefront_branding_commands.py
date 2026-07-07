from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.core.validators import URLValidator
from django.db import connection

from app.modules.accounts.application.admin_permissions import PERMISSION_STOREFRONT_BRANDING_MANAGE, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.tenants.domain.branding_colors import validate_conversion_primary_color


BRANDING_FIELDS = (
    "logo_url",
    "conversion_primary_color",
    "storefront_hero_enabled",
    "storefront_hero_title",
    "storefront_hero_description",
    "storefront_hero_image_url",
    "storefront_hero_cta_label",
    "storefront_hero_cta_href",
)


def _string(value: object) -> str:
    return str(value or "").strip()


def _checkbox(value: object) -> bool:
    return _string(value).lower() in {"1", "true", "on", "yes", "sim"}


class StorefrontBrandingCommandRepository(Protocol):
    def update_storefront_hero(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmStorefrontBrandingCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.tenants.models import Tenant
        except Exception:
            self.tenant_model = None
            return
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_name = self.tenant_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                return table_name in set(connection.introspection.table_names(cursor))
        except Exception:
            return False

    def update_storefront_hero(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_STOREFRONT_BRANDING_MANAGE)
        if not permission.allowed:
            return {
                "result": "storefront-branding-permission-denied",
                "errors": {"__all__": "Permissão insuficiente para gerenciar branding da loja."},
            }
        if not tenant_id or not self.is_ready():
            return {
                "result": "storefront-branding-tenant-required",
                "errors": {"__all__": "Tenant obrigatório para configurar branding."},
            }
        tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
        if tenant is None:
            return {
                "result": "storefront-branding-tenant-required",
                "errors": {"__all__": "Tenant obrigatório para configurar branding."},
            }
        values, errors = self._validated_values(payload=payload)
        if errors:
            return {"result": "storefront-branding-invalid", "errors": errors}

        previous_enabled = bool(getattr(tenant, "storefront_hero_enabled", True))
        previous_conversion_color = _string(getattr(tenant, "conversion_primary_color", ""))
        for field_name, value in values.items():
            setattr(tenant, field_name, value)
        tenant.save(update_fields=[*BRANDING_FIELDS, "updated_at"])
        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="tenants",
            action="tenant.storefront_branding_updated",
            entity_type="Tenant",
            entity_id=str(tenant.id),
            actor_label=_string(actor_label),
            summary="Branding institucional da storefront atualizado.",
            metadata={
                "tenant_slug": tenant.slug,
                "previous_enabled": previous_enabled,
                "enabled": values["storefront_hero_enabled"],
                "has_logo": bool(values["logo_url"]),
                "previous_conversion_primary_color": bool(previous_conversion_color),
                "has_conversion_primary_color": bool(values["conversion_primary_color"]),
                "has_title": bool(values["storefront_hero_title"]),
                "has_description": bool(values["storefront_hero_description"]),
                "has_image": bool(values["storefront_hero_image_url"]),
                "has_cta": bool(values["storefront_hero_cta_label"] or values["storefront_hero_cta_href"]),
            },
        )
        return {"result": "storefront-branding-updated", "tenant": {"id": tenant.id, "slug": tenant.slug}}

    def _validated_values(self, *, payload: dict[str, object]) -> tuple[dict[str, object], dict[str, str]]:
        errors: dict[str, str] = {}
        logo_url = _string(payload.get("logo_url"))
        conversion_primary_color, conversion_color_error = validate_conversion_primary_color(
            payload.get("conversion_primary_color")
        )
        title = _string(payload.get("storefront_hero_title"))
        description = _string(payload.get("storefront_hero_description"))
        image_url = _string(payload.get("storefront_hero_image_url"))
        cta_label = _string(payload.get("storefront_hero_cta_label"))
        cta_href = _string(payload.get("storefront_hero_cta_href"))

        if len(logo_url) > 500:
            errors["logo_url"] = "Use no máximo 500 caracteres."
        if conversion_color_error:
            errors["conversion_primary_color"] = conversion_color_error
        if len(title) > 160:
            errors["storefront_hero_title"] = "Use no máximo 160 caracteres."
        if len(description) > 600:
            errors["storefront_hero_description"] = "Use no máximo 600 caracteres."
        if len(image_url) > 500:
            errors["storefront_hero_image_url"] = "Use no máximo 500 caracteres."
        if len(cta_label) > 80:
            errors["storefront_hero_cta_label"] = "Use no máximo 80 caracteres."
        if len(cta_href) > 255:
            errors["storefront_hero_cta_href"] = "Use no máximo 255 caracteres."

        if logo_url:
            try:
                URLValidator()(logo_url)
            except Exception:
                errors["logo_url"] = "Informe uma URL completa e válida para o logo."
        if image_url:
            try:
                URLValidator()(image_url)
            except Exception:
                errors["storefront_hero_image_url"] = "Informe uma URL completa e válida para a imagem."
        if cta_href and (not cta_href.startswith("/") or cta_href.startswith("//")):
            errors["storefront_hero_cta_href"] = "Use um caminho interno começando com /."

        return (
            {
                "logo_url": logo_url,
                "conversion_primary_color": conversion_primary_color,
                "storefront_hero_enabled": "storefront_hero_enabled" in payload
                and _checkbox(payload.get("storefront_hero_enabled")),
                "storefront_hero_title": title,
                "storefront_hero_description": description,
                "storefront_hero_image_url": image_url,
                "storefront_hero_cta_label": cta_label,
                "storefront_hero_cta_href": cta_href,
            },
            errors,
        )


@dataclass
class StorefrontBrandingCommandService:
    repository: StorefrontBrandingCommandRepository

    def update_storefront_hero(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        return self.repository.update_storefront_hero(
            tenant_id=tenant_id,
            payload=payload,
            actor_label=actor_label,
            actor_role=actor_role,
        )


storefront_branding_commands = StorefrontBrandingCommandService(
    repository=DjangoOrmStorefrontBrandingCommandRepository()
)
