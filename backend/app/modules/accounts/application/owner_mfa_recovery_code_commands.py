from __future__ import annotations

import secrets
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, admin_permissions
from app.modules.accounts.models import OwnerMfaFactor, OwnerMfaRecoveryCode, OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _normalize_code(value: object) -> str:
    return _string(value, limit=64).replace(" ", "").replace("-", "").upper()


@dataclass
class OwnerMfaRecoveryCodeCommandService:
    def generate_codes(
        self,
        *,
        tenant_id: int | str | None,
        owner_id: int | str,
        count: int = 8,
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-mfa-permission-denied", "errors": {"__all__": "Permissão insuficiente para gerar recovery codes."}}
        owner = self._get_owner(tenant_id=tenant_id, owner_id=owner_id)
        if owner is None:
            return {"result": "owner-mfa-owner-not-found", "errors": {"__all__": "Owner não encontrado neste tenant."}}
        safe_count = min(max(int(count or 0), 1), 20)
        raw_codes = tuple(self._new_code() for _ in range(safe_count))
        with transaction.atomic():
            OwnerMfaRecoveryCode.objects.filter(tenant_id=owner.tenant_id, owner=owner, used_at__isnull=True).delete()
            factor, _created = OwnerMfaFactor.objects.get_or_create(
                tenant_id=owner.tenant_id,
                owner=owner,
                factor_type=OwnerMfaFactor.FactorType.RECOVERY_CODE,
                provider_key="internal",
                defaults={"label": "Recovery codes", "is_verified": True, "is_active": True, "verified_at": timezone.now()},
            )
            factor.is_active = True
            factor.is_verified = True
            if factor.verified_at is None:
                factor.verified_at = timezone.now()
            factor.save(update_fields=("is_active", "is_verified", "verified_at", "updated_at"))
            OwnerMfaRecoveryCode.objects.bulk_create(
                [
                    OwnerMfaRecoveryCode(
                        tenant_id=owner.tenant_id,
                        owner=owner,
                        code_hash=make_password(_normalize_code(code)),
                        label=f"Recovery code {index}",
                    )
                    for index, code in enumerate(raw_codes, start=1)
                ]
            )
        self._record_event(
            owner=owner,
            action="owner.mfa_recovery_codes_generated",
            actor_label=actor_label,
            metadata={"count": safe_count},
        )
        return {"result": "owner-mfa-recovery-codes-generated", "codes": raw_codes, "count": safe_count}

    def consume_code(self, *, tenant_id: int | str | None, owner: OwnerUser, code: object) -> OwnerMfaRecoveryCode | None:
        normalized_code = _normalize_code(code)
        if not normalized_code:
            return None
        codes = OwnerMfaRecoveryCode.objects.filter(
            tenant_id=tenant_id,
            owner=owner,
            used_at__isnull=True,
        ).order_by("created_at")
        for recovery_code in codes:
            if check_password(normalized_code, recovery_code.code_hash):
                recovery_code.used_at = timezone.now()
                recovery_code.save(update_fields=("used_at",))
                self._record_event(
                    owner=owner,
                    action="owner.mfa_recovery_code_used",
                    actor_label=owner.email,
                    metadata={"recovery_code_id": recovery_code.id},
                )
                return recovery_code
        return None

    def unused_count(self, *, tenant_id: int | str | None, owner: OwnerUser) -> int:
        return OwnerMfaRecoveryCode.objects.filter(tenant_id=tenant_id, owner=owner, used_at__isnull=True).count()

    def _get_owner(self, *, tenant_id: int | str | None, owner_id: int | str):
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_owner_id = str(owner_id or "").strip()
        if not normalized_tenant_id or not normalized_owner_id:
            return None
        return OwnerUser.objects.filter(tenant_id=normalized_tenant_id, id=normalized_owner_id, is_active=True).first()

    def _new_code(self) -> str:
        token = secrets.token_hex(5).upper()
        return f"{token[:5]}-{token[5:]}"

    def _record_event(self, *, owner: OwnerUser, action: str, actor_label: str, metadata: dict[str, object]) -> None:
        audit_log_commands.record_event(
            tenant_id=owner.tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerMfaRecoveryCode",
            entity_id=str(owner.id),
            actor_label=actor_label,
            summary=f"Recovery codes MFA atualizados para owner {owner.email}.",
            metadata={"owner_id": owner.id, "owner_email": owner.email, **metadata},
        )


owner_mfa_recovery_code_commands = OwnerMfaRecoveryCodeCommandService()
