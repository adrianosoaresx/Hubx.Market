from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.models import User

from app.modules.accounts.application.admin_permissions import ROLE_ADMIN, ROLE_OWNER, ROLE_PERMISSIONS, admin_permissions
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


REQUIRED_OPS_PERMISSIONS = {
    "audit.view",
    "catalog.view",
    "checkout.view",
    "coupons.manage",
    "customers.view",
    "newsletter.view",
    "orders.view",
    "owners.manage",
    "pages.manage",
    "payments.view",
    "reviews.moderate",
    "shipping.view",
}


@dataclass(frozen=True)
class OpsRbacTenantReadiness:
    tenant_id: int
    tenant_slug: str
    active_owner_count: int
    full_admin_count: int
    unknown_roles: tuple[str, ...]
    full_admin_missing_user_emails: tuple[str, ...]
    full_admin_inactive_user_emails: tuple[str, ...]
    full_admin_duplicate_user_emails: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return (
            self.full_admin_count > 0
            and not self.unknown_roles
            and not self.full_admin_missing_user_emails
            and not self.full_admin_inactive_user_emails
            and not self.full_admin_duplicate_user_emails
        )

    @property
    def blockers(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.full_admin_count == 0:
            values.append("no_active_full_admin_owner")
        if self.unknown_roles:
            values.append("unknown_owner_role")
        if self.full_admin_missing_user_emails:
            values.append("full_admin_without_django_user")
        if self.full_admin_inactive_user_emails:
            values.append("full_admin_with_inactive_django_user")
        if self.full_admin_duplicate_user_emails:
            values.append("full_admin_email_ambiguous")
        return tuple(values)


@dataclass
class OpsRbacProductionReadinessQueryService:
    def get_readiness(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "enabled",
    ) -> dict[str, object]:
        gate_enabled = bool(getattr(settings, "HUBX_OPS_AUTH_GATE_ENFORCED", False))
        matrix_blockers = self._matrix_blockers()
        tenants = Tenant.objects.filter(is_active=True).order_by("slug")
        if tenant_id:
            tenants = tenants.filter(pk=tenant_id)

        tenant_results = [self._build_tenant_readiness(tenant=tenant) for tenant in tenants]
        blockers: list[str] = list(matrix_blockers)
        if expected_gate_state == "enabled" and not gate_enabled:
            blockers.append("ops-gate-not-enabled")
        if expected_gate_state == "disabled" and gate_enabled:
            blockers.append("ops-gate-already-enabled")
        for tenant in tenant_results:
            blockers.extend(f"tenant-{tenant.tenant_id}:{blocker}" for blocker in tenant.blockers)

        return {
            "result": "ops-rbac-production-ready" if not blockers else "ops-rbac-production-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "gate_enabled": gate_enabled,
            "expected_gate_state": expected_gate_state,
            "required_permissions": tuple(sorted(REQUIRED_OPS_PERMISSIONS)),
            "matrix_blockers": tuple(matrix_blockers),
            "tenants": tenant_results,
            "tenant_count": len(tenant_results),
            "blocked_tenant_count": sum(1 for tenant in tenant_results if not tenant.ready),
        }

    def _matrix_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        owner_permissions = ROLE_PERMISSIONS.get(ROLE_OWNER, set())
        admin_permissions_set = ROLE_PERMISSIONS.get(ROLE_ADMIN, set())
        missing_for_owner = sorted(REQUIRED_OPS_PERMISSIONS - owner_permissions)
        missing_for_admin = sorted(REQUIRED_OPS_PERMISSIONS - admin_permissions_set)
        if missing_for_owner:
            blockers.append(f"owner-role-missing-permissions:{','.join(missing_for_owner)}")
        if missing_for_admin:
            blockers.append(f"admin-role-missing-permissions:{','.join(missing_for_admin)}")
        return tuple(blockers)

    def _build_tenant_readiness(self, *, tenant: Tenant) -> OpsRbacTenantReadiness:
        owners = list(OwnerUser.objects.filter(tenant=tenant, is_active=True).exclude(email="").order_by("email"))
        unknown_roles: list[str] = []
        full_admin_count = 0
        missing_user_emails: list[str] = []
        inactive_user_emails: list[str] = []
        duplicate_user_emails: list[str] = []

        for owner in owners:
            decision = admin_permissions.check(role=owner.role, permission="owners.manage")
            if decision.reason == "admin-role-unknown":
                unknown_roles.append(str(owner.role or ""))
                continue
            if decision.role not in {ROLE_OWNER, ROLE_ADMIN}:
                continue
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
            full_admin_count += 1

        return OpsRbacTenantReadiness(
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            active_owner_count=len(owners),
            full_admin_count=full_admin_count,
            unknown_roles=tuple(sorted(set(unknown_roles))),
            full_admin_missing_user_emails=tuple(missing_user_emails),
            full_admin_inactive_user_emails=tuple(inactive_user_emails),
            full_admin_duplicate_user_emails=tuple(duplicate_user_emails),
        )


ops_rbac_production_readiness_queries = OpsRbacProductionReadinessQueryService()
