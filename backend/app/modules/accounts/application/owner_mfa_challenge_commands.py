from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import struct
import time
from dataclasses import dataclass, field

from django.utils import timezone

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, admin_permissions
from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class TotpChallengeVerifier:
    digits: int = 6
    interval_seconds: int = 30
    window: int = 1

    def verify(self, *, secret: str, challenge: object, now: int | None = None) -> bool:
        normalized_secret = self._normalize_secret(secret)
        normalized_challenge = _string(challenge, limit=16).replace(" ", "")
        if not normalized_secret or not normalized_challenge.isdigit():
            return False
        current_time = int(time.time() if now is None else now)
        time_step = current_time // self.interval_seconds
        return any(
            hmac.compare_digest(self._code(secret=normalized_secret, counter=time_step + offset), normalized_challenge)
            for offset in range(-self.window, self.window + 1)
        )

    def _normalize_secret(self, secret: str) -> bytes:
        normalized = _string(secret, limit=255).replace(" ", "").upper()
        if not normalized:
            return b""
        padding = "=" * ((8 - len(normalized) % 8) % 8)
        try:
            return base64.b32decode(normalized + padding, casefold=True)
        except (binascii.Error, ValueError):
            return b""

    def _code(self, *, secret: bytes, counter: int) -> str:
        digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(value % (10**self.digits)).zfill(self.digits)


@dataclass
class OwnerMfaChallengeCommandService:
    verifier: TotpChallengeVerifier = field(default_factory=TotpChallengeVerifier)

    def verify_factor(
        self,
        *,
        tenant_id: int | str | None,
        factor_id: int | str,
        challenge: object,
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-mfa-permission-denied", "errors": {"__all__": "Permissão insuficiente para verificar MFA."}}
        factor = OwnerMfaFactor.objects.filter(tenant_id=tenant_id, id=factor_id, is_active=True).select_related("owner").first()
        if factor is None:
            return {"result": "owner-mfa-factor-not-found", "errors": {"__all__": "Fator MFA ativo não encontrado neste tenant."}}
        if factor.factor_type != OwnerMfaFactor.FactorType.TOTP:
            return {"result": "owner-mfa-factor-unsupported", "errors": {"factor_type": "Somente TOTP interno pode ser verificado nesta fase."}}
        resolution = owner_mfa_secret_storage.resolve(factor.secret_reference)
        if not resolution.ready:
            return {"result": "owner-mfa-factor-not-ready", "errors": {"secret_reference": "Fator MFA não possui segredo TOTP resolvível nesta fase."}}
        if resolution.storage_mode == "local-plain" and not owner_mfa_secret_storage.can_accept_local_plain():
            return {"result": "owner-mfa-factor-not-ready", "errors": {"secret_reference": "Segredo TOTP local está desabilitado por configuração."}}
        verified = self.verifier.verify(secret=resolution.secret, challenge=challenge)
        factor.last_challenged_at = timezone.now()
        if not verified:
            factor.save(update_fields=("last_challenged_at", "updated_at"))
            self._record_factor_event(factor=factor, action="owner.mfa_factor_verification_failed", actor_label=actor_label)
            return {"result": "owner-mfa-factor-challenge-invalid", "factor": {"id": factor.id, "is_verified": factor.is_verified}}
        factor.is_verified = True
        factor.verified_at = timezone.now()
        factor.save(update_fields=("is_verified", "verified_at", "last_challenged_at", "updated_at"))
        self._record_factor_event(factor=factor, action="owner.mfa_factor_verified", actor_label=actor_label)
        return {"result": "owner-mfa-factor-verified", "factor": {"id": factor.id, "is_verified": True}}

    def _record_factor_event(self, *, factor: OwnerMfaFactor, action: str, actor_label: str) -> None:
        audit_log_commands.record_event(
            tenant_id=factor.tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerMfaFactor",
            entity_id=str(factor.id),
            actor_label=actor_label,
            summary=f"Challenge MFA {factor.factor_type} processado para owner {factor.owner.email}.",
            metadata={
                "owner_id": factor.owner_id,
                "owner_email": factor.owner.email,
                "factor_type": factor.factor_type,
                "provider_key": factor.provider_key,
                "is_verified": factor.is_verified,
                "is_active": factor.is_active,
            },
        )


owner_mfa_challenge_commands = OwnerMfaChallengeCommandService()
