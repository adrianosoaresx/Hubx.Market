from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdminOwnerItem:
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    receives_notifications: bool


class DjangoOrmAdminOwnerQueryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts.models import OwnerUser
        except Exception:
            self.owner_model = None
            return
        self.owner_model = OwnerUser

    def list_owners(self, *, tenant_id: int | str, search: str = "") -> list[AdminOwnerItem]:
        if self.owner_model is None:
            return []
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return []
        queryset = self.owner_model._default_manager.filter(tenant_id=normalized_tenant_id).order_by("email")
        normalized_search = str(search or "").strip()
        if normalized_search:
            queryset = queryset.filter(email__icontains=normalized_search)
        return [
            AdminOwnerItem(
                id=owner.id,
                email=owner.email,
                full_name=owner.full_name,
                role=owner.role,
                is_active=owner.is_active,
                receives_notifications=owner.receives_notifications,
            )
            for owner in queryset
        ]


@dataclass
class AdminOwnerQueryService:
    repository: DjangoOrmAdminOwnerQueryRepository

    def list_owners(self, *, tenant_id: int | str, search: str = "") -> list[AdminOwnerItem]:
        return self.repository.list_owners(tenant_id=tenant_id, search=search)


admin_owner_queries = AdminOwnerQueryService(repository=DjangoOrmAdminOwnerQueryRepository())
