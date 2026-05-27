from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers


LOCAL_PREFIX = "plain:"
REFERENCE_PREFIX = "ref:"


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaSecretResolution:
    result: str
    storage_mode: str
    secret: str
    reference: str
    ready: bool


@dataclass
class OwnerMfaSecretStorageResolver:
    def resolve(self, secret_reference: object) -> OwnerMfaSecretResolution:
        value = _string(secret_reference)
        if not value:
            return OwnerMfaSecretResolution(
                result="owner-mfa-secret-missing",
                storage_mode="missing",
                secret="",
                reference="",
                ready=False,
            )
        if value.startswith(REFERENCE_PREFIX):
            reference = value[len(REFERENCE_PREFIX) :].strip()
            provider_result = owner_mfa_secret_providers.resolve(reference)
            return OwnerMfaSecretResolution(
                result=provider_result.result,
                storage_mode="external-reference",
                secret=provider_result.secret,
                reference=reference,
                ready=provider_result.ready,
            )
        return OwnerMfaSecretResolution(
            result="owner-mfa-secret-local-unsupported",
            storage_mode="unsupported-local",
            secret="",
            reference="",
            ready=False,
        )

    def can_accept_local_plain(self) -> bool:
        return bool(getattr(settings, "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET", True))


owner_mfa_secret_storage = OwnerMfaSecretStorageResolver()
