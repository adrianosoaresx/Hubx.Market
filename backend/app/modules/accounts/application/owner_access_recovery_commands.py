from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, admin_permissions
from app.modules.accounts.models import OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.notifications.application.owner_access_email_commands import owner_access_email_commands


GENERIC_RESET_MESSAGE = "Se este e-mail estiver habilitado para esta loja, enviaremos instruções de acesso."


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _username_from_email(email: str) -> str:
    base = email.split("@", 1)[0].replace(".", "-").replace("_", "-") or "owner"
    username = base[:120]
    if not User.objects.filter(username__iexact=username).exists():
        return username
    suffix = 2
    while True:
        candidate = f"{base[:110]}-{suffix}"
        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate
        suffix += 1


@dataclass
class OwnerAccessRecoveryCommandService:
    def invite_owner(
        self,
        *,
        request,
        tenant_id: int | str | None,
        owner_id: int | str,
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-invite-permission-denied", "errors": {"__all__": "Permissão insuficiente para convidar owners."}}

        owner = self._get_active_owner(tenant_id=tenant_id, owner_id=owner_id)
        if owner is None:
            return {"result": "owner-invite-not-found", "errors": {"__all__": "Owner ativo não encontrado neste tenant."}}

        user_result = self._get_or_create_user_for_owner(owner)
        if user_result["result"] != "owner-user-ready":
            return user_result

        user = user_result["user"]
        reset_url = self._build_reset_url(request=request, user=user)
        email_log = owner_access_email_commands.record_owner_invite_email(
            tenant_id=owner.tenant_id,
            owner_id=owner.id,
            owner_email=owner.email,
            owner_name=owner.full_name,
            reset_url=reset_url,
        ).log
        audit_log_commands.record_event(
            tenant_id=owner.tenant_id,
            module="accounts",
            action="owner.invited",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=actor_label,
            summary=f"Convite de acesso gerado para owner {owner.email}.",
            metadata={
                "email": owner.email,
                "role": owner.role,
                "created_user": bool(user_result.get("created")),
                "email_log_id": email_log.id,
            },
        )
        return {
            "result": "owner-invite-created",
            "owner": {"id": owner.id, "email": owner.email},
            "reset_url": reset_url,
            "email_log": {"id": email_log.id, "status": email_log.status},
        }

    def request_password_reset(self, *, request, tenant_id: int | str | None, email: object) -> dict[str, object]:
        normalized_email = _email(email)
        owner = OwnerUser.objects.filter(tenant_id=tenant_id, email__iexact=normalized_email, is_active=True).first()
        user = self._resolve_single_active_user(email=normalized_email)
        if owner is not None and user is not None:
            reset_url = self._build_reset_url(request=request, user=user)
            email_log = owner_access_email_commands.record_owner_password_reset_email(
                tenant_id=owner.tenant_id,
                owner_id=owner.id,
                owner_email=owner.email,
                owner_name=owner.full_name,
                reset_url=reset_url,
            ).log
            audit_log_commands.record_event(
                tenant_id=owner.tenant_id,
                module="accounts",
                action="owner.password_reset_requested",
                entity_type="OwnerUser",
                entity_id=str(owner.id),
                actor_label=owner.email,
                summary=f"Reset de senha solicitado para owner {owner.email}.",
                metadata={"email": owner.email, "email_log_id": email_log.id},
            )
            return {
                "result": "owner-password-reset-requested",
                "message": GENERIC_RESET_MESSAGE,
                "reset_url": reset_url,
                "email_log": {"id": email_log.id, "status": email_log.status},
            }
        return {"result": "owner-password-reset-requested", "message": GENERIC_RESET_MESSAGE}

    def complete_password_reset(
        self,
        *,
        tenant_id: int | str | None,
        uidb64: object,
        token: object,
        password: object,
        confirm_password: object,
    ) -> dict[str, object]:
        user = self._decode_user(uidb64)
        if user is None or not default_token_generator.check_token(user, _string(token, limit=256)):
            return {"result": "owner-password-reset-invalid", "errors": {"__all__": "Link de redefinição inválido ou expirado."}}
        owner = OwnerUser.objects.filter(tenant_id=tenant_id, email__iexact=user.email, is_active=True).first()
        if owner is None:
            return {"result": "owner-password-reset-invalid", "errors": {"__all__": "Link de redefinição inválido ou expirado."}}

        raw_password = str(password or "")
        if raw_password != str(confirm_password or ""):
            return {"result": "owner-password-reset-invalid", "errors": {"confirm_password": "As senhas informadas não conferem."}}
        try:
            validate_password(raw_password, user=user)
        except ValidationError as exc:
            return {"result": "owner-password-reset-invalid", "errors": {"password": " ".join(exc.messages)}}

        user.set_password(raw_password)
        user.is_active = True
        user.save(update_fields=("password", "is_active"))
        audit_log_commands.record_event(
            tenant_id=owner.tenant_id,
            module="accounts",
            action="owner.password_reset_completed",
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=owner.email,
            summary=f"Senha redefinida para owner {owner.email}.",
            metadata={"email": owner.email, "role": owner.role},
        )
        return {"result": "owner-password-reset-completed", "owner": {"id": owner.id, "email": owner.email}}

    def _get_active_owner(self, *, tenant_id: int | str | None, owner_id: int | str):
        return OwnerUser.objects.filter(pk=owner_id, tenant_id=tenant_id, is_active=True).first()

    def _get_or_create_user_for_owner(self, owner):
        matches = list(User.objects.filter(email__iexact=owner.email).order_by("id")[:2])
        if len(matches) > 1:
            return {"result": "owner-invite-ambiguous-user", "errors": {"__all__": "Há mais de um usuário Django com este e-mail."}}
        if matches:
            user = matches[0]
            if not user.is_active:
                return {"result": "owner-invite-inactive-user", "errors": {"__all__": "Usuário Django existente está inativo."}}
            return {"result": "owner-user-ready", "user": user, "created": False}
        user = User.objects.create_user(
            username=_username_from_email(owner.email),
            email=owner.email,
            password=None,
            first_name=owner.full_name[:150],
        )
        user.set_unusable_password()
        user.save(update_fields=("password",))
        return {"result": "owner-user-ready", "user": user, "created": True}

    def _resolve_single_active_user(self, *, email: str):
        if not email:
            return None
        matches = list(User.objects.filter(email__iexact=email).order_by("id")[:2])
        if len(matches) != 1 or not matches[0].is_active:
            return None
        return matches[0]

    def _build_reset_url(self, *, request, user) -> str:
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        path = reverse("accounts:reset-password-token", kwargs={"uidb64": uidb64, "token": token})
        return request.build_absolute_uri(path)

    def _decode_user(self, uidb64: object):
        try:
            user_id = force_str(urlsafe_base64_decode(_string(uidb64, limit=256)))
        except Exception:
            return None
        return User.objects.filter(pk=user_id, is_active=True).first()


owner_access_recovery_commands = OwnerAccessRecoveryCommandService()
