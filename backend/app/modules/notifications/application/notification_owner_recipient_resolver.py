from __future__ import annotations

from typing import Protocol

from app.modules.notifications.application.notification_recipient_targets import (
    NotificationRecipientTarget,
    build_owner_recipient_target,
)


class OwnerRecipientRepository(Protocol):
    def list_active_owners(self, *, tenant_id: int | str) -> list[object]:
        ...


class DjangoOrmOwnerRecipientRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts.models import OwnerUser
        except Exception:
            self.owner_model = None
            return
        self.owner_model = OwnerUser

    def list_active_owners(self, *, tenant_id: int | str) -> list[object]:
        if self.owner_model is None:
            return []
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return []
        try:
            return list(
                self.owner_model._default_manager.filter(
                    tenant_id=normalized_tenant_id,
                    is_active=True,
                    receives_notifications=True,
                ).order_by("email")
            )
        except Exception:
            return []


def resolve_owner_recipient_targets(
    *,
    tenant_id: int | str,
    repository: OwnerRecipientRepository | None = None,
) -> list[NotificationRecipientTarget]:
    repo = repository or DjangoOrmOwnerRecipientRepository()
    targets: list[NotificationRecipientTarget] = []
    for owner in repo.list_active_owners(tenant_id=tenant_id):
        target = build_owner_recipient_target(
            tenant_id=tenant_id,
            owner_id=getattr(owner, "id", ""),
            email=getattr(owner, "email", ""),
            display_name=getattr(owner, "full_name", ""),
        )
        if target is not None and target.is_deliverable:
            targets.append(target)
    return targets
