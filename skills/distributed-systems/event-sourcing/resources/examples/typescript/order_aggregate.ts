/**
 * Order Aggregate - Event Sourcing Example (TypeScript)
 *
 * Complete TypeScript implementation of an event-sourced order aggregate
 * demonstrating type safety, command handling, and event application.
 *
 * Features:
 * - Strong typing with TypeScript
 * - Command pattern
 * - Event sourcing
 * - Invariant enforcement
 * - Immutable events
 */

import { v4 as uuid } from 'uuid';

// Event types
interface BaseEvent {
  eventId: string;
  eventType: string;
  aggregateId: string;
  aggregateType: string;
  version: number;
  data: Record<string, any>;
  metadata: Record<string, any>;
  timestamp: Date;
}

interface OrderCreatedEvent extends BaseEvent {
  eventType: 'OrderCreated';
  data: {
    orderId: string;
    customerId: string;
  };
}

interface ItemAddedEvent extends BaseEvent {
  eventType: 'ItemAdded';
  data: {
    orderId: string;
    productId: string;
    quantity: number;
    price: number;
  };
}

interface ItemRemovedEvent extends BaseEvent {
  eventType: 'ItemRemoved';
  data: {
    orderId: string;
    productId: string;
  };
}

interface OrderSubmittedEvent extends BaseEvent {
  eventType: 'OrderSubmitted';
  data: {
    orderId: string;
    totalAmount: number;
    submittedAt: string;
  };
}

interface OrderCancelledEvent extends BaseEvent {
  eventType: 'OrderCancelled';
  data: {
    orderId: string;
    reason: string;
  };
}

type OrderEvent =
  | OrderCreatedEvent
  | ItemAddedEvent
  | ItemRemovedEvent
  | OrderSubmittedEvent
  | OrderCancelledEvent;

// Domain types
enum OrderStatus {
  Pending = 'pending',
  Submitted = 'submitted',
  Cancelled = 'cancelled',
}

interface OrderItem {
  productId: string;
  quantity: number;
  price: number;
}

// Errors
class OrderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'OrderError';
  }
}

class OrderAlreadySubmittedError extends OrderError {
  constructor() {
    super('Order has already been submitted');
    this.name = 'OrderAlreadySubmittedError';
  }
}

class EmptyOrderError extends OrderError {
  constructor() {
    super('Cannot submit empty order');
    this.name = 'EmptyOrderError';
  }
}

// Aggregate
export class Order {
  private orderId: string;
  private customerId?: string;
  private items: Map<string, OrderItem> = new Map();
  private status: OrderStatus = OrderStatus.Pending;
  private version: number = 0;
  private uncommittedEvents: OrderEvent[] = [];

  constructor(orderId: string) {
    this.orderId = orderId;
  }

