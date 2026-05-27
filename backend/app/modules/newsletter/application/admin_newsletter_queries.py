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


class DjangoOrmAdminNewsletterRepository:
    def __init__(self) -> None:
        try:
            from app.modules.newsletter.models import NewsletterSubscriber
        except Exception:
            self.subscriber_model = None
            return
        self.subscriber_model = NewsletterSubscriber

    def is_ready(self) -> bool:
        try:
            table_name = self.subscriber_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                return table_name in set(connection.introspection.table_names(cursor))
        except Exception:
            return False

    def list_subscribers(self, *, tenant_id: int | str | None) -> list[object]:
        if not tenant_id or not self.is_ready():
            return []
        return list(self.subscriber_model._default_manager.filter(tenant_id=tenant_id).order_by("-updated_at", "email")[:200])


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


admin_newsletter_queries = AdminNewsletterQueryService(repository=DjangoOrmAdminNewsletterRepository())
