from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection, transaction
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.notifications.application.notification_dispatch_envelopes import NotificationDispatchEnvelope
from app.modules.notifications.application.notification_log_writer import record_email_log_from_envelope


def _string(value: object, *, limit: int | None = None) -> str:
    text = str(value or "").strip()
    return text[:limit] if limit is not None else text


class NewsletterCampaignRepository(Protocol):
    def create_campaign(
        self,
        *,
        tenant_id: int | str | None,
        title: object,
        subject: object,
        body_text: object,
        actor_label: object = "",
    ) -> dict[str, object]:
        ...

    def send_campaign(
        self,
        *,
        tenant_id: int | str | None,
        campaign_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmNewsletterCampaignRepository:
    def __init__(self) -> None:
        try:
            from app.modules.newsletter.models import NewsletterCampaign, NewsletterSubscriber
            from app.modules.notifications.models import EmailLog
            from app.modules.tenants.models import Tenant
        except Exception:
            self.campaign_model = None
            self.subscriber_model = None
            self.email_log_model = None
            self.tenant_model = None
            return
        self.campaign_model = NewsletterCampaign
        self.subscriber_model = NewsletterSubscriber
        self.email_log_model = EmailLog
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.campaign_model._meta.db_table,
                self.subscriber_model._meta.db_table,
                self.email_log_model._meta.db_table,
                self.tenant_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def create_campaign(
        self,
        *,
        tenant_id: int | str | None,
        title: object,
        subject: object,
        body_text: object,
        actor_label: object = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "newsletter-campaign-unavailable", "errors": {"__all__": "Campanhas indisponíveis."}}
        tenant = self._tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "newsletter-campaign-tenant-required", "errors": {"__all__": "Tenant obrigatório."}}
        payload = {
            "title": _string(title, limit=150),
            "subject": _string(subject, limit=180),
            "body_text": _string(body_text, limit=8000),
        }
        errors = self._validate_payload(payload)
        if errors:
            return {"result": "newsletter-campaign-invalid", "errors": errors}

        campaign = self.campaign_model._default_manager.create(
            tenant=tenant,
            title=payload["title"],
            subject=payload["subject"],
            body_text=payload["body_text"],
            created_by_label=_string(actor_label, limit=180),
        )
        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="newsletter",
            action="newsletter.campaign_created",
            entity_type="NewsletterCampaign",
            entity_id=str(campaign.id),
            actor_label=_string(actor_label, limit=180),
            summary=f"Campanha {campaign.title} criada",
            metadata={"campaign_id": campaign.id, "status": campaign.status},
        )
        return {
            "result": "newsletter-campaign-created",
            "campaign": {"id": campaign.id, "status": campaign.status},
        }

    def send_campaign(
        self,
        *,
        tenant_id: int | str | None,
        campaign_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "newsletter-campaign-unavailable", "errors": {"__all__": "Campanhas indisponíveis."}}
        tenant = self._tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "newsletter-campaign-tenant-required", "errors": {"__all__": "Tenant obrigatório."}}
        campaign = self.campaign_model._default_manager.filter(pk=campaign_id, tenant=tenant).first()
        if campaign is None:
            return {"result": "newsletter-campaign-not-found", "errors": {"__all__": "Campanha não encontrada."}}
        if campaign.status == self.campaign_model.Status.SENT:
            return {
                "result": "newsletter-campaign-already-sent",
                "campaign": {"id": campaign.id, "status": campaign.status},
            }

        subscribers = list(
            self.subscriber_model._default_manager.filter(
                tenant=tenant,
                status=self.subscriber_model.Status.SUBSCRIBED,
            ).order_by("id")
        )
        if not subscribers:
            return {
                "result": "newsletter-campaign-no-recipients",
                "errors": {"__all__": "Não há inscritos ativos para enviar esta campanha."},
            }

        created_logs = 0
        with transaction.atomic():
            for subscriber in subscribers:
                write_result = record_email_log_from_envelope(
                    envelope=self._build_envelope(tenant_id=tenant.id, campaign=campaign, subscriber=subscriber)
                )
                if write_result.created:
                    created_logs += 1
            campaign.status = self.campaign_model.Status.SENT
            campaign.recipient_count = len(subscribers)
            campaign.sent_by_label = _string(actor_label, limit=180)
            campaign.sent_at = timezone.now()
            campaign.last_error = ""
            campaign.save(
                update_fields=[
                    "status",
                    "recipient_count",
                    "sent_by_label",
                    "sent_at",
                    "last_error",
                    "updated_at",
                ]
            )

        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="newsletter",
            action="newsletter.campaign_sent",
            entity_type="NewsletterCampaign",
            entity_id=str(campaign.id),
            actor_label=_string(actor_label, limit=180),
            summary=f"Campanha {campaign.title} enviada para outbox",
            metadata={"campaign_id": campaign.id, "recipient_count": len(subscribers), "created_logs": created_logs},
        )
        return {
            "result": "newsletter-campaign-sent",
            "campaign": {
                "id": campaign.id,
                "status": campaign.status,
                "recipient_count": len(subscribers),
                "created_logs": created_logs,
            },
        }

    def _tenant(self, *, tenant_id: int | str | None):
        if not tenant_id:
            return None
        return self.tenant_model._default_manager.filter(pk=tenant_id).first()

    def _validate_payload(self, payload: dict[str, str]) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not payload["title"]:
            errors["title"] = "Informe o nome interno da campanha."
        if not payload["subject"]:
            errors["subject"] = "Informe o assunto do e-mail."
        if not payload["body_text"]:
            errors["body_text"] = "Informe o conteúdo da campanha."
        return errors

    def _build_envelope(self, *, tenant_id: int | str, campaign, subscriber) -> NotificationDispatchEnvelope:
        idempotency_key = f"{tenant_id}:newsletter.campaign:{campaign.id}:email"
        return NotificationDispatchEnvelope(
            tenant_id=str(tenant_id),
            source_event="newsletter.campaign.sent",
            entity_type="NewsletterCampaign",
            entity_id=str(campaign.id),
            audience="customer",
            channel="email",
            intent_key="newsletter.campaign",
            idempotency_key=idempotency_key,
            recipient_delivery_key=f"{idempotency_key}:newsletter_subscriber:{subscriber.id}",
            recipient_type="newsletter_subscriber",
            recipient_id=str(subscriber.id),
            recipient_email=subscriber.email,
            recipient_display_name=subscriber.name,
            title=campaign.subject,
            description=campaign.body_text,
            cta_label="",
            cta_target="",
        )


@dataclass
class NewsletterCampaignCommandService:
    repository: NewsletterCampaignRepository

    def create_campaign(
        self,
        *,
        tenant_id: int | str | None,
        title: object,
        subject: object,
        body_text: object,
        actor_label: object = "",
    ) -> dict[str, object]:
        return self.repository.create_campaign(
            tenant_id=tenant_id,
            title=title,
            subject=subject,
            body_text=body_text,
            actor_label=actor_label,
        )

    def send_campaign(
        self,
        *,
        tenant_id: int | str | None,
        campaign_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        return self.repository.send_campaign(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            actor_label=actor_label,
        )


newsletter_campaign_commands = NewsletterCampaignCommandService(
    repository=DjangoOrmNewsletterCampaignRepository(),
)
