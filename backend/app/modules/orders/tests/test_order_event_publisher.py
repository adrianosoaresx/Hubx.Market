from dataclasses import dataclass, field

from django.test import SimpleTestCase

from app.modules.orders.application.order_event_publisher import OrderEventPublisher


@dataclass
class StubOrderEventSubscriber:
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def record_customer_order_event_email_logs(self, *, tenant_id, source_event, order_number):
        self.calls.append(("customer", str(tenant_id), f"{source_event}:{order_number}"))
        return [object()]

    def record_owner_order_event_email_logs(self, *, tenant_id, source_event, order_number):
        self.calls.append(("owner", str(tenant_id), f"{source_event}:{order_number}"))
        return [object(), object()]


class OrderEventPublisherTests(SimpleTestCase):
    def test_publish_order_created_delegates_to_customer_and_owner_subscribers(self):
        subscriber = StubOrderEventSubscriber()
        publisher = OrderEventPublisher(subscriber=subscriber)

        count = publisher.publish_order_created(tenant_id=42, order_number="1001")

        self.assertEqual(count, 3)
        self.assertEqual(
            subscriber.calls,
            [
                ("customer", "42", "order.created:1001"),
                ("owner", "42", "order.created:1001"),
            ],
        )
