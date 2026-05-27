from __future__ import annotations

from dataclasses import dataclass

from app.modules.newsletter.models import NewsletterSubscriber


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class NewsletterSegmentQueryService:
    def list_subscribed_segment(self, *, tenant_id: int | str | None, limit: int = 200) -> list[dict[str, object]]:
        if not tenant_id:
            return []
        safe_limit = max(1, min(int(limit or 200), 500))
        subscribers = NewsletterSubscriber.objects.filter(
            tenant_id=tenant_id,
            status=NewsletterSubscriber.Status.SUBSCRIBED,
        ).order_by("-consented_at", "-updated_at", "email")[:safe_limit]
        return [
            {
                "id": subscriber.id,
                "tenant_id": subscriber.tenant_id,
                "email": subscriber.email,
                "name": _string(subscriber.name),
                "source": _string(subscriber.source) or "storefront",
                "consent_label": _string(subscriber.consent_label),
                "consented_at": subscriber.consented_at,
            }
            for subscriber in subscribers
        ]


newsletter_segment_queries = NewsletterSegmentQueryService()
