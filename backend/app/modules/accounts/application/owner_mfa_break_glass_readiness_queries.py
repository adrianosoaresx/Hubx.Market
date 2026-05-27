from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.models import OwnerUser


@dataclass
class OwnerMfaBreakGlassReadinessQueryService:
    def get_readiness(self, *, tenant_id: int | str | None) -> dict[str, object]:
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return {
                "result": "owner-mfa-break-glass-tenant-required",
                "ready": False,
                "enabled": False,
                "blockers": ("tenant-required",),
                "accounts": (),
            }
        enabled = bool(getattr(settings, "OWNER_MFA_BREAK_GLASS_ENABLED", False))
        configured_emails = self._configured_emails()
        active_owner_emails = tuple(
            str(email or "").strip().lower()
            for email in OwnerUser.objects.filter(tenant_id=normalized_tenant_id, is_active=True).order_by("email").values_list("email", flat=True)
        )
        accounts = tuple(email for email in configured_emails if email in active_owner_emails)
        blockers = []
        if not enabled:
            blockers.append("break-glass-disabled")
        if enabled and not configured_emails:
            blockers.append("break-glass-email-required")
        missing = tuple(email for email in configured_emails if email not in accounts)
        blockers.extend(f"break-glass-owner-missing:{email}" for email in missing)
        return {
            "result": "owner-mfa-break-glass-ready" if not blockers else "owner-mfa-break-glass-blocked",
            "ready": not blockers,
            "enabled": enabled,
            "configured_emails": configured_emails,
            "accounts": accounts,
            "blockers": tuple(blockers),
        }

    def _configured_emails(self) -> tuple[str, ...]:
        raw_value = getattr(settings, "OWNER_MFA_BREAK_GLASS_OWNER_EMAILS", ())
        if isinstance(raw_value, str):
            values = raw_value.split(",")
        else:
            values = raw_value
        return tuple(sorted({str(value or "").strip().lower() for value in values if str(value or "").strip()}))


owner_mfa_break_glass_readiness_queries = OwnerMfaBreakGlassReadinessQueryService()
