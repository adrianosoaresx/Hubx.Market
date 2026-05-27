from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


def _setting_bool(name: str, default: bool = False) -> bool:
    return bool(getattr(settings, name, default))


def _setting_string(name: str) -> str:
    return str(getattr(settings, name, "") or "").strip()


@dataclass(frozen=True)
class OwnerMfaSsoContract:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaSsoReadinessQueryService:
    def get_readiness(self) -> dict[str, object]:
        mfa_required = _setting_bool("OWNER_MFA_REQUIRED", False)
        mfa_provider = _setting_string("OWNER_MFA_PROVIDER")
        sso_enabled = _setting_bool("OWNER_SSO_ENABLED", False)
        sso_provider = _setting_string("OWNER_SSO_PROVIDER")
        sso_login_url = _setting_string("OWNER_SSO_LOGIN_URL")
        sso_callback_path = _setting_string("OWNER_SSO_CALLBACK_PATH")
        blockers: list[str] = []

        if mfa_required and not mfa_provider:
            blockers.append("owner-mfa-provider-missing")
        if sso_enabled and not sso_provider:
            blockers.append("owner-sso-provider-missing")
        if sso_enabled and not sso_login_url:
            blockers.append("owner-sso-login-url-missing")
        if sso_enabled and not sso_callback_path:
            blockers.append("owner-sso-callback-path-missing")

        return {
            "result": "owner-mfa-sso-ready" if not blockers else "owner-mfa-sso-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "mode": self._mode(mfa_required=mfa_required, sso_enabled=sso_enabled),
            "mfa_required": mfa_required,
            "mfa_provider": mfa_provider,
            "sso_enabled": sso_enabled,
            "sso_provider": sso_provider,
            "sso_login_url_configured": bool(sso_login_url),
            "sso_callback_path": sso_callback_path,
            "contracts": self._contracts(),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _mode(self, *, mfa_required: bool, sso_enabled: bool) -> str:
        if mfa_required and sso_enabled:
            return "password-mfa-sso"
        if mfa_required:
            return "password-mfa"
        if sso_enabled:
            return "sso"
        return "password-only"

    def _contracts(self) -> tuple[OwnerMfaSsoContract, ...]:
        return (
            OwnerMfaSsoContract(
                key="password-login",
                status="current",
                summary="login owner/admin atual continua baseado em User Django, OwnerUser tenant-scoped, rate limit e sessão owner",
            ),
            OwnerMfaSsoContract(
                key="mfa",
                status="contract-only",
                summary="MFA futuro deve ser aplicado depois da senha e antes de sessão owner efetiva",
            ),
            OwnerMfaSsoContract(
                key="sso",
                status="contract-only",
                summary="SSO futuro deve resolver identidade externa para User + OwnerUser do mesmo tenant",
            ),
            OwnerMfaSsoContract(
                key="audit",
                status="required",
                summary="desafios, bypasses, falhas e sucesso futuro devem registrar AuditLog owner access",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "não existe enrollment de MFA por owner nesta fase",
            "não existe provider SSO real conectado nesta fase",
            "não existe bypass/break-glass formal para owner MFA/SSO",
            "não existe UI de gerenciamento de fatores ou IdP",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Owner MFA Enrollment Model Review",
            "Owner SSO Provider Adapter Review",
            "Owner Break-Glass Access Review",
        )


owner_mfa_sso_readiness_queries = OwnerMfaSsoReadinessQueryService()
