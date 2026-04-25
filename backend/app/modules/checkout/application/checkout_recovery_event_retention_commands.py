from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.utils import timezone

from app.modules.checkout.models import CheckoutRecoveryEvent


@dataclass(frozen=True)
class CheckoutRecoveryEventPruneSummary:
    tenant_id: str
    candidates: int
    deleted: int
    dry_run: bool
    older_than_days: int
    limit: int


class CheckoutRecoveryEventRetentionRepository(Protocol):
    def prune_events(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutRecoveryEventPruneSummary:
        ...


class DjangoOrmCheckoutRecoveryEventRetentionRepository:
    def prune_events(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutRecoveryEventPruneSummary:
        normalized_tenant_id = str(tenant_id or "").strip()
        safe_days = max(180, int(older_than_days or 180))
        safe_limit = min(max(1, int(limit or 250)), 1000)
        cutoff = timezone.now() - timezone.timedelta(days=safe_days)
        queryset = CheckoutRecoveryEvent.objects.filter(
            tenant_id=normalized_tenant_id,
            created_at__lt=cutoff,
        ).order_by("created_at", "id")
        candidate_ids = list(queryset.values_list("id", flat=True)[:safe_limit])
        candidates = len(candidate_ids)
        deleted = 0
        if candidate_ids and not dry_run:
            deleted, _ = CheckoutRecoveryEvent.objects.filter(
                id__in=candidate_ids,
                tenant_id=normalized_tenant_id,
            ).delete()
        return CheckoutRecoveryEventPruneSummary(
            tenant_id=normalized_tenant_id,
            candidates=candidates,
            deleted=deleted,
            dry_run=dry_run,
            older_than_days=safe_days,
            limit=safe_limit,
        )


@dataclass
class CheckoutRecoveryEventRetentionCommandService:
    repository: CheckoutRecoveryEventRetentionRepository

    def prune_events(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutRecoveryEventPruneSummary:
        return self.repository.prune_events(
            tenant_id=tenant_id,
            older_than_days=older_than_days,
            limit=limit,
            dry_run=dry_run,
        )


checkout_recovery_event_retention_commands = CheckoutRecoveryEventRetentionCommandService(
    repository=DjangoOrmCheckoutRecoveryEventRetentionRepository(),
)
