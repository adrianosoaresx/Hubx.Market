from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count

from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class NotificationReadinessSnapshot:
    tenant_id: str
    total: int
    planned: int
    requested: int
    sent: int
    failed: int
    skipped: int

    @property
    def has_pending_delivery(self) -> bool:
        return self.planned > 0 or self.requested > 0

    @property
    def has_failures(self) -> bool:
        return self.failed > 0


def get_notification_readiness_snapshot(*, tenant_id: int | str) -> NotificationReadinessSnapshot:
    normalized_tenant_id = str(tenant_id or "").strip()
    if not normalized_tenant_id:
        return NotificationReadinessSnapshot(
            tenant_id="",
            total=0,
            planned=0,
            requested=0,
            sent=0,
            failed=0,
            skipped=0,
        )

    rows = (
        EmailLog.objects.filter(tenant_id=normalized_tenant_id)
        .values("status")
        .annotate(count=Count("id"))
    )
    counts = {str(row["status"]): int(row["count"]) for row in rows}
    return NotificationReadinessSnapshot(
        tenant_id=normalized_tenant_id,
        total=sum(counts.values()),
        planned=counts.get(EmailLog.Status.PLANNED, 0),
        requested=counts.get(EmailLog.Status.REQUESTED, 0),
        sent=counts.get(EmailLog.Status.SENT, 0),
        failed=counts.get(EmailLog.Status.FAILED, 0),
        skipped=counts.get(EmailLog.Status.SKIPPED, 0),
    )
