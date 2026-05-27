from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from django.utils import timezone

from app.modules.notifications.application.notification_delivery_commands import EmailDeliveryCommandService
from app.modules.notifications.application.notification_failure_classification import classify_notification_failure
from app.modules.notifications.application.notification_provider_readiness import get_notification_provider_readiness
from app.modules.notifications.models import EmailLog


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _mask_email(value: object) -> str:
    email = _string(value, limit=254)
    if "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if not local or not domain:
        return ""
    visible = local[:2]
    return f"{visible}{'*' * max(len(local) - len(visible), 2)}@{domain}"


@dataclass(frozen=True)
class NotificationProductionSmokeResult:
    result: str
    log: EmailLog | None
    evidence: dict[str, object]


@dataclass
class NotificationProductionDeliveryCommandService:
    delivery_service: EmailDeliveryCommandService

    def execute_transactional_smoke(
        self,
        *,
        tenant_id: int | str | None,
        recipient_email: object,
        smoke_key: object = "production-smoke",
    ) -> NotificationProductionSmokeResult:
        normalized_tenant_id = _string(tenant_id, limit=40)
        normalized_email = _string(recipient_email, limit=254)
        normalized_smoke_key = _string(smoke_key, limit=80) or "production-smoke"
        if not normalized_tenant_id:
            return self._result("notification-smoke-tenant-required", None, recipient_email=normalized_email)
        if "@" not in normalized_email:
            return self._result("notification-smoke-recipient-invalid", None, recipient_email=normalized_email)

        readiness = get_notification_provider_readiness()
        if not readiness.can_attempt_real_delivery:
            return self._result(
                "notification-smoke-provider-blocked",
                None,
                recipient_email=normalized_email,
                extra={"provider_blockers": ",".join(readiness.blockers)},
            )

        email_hash = sha256(normalized_email.lower().encode("utf-8")).hexdigest()[:16]
        delivery_key = f"{normalized_tenant_id}:notification.production_smoke:{normalized_smoke_key}:email:system:{email_hash}"
        log, _created = EmailLog.objects.get_or_create(
            recipient_delivery_key=delivery_key,
            defaults={
                "tenant_id": normalized_tenant_id,
                "source_event": "notification.production_smoke",
                "intent_key": "system.notification.production_smoke",
                "audience": "system",
                "channel": "email",
                "entity_type": "notification_smoke",
                "entity_id": normalized_smoke_key,
                "idempotency_key": f"{normalized_tenant_id}:system.notification.production_smoke:notification_smoke:{normalized_smoke_key}:email",
                "recipient_type": "system",
                "recipient_id": email_hash,
                "recipient_email": normalized_email,
                "recipient_display_name": "Production smoke",
                "title": "Hubx notification smoke",
                "description": "Smoke transacional para validar o provider de notificações em produção.",
                "cta_label": "",
                "cta_target": "",
            },
        )
        if log.status != EmailLog.Status.PLANNED:
            return self._result("notification-smoke-already-processed", log, recipient_email=normalized_email)

        delivery = self.delivery_service.process_email_log(tenant_id=normalized_tenant_id, log_id=log.id)
        updated_log = delivery.log
        if updated_log and updated_log.status == EmailLog.Status.SENT:
            return self._result("notification-smoke-sent", updated_log, recipient_email=normalized_email)
        if updated_log and updated_log.status == EmailLog.Status.FAILED:
            return self._result(
                "notification-smoke-failed",
                updated_log,
                recipient_email=normalized_email,
                extra={"failure_classification": classify_notification_failure(updated_log.last_error)},
            )
        return self._result(delivery.result, updated_log, recipient_email=normalized_email)

    def _result(
        self,
        result: str,
        log: EmailLog | None,
        *,
        recipient_email: object,
        extra: dict[str, object] | None = None,
    ) -> NotificationProductionSmokeResult:
        evidence = {
            "result": result,
            "log_id": getattr(log, "id", None),
            "status": _string(getattr(log, "status", "")),
            "recipient": _mask_email(recipient_email),
            "captured_at": timezone.now().isoformat(),
        }
        if extra:
            evidence.update(extra)
        return NotificationProductionSmokeResult(result=result, log=log, evidence=evidence)


notification_production_delivery_commands = NotificationProductionDeliveryCommandService(
    delivery_service=EmailDeliveryCommandService(),
)