  // Factory method
  static create(orderId: string, customerId: string, userId: string): Order {
    const order = new Order(orderId);

    const event: OrderCreatedEvent = {
      eventId: uuid(),
      eventType: 'OrderCreated',
      aggregateId: orderId,
      aggregateType: 'Order',
      version: 1,
      data: {
        orderId,
        customerId,
      },
      metadata: {
        userId,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date(),
    };

    order.applyEvent(event);
    order.uncommittedEvents.push(event);

    return order;
  }

  // Commands
  addItem(productId: string, quantity: number, price: number, userId: string): void {
    // Validate
    if (this.status !== OrderStatus.Pending) {
      throw new OrderAlreadySubmittedError();
    }

    if (quantity <= 0) {
      throw new OrderError('Quantity must be positive');
    }

    if (price < 0) {
      throw new OrderError('Price cannot be negative');
    }

    // Create event
    const event: ItemAddedEvent = {
      eventId: uuid(),
      eventType: 'ItemAdded',
      aggregateId: this.orderId,
      aggregateType: 'Order',
      version: this.version + 1,
      data: {
        orderId: this.orderId,
        productId,
        quantity,
        price,
      },
      metadata: {
        userId,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date(),
    };

    // Apply and store
    this.applyEvent(event);
    this.uncommittedEvents.push(event);
  }

  removeItem(productId: string, userId: string): void {
    // Validate
    if (this.status !== OrderStatus.Pending) {
      throw new OrderAlreadySubmittedError();
    }

    if (!this.items.has(productId)) {
      throw new OrderError(`Product ${productId} not in order`);
    }

    // Create event
    const event: ItemRemovedEvent = {
      eventId: uuid(),
      eventType: 'ItemRemoved',
      aggregateId: this.orderId,
      aggregateType: 'Order',
      version: this.version + 1,
      data: {
        orderId: this.orderId,
        productId,
      },
      metadata: {
        userId,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date(),
    };

    // Apply and store
    this.applyEvent(event);
    this.uncommittedEvents.push(event);
  }

  submit(userId: string): void {
    // Validate
    if (this.status !== OrderStatus.Pending) {
      throw new OrderAlreadySubmittedError();
    }

    if (this.items.size === 0) {
      throw new EmptyOrderError();
    }

    // Calculate total
    const totalAmount = Array.from(this.items.values()).reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );

    // Create event
    const event: OrderSubmittedEvent = {
      eventId: uuid(),
      eventType: 'OrderSubmitted',
      aggregateId: this.orderId,
      aggregateType: 'Order',
      version: this.version + 1,
      data: {
        orderId: this.orderId,
        totalAmount,
        submittedAt: new Date().toISOString(),
      },
      metadata: {
        userId,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date(),
    };

    // Apply and store
    this.applyEvent(event);
    this.uncommittedEvents.push(event);
  }

  cancel(reason: string, userId: string): void {
    // Validate
    if (this.status === OrderStatus.Cancelled) {
      throw new OrderError('Order is already cancelled');
    }

    // Create event
    const event: OrderCancelledEvent = {
      eventId: uuid(),
      eventType: 'OrderCancelled',
      aggregateId: this.orderId,
      aggregateType: 'Order',
      version: this.version + 1,
      data: {
        orderId: this.orderId,
        reason,
      },
      metadata: {
        userId,
        timestamp: new Date().toISOString(),
      },
      timestamp: new Date(),
    };

    // Apply and store
    this.applyEvent(event);
    this.uncommittedEvents.push(event);
  }

  // Event application (NO business logic, only state mutations)
  private applyEvent(event: OrderEvent): void {
    switch (event.eventType) {
      case 'OrderCreated':
        this.customerId = event.data.customerId;
        break;

      case 'ItemAdded':
        this.items.set(event.data.productId, {
          productId: event.data.productId,
          quantity: event.data.quantity,
          price: event.data.price,
        });
        break;

      case 'ItemRemoved':
        this.items.delete(event.data.productId);
        break;

      case 'OrderSubmitted':
        this.status = OrderStatus.Submitted;
        break;

      case 'OrderCancelled':
        this.status = OrderStatus.Cancelled;
        break;
    }

    this.version = event.version;
  }

  // Getters
  getOrderId(): string {
    return this.orderId;
  }

  getCustomerId(): string | undefined {
    return this.customerId;
  }

  getStatus(): OrderStatus {
    return this.status;
  }

  getItems(): OrderItem[] {
    return Array.from(this.items.values());
  }

  getTotalAmount(): number {
    return Array.from(this.items.values()).reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
  }

  getVersion(): number {
    return this.version;
  }

  getUncommittedEvents(): OrderEvent[] {
    return [...this.uncommittedEvents];
  }

  markEventsCommitted(): void {
    this.uncommittedEvents = [];
  }

  // Reconstruction
  static fromEvents(orderId: string, events: OrderEvent[]): Order {
    const order = new Order(orderId);
    events.forEach((event) => order.applyEvent(event));
    return order;
  }
}

// Usage example
if (require.main === module) {
  // Create order
  const order = Order.create('order-123', 'customer-456', 'admin-1');
  console.log(`Order ${order.getOrderId()} created for customer ${order.getCustomerId()}`);

  // Add items
  order.addItem('product-1', 2, 19.99, 'admin-1');
  order.addItem('product-2', 1, 29.99, 'admin-1');
  console.log(`Added ${order.getItems().length} items`);
  console.log(`Total: $${order.getTotalAmount().toFixed(2)}`);

  // Submit order
  order.submit('admin-1');
  console.log(`Order submitted with status: ${order.getStatus()}`);

  // Get uncommitted events
  const events = order.getUncommittedEvents();
  console.log(`\nUncommitted events: ${events.length}`);
  events.forEach((event, i) => {
    console.log(`  ${i + 1}. ${event.eventType} (v${event.version})`);
  });

  // Simulate persistence and reconstruction
  console.log('\n--- Simulating persistence and reconstruction ---\n');

  const savedEvents = order.getUncommittedEvents();
  order.markEventsCommitted();

  // Reconstruct from events
  const reconstructed = Order.fromEvents('order-123', savedEvents);
  console.log(`Reconstructed order`);
  console.log(`Customer: ${reconstructed.getCustomerId()}`);
  console.log(`Items: ${reconstructed.getItems().length}`);
  console.log(`Total: $${reconstructed.getTotalAmount().toFixed(2)}`);
  console.log(`Status: ${reconstructed.getStatus()}`);
  console.log(`Version: ${reconstructed.getVersion()}`);
}
