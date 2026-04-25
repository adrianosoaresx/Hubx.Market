from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationRecipientTarget:
    tenant_id: str
    audience: str
    recipient_type: str
    recipient_id: str
    email: str
    display_name: str

    @property
    def is_deliverable(self) -> bool:
        return bool(self.email)


def build_customer_recipient_target(
    *,
    tenant_id: int | str,
    customer_id: int | str,
    email: str,
    display_name: str = "",
) -> NotificationRecipientTarget | None:
    normalized_tenant_id = str(tenant_id or "").strip()
    normalized_customer_id = str(customer_id or "").strip()
    if not normalized_tenant_id or not normalized_customer_id:
        return None

    return NotificationRecipientTarget(
        tenant_id=normalized_tenant_id,
        audience="customer",
        recipient_type="customer",
        recipient_id=normalized_customer_id,
        email=str(email or "").strip(),
        display_name=str(display_name or "").strip(),
    )


def build_owner_recipient_target(
    *,
    tenant_id: int | str,
    owner_id: int | str,
    email: str,
    display_name: str = "",
) -> NotificationRecipientTarget | None:
    normalized_tenant_id = str(tenant_id or "").strip()
    normalized_owner_id = str(owner_id or "").strip()
    if not normalized_tenant_id or not normalized_owner_id:
        return None

    return NotificationRecipientTarget(
        tenant_id=normalized_tenant_id,
        audience="owner",
        recipient_type="owner_user",
        recipient_id=normalized_owner_id,
        email=str(email or "").strip(),
        display_name=str(display_name or "").strip(),
    )
