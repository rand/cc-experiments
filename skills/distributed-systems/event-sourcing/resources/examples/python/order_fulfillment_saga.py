"""
Order Fulfillment Saga - Event Sourcing Example

Demonstrates saga pattern for coordinating long-running processes
across multiple aggregates/services in an event-sourced system.

Saga steps:
1. Order submitted
2. Reserve inventory
3. Process payment
4. Ship order
5. Complete order

Compensating actions if any step fails:
- Release reserved inventory
- Refund payment
- Cancel order

Features:
- State machine pattern
- Compensating transactions
- Idempotent handlers
- Persistent state
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class SagaStatus(Enum):
    """Saga status"""
    STARTED = "started"
    INVENTORY_RESERVING = "inventory_reserving"
    INVENTORY_RESERVED = "inventory_reserved"
    PAYMENT_PROCESSING = "payment_processing"
    PAYMENT_PROCESSED = "payment_processed"
    SHIPPING = "shipping"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"


@dataclass
class Event:
    """Event data structure"""
    event_id: str
    event_type: str
    aggregate_id: str
    data: Dict[str, Any]
    timestamp: datetime


@dataclass
class Command:
    """Command data structure"""
    command_id: str
    command_type: str
    aggregate_id: str
    data: Dict[str, Any]


class OrderFulfillmentSaga:
    """
    Order Fulfillment Saga

    Coordinates order fulfillment process across multiple services:
    - Order service
    - Inventory service
    - Payment service
    - Shipping service

    Maintains saga state and handles compensations on failure.
    """

    def __init__(self, saga_id: str, command_bus, event_store):
        self.saga_id = saga_id
        self.command_bus = command_bus
        self.event_store = event_store

        # Saga state
        self.order_id: Optional[str] = None
        self.customer_id: Optional[str] = None
        self.items: list = []
        self.total_amount: float = 0
        self.status = SagaStatus.STARTED

        # Track what's been done (for compensation)
        self.inventory_reserved = False
        self.payment_processed = False
        self.order_shipped = False

        # Store event IDs we've processed (idempotency)
        self.processed_events = set()

    def handle_event(self, event: Event):
        """
        Handle event and advance saga state

        Events are handled idempotently - processing the same event
        multiple times has the same effect as processing it once.
        """
        # Idempotency check
        if event.event_id in self.processed_events:
            print(f"Event {event.event_id} already processed, skipping")
            return

        # Route to handler
        if event.event_type == "OrderSubmitted":
            self._handle_order_submitted(event)

        elif event.event_type == "InventoryReserved":
            self._handle_inventory_reserved(event)

        elif event.event_type == "InventoryReservationFailed":
            self._handle_inventory_reservation_failed(event)

        elif event.event_type == "PaymentProcessed":
            self._handle_payment_processed(event)

        elif event.event_type == "PaymentFailed":
            self._handle_payment_failed(event)

        elif event.event_type == "OrderShipped":
            self._handle_order_shipped(event)

        elif event.event_type == "ShippingFailed":
            self._handle_shipping_failed(event)

        # Mark as processed
        self.processed_events.add(event.event_id)

        # Persist saga state
        self._save_state()

    def _handle_order_submitted(self, event: Event):
        """Step 1: Order submitted, start saga"""
        print(f"\n[Saga {self.saga_id}] Step 1: Order submitted")

        self.order_id = event.data['orderId']
        self.customer_id = event.data['customerId']
        self.items = event.data['items']
        self.total_amount = event.data['totalAmount']
        self.status = SagaStatus.INVENTORY_RESERVING

        print(f"  Order: {self.order_id}")
        print(f"  Customer: {self.customer_id}")
        print(f"  Items: {len(self.items)}")
        print(f"  Total: ${self.total_amount}")

        # Send command to reserve inventory
        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="ReserveInventory",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'items': self.items
            }
        )

        print(f"  → Sending ReserveInventory command")
        self.command_bus.send(command)

    def _handle_inventory_reserved(self, event: Event):
        """Step 2: Inventory reserved, process payment"""
        print(f"\n[Saga {self.saga_id}] Step 2: Inventory reserved")

        self.inventory_reserved = True
        self.status = SagaStatus.INVENTORY_RESERVED

        print(f"  Order: {event.data['orderId']}")
        print(f"  Reserved items: {len(event.data.get('items', []))}")

        # Send command to process payment
        self.status = SagaStatus.PAYMENT_PROCESSING

        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="ProcessPayment",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'amount': self.total_amount
            }
        )

        print(f"  → Sending ProcessPayment command")
        self.command_bus.send(command)

    def _handle_payment_processed(self, event: Event):
        """Step 3: Payment processed, ship order"""
        print(f"\n[Saga {self.saga_id}] Step 3: Payment processed")

        self.payment_processed = True
        self.status = SagaStatus.PAYMENT_PROCESSED

        print(f"  Order: {event.data['orderId']}")
        print(f"  Amount: ${event.data['amount']}")
        print(f"  Transaction: {event.data.get('transactionId')}")

        # Send command to ship order
        self.status = SagaStatus.SHIPPING

        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="ShipOrder",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'customerId': self.customer_id,
                'shippingAddress': event.data.get('shippingAddress', {})
            }
        )

        print(f"  → Sending ShipOrder command")
        self.command_bus.send(command)

    def _handle_order_shipped(self, event: Event):
        """Step 4: Order shipped, complete saga"""
        print(f"\n[Saga {self.saga_id}] Step 4: Order shipped")

        self.order_shipped = True
        self.status = SagaStatus.COMPLETED

        print(f"  Order: {event.data['orderId']}")
        print(f"  Tracking: {event.data.get('trackingNumber')}")
        print(f"  ✅ Saga completed successfully!")

    def _handle_inventory_reservation_failed(self, event: Event):
        """Compensation: Inventory reservation failed"""
        print(f"\n[Saga {self.saga_id}] ❌ Inventory reservation failed")
        print(f"  Reason: {event.data.get('reason')}")

        self.status = SagaStatus.COMPENSATING

        # Cancel order (no compensation needed, nothing done yet)
        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="CancelOrder",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'reason': 'Insufficient inventory'
            }
        )

        print(f"  → Sending CancelOrder command")
        self.command_bus.send(command)

        self.status = SagaStatus.FAILED

    def _handle_payment_failed(self, event: Event):
        """Compensation: Payment failed, release inventory"""
        print(f"\n[Saga {self.saga_id}] ❌ Payment failed")
        print(f"  Reason: {event.data.get('reason')}")

        self.status = SagaStatus.COMPENSATING

        # Compensate: Release reserved inventory
        if self.inventory_reserved:
            command = Command(
                command_id=str(uuid.uuid4()),
                command_type="ReleaseInventory",
                aggregate_id=self.order_id,
                data={
                    'orderId': self.order_id,
                    'items': self.items
                }
            )

            print(f"  → Compensating: Releasing inventory")
            self.command_bus.send(command)

        # Cancel order
        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="CancelOrder",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'reason': 'Payment failed'
            }
        )

        print(f"  → Sending CancelOrder command")
        self.command_bus.send(command)

        self.status = SagaStatus.FAILED

    def _handle_shipping_failed(self, event: Event):
        """Compensation: Shipping failed, refund payment and release inventory"""
        print(f"\n[Saga {self.saga_id}] ❌ Shipping failed")
        print(f"  Reason: {event.data.get('reason')}")

        self.status = SagaStatus.COMPENSATING

        # Compensate: Refund payment
        if self.payment_processed:
            command = Command(
                command_id=str(uuid.uuid4()),
                command_type="RefundPayment",
                aggregate_id=self.order_id,
                data={
                    'orderId': self.order_id,
                    'amount': self.total_amount
                }
            )

            print(f"  → Compensating: Refunding payment")
            self.command_bus.send(command)

        # Compensate: Release inventory
        if self.inventory_reserved:
            command = Command(
                command_id=str(uuid.uuid4()),
                command_type="ReleaseInventory",
                aggregate_id=self.order_id,
                data={
                    'orderId': self.order_id,
                    'items': self.items
                }
            )

            print(f"  → Compensating: Releasing inventory")
            self.command_bus.send(command)

        # Cancel order
        command = Command(
            command_id=str(uuid.uuid4()),
            command_type="CancelOrder",
            aggregate_id=self.order_id,
            data={
                'orderId': self.order_id,
                'reason': 'Shipping failed'
            }
        )

        print(f"  → Sending CancelOrder command")
        self.command_bus.send(command)

        self.status = SagaStatus.FAILED

    def _save_state(self):
        """Persist saga state to database"""
        state = {
            'sagaId': self.saga_id,
            'orderId': self.order_id,
            'customerId': self.customer_id,
            'items': self.items,
            'totalAmount': self.total_amount,
            'status': self.status.value,
            'inventoryReserved': self.inventory_reserved,
            'paymentProcessed': self.payment_processed,
            'orderShipped': self.order_shipped,
            'processedEvents': list(self.processed_events)
        }

        # In production: save to database
        print(f"  💾 Saving saga state: {self.status.value}")

    def get_state(self) -> Dict[str, Any]:
        """Get current saga state"""
        return {
            'sagaId': self.saga_id,
            'orderId': self.order_id,
            'status': self.status.value,
            'inventoryReserved': self.inventory_reserved,
            'paymentProcessed': self.payment_processed,
            'orderShipped': self.order_shipped
        }


# Mock command bus for demo
class MockCommandBus:
    """Mock command bus for demonstration"""

    def send(self, command: Command):
        """Send command (in production: publish to queue/bus)"""
        print(f"     📤 Command sent: {command.command_type} ({command.command_id})")


# Usage example
if __name__ == '__main__':
    # Create saga
    command_bus = MockCommandBus()
    saga = OrderFulfillmentSaga(
        saga_id='saga-123',
        command_bus=command_bus,
        event_store=None  # Mock
    )

    print("="*80)
    print("Order Fulfillment Saga - Happy Path")
    print("="*80)

    # Simulate events (happy path)
    events = [
        Event(
            event_id=str(uuid.uuid4()),
            event_type='OrderSubmitted',
            aggregate_id='order-123',
            data={
                'orderId': 'order-123',
                'customerId': 'customer-456',
                'items': [
                    {'productId': 'prod-1', 'quantity': 2, 'price': 19.99},
                    {'productId': 'prod-2', 'quantity': 1, 'price': 29.99}
                ],
                'totalAmount': 69.97
            },
            timestamp=datetime.now()
        ),
        Event(
            event_id=str(uuid.uuid4()),
            event_type='InventoryReserved',
            aggregate_id='order-123',
            data={
                'orderId': 'order-123',
                'items': [
                    {'productId': 'prod-1', 'quantity': 2},
                    {'productId': 'prod-2', 'quantity': 1}
                ]
            },
            timestamp=datetime.now()
        ),
        Event(
            event_id=str(uuid.uuid4()),
            event_type='PaymentProcessed',
            aggregate_id='order-123',
            data={
                'orderId': 'order-123',
                'amount': 69.97,
                'transactionId': 'txn-789'
            },
            timestamp=datetime.now()
        ),
        Event(
            event_id=str(uuid.uuid4()),
            event_type='OrderShipped',
            aggregate_id='order-123',
            data={
                'orderId': 'order-123',
                'trackingNumber': 'TRACK-123456'
            },
            timestamp=datetime.now()
        )
    ]

    # Process events
    for event in events:
        saga.handle_event(event)

    print("\n" + "="*80)
    print("Final State:")
    print(json.dumps(saga.get_state(), indent=2))
    print("="*80)

    # Example: Compensation path (payment failure)
    print("\n\n" + "="*80)
    print("Order Fulfillment Saga - Payment Failure (Compensation)")
    print("="*80)

    saga2 = OrderFulfillmentSaga(
        saga_id='saga-456',
        command_bus=command_bus,
        event_store=None
    )

    failure_events = [
        Event(
            event_id=str(uuid.uuid4()),
            event_type='OrderSubmitted',
            aggregate_id='order-456',
            data={
                'orderId': 'order-456',
                'customerId': 'customer-789',
                'items': [{'productId': 'prod-3', 'quantity': 1, 'price': 99.99}],
                'totalAmount': 99.99
            },
            timestamp=datetime.now()
        ),
        Event(
            event_id=str(uuid.uuid4()),
            event_type='InventoryReserved',
            aggregate_id='order-456',
            data={
                'orderId': 'order-456',
                'items': [{'productId': 'prod-3', 'quantity': 1}]
            },
            timestamp=datetime.now()
        ),
        Event(
            event_id=str(uuid.uuid4()),
            event_type='PaymentFailed',
            aggregate_id='order-456',
            data={
                'orderId': 'order-456',
                'reason': 'Insufficient funds'
            },
            timestamp=datetime.now()
        )
    ]

    for event in failure_events:
        saga2.handle_event(event)

    print("\n" + "="*80)
    print("Final State (After Compensation):")
    print(json.dumps(saga2.get_state(), indent=2))
    print("="*80)
