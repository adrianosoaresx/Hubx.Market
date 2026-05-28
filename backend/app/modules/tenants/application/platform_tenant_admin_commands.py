from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    admin_permissions,
    normalize_admin_role,
)
from app.modules.accounts.application.initial_owner_provisioning_commands import initial_owner_provisioning_commands
from app.modules.accounts.models import OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.tenants.models import Tenant


DEFAULT_RESERVED_SUBDOMAINS = ("www", "app", "api", "docs", "cdn", "admin")
TENANT_STATE_ACTIONS = ("activate", "deactivate", "maintenance-on", "maintenance-off")


def _string(value: object, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _bool(value: object, *, default: bool = False) -> bool:
    if value in ("", None):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "sim"}


def _reserved_subdomains() -> set[str]:
    configured = getattr(settings, "HUBX_MARKET_RESERVED_SUBDOMAINS", DEFAULT_RESERVED_SUBDOMAINS)
    return {str(item).strip().lower() for item in configured if str(item).strip()}


def _normalize_slug(value: object, *, limit: int) -> str:
    return slugify(_string(value, limit=limit)).strip("-")[:limit]


def _normalize_custom_domain(value: object) -> str:
    raw_value = _string(value, limit=255).lower().strip(".")
    if not raw_value:
        return ""

    parsed = urlsplit(raw_value if "://" in raw_value else f"//{raw_value}")
    hostname = parsed.hostname or raw_value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    return hostname.strip().lower().strip(".")[:255]


def _custom_domain_error(custom_domain: str) -> str:
    if not custom_domain:
        return ""
    if len(custom_domain) > 255 or "." not in custom_domain or ".." in custom_domain:
        return "Domínio customizado inválido."
    labels = custom_domain.split(".")
    for label in labels:
        if not label or len(label) > 63:
            return "Domínio customizado inválido."
        if label.startswith("-") or label.endswith("-"):
            return "Domínio customizado inválido."
        if not all(character.isalnum() or character == "-" for character in label):
            return "Domínio customizado inválido."
    return ""


