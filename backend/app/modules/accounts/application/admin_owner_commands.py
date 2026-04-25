from __future__ import annotations

from dataclasses import dataclass


class DjangoOrmAdminOwnerCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts.models import OwnerUser
        except Exception:
            self.owner_model = None
            return
        self.owner_model = OwnerUser

    def get_owner(self, *, tenant_id: int | str, owner_id: int | str):
        if self.owner_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_owner_id = str(owner_id or "").strip()
        if not normalized_tenant_id or not normalized_owner_id:
            return None
        try:
            return self.owner_model._default_manager.filter(id=normalized_owner_id, tenant_id=normalized_tenant_id).first()
        except Exception:
            return None


@dataclass
class AdminOwnerCommandService:
    repository: DjangoOrmAdminOwnerCommandRepository

    def set_notification_preference(
        self,
        *,
        tenant_id: int | str,
        owner_id: int | str,
        receives_notifications: bool,
    ) -> str:
        owner = self.repository.get_owner(tenant_id=tenant_id, owner_id=owner_id)
        if owner is None:
            return "owner-not-found"
        if bool(owner.receives_notifications) == bool(receives_notifications):
            return "owner-notifications-unchanged"
        owner.receives_notifications = bool(receives_notifications)
        owner.save(update_fields=("receives_notifications", "updated_at"))
        return "owner-notifications-enabled" if receives_notifications else "owner-notifications-disabled"


admin_owner_commands = AdminOwnerCommandService(repository=DjangoOrmAdminOwnerCommandRepository())
