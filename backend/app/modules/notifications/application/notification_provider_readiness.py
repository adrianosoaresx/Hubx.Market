from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class NotificationProviderReadiness:
    dry_run: bool
    backend: str
    from_email: str
    can_attempt_real_delivery: bool
    blockers: tuple[str, ...]


def get_notification_provider_readiness() -> NotificationProviderReadiness:
    dry_run = bool(getattr(settings, "NOTIFICATIONS_EMAIL_DRY_RUN", True))
    backend = str(getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    from_email = str(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    blockers: list[str] = []

    if dry_run:
        blockers.append("dry-run-enabled")
    if not backend:
        blockers.append("email-backend-missing")
    if not from_email:
        blockers.append("default-from-email-missing")

    return NotificationProviderReadiness(
        dry_run=dry_run,
        backend=backend,
        from_email=from_email,
        can_attempt_real_delivery=not blockers,
        blockers=tuple(blockers),
    )
