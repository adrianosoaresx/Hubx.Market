from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.utils import timezone

from app.modules.checkout.models import CheckoutSession


@dataclass(frozen=True)
class CheckoutSessionExpirationSummary:
    tenant_id: str
    candidates: int
    expired: int
    dry_run: bool
    older_than_hours: int
    limit: int


@dataclass(frozen=True)
class CheckoutSessionPruneSummary:
    tenant_id: str
    candidates: int
    deleted: int
    dry_run: bool
    older_than_days: int
    limit: int


class CheckoutSessionRetentionRepository(Protocol):
    def expire_stale_open_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_hours: int = 24,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionExpirationSummary:
        ...

    def prune_expired_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionPruneSummary:
        ...


class DjangoOrmCheckoutSessionRetentionRepository:
    def expire_stale_open_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_hours: int = 24,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionExpirationSummary:
        normalized_tenant_id = str(tenant_id or "").strip()
        safe_hours = max(6, int(older_than_hours or 24))
        safe_limit = min(max(1, int(limit or 250)), 1000)
        now = timezone.now()
        stale_cutoff = now - timezone.timedelta(hours=safe_hours)
        queryset = CheckoutSession.objects.filter(
            tenant_id=normalized_tenant_id,
            status=CheckoutSession.Status.OPEN,
        ).filter(
            expires_at__lte=now,
        ) | CheckoutSession.objects.filter(
            tenant_id=normalized_tenant_id,
            status=CheckoutSession.Status.OPEN,
            updated_at__lte=stale_cutoff,
        )
        queryset = queryset.order_by("updated_at", "id")
        candidate_ids = list(queryset.values_list("id", flat=True)[:safe_limit])
        candidates = len(candidate_ids)
        expired = 0
        if candidate_ids and not dry_run:
            expired = CheckoutSession.objects.filter(id__in=candidate_ids, status=CheckoutSession.Status.OPEN).update(
                status=CheckoutSession.Status.EXPIRED,
                updated_at=now,
            )
        return CheckoutSessionExpirationSummary(
            tenant_id=normalized_tenant_id,
            candidates=candidates,
            expired=expired,
            dry_run=dry_run,
            older_than_hours=safe_hours,
            limit=safe_limit,
        )

    def prune_expired_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionPruneSummary:
        normalized_tenant_id = str(tenant_id or "").strip()
        safe_days = max(180, int(older_than_days or 180))
        safe_limit = min(max(1, int(limit or 250)), 1000)
        cutoff = timezone.now() - timezone.timedelta(days=safe_days)
        queryset = CheckoutSession.objects.filter(
            tenant_id=normalized_tenant_id,
            status=CheckoutSession.Status.EXPIRED,
            updated_at__lt=cutoff,
        ).order_by("updated_at", "id")
        candidate_ids = list(queryset.values_list("id", flat=True)[:safe_limit])
        candidates = len(candidate_ids)
        deleted = 0
        if candidate_ids and not dry_run:
            deleted, _ = CheckoutSession.objects.filter(
                id__in=candidate_ids,
                tenant_id=normalized_tenant_id,
                status=CheckoutSession.Status.EXPIRED,
            ).delete()
        return CheckoutSessionPruneSummary(
            tenant_id=normalized_tenant_id,
            candidates=candidates,
            deleted=deleted,
            dry_run=dry_run,
            older_than_days=safe_days,
            limit=safe_limit,
        )


@dataclass
class CheckoutSessionRetentionCommandService:
    repository: CheckoutSessionRetentionRepository

    def expire_stale_open_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_hours: int = 24,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionExpirationSummary:
        return self.repository.expire_stale_open_sessions(
            tenant_id=tenant_id,
            older_than_hours=older_than_hours,
            limit=limit,
            dry_run=dry_run,
        )

    def prune_expired_sessions(
        self,
        *,
        tenant_id: int | str,
        older_than_days: int = 180,
        limit: int = 250,
        dry_run: bool = True,
    ) -> CheckoutSessionPruneSummary:
        return self.repository.prune_expired_sessions(
            tenant_id=tenant_id,
            older_than_days=older_than_days,
            limit=limit,
            dry_run=dry_run,
        )


checkout_session_retention_commands = CheckoutSessionRetentionCommandService(
    repository=DjangoOrmCheckoutSessionRetentionRepository(),
)
