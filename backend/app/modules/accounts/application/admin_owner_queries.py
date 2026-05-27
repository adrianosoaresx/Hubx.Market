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

    def get_owner_role_by_email(self, *, tenant_id: int | str | None, email: object) -> str:
        if self.owner_model is None:
            return ""
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_email = str(email or "").strip()
        if not normalized_tenant_id or not normalized_email:
            return ""
        owner = self.owner_model._default_manager.filter(
            tenant_id=normalized_tenant_id,
            email__iexact=normalized_email,
            is_active=True,
        ).first()
        return str(getattr(owner, "role", "") or "").strip()

    def get_owner(self, *, tenant_id: int | str | None, owner_id: int | str | None) -> AdminOwnerItem | None:
        if self.owner_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_owner_id = str(owner_id or "").strip()
        if not normalized_tenant_id or not normalized_owner_id:
            return None
        owner = self.owner_model._default_manager.filter(tenant_id=normalized_tenant_id, pk=normalized_owner_id).first()
        if owner is None:
            return None
        return AdminOwnerItem(
            id=owner.id,
            email=owner.email,
            full_name=owner.full_name,
            role=owner.role,
            is_active=owner.is_active,
            receives_notifications=owner.receives_notifications,
        )


@dataclass
class AdminOwnerQueryService:
    repository: DjangoOrmAdminOwnerQueryRepository

    def list_owners(self, *, tenant_id: int | str, search: str = "") -> list[AdminOwnerItem]:
        return self.repository.list_owners(tenant_id=tenant_id, search=search)

    def get_owner_role_by_email(self, *, tenant_id: int | str | None, email: object) -> str:
        return self.repository.get_owner_role_by_email(tenant_id=tenant_id, email=email)

    def get_owner(self, *, tenant_id: int | str | None, owner_id: int | str | None) -> AdminOwnerItem | None:
        return self.repository.get_owner(tenant_id=tenant_id, owner_id=owner_id)


admin_owner_queries = AdminOwnerQueryService(repository=DjangoOrmAdminOwnerQueryRepository())
