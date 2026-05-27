from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.owner_mfa_break_glass_readiness_queries import owner_mfa_break_glass_readiness_queries
from app.modules.accounts.application.owner_mfa_enrollment_queries import owner_mfa_enrollment_queries


@dataclass
class OwnerMfaLoginEnforcementReadinessQueryService:
    def get_readiness(self, *, tenant_id: int | str | None) -> dict[str, object]:
        mfa_required = bool(getattr(settings, "OWNER_MFA_REQUIRED", False))
        enrollment = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=tenant_id)
        break_glass = owner_mfa_break_glass_readiness_queries.get_readiness(tenant_id=tenant_id)
        blockers = []
        if not tenant_id:
            blockers.append("tenant-required")
        if not mfa_required:
            blockers.append("owner-mfa-required-disabled")
        if not enrollment.get("ready"):
            blockers.extend(f"enrollment:{blocker}" for blocker in enrollment.get("blockers", ()))
        if not break_glass.get("ready"):
            blockers.extend(f"break-glass:{blocker}" for blocker in break_glass.get("blockers", ()))
        return {
            "result": "owner-mfa-login-enforcement-ready" if not blockers else "owner-mfa-login-enforcement-blocked",
            "ready": not blockers,
            "mfa_required": mfa_required,
            "enrollment": enrollment,
            "break_glass": break_glass,
            "blockers": tuple(blockers),
            "manual_checks": (
                "validar login owner/admin com fator verificado",
                "validar falha de challenge sem criar sessão owner/admin",
                "validar break-glass documentado antes de ativar enforcement",
            ),
        }


owner_mfa_login_enforcement_readiness_queries = OwnerMfaLoginEnforcementReadinessQueryService()
