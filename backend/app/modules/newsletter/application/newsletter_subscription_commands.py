from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone


DEFAULT_CONSENT_LABEL = "Aceito receber novidades e comunicações desta loja."


def normalize_email(value: object) -> str:
    return str(value or "").strip().lower()


def _string(value: object, *, limit: int | None = None) -> str:
    text = str(value or "").strip()
    if limit is not None:
        return text[:limit]
    return text


def _valid_email(email: str) -> bool:
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


class NewsletterSubscriptionRepository(Protocol):
    def subscribe(
        self,
        *,
        tenant_id: int | str | None,
        email: str,
        name: str = "",
        source: str = "",
        consent_label: str = DEFAULT_CONSENT_LABEL,
    ) -> dict[str, object]:
        ...

    def unsubscribe(self, *, tenant_id: int | str | None, email: str) -> dict[str, object]:
        ...


class DjangoOrmNewsletterSubscriptionRepository:
    def __init__(self) -> None:
        try:
            from app.modules.newsletter.models import NewsletterSubscriber
            from app.modules.tenants.models import Tenant
        except Exception:
            self.subscriber_model = None
            self.tenant_model = None
            return
        self.subscriber_model = NewsletterSubscriber
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {self.subscriber_model._meta.db_table, self.tenant_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def subscribe(
        self,
        *,
        tenant_id: int | str | None,
        email: str,
        name: str = "",
        source: str = "",
        consent_label: str = DEFAULT_CONSENT_LABEL,
    ) -> dict[str, object]:
        if not tenant_id or not self.is_ready():
            return {"result": "newsletter-tenant-required", "errors": {"__all__": "Tenant obrigatório para inscrição."}}
        if not _valid_email(email):
            return {"result": "newsletter-invalid-email", "errors": {"email": "Informe um e-mail válido."}}
        tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
        if tenant is None:
            return {"result": "newsletter-tenant-required", "errors": {"__all__": "Tenant obrigatório para inscrição."}}

        now = timezone.now()
        subscriber, created = self.subscriber_model._default_manager.get_or_create(
            tenant=tenant,
            email=email,
            defaults={
                "name": _string(name, limit=120),
                "status": self.subscriber_model.Status.SUBSCRIBED,
                "source": _string(source, limit=80),
                "consent_label": _string(consent_label, limit=180),
                "consented_at": now,
            },
        )
        if created:
            return {"result": "newsletter-subscribed", "subscriber": {"id": subscriber.id, "email": subscriber.email}}

        subscriber.name = _string(name, limit=120) or subscriber.name
        subscriber.status = self.subscriber_model.Status.SUBSCRIBED
        subscriber.source = _string(source, limit=80) or subscriber.source
        subscriber.consent_label = _string(consent_label, limit=180) or subscriber.consent_label
        subscriber.consented_at = now
        subscriber.unsubscribed_at = None
        subscriber.save(
            update_fields=[
                "name",
                "status",
                "source",
                "consent_label",
                "consented_at",
                "unsubscribed_at",
                "updated_at",
            ]
        )
        return {"result": "newsletter-resubscribed", "subscriber": {"id": subscriber.id, "email": subscriber.email}}

    def unsubscribe(self, *, tenant_id: int | str | None, email: str) -> dict[str, object]:
        if not tenant_id or not self.is_ready():
            return {"result": "newsletter-tenant-required", "errors": {"__all__": "Tenant obrigatório para descadastro."}}
        if not _valid_email(email):
            return {"result": "newsletter-invalid-email", "errors": {"email": "Informe um e-mail válido."}}
        subscriber = self.subscriber_model._default_manager.filter(tenant_id=tenant_id, email=email).first()
        if subscriber is None:
            return {"result": "newsletter-not-found", "errors": {"email": "Inscrição não encontrada para este tenant."}}
        subscriber.status = self.subscriber_model.Status.UNSUBSCRIBED
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=["status", "unsubscribed_at", "updated_at"])
        return {"result": "newsletter-unsubscribed", "subscriber": {"id": subscriber.id, "email": subscriber.email}}


@dataclass
class NewsletterSubscriptionCommandService:
    repository: NewsletterSubscriptionRepository

    def subscribe(
        self,
        *,
        tenant_id: int | str | None,
        email: object,
        name: object = "",
        source: object = "",
        consent_label: object = DEFAULT_CONSENT_LABEL,
    ) -> dict[str, object]:
        return self.repository.subscribe(
            tenant_id=tenant_id,
            email=normalize_email(email),
            name=_string(name),
            source=_string(source),
            consent_label=_string(consent_label) or DEFAULT_CONSENT_LABEL,
        )

    def unsubscribe(self, *, tenant_id: int | str | None, email: object) -> dict[str, object]:
        return self.repository.unsubscribe(tenant_id=tenant_id, email=normalize_email(email))


newsletter_subscription_commands = NewsletterSubscriptionCommandService(
    repository=DjangoOrmNewsletterSubscriptionRepository(),
)
