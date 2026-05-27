from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.utils import timezone

from app.modules.accounts.application.owner_mfa_challenge_commands import TotpChallengeVerifier
from app.modules.accounts.application.owner_mfa_recovery_code_commands import owner_mfa_recovery_code_commands
from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.accounts.application.owner_access_rate_limit import owner_access_rate_limit
from app.modules.accounts.application.owner_session_policy import apply_owner_session_policy
from app.modules.audit.application.audit_log_commands import audit_log_commands


GENERIC_LOGIN_ERROR = "Não foi possível entrar com essas credenciais para esta loja."
OWNER_MFA_PENDING_SESSION_KEY = "hubx_owner_mfa_pending"


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _request_ip(request) -> str | None:
    forwarded = str(request.META.get("HTTP_X_FORWARDED_FOR", "") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or None


@dataclass
class OwnerLoginCommandService:
    mfa_verifier: TotpChallengeVerifier = field(default_factory=TotpChallengeVerifier)

    def authenticate_owner(
        self,
        *,
        request,
        tenant_id: int | None,
        login: object,
        password: object,
        remember_me: bool = False,
    ) -> dict[str, object]:
        normalized_login = _string(login)
        raw_password = str(password or "")
        if not tenant_id:
            return self._invalid("owner-login-tenant-required")
        if not normalized_login or not raw_password:
            return self._invalid("owner-login-invalid")

        rate_limit = owner_access_rate_limit.check_login_allowed(
            tenant_id=tenant_id,
            login=normalized_login,
            ip_address=_request_ip(request),
        )
        if not rate_limit.allowed:
            self._record_login_failure(
                request=request,
                tenant_id=tenant_id,
                login=normalized_login,
                reason=rate_limit.reason,
                metadata={"attempts": rate_limit.attempts, "max_attempts": rate_limit.max_attempts},
                action="owner.login_rate_limited",
            )
            return {
                "result": "owner-login-rate-limited",
                "errors": {"__all__": "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente."},
                "retry_after_seconds": rate_limit.retry_after_seconds,
            }

        user = self._resolve_user(normalized_login)
        if user is None:
            self._record_login_failure(request=request, tenant_id=tenant_id, login=normalized_login, reason="user-not-found")
            owner_access_rate_limit.record_login_failure(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
            return self._invalid("owner-login-invalid")

        authenticated_user = authenticate(request, username=user.get_username(), password=raw_password)
        if authenticated_user is None or not authenticated_user.is_active:
            self._record_login_failure(request=request, tenant_id=tenant_id, login=normalized_login, reason="invalid-credentials")
            owner_access_rate_limit.record_login_failure(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
            return self._invalid("owner-login-invalid")

        owner = OwnerUser.objects.filter(
            tenant_id=tenant_id,
            email__iexact=_string(authenticated_user.email),
            is_active=True,
        ).first()
        if owner is None:
            self._record_login_failure(request=request, tenant_id=tenant_id, login=normalized_login, reason="owner-not-found")
            owner_access_rate_limit.record_login_failure(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
            return self._invalid("owner-login-invalid")

        if self._mfa_required() and not self._owner_has_verified_factor(owner=owner):
            self._record_login_failure(
                request=request,
                tenant_id=tenant_id,
                login=normalized_login,
                reason="owner-mfa-factor-required",
                action="owner.login_mfa_blocked",
            )
            owner_access_rate_limit.record_login_failure(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
            return {
                "result": "owner-login-mfa-required",
                "errors": {"__all__": "MFA obrigatório para este owner, mas não há fator ativo/verificado."},
            }

        if self._mfa_required():
            self._set_mfa_pending(
                request=request,
                tenant_id=tenant_id,
                owner=owner,
                user=authenticated_user,
                remember_me=remember_me,
            )
            owner_access_rate_limit.clear_login_failures(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
            self._record_mfa_required(request=request, tenant_id=tenant_id, owner=owner)
            return {
                "result": "owner-login-mfa-challenge-required",
                "owner": {"id": owner.id, "email": owner.email, "role": owner.role},
            }

        django_login(request, authenticated_user)
        session_policy = apply_owner_session_policy(request, remember_me=remember_me)
        owner_access_rate_limit.clear_login_failures(tenant_id=tenant_id, login=normalized_login, ip_address=_request_ip(request))
        self._record_login(request=request, tenant_id=tenant_id, owner=owner, session_policy=session_policy)
        return {
            "result": "owner-login-authenticated",
            "owner": {"id": owner.id, "email": owner.email, "role": owner.role},
            "session": {
                "expiry_seconds": session_policy.expiry_seconds,
                "remembered": session_policy.remembered,
                "expires_at": session_policy.expires_at,
            },
        }

    def complete_mfa_challenge(
        self,
        *,
        request,
        tenant_id: int | None,
        challenge: object,
    ) -> dict[str, object]:
        pending = request.session.get(OWNER_MFA_PENDING_SESSION_KEY)
        if not tenant_id or not isinstance(pending, dict):
            return self._invalid("owner-mfa-challenge-missing")
        if str(pending.get("tenant_id")) != str(tenant_id):
            self._clear_mfa_pending(request)
            return self._invalid("owner-mfa-challenge-missing")
        if self._pending_expired(pending):
            self._clear_mfa_pending(request)
            return self._invalid("owner-mfa-challenge-expired")

        owner = OwnerUser.objects.filter(tenant_id=tenant_id, id=pending.get("owner_id"), is_active=True).first()
        user = User.objects.filter(id=pending.get("user_id"), is_active=True).first()
        if owner is None or user is None or _string(user.email).lower() != _string(owner.email).lower():
            self._clear_mfa_pending(request)
            return self._invalid("owner-mfa-challenge-missing")

        factor = OwnerMfaFactor.objects.filter(
            tenant_id=tenant_id,
            owner=owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            is_active=True,
            is_verified=True,
        ).order_by("id").first()
        if factor is not None and self._verify_totp_factor(factor=factor, challenge=challenge):
            factor.last_challenged_at = timezone.now()
            factor.save(update_fields=("last_challenged_at", "updated_at"))
            return self._complete_owner_login_after_mfa(
                request=request,
                tenant_id=tenant_id,
                owner=owner,
                user=user,
                pending=pending,
                metadata={"factor_id": factor.id, "factor_type": factor.factor_type},
            )

        recovery_code = owner_mfa_recovery_code_commands.consume_code(tenant_id=tenant_id, owner=owner, code=challenge)
        if recovery_code is not None:
            return self._complete_owner_login_after_mfa(
                request=request,
                tenant_id=tenant_id,
                owner=owner,
                user=user,
                pending=pending,
                metadata={"recovery_code_id": recovery_code.id, "factor_type": OwnerMfaFactor.FactorType.RECOVERY_CODE},
            )

        if factor is None:
            self._record_mfa_failure(request=request, tenant_id=tenant_id, owner=owner, reason="invalid-challenge")
            return self._invalid("owner-mfa-challenge-invalid")

        self._record_mfa_failure(request=request, tenant_id=tenant_id, owner=owner, reason="invalid-challenge")
        return self._invalid("owner-mfa-challenge-invalid")

    def _complete_owner_login_after_mfa(
        self,
        *,
        request,
        tenant_id: int,
        owner: OwnerUser,
        user: User,
        pending: dict[str, object],
        metadata: dict[str, object],
    ) -> dict[str, object]:
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        session_policy = apply_owner_session_policy(request, remember_me=bool(pending.get("remember_me")))
        self._clear_mfa_pending(request)
        self._record_login(request=request, tenant_id=tenant_id, owner=owner, session_policy=session_policy)
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action="owner.login_mfa_completed",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=owner.email,
            summary=f"Owner {owner.email} concluiu challenge MFA.",
            metadata=metadata,
            ip_address=_request_ip(request),
        )
        return {
            "result": "owner-login-authenticated",
            "owner": {"id": owner.id, "email": owner.email, "role": owner.role},
        }

    def get_pending_mfa(self, *, request, tenant_id: int | None) -> dict[str, object]:
        pending = request.session.get(OWNER_MFA_PENDING_SESSION_KEY)
        if not tenant_id or not isinstance(pending, dict) or str(pending.get("tenant_id")) != str(tenant_id):
            return {"result": "owner-mfa-challenge-missing", "ready": False}
        if self._pending_expired(pending):
            self._clear_mfa_pending(request)
            return {"result": "owner-mfa-challenge-expired", "ready": False}
        return {
            "result": "owner-mfa-challenge-ready",
            "ready": True,
            "owner_email": pending.get("owner_email", ""),
            "next_url": pending.get("next_url", ""),
        }

    def logout_owner(self, *, request, tenant_id: int | None) -> dict[str, object]:
        owner = getattr(request, "owner_user", None) or self._resolve_owner_from_request(request=request, tenant_id=tenant_id)
        if owner is not None and tenant_id:
            audit_log_commands.record_event(
                tenant_id=tenant_id,
                module="accounts",
                action="owner.logout",
                entity_type="OwnerUser",
                entity_id=str(owner.id),
                actor_label=owner.email,
                summary=f"Owner {owner.email} saiu da operação.",
                metadata={"role": owner.role},
                ip_address=_request_ip(request),
            )
        django_logout(request)
        return {"result": "owner-logout-completed"}

    def _resolve_user(self, login: str):
        lookup = {"email__iexact": login} if "@" in login else {"username__iexact": login}
        matches = list(User.objects.filter(**lookup)[:2])
        if len(matches) != 1:
            return None
        return matches[0]

    def _record_login(self, *, request, tenant_id: int, owner: OwnerUser, session_policy) -> None:
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action="owner.login",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=owner.email,
            summary=f"Owner {owner.email} entrou na operação.",
            metadata={
                "role": owner.role,
                "logged_at": timezone.now().isoformat(),
                "session_expiry_seconds": session_policy.expiry_seconds,
                "session_remembered": session_policy.remembered,
            },
            ip_address=_request_ip(request),
        )

    def _record_mfa_required(self, *, request, tenant_id: int, owner: OwnerUser) -> None:
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action="owner.login_mfa_required",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=owner.email,
            summary=f"Owner {owner.email} precisa concluir MFA antes da sessão.",
            metadata={"role": owner.role},
            ip_address=_request_ip(request),
        )

    def _record_mfa_failure(self, *, request, tenant_id: int, owner: OwnerUser, reason: str) -> None:
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action="owner.login_mfa_failed",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=owner.email,
            summary="Falha de challenge MFA owner/admin.",
            metadata={"reason": reason},
            ip_address=_request_ip(request),
        )

    def _record_login_failure(
        self,
        *,
        request,
        tenant_id: int | None,
        login: str,
        reason: str,
        metadata: dict[str, object] | None = None,
        action: str = "owner.login_failed",
    ) -> None:
        if not tenant_id:
            return
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerUser",
            entity_id="",
            actor_label=login,
            summary="Falha de login owner/admin.",
            metadata={"reason": reason, **(metadata or {})},
            ip_address=_request_ip(request),
        )

    def _resolve_owner_from_request(self, *, request, tenant_id: int | None):
        user = getattr(request, "user", None)
        user_email = _string(getattr(user, "email", ""))
        if not tenant_id or not user_email or not getattr(user, "is_authenticated", False):
            return None
        return OwnerUser.objects.filter(tenant_id=tenant_id, email__iexact=user_email, is_active=True).first()

    def _mfa_required(self) -> bool:
        return bool(getattr(settings, "OWNER_MFA_REQUIRED", False))

    def _owner_has_verified_factor(self, *, owner: OwnerUser) -> bool:
        has_totp = OwnerMfaFactor.objects.filter(
            tenant_id=owner.tenant_id,
            owner=owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            is_active=True,
            is_verified=True,
        ).exists()
        if has_totp:
            return True
        return owner_mfa_recovery_code_commands.unused_count(tenant_id=owner.tenant_id, owner=owner) > 0

    def _verify_totp_factor(self, *, factor: OwnerMfaFactor, challenge: object) -> bool:
        resolution = owner_mfa_secret_storage.resolve(factor.secret_reference)
        if not resolution.ready:
            return False
        if resolution.storage_mode == "local-plain" and not owner_mfa_secret_storage.can_accept_local_plain():
            return False
        return self.mfa_verifier.verify(secret=resolution.secret, challenge=challenge)

    def _set_mfa_pending(self, *, request, tenant_id: int, owner: OwnerUser, user: User, remember_me: bool) -> None:
        expires_at = timezone.now() + timezone.timedelta(seconds=self._mfa_pending_seconds())
        request.session[OWNER_MFA_PENDING_SESSION_KEY] = {
            "tenant_id": tenant_id,
            "owner_id": owner.id,
            "owner_email": owner.email,
            "user_id": user.id,
            "remember_me": bool(remember_me),
            "next_url": str(request.POST.get("next") or "")[:255],
            "expires_at": expires_at.isoformat(),
        }

    def _clear_mfa_pending(self, request) -> None:
        if OWNER_MFA_PENDING_SESSION_KEY in request.session:
            del request.session[OWNER_MFA_PENDING_SESSION_KEY]

    def _pending_expired(self, pending: dict[str, object]) -> bool:
        try:
            expires_at = timezone.datetime.fromisoformat(str(pending.get("expires_at") or ""))
        except ValueError:
            return True
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
        return timezone.now() > expires_at

    def _mfa_pending_seconds(self) -> int:
        return max(int(getattr(settings, "OWNER_MFA_CHALLENGE_PENDING_SECONDS", 300)), 60)

    def _invalid(self, result: str) -> dict[str, object]:
        return {"result": result, "errors": {"__all__": GENERIC_LOGIN_ERROR}}


owner_login_commands = OwnerLoginCommandService()