@dataclass
class PlatformTenantAdminCommandService:
    def _check_manage_permission(self, *, actor_role: object, denied_result: str) -> dict[str, object] | None:
        normalized_role = normalize_admin_role(actor_role)
        if not normalized_role:
            return {
                "result": denied_result,
                "errors": {"__all__": "Permissão platform obrigatória para gerenciar lojas."},
            }
        permission = admin_permissions.check(role=normalized_role, permission=PERMISSION_PLATFORM_TENANTS_MANAGE)
        if not permission.allowed:
            return {
                "result": denied_result,
                "errors": {"__all__": "Permissão insuficiente para gerenciar lojas."},
            }
        return None

    def create_tenant(
        self,
        *,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._check_manage_permission(
            actor_role=actor_role,
            denied_result="platform-tenant-create-permission-denied",
        )
        if denied:
            return denied

        values = {
            "name": _string(payload.get("name"), limit=150),
            "slug": _normalize_slug(payload.get("slug"), limit=150),
            "subdomain": _normalize_slug(payload.get("subdomain"), limit=63),
            "custom_domain": _string(payload.get("custom_domain"), limit=255),
            "is_active": _bool(payload.get("is_active"), default=True),
            "maintenance_mode": _bool(payload.get("maintenance_mode"), default=False),
        }
        errors = self._validate(values)
        if errors:
            return {"result": "platform-tenant-create-invalid", "errors": errors}

        with transaction.atomic():
            tenant = Tenant.objects.create(
                name=values["name"],
                slug=values["slug"],
                subdomain=values["subdomain"],
                custom_domain=values["custom_domain"] or None,
                is_active=values["is_active"],
                maintenance_mode=values["maintenance_mode"],
            )
            audit_result = audit_log_commands.record_event(
                tenant_id=None,
                module="tenants",
                action="platform.tenant.created",
                entity_type="Tenant",
                entity_id=str(tenant.id),
                actor_label=_string(actor_label, limit=180),
                summary="Tenant criado por surface platform.",
                metadata={
                    "tenant_slug": tenant.slug,
                    "tenant_subdomain": tenant.subdomain,
                    "custom_domain_configured": bool(tenant.custom_domain),
                    "is_active": tenant.is_active,
                    "maintenance_mode": tenant.maintenance_mode,
                },
                allow_platform_scope=True,
            )
            if audit_result.get("result") != "audit-recorded":
                transaction.set_rollback(True)
                return {
                    "result": "platform-tenant-create-audit-unavailable",
                    "errors": {"__all__": "AuditLog platform-scope obrigatório para criar lojas."},
                }

        return {
            "result": "platform-tenant-created",
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "subdomain": tenant.subdomain,
                "custom_domain": tenant.custom_domain or "",
                "is_active": tenant.is_active,
                "maintenance_mode": tenant.maintenance_mode,
            },
        }

    def update_tenant_state(
        self,
        *,
        tenant_slug: object,
        action: object,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._check_manage_permission(
            actor_role=actor_role,
            denied_result="platform-tenant-state-permission-denied",
        )
        if denied:
            return denied

        normalized_slug = _normalize_slug(tenant_slug, limit=150)
        normalized_action = _string(action, limit=40)
        if normalized_action not in TENANT_STATE_ACTIONS:
            return {
                "result": "platform-tenant-state-invalid-action",
                "errors": {"action": "Ação de estado inválida."},
            }

        with transaction.atomic():
            tenant = Tenant.objects.select_for_update().filter(slug=normalized_slug).first()
            if tenant is None:
                return {
                    "result": "platform-tenant-state-not-found",
                    "errors": {"tenant_slug": "Tenant não encontrado."},
                }

            previous_state = {
                "is_active": tenant.is_active,
                "maintenance_mode": tenant.maintenance_mode,
            }
            if normalized_action == "activate":
                tenant.is_active = True
            elif normalized_action == "deactivate":
                tenant.is_active = False
            elif normalized_action == "maintenance-on":
                tenant.maintenance_mode = True
            elif normalized_action == "maintenance-off":
                tenant.maintenance_mode = False
            tenant.save(update_fields=["is_active", "maintenance_mode", "updated_at"])

            audit_result = audit_log_commands.record_event(
                tenant_id=None,
                module="tenants",
                action=f"platform.tenant.{normalized_action}",
                entity_type="Tenant",
                entity_id=str(tenant.id),
                actor_label=_string(actor_label, limit=180),
                summary="Estado do tenant alterado por surface platform.",
                metadata={
                    "tenant_slug": tenant.slug,
                    "tenant_subdomain": tenant.subdomain,
                    "previous_is_active": previous_state["is_active"],
                    "previous_maintenance_mode": previous_state["maintenance_mode"],
                    "is_active": tenant.is_active,
                    "maintenance_mode": tenant.maintenance_mode,
                },
                allow_platform_scope=True,
            )
            if audit_result.get("result") != "audit-recorded":
                transaction.set_rollback(True)
                return {
                    "result": "platform-tenant-state-audit-unavailable",
                    "errors": {"__all__": "AuditLog platform-scope obrigatório para alterar estado da loja."},
                }

        return {
            "result": "platform-tenant-state-updated",
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "subdomain": tenant.subdomain,
                "is_active": tenant.is_active,
                "maintenance_mode": tenant.maintenance_mode,
            },
            "action": normalized_action,
            "previous_state": previous_state,
        }

    def update_custom_domain(
        self,
        *,
        tenant_slug: object,
        custom_domain: object,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._check_manage_permission(
            actor_role=actor_role,
            denied_result="platform-tenant-custom-domain-permission-denied",
        )
        if denied:
            return denied

        normalized_slug = _normalize_slug(tenant_slug, limit=150)
        normalized_domain = _normalize_custom_domain(custom_domain)
        domain_error = _custom_domain_error(normalized_domain)
        if domain_error:
            return {
                "result": "platform-tenant-custom-domain-invalid",
                "errors": {"custom_domain": domain_error},
            }

        with transaction.atomic():
            tenant = Tenant.objects.select_for_update().filter(slug=normalized_slug).first()
            if tenant is None:
                return {
                    "result": "platform-tenant-custom-domain-not-found",
                    "errors": {"tenant_slug": "Tenant não encontrado."},
                }

            if (
                normalized_domain
                and Tenant.objects.filter(custom_domain__iexact=normalized_domain)
                .exclude(pk=tenant.pk)
                .exists()
            ):
                return {
                    "result": "platform-tenant-custom-domain-invalid",
                    "errors": {"custom_domain": "Já existe uma loja com este domínio customizado."},
                }

            previous_custom_domain = tenant.custom_domain or ""
            tenant.custom_domain = normalized_domain or None
            tenant.save(update_fields=["custom_domain", "updated_at"])

            audit_result = audit_log_commands.record_event(
                tenant_id=None,
                module="tenants",
                action="platform.tenant.custom_domain_updated",
                entity_type="Tenant",
                entity_id=str(tenant.id),
                actor_label=_string(actor_label, limit=180),
                summary="Domínio customizado do tenant alterado por surface platform.",
                metadata={
                    "tenant_slug": tenant.slug,
                    "tenant_subdomain": tenant.subdomain,
                    "previous_custom_domain": previous_custom_domain,
                    "custom_domain": tenant.custom_domain or "",
                    "custom_domain_configured": bool(tenant.custom_domain),
                },
                allow_platform_scope=True,
            )
            if audit_result.get("result") != "audit-recorded":
                transaction.set_rollback(True)
                return {
                    "result": "platform-tenant-custom-domain-audit-unavailable",
                    "errors": {"__all__": "AuditLog platform-scope obrigatório para alterar domínio customizado."},
                }

        return {
            "result": "platform-tenant-custom-domain-updated",
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "subdomain": tenant.subdomain,
                "custom_domain": tenant.custom_domain or "",
                "is_active": tenant.is_active,
                "maintenance_mode": tenant.maintenance_mode,
            },
            "previous_custom_domain": previous_custom_domain,
        }

    def bootstrap_owner(
        self,
        *,
        tenant_slug: object,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._check_manage_permission(
            actor_role=actor_role,
            denied_result="platform-tenant-owner-bootstrap-permission-denied",
        )
        if denied:
            return denied

        normalized_slug = _normalize_slug(tenant_slug, limit=150)
        owner_email = _string(payload.get("owner_email"), limit=254).lower()
        owner_name = _string(payload.get("owner_name"), limit=150)
        owner_role = _string(payload.get("owner_role"), limit=64).lower().replace("-", "_") or "owner"
        errors: dict[str, str] = {}
        if not owner_email or "@" not in owner_email:
            errors["owner_email"] = "Informe um e-mail válido para o owner inicial."
        if owner_role not in {"owner", "admin"}:
            errors["owner_role"] = "Owner inicial aceita apenas role owner ou admin."
        if errors:
            return {"result": "platform-tenant-owner-bootstrap-invalid", "errors": errors}

        with transaction.atomic():
            tenant = Tenant.objects.select_for_update().filter(slug=normalized_slug, is_active=True).first()
            if tenant is None:
                return {
                    "result": "platform-tenant-owner-bootstrap-not-found",
                    "errors": {"tenant_slug": "Tenant ativo não encontrado."},
                }

            existing_active_owner = OwnerUser.objects.filter(tenant=tenant, is_active=True).first()
            if existing_active_owner is not None:
                return {
                    "result": "platform-tenant-owner-bootstrap-already-has-owner",
                    "errors": {"__all__": "Tenant já possui owner ativo."},
                    "owner": {"id": existing_active_owner.id, "email": existing_active_owner.email},
                }

            provisioning_result = initial_owner_provisioning_commands.provision_initial_owner(
                tenant_id=tenant.id,
                email=owner_email,
                full_name=owner_name,
                role=owner_role,
                actor_label=_string(actor_label, limit=180),
            )
            if provisioning_result.get("result") != "initial-owner-provisioned":
                transaction.set_rollback(True)
                return {
                    "result": "platform-tenant-owner-bootstrap-invalid",
                    "errors": provisioning_result.get("errors") or {"__all__": "Não foi possível provisionar owner inicial."},
                    "provisioning_result": provisioning_result.get("result"),
                }

            owner = provisioning_result.get("owner") or {}
            user = provisioning_result.get("user") or {}
            audit_result = audit_log_commands.record_event(
                tenant_id=None,
                module="tenants",
                action="platform.tenant.owner_bootstrapped",
                entity_type="OwnerUser",
                entity_id=str(owner.get("id") or ""),
                actor_label=_string(actor_label, limit=180),
                summary="Owner inicial do tenant provisionado por surface platform.",
                metadata={
                    "tenant_id": tenant.id,
                    "tenant_slug": tenant.slug,
                    "tenant_subdomain": tenant.subdomain,
                    "owner_email": owner_email,
                    "owner_role": owner_role,
                    "owner_created": bool(owner.get("created")),
                    "user_id": user.get("id"),
                    "user_created": bool(user.get("created")),
                },
                allow_platform_scope=True,
            )
            if audit_result.get("result") != "audit-recorded":
                transaction.set_rollback(True)
                return {
                    "result": "platform-tenant-owner-bootstrap-audit-unavailable",
                    "errors": {"__all__": "AuditLog platform-scope obrigatório para provisionar owner inicial."},
                }

        return {
            "result": "platform-tenant-owner-bootstrapped",
            "tenant": {"id": tenant.id, "slug": tenant.slug, "subdomain": tenant.subdomain},
            "owner": owner,
            "user": user,
        }

    def _validate(self, values: dict[str, object]) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not values["name"]:
            errors["name"] = "Nome da loja é obrigatório."
        if not values["slug"]:
            errors["slug"] = "Slug do tenant é obrigatório."
        elif Tenant.objects.filter(slug=values["slug"]).exists():
            errors["slug"] = "Já existe uma loja com este slug."
        if not values["subdomain"]:
            errors["subdomain"] = "Subdomínio é obrigatório."
        elif values["subdomain"] in _reserved_subdomains():
            errors["subdomain"] = "Este subdomínio é reservado para a plataforma."
        elif Tenant.objects.filter(subdomain=values["subdomain"]).exists():
            errors["subdomain"] = "Já existe uma loja com este subdomínio."
        if values["custom_domain"] and Tenant.objects.filter(custom_domain__iexact=values["custom_domain"]).exists():
            errors["custom_domain"] = "Já existe uma loja com este domínio customizado."
        return errors


platform_tenant_admin_commands = PlatformTenantAdminCommandService()
