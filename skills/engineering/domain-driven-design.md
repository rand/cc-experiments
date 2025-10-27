---
name: engineering-domain-driven-design
description: Domain-Driven Design patterns, bounded contexts, aggregates, entities, value objects, and strategic design
---

# Domain-Driven Design (DDD)

**Scope**: Comprehensive guide to DDD patterns, strategic design, tactical patterns, and domain modeling
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building complex business domains with rich logic
- Designing microservices boundaries
- Establishing ubiquitous language with stakeholders
- Modeling enterprise applications
- Refactoring from anemic domain models
- Defining bounded contexts in large systems
- Implementing event-driven architectures
- Collaborating between technical and domain experts

## Core Concepts

### Concept 1: Strategic Design

**Ubiquitous Language**
> Shared language between developers and domain experts

```python
# Bad: Technical jargon disconnected from business
class DataProcessor:
    def execute(self, input_params):
        result = self.algorithm(input_params)
        self.persist(result)

# Good: Business language
class OrderFulfillment:
    def fulfill_order(self, order: Order):
        shipment = self.prepare_shipment(order)
        self.ship_to_customer(shipment)
```

**Bounded Context**
> Clear boundary where a model applies

```
E-commerce System:
┌─────────────────────┐
│ Sales Context       │  "Customer" = buyer
│ - Customer          │  "Order" = purchase
│ - Order             │
│ - Product           │
└─────────────────────┘

┌─────────────────────┐
│ Shipping Context    │  "Customer" = recipient
│ - Recipient         │  "Order" = shipment
│ - Shipment          │
│ - Delivery          │
└─────────────────────┘

Same words, different meanings in each context!
```

**Context Map**
> Relationships between bounded contexts

```
[Sales Context] ---(Customer/Supplier)---> [Inventory Context]
      ↓
   (ACL - Anti-Corruption Layer)
      ↓
[Shipping Context] <---(Shared Kernel)--- [Billing Context]
```

---

### Concept 2: Tactical Patterns - Building Blocks

**Entity**
> Object with identity that persists over time

```typescript
class Order {
  private id: OrderId;  // Identity
  private customerId: CustomerId;
  private items: OrderItem[];
  private status: OrderStatus;
  private total: Money;

  // Identity matters - same ID = same order
  equals(other: Order): boolean {
    return this.id.equals(other.id);
  }
}
```

**Value Object**
> Object defined by its attributes, no identity

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Immutable
class Money:
    amount: Decimal
    currency: str

    def add(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

# Value objects compared by value, not identity
money1 = Money(Decimal("10.00"), "USD")
money2 = Money(Decimal("10.00"), "USD")
assert money1 == money2  # Equal by value
```

**Aggregate**
> Cluster of entities/value objects with a root

```go
// Order Aggregate Root
type Order struct {
    id         OrderID         // Identity
    customerID CustomerID
    items      []OrderItem     // Internal entities
    status     OrderStatus
    total      Money
}

// Only access OrderItems through Order (aggregate root)
func (o *Order) AddItem(product Product, quantity int) error {
    if o.status != StatusDraft {
        return errors.New("cannot modify non-draft order")
    }

    item := NewOrderItem(product, quantity)
    o.items = append(o.items, item)
    o.recalculateTotal()  // Invariants maintained by root
    return nil
}

// Aggregate boundary: Order controls access to OrderItems
// Can't modify OrderItem directly - must go through Order
```

---

### Concept 3: Repositories & Services

**Repository**
> Abstraction for collection-like access to aggregates

```typescript
interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  save(order: Order): Promise<void>;
  findByCustomer(customerId: CustomerId): Promise<Order[]>;
}

