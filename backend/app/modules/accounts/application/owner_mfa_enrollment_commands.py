from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, admin_permissions
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class OwnerMfaEnrollmentCommandService:
    def register_factor(
        self,
        *,
        tenant_id: int | str | None,
        owner_id: int | str,
        factor_type: object,
        provider_key: object = "internal",
        label: object = "",
        secret_reference: object = "",
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-mfa-permission-denied", "errors": {"__all__": "Permissão insuficiente para gerenciar MFA."}}
        owner = self._get_owner(tenant_id=tenant_id, owner_id=owner_id)
        if owner is None:
            return {"result": "owner-mfa-owner-not-found", "errors": {"__all__": "Owner não encontrado neste tenant."}}
        factor_type_value = _string(factor_type, limit=32)
        provider_key_value = _string(provider_key, limit=64) or "internal"
        if factor_type_value not in OwnerMfaFactor.FactorType.values:
            return {"result": "owner-mfa-invalid", "errors": {"factor_type": "Tipo de fator MFA inválido."}}
        factor, created = OwnerMfaFactor.objects.get_or_create(
            tenant_id=owner.tenant_id,
            owner=owner,
            factor_type=factor_type_value,
            provider_key=provider_key_value,
            defaults={
                "label": _string(label, limit=120),
                "secret_reference": _string(secret_reference, limit=255),
                "is_verified": False,
                "is_active": True,
            },
        )
        changed = created
        if not factor.is_active:
            factor.is_active = True
            changed = True
        new_label = _string(label, limit=120)
        new_secret_reference = _string(secret_reference, limit=255)
        if new_label and factor.label != new_label:
            factor.label = new_label
            changed = True
        if new_secret_reference and factor.secret_reference != new_secret_reference:
            factor.secret_reference = new_secret_reference
            changed = True
        if changed:
            factor.save()
            self._record_factor_event(factor=factor, action="owner.mfa_factor_registered", actor_label=actor_label)
            result = "owner-mfa-factor-registered" if created else "owner-mfa-factor-reactivated"
            return {"result": result, "factor": {"id": factor.id, "is_verified": factor.is_verified}}
        return {"result": "owner-mfa-factor-unchanged", "factor": {"id": factor.id, "is_verified": factor.is_verified}}

    def deactivate_factor(
        self,
        *,
        tenant_id: int | str | None,
        factor_id: int | str,
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-mfa-permission-denied", "errors": {"__all__": "Permissão insuficiente para gerenciar MFA."}}
        factor = OwnerMfaFactor.objects.filter(tenant_id=tenant_id, id=factor_id).select_related("owner").first()
        if factor is None:
            return {"result": "owner-mfa-factor-not-found", "errors": {"__all__": "Fator MFA não encontrado neste tenant."}}
        if not factor.is_active:
            return {"result": "owner-mfa-factor-unchanged", "factor": {"id": factor.id, "is_active": False}}
        factor.is_active = False
        factor.save(update_fields=("is_active", "updated_at"))
        self._record_factor_event(factor=factor, action="owner.mfa_factor_deactivated", actor_label=actor_label)
        return {"result": "owner-mfa-factor-deactivated", "factor": {"id": factor.id, "is_active": False}}

    def _get_owner(self, *, tenant_id: int | str | None, owner_id: int | str):
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_owner_id = str(owner_id or "").strip()
        if not normalized_tenant_id or not normalized_owner_id:
            return None
        return OwnerUser.objects.filter(tenant_id=normalized_tenant_id, id=normalized_owner_id, is_active=True).first()

    def _record_factor_event(self, *, factor: OwnerMfaFactor, action: str, actor_label: str) -> None:
        audit_log_commands.record_event(
            tenant_id=factor.tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerMfaFactor",
            entity_id=str(factor.id),
            actor_label=actor_label,
            summary=f"Fator MFA {factor.factor_type} atualizado para owner {factor.owner.email}.",
            metadata={
                "owner_id": factor.owner_id,
                "owner_email": factor.owner.email,
                "factor_type": factor.factor_type,
                "provider_key": factor.provider_key,
                "is_verified": factor.is_verified,
                "is_active": factor.is_active,
            },
        )


owner_mfa_enrollment_commands = OwnerMfaEnrollmentCommandService()
