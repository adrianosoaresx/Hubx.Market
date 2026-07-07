from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone


STATUS_OPTIONS = [
    {"value": "", "label": "Todos"},
    {"value": "subscribed", "label": "Inscritos"},
    {"value": "unsubscribed", "label": "Descadastrados"},
]


def _string(value: object) -> str:
    return str(value or "").strip()


def _format_datetime(value: object) -> str:
    if not value:
        return "-"
    try:
        return timezone.localtime(value).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(value)


class AdminNewsletterReadRepository(Protocol):
    def list_subscribers(self, *, tenant_id: int | str | None) -> list[object]:
        ...

    def list_campaigns(self, *, tenant_id: int | str | None) -> list[object]:
        ...


class DjangoOrmAdminNewsletterRepository:
    def __init__(self) -> None:
        try:
            from app.modules.newsletter.models import NewsletterCampaign, NewsletterSubscriber
        except Exception:
            self.campaign_model = None
            self.subscriber_model = None
            return
        self.campaign_model = NewsletterCampaign
        self.subscriber_model = NewsletterSubscriber

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.subscriber_model._meta.db_table,
                self.campaign_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                return table_names.issubset(set(connection.introspection.table_names(cursor)))
        except Exception:
            return False

    def list_subscribers(self, *, tenant_id: int | str | None) -> list[object]:
        if not tenant_id or not self.is_ready():
            return []
        return list(
            self.subscriber_model._default_manager.filter(tenant_id=tenant_id).order_by("-updated_at", "email")[:200]
        )

    def list_campaigns(self, *, tenant_id: int | str | None) -> list[object]:
        if not tenant_id or not self.is_ready() or self.campaign_model is None:
            return []
        return list(
            self.campaign_model._default_manager.filter(tenant_id=tenant_id).order_by("-created_at", "-id")[:100]
        )


@dataclass
class AdminNewsletterQueryService:
    repository: AdminNewsletterReadRepository

    def list_subscribers(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        subscribers = self.repository.list_subscribers(tenant_id=tenant_id)
        return [
            {
                "id": subscriber.id,
                "email": subscriber.email,
                "name": _string(subscriber.name) or "Sem nome",
                "status": subscriber.status,
                "status_label": subscriber.get_status_display(),
                "source": _string(subscriber.source) or "storefront",
                "consented_at": _format_datetime(subscriber.consented_at),
                "updated_at": _format_datetime(subscriber.updated_at),
            }
            for subscriber in subscribers
        ]

    def list_campaigns(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        campaigns = self.repository.list_campaigns(tenant_id=tenant_id)
        return [
            {
                "id": campaign.id,
                "title": campaign.title,
                "subject": campaign.subject,
                "status": campaign.status,
                "status_label": campaign.get_status_display(),
                "recipient_count": campaign.recipient_count,
                "recipient_label": f"{campaign.recipient_count} destinatário(s)",
                "created_at": _format_datetime(campaign.created_at),
                "sent_at": _format_datetime(campaign.sent_at),
                "can_send": campaign.status != campaign.Status.SENT,
            }
            for campaign in campaigns
        ]


admin_newsletter_queries = AdminNewsletterQueryService(repository=DjangoOrmAdminNewsletterRepository())
