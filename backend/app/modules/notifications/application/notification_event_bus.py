from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class NotificationEvent:
    name: str
    tenant_id: str
    entity_type: str
    entity_id: str
    metadata: dict[str, str]


NotificationEventHandler = Callable[[NotificationEvent], None]


class NotificationEventPublisher:
    def __init__(self) -> None:
        self._handlers: dict[str, list[NotificationEventHandler]] = {}

    def subscribe(self, *, event_name: str, handler: NotificationEventHandler) -> None:
        normalized_name = str(event_name or "").strip()
        if not normalized_name:
            return
        self._handlers.setdefault(normalized_name, []).append(handler)

    def publish(self, *, event: NotificationEvent) -> int:
        normalized_name = str(event.name or "").strip()
        handlers = list(self._handlers.get(normalized_name, []))
        for handler in handlers:
            handler(event)
        return len(handlers)


notification_event_publisher = NotificationEventPublisher()
