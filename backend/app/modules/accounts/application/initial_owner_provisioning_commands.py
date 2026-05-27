from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import User
from django.db import transaction

from app.modules.accounts.models import OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.tenants.models import Tenant


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _username_from_email(email: str) -> str:
    base = email.split("@", 1)[0].replace(".", "-").replace("_", "-") or "owner"
    username = base[:120]
    if not User.objects.filter(username__iexact=username).exists():
        return username
    suffix = 2
    while True:
        candidate = f"{base[:110]}-{suffix}"
        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate
        suffix += 1


@dataclass
class InitialOwnerProvisioningCommandService:
    def provision_initial_owner(
        self,
        *,
        tenant_id: int | str | None,
        email: object,
        full_name: object = "",
        role: object = "owner",
        dry_run: bool = False,
        actor_label: object = "system",
    ) -> dict[str, object]:
        normalized_email = _email(email)
        normalized_role = _string(role, limit=64).lower().replace("-", "_") or "owner"
        if not tenant_id:
            return {"result": "initial-owner-tenant-required", "errors": {"__all__": "Tenant obrigatório para provisionar owner inicial."}}
        if not normalized_email or "@" not in normalized_email:
            return {"result": "initial-owner-invalid", "errors": {"email": "Informe um e-mail válido."}}
        if normalized_role not in {"owner", "admin"}:
            return {"result": "initial-owner-invalid", "errors": {"role": "Provisionamento inicial aceita apenas owner ou admin."}}

        tenant = Tenant.objects.filter(pk=tenant_id, is_active=True).first()
        if tenant is None:
            return {"result": "initial-owner-tenant-not-found", "errors": {"__all__": "Tenant ativo não encontrado."}}

        existing_owner = OwnerUser.objects.filter(tenant=tenant, email__iexact=normalized_email).first()
        user_matches = list(User.objects.filter(email__iexact=normalized_email).order_by("id")[:2])
        if len(user_matches) > 1:
            return {"result": "initial-owner-ambiguous-user", "errors": {"__all__": "Há mais de um User Django com este e-mail."}}

        if dry_run:
            return {
                "result": "initial-owner-dry-run",
                "tenant": {"id": tenant.id, "slug": tenant.slug},
                "owner": {"exists": existing_owner is not None, "email": normalized_email},
                "user": {"exists": bool(user_matches), "email": normalized_email},
            }

        with transaction.atomic():
            owner_created = False
            user_created = False
            if existing_owner is None:
                owner = OwnerUser.objects.create(
                    tenant=tenant,
                    email=normalized_email,
                    full_name=_string(full_name, limit=150),
                    role=normalized_role,
                    is_active=True,
                    receives_notifications=True,
                )
                owner_created = True
            else:
                owner = existing_owner
                changed_fields: list[str] = []
                if not owner.is_active:
                    owner.is_active = True
                    changed_fields.append("is_active")
                if not owner.receives_notifications:
                    owner.receives_notifications = True
                    changed_fields.append("receives_notifications")
                if owner.role not in {"owner", "admin"}:
                    owner.role = normalized_role
                    changed_fields.append("role")
                if changed_fields:
                    owner.save(update_fields=[*changed_fields, "updated_at"])

            if user_matches:
                user = user_matches[0]
                if not user.is_active:
                    return {"result": "initial-owner-inactive-user", "errors": {"__all__": "User Django existente está inativo."}}
            else:
                user = User.objects.create_user(
                    username=_username_from_email(normalized_email),
                    email=normalized_email,
                    password=None,
                    first_name=_string(full_name, limit=150),
                )
                user.set_unusable_password()
                user.save(update_fields=("password",))
                user_created = True

            audit_log_commands.record_event(
                tenant_id=tenant.id,
                module="accounts",
                action="owner.initial_provisioned",
                entity_type="OwnerUser",
                entity_id=str(owner.id),
                actor_label=_string(actor_label, limit=180),
                summary=f"Owner inicial {owner.email} provisionado para tenant {tenant.slug}.",
                metadata={
                    "email": owner.email,
                    "role": owner.role,
                    "owner_created": owner_created,
                    "user_created": user_created,
                    "user_id": user.id,
                },
            )

        return {
            "result": "initial-owner-provisioned",
            "tenant": {"id": tenant.id, "slug": tenant.slug},
            "owner": {"id": owner.id, "email": owner.email, "created": owner_created},
            "user": {"id": user.id, "email": user.email, "created": user_created},
        }


initial_owner_provisioning_commands = InitialOwnerProvisioningCommandService()
