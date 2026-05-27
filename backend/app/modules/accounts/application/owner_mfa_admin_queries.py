from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.models import OwnerMfaFactor


@dataclass(frozen=True)
class OwnerMfaAdminFactorItem:
    id: int
    owner_id: int
    owner_email: str
    factor_type: str
    provider_key: str
    label: str
    is_verified: bool
    is_active: bool
    verified_at: object
    last_challenged_at: object


@dataclass
class OwnerMfaAdminQueryService:
    def list_factors(self, *, tenant_id: int | str | None, search: str = "") -> list[OwnerMfaAdminFactorItem]:
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return []
        queryset = OwnerMfaFactor.objects.filter(tenant_id=normalized_tenant_id).select_related("owner").order_by("owner__email", "factor_type")
        normalized_search = str(search or "").strip()
        if normalized_search:
            queryset = queryset.filter(owner__email__icontains=normalized_search)
        return [
            OwnerMfaAdminFactorItem(
                id=factor.id,
                owner_id=factor.owner_id,
                owner_email=factor.owner.email,
                factor_type=factor.factor_type,
                provider_key=factor.provider_key,
                label=factor.label,
                is_verified=factor.is_verified,
                is_active=factor.is_active,
                verified_at=factor.verified_at,
                last_challenged_at=factor.last_challenged_at,
            )
            for factor in queryset
        ]


owner_mfa_admin_queries = OwnerMfaAdminQueryService()
