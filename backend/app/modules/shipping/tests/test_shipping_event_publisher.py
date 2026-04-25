from dataclasses import dataclass, field

from django.test import SimpleTestCase

from app.modules.shipping.application.shipping_event_publisher import ShippingEventPublisher


@dataclass
class StubShippingEventSubscriber:
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def record_customer_order_event_email_logs(self, *, tenant_id, source_event, order_number):
        self.calls.append(("customer", str(tenant_id), f"{source_event}:{order_number}"))
        return [object()]

    def record_owner_order_event_email_logs(self, *, tenant_id, source_event, order_number):
        self.calls.append(("owner", str(tenant_id), f"{source_event}:{order_number}"))
        return []


class ShippingEventPublisherTests(SimpleTestCase):
    def test_publish_shipment_sent_delegates_to_subscribers(self):
        subscriber = StubShippingEventSubscriber()
        publisher = ShippingEventPublisher(subscriber=subscriber)

        count = publisher.publish_shipment_sent(tenant_id=42, order_number="1001")

        self.assertEqual(count, 1)
        self.assertEqual(
            subscriber.calls,
            [
                ("customer", "42", "shipment.sent:1001"),
                ("owner", "42", "shipment.sent:1001"),
            ],
        )

    def test_publish_shipment_delivered_delegates_to_subscribers(self):
        subscriber = StubShippingEventSubscriber()
        publisher = ShippingEventPublisher(subscriber=subscriber)

        count = publisher.publish_shipment_delivered(tenant_id=42, order_number="1001")

        self.assertEqual(count, 1)
        self.assertEqual(
            subscriber.calls,
            [
                ("customer", "42", "shipment.delivered:1001"),
                ("owner", "42", "shipment.delivered:1001"),
            ],
        )