// Implementation hidden behind interface
class PostgresOrderRepository implements OrderRepository {
  async findById(id: OrderId): Promise<Order | null> {
    // Database access details hidden
  }
}
```

**Domain Service**
> Operation that doesn't belong to any entity

```python
class PricingService:
    """Domain service for complex pricing logic"""

    def calculate_order_total(
        self,
        items: List[OrderItem],
        customer: Customer,
        promotion: Optional[Promotion]
    ) -> Money:
        subtotal = sum(item.price for item in items)

        # Business logic that spans multiple entities
        if customer.is_vip():
            subtotal = subtotal * Decimal("0.9")

        if promotion:
            subtotal = promotion.apply(subtotal)

        return Money(subtotal, "USD")
```

---

## Patterns

### Pattern 1: Entity vs Value Object

**Entity Example (Order)**:
```python
class Order:
    def __init__(self, order_id: OrderId):
        self.id = order_id  # Identity
        self.items: List[OrderItem] = []
        self.created_at = datetime.now()

    def __eq__(self, other):
        return isinstance(other, Order) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

# Same ID = same order, even if attributes differ
order1 = Order(OrderId("123"))
order1.items.append(OrderItem("Widget"))

order2 = Order(OrderId("123"))
# order2 has no items, but equals order1 by identity
assert order1 == order2
```

**Value Object Example (Address)**:
```python
@dataclass(frozen=True)  # Immutable
class Address:
    street: str
    city: str
    state: str
    zip_code: str

    def __post_init__(self):
        if not self.zip_code or len(self.zip_code) != 5:
            raise ValueError("Invalid zip code")

# Value objects compared by value
addr1 = Address("123 Main St", "Boston", "MA", "02101")
addr2 = Address("123 Main St", "Boston", "MA", "02101")
assert addr1 == addr2  # Same values = equal

# Immutable - create new instance to "change"
addr3 = Address(addr1.street, "Cambridge", addr1.state, addr1.zip_code)
```

---

### Pattern 2: Aggregate Design

**Bad: No aggregate boundary**:
```typescript
// Can modify OrderItem directly - invariants can break!
const order = orderRepo.findById("123");
const item = orderItemRepo.findById("456");
item.quantity = 0;  // Violates business rule!
item.price = -100;  // Invalid state!
orderItemRepo.save(item);
```

**Good: Aggregate enforces invariants**:
```typescript
class Order {  // Aggregate Root
  private items: OrderItem[] = [];

  addItem(product: Product, quantity: number): void {
    if (quantity <= 0) {
      throw new Error("Quantity must be positive");
    }

    const item = new OrderItem(product, quantity);
    this.items.push(item);
    this.recalculateTotal();  // Maintain invariant
  }

  removeItem(itemId: string): void {
    this.items = this.items.filter(item => item.id !== itemId);
    this.recalculateTotal();  // Maintain invariant
  }

  private recalculateTotal(): void {
    this.total = this.items.reduce(
      (sum, item) => sum.add(item.subtotal()),
      Money.zero("USD")
    );
  }
}

// Usage: Can only modify through aggregate root
const order = await orderRepo.findById("123");
order.addItem(product, 5);  // Invariants guaranteed
await orderRepo.save(order);
```

---

### Pattern 3: Domain Events

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class OrderPlaced:
    """Domain event: Something that happened in the domain"""
    order_id: str
    customer_id: str
    total: Money
    occurred_at: datetime

class Order:
    def __init__(self, order_id: str, customer_id: str):
        self.id = order_id
        self.customer_id = customer_id
        self.items: List[OrderItem] = []
        self.status = OrderStatus.DRAFT
        self._events: List[DomainEvent] = []

    def place_order(self):
        if not self.items:
            raise ValueError("Cannot place empty order")

        self.status = OrderStatus.PLACED

        # Record what happened
        event = OrderPlaced(
            order_id=self.id,
            customer_id=self.customer_id,
            total=self.calculate_total(),
            occurred_at=datetime.now()
        )
        self._events.append(event)

    def get_events(self) -> List[DomainEvent]:
        return self._events.copy()

# Event handlers in other contexts
class SendConfirmationEmailHandler:
    def handle(self, event: OrderPlaced):
        email_service.send(
            to=get_customer_email(event.customer_id),
            subject="Order Confirmation",
            body=f"Your order {event.order_id} has been placed!"
        )

class UpdateInventoryHandler:
    def handle(self, event: OrderPlaced):
        order = order_repo.find(event.order_id)
        for item in order.items:
            inventory.reserve(item.product_id, item.quantity)
```

