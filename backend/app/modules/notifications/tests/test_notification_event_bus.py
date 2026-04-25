from django.test import SimpleTestCase

from app.modules.notifications.application.notification_event_bus import (
    NotificationEvent,
    NotificationEventPublisher,
)


class NotificationEventBusTests(SimpleTestCase):
    def test_publishes_event_to_registered_handlers(self):
        publisher = NotificationEventPublisher()
        received = []

        publisher.subscribe(event_name="order.created", handler=received.append)
        count = publisher.publish(
            event=NotificationEvent(
                name="order.created",
                tenant_id="42",
                entity_type="order",
                entity_id="99",
                metadata={"order_number": "1001"},
            )
        )

        self.assertEqual(count, 1)
        self.assertEqual(received[0].metadata["order_number"], "1001")

    def test_publish_without_handlers_is_noop(self):
        publisher = NotificationEventPublisher()

        count = publisher.publish(
            event=NotificationEvent(
                name="shipment.sent",
                tenant_id="42",
                entity_type="shipment",
                entity_id="9",
                metadata={},
            )
        )

        self.assertEqual(count, 0)
