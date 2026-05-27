from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import User

from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


@dataclass(frozen=True)
class OpsGateTenantReadiness:
    tenant_id: int
    tenant_slug: str
    subdomain: str
    active_owners: int
    owners_with_user: int
    missing_user_emails: tuple[str, ...]
    inactive_user_emails: tuple[str, ...]
    duplicate_user_emails: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return (
            self.active_owners > 0
            and self.owners_with_user > 0
            and not self.missing_user_emails
            and not self.inactive_user_emails
            and not self.duplicate_user_emails
        )

    @property
    def blockers(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.active_owners == 0:
            values.append("no_active_owner")
        if self.missing_user_emails:
            values.append("owner_without_django_user")
        if self.inactive_user_emails:
            values.append("owner_with_inactive_django_user")
        if self.duplicate_user_emails:
            values.append("owner_email_ambiguous")
        return tuple(values)


@dataclass
class OpsGateReadinessQueryService:
    def get_readiness(self, *, tenant_id: int | str | None = None) -> dict[str, object]:
        tenants = Tenant.objects.filter(is_active=True).order_by("slug")
        if tenant_id:
            tenants = tenants.filter(pk=tenant_id)

        tenant_results = [self._build_tenant_readiness(tenant=tenant) for tenant in tenants]
        blockers = [tenant for tenant in tenant_results if not tenant.ready]
        return {
            "result": "ops-gate-ready" if not blockers else "ops-gate-blocked",
            "ready": not blockers,
            "tenant_count": len(tenant_results),
            "blocked_tenant_count": len(blockers),
            "tenants": tenant_results,
        }

    def _build_tenant_readiness(self, *, tenant: Tenant) -> OpsGateTenantReadiness:
        owners = list(
            OwnerUser.objects.filter(tenant=tenant, is_active=True)
            .exclude(email="")
            .order_by("email")
        )
        owners_with_user = 0
        missing_user_emails: list[str] = []
        inactive_user_emails: list[str] = []
        duplicate_user_emails: list[str] = []

        for owner in owners:
            users = list(User.objects.filter(email__iexact=owner.email).order_by("id")[:2])
            if not users:
                missing_user_emails.append(owner.email)
                continue
            if len(users) > 1:
                duplicate_user_emails.append(owner.email)
                continue
            if not users[0].is_active:
                inactive_user_emails.append(owner.email)
                continue
            owners_with_user += 1

        return OpsGateTenantReadiness(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            subdomain=tenant.subdomain,
            active_owners=len(owners),
            owners_with_user=owners_with_user,
            missing_user_emails=tuple(missing_user_emails),
            inactive_user_emails=tuple(inactive_user_emails),
            duplicate_user_emails=tuple(duplicate_user_emails),
        )


ops_gate_readiness_queries = OpsGateReadinessQueryService()