---

### Pattern 4: Specification Pattern

```typescript
// Encapsulate business rules in reusable specifications
interface Specification<T> {
  isSatisfiedBy(candidate: T): boolean;
  and(other: Specification<T>): Specification<T>;
  or(other: Specification<T>): Specification<T>;
}

class VIPCustomerSpecification implements Specification<Customer> {
  isSatisfiedBy(customer: Customer): boolean {
    return customer.totalPurchases.isGreaterThan(Money.dollars(10000));
  }
}

class RecentCustomerSpecification implements Specification<Customer> {
  isSatisfiedBy(customer: Customer): boolean {
    const daysSinceLastOrder = customer.daysSinceLastOrder();
    return daysSinceLastOrder < 30;
  }
}

// Compose specifications
const vipSpec = new VIPCustomerSpecification();
const recentSpec = new RecentCustomerSpecification();
const eligibleForDiscount = vipSpec.or(recentSpec);

if (eligibleForDiscount.isSatisfiedBy(customer)) {
  order.applyDiscount(0.10);
}
```

---

### Pattern 5: Factory Pattern

```python
class OrderFactory:
    """Create complex aggregates with valid initial state"""

    def create_order(
        self,
        customer: Customer,
        items: List[Tuple[Product, int]],
        shipping_address: Address
    ) -> Order:
        # Validate business rules
        if not customer.is_active():
            raise ValueError("Cannot create order for inactive customer")

        if not items:
            raise ValueError("Order must have at least one item")

        # Create aggregate with valid state
        order = Order(
            order_id=OrderId.generate(),
            customer_id=customer.id,
            shipping_address=shipping_address
        )

        for product, quantity in items:
            if not product.is_available(quantity):
                raise ValueError(f"Product {product.name} not available")
            order.add_item(product, quantity)

        return order
```

---

### Pattern 6: Anti-Corruption Layer (ACL)

```go
// Protect our domain from external system's model
type ExternalPaymentService struct {
    client *ThirdPartyAPI
}

// External model (we don't control)
type ThirdPartyPaymentResponse struct {
    TxnID       string
    StatusCode  int  // 1=pending, 2=success, 3=failed
    AmountCents int
}

// Our domain model
type PaymentResult struct {
    TransactionID string
    Status        PaymentStatus  // enum: Pending, Completed, Failed
    Amount        Money
}

// Anti-Corruption Layer: Translate external model to our model
func (s *ExternalPaymentService) ProcessPayment(
    amount Money,
) (PaymentResult, error) {
    // Call external service
    response, err := s.client.Charge(amount.Cents(), amount.Currency())
    if err != nil {
        return PaymentResult{}, err
    }

    // Translate to our domain model
    return PaymentResult{
        TransactionID: response.TxnID,
        Status:        translateStatus(response.StatusCode),
        Amount:        Money{Amount: response.AmountCents / 100.0},
    }, nil
}

func translateStatus(code int) PaymentStatus {
    switch code {
    case 1:
        return PaymentStatusPending
    case 2:
        return PaymentStatusCompleted
    case 3:
        return PaymentStatusFailed
    default:
        return PaymentStatusUnknown
    }
}
```

---

## Best Practices

### Modeling Guidelines

**Entity Design**:
- [ ] Has unique identity
- [ ] Identity persists over time
- [ ] Equality based on ID, not attributes
- [ ] Can change attributes without changing identity

**Value Object Design**:
- [ ] Immutable (cannot change after creation)
- [ ] Equality based on all attributes
- [ ] No identity
- [ ] Can be shared/cached safely

