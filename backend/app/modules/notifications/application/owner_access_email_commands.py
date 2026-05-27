from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_dispatch_envelopes import NotificationDispatchEnvelope
from app.modules.notifications.application.notification_log_writer import EmailLogWriteResult, record_email_log_from_envelope


def _string(value: object, *, limit: int = 240) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class OwnerAccessEmailCommandService:
    def record_owner_invite_email(
        self,
        *,
        tenant_id: int | str,
        owner_id: int | str,
        owner_email: object,
        owner_name: object = "",
        reset_url: object,
    ) -> EmailLogWriteResult:
        email = _string(owner_email, limit=254).lower()
        return record_email_log_from_envelope(
            envelope=NotificationDispatchEnvelope(
                tenant_id=str(tenant_id),
                source_event="owner.invited",
                entity_type="owner_user",
                entity_id=str(owner_id),
                audience="owner",
                channel="email",
                intent_key="owner.access.invite",
                idempotency_key=f"{tenant_id}:owner.access.invite:owner_user:{owner_id}",
                recipient_delivery_key=f"{tenant_id}:owner.access.invite:owner_user:{owner_id}:email:{email}",
                recipient_type="owner_user",
                recipient_id=str(owner_id),
                recipient_email=email,
                recipient_display_name=_string(owner_name, limit=150),
                title="Acesso administrativo Hubx Market",
                description=(
                    "Seu acesso administrativo foi preparado para esta loja. "
                    f"Defina sua senha para entrar na operação: {_string(reset_url, limit=500)}"
                ),
                cta_label="",
                cta_target="",
            )
        )

    def record_owner_password_reset_email(
        self,
        *,
        tenant_id: int | str,
        owner_id: int | str,
        owner_email: object,
        owner_name: object = "",
        reset_url: object,
    ) -> EmailLogWriteResult:
        email = _string(owner_email, limit=254).lower()
        return record_email_log_from_envelope(
            envelope=NotificationDispatchEnvelope(
                tenant_id=str(tenant_id),
                source_event="owner.password_reset_requested",
                entity_type="owner_user",
                entity_id=str(owner_id),
                audience="owner",
                channel="email",
                intent_key="owner.access.password_reset",
                idempotency_key=f"{tenant_id}:owner.access.password_reset:owner_user:{owner_id}",
                recipient_delivery_key=f"{tenant_id}:owner.access.password_reset:owner_user:{owner_id}:email:{email}",
                recipient_type="owner_user",
                recipient_id=str(owner_id),
                recipient_email=email,
                recipient_display_name=_string(owner_name, limit=150),
                title="Redefinição de senha Hubx Market",
                description=(
                    "Recebemos uma solicitação para redefinir sua senha administrativa. "
                    f"Use este link para continuar: {_string(reset_url, limit=500)}"
                ),
                cta_label="",
                cta_target="",
            )
        )


owner_access_email_commands = OwnerAccessEmailCommandService()
