from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.models import OwnerMfaFactor, OwnerMfaRecoveryCode, OwnerUser


@dataclass(frozen=True)
class OwnerMfaEnrollmentSummary:
    owner_id: int
    email: str
    role: str
    active_factor_count: int
    verified_factor_count: int

    @property
    def enrolled(self) -> bool:
        return self.active_factor_count > 0 and self.verified_factor_count > 0


@dataclass
class OwnerMfaEnrollmentQueryService:
    def list_owner_enrollment(self, *, tenant_id: int | str | None) -> dict[str, object]:
        if not tenant_id:
            return {
                "result": "owner-mfa-enrollment-tenant-required",
                "ready": False,
                "owners": (),
                "blockers": ("tenant-required",),
            }
        owners = list(OwnerUser.objects.filter(tenant_id=tenant_id, is_active=True).order_by("email"))
        factors = OwnerMfaFactor.objects.filter(tenant_id=tenant_id, owner_id__in=[owner.id for owner in owners])
        recovery_code_owner_ids = set(
            OwnerMfaRecoveryCode.objects.filter(
                tenant_id=tenant_id,
                owner_id__in=[owner.id for owner in owners],
                used_at__isnull=True,
            ).values_list("owner_id", flat=True)
        )
        factor_counts: dict[int, dict[str, int]] = {owner.id: {"active": 0, "verified": 0} for owner in owners}
        for factor in factors:
            if not factor.is_active:
                continue
            factor_counts.setdefault(factor.owner_id, {"active": 0, "verified": 0})
            factor_counts[factor.owner_id]["active"] += 1
            if factor.factor_type == OwnerMfaFactor.FactorType.RECOVERY_CODE:
                if factor.is_verified and factor.owner_id in recovery_code_owner_ids:
                    factor_counts[factor.owner_id]["verified"] += 1
            elif factor.is_verified:
                factor_counts[factor.owner_id]["verified"] += 1
        summaries = tuple(
            OwnerMfaEnrollmentSummary(
                owner_id=owner.id,
                email=owner.email,
                role=owner.role,
                active_factor_count=factor_counts.get(owner.id, {}).get("active", 0),
                verified_factor_count=factor_counts.get(owner.id, {}).get("verified", 0),
            )
            for owner in owners
        )
        blockers = tuple(f"owner-{summary.owner_id}:mfa-not-enrolled" for summary in summaries if not summary.enrolled)
        return {
            "result": "owner-mfa-enrollment-ready" if not blockers else "owner-mfa-enrollment-incomplete",
            "ready": not blockers,
            "owners": summaries,
            "owner_count": len(summaries),
            "enrolled_owner_count": sum(1 for summary in summaries if summary.enrolled),
            "blockers": blockers,
        }


owner_mfa_enrollment_queries = OwnerMfaEnrollmentQueryService()