**Aggregate Design**:
- [ ] Has single root entity
- [ ] External objects reference only the root
- [ ] Internal objects not accessible outside
- [ ] Maintains invariants across all contained objects
- [ ] Loaded and saved as a unit

---

### Bounded Context Rules

1. **Each context has its own model** - Don't share entities across contexts
2. **Use context maps** - Document relationships between contexts
3. **Use ACL** - Protect your model from external models
4. **Published language** - Define contracts between contexts
5. **Shared kernel** - Minimize shared code between contexts

---

## Anti-Patterns

### Common DDD Mistakes

```
❌ Anemic Domain Model
→ Entities with only getters/setters, logic in services
✅ Rich domain model with behavior in entities

❌ Giant Aggregates
→ Aggregate contains entire object graph
✅ Small aggregates with clear boundaries

❌ Missing Ubiquitous Language
→ Technical terms disconnected from business
✅ Code uses business domain terms

❌ CRUD-based Design
→ Thinking in database tables, not domain
✅ Model business processes and rules

❌ Ignoring Bounded Contexts
→ One model for entire system
✅ Multiple models with clear boundaries

❌ Repository per Entity
→ Repository for every entity
✅ Repository per aggregate root only

❌ Domain Events as DTOs
→ Events with no business meaning
✅ Events capture domain concepts
```

---

## Example: E-Commerce Order

```python
# Value Objects
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def add(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)
class ProductId:
    value: str

# Entity (within Order aggregate)
class OrderItem:
    def __init__(self, product_id: ProductId, quantity: int, unit_price: Money):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self._product_id = product_id
        self._quantity = quantity
        self._unit_price = unit_price

    def subtotal(self) -> Money:
        return Money(
            self._unit_price.amount * self._quantity,
            self._unit_price.currency
        )

# Aggregate Root
class Order:
    def __init__(self, order_id: str, customer_id: str):
        self.id = order_id
        self.customer_id = customer_id
        self._items: List[OrderItem] = []
        self._status = OrderStatus.DRAFT
        self._events: List[DomainEvent] = []

    def add_item(self, product_id: ProductId, quantity: int, unit_price: Money):
        """Business logic in aggregate root"""
        if self._status != OrderStatus.DRAFT:
            raise ValueError("Cannot modify non-draft order")

        item = OrderItem(product_id, quantity, unit_price)
        self._items.append(item)

    def place_order(self):
        """Business operation"""
        if not self._items:
            raise ValueError("Cannot place empty order")

        self._status = OrderStatus.PLACED
        self._events.append(OrderPlaced(self.id, datetime.now()))

    def calculate_total(self) -> Money:
        """Business logic"""
        return sum(
            (item.subtotal() for item in self._items),
            start=Money(Decimal("0"), "USD")
        )

# Repository (only for aggregate roots)
class OrderRepository(ABC):
    @abstractmethod
    def find_by_id(self, order_id: str) -> Optional[Order]:
        pass

    @abstractmethod
    def save(self, order: Order) -> None:
        pass

# Domain Service
class OrderFulfillmentService:
    """Cross-aggregate business logic"""

    def fulfill_order(self, order: Order, inventory: Inventory):
        for item in order.items:
            if not inventory.is_available(item.product_id, item.quantity):
                raise InsufficientInventoryError()

        for item in order.items:
            inventory.reserve(item.product_id, item.quantity)

        order.mark_as_fulfilled()
```

---

## Related Skills

- **engineering-design-patterns**: GoF patterns used in DDD
- **engineering-code-quality**: Quality in domain models
- **engineering-test-driven-development**: Testing domain logic
- **engineering-refactoring-patterns**: Refactoring toward DDD
- **api-rest-design**: Designing APIs for bounded contexts

---

## References

- [Domain-Driven Design by Eric Evans](https://www.amazon.com/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215)
- [Implementing Domain-Driven Design by Vaughn Vernon](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577)
- [DDD Patterns](https://martinfowler.com/tags/domain%20driven%20design.html)
- [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html)
