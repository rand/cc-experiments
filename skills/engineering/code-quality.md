---
name: engineering-code-quality
description: Code quality metrics, maintainability principles, SOLID design, code smells detection, and quality measurement
---

# Code Quality & Maintainability

**Scope**: Comprehensive guide to code quality principles, SOLID design, code smells, metrics, and long-term maintainability
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Evaluating code quality in reviews or audits
- Establishing quality standards for a team
- Refactoring legacy code to improve maintainability
- Setting up code quality metrics and monitoring
- Training engineers on clean code principles
- Defining "done" criteria for features
- Improving codebase health over time
- Reducing bug rates and technical debt

## Core Concepts

### Concept 1: The SOLID Principles

**S - Single Responsibility Principle**
> A class/function should have one reason to change

```python
# Bad: User class does too much
class User:
    def save_to_database(self): ...
    def send_email(self): ...
    def generate_pdf_report(self): ...
    def validate_password(self): ...

# Good: Each class has one responsibility
class User:
    def validate_password(self): ...

class UserRepository:
    def save(self, user: User): ...

class EmailService:
    def send_welcome_email(self, user: User): ...

class ReportGenerator:
    def generate_user_report(self, user: User): ...
```

**O - Open/Closed Principle**
> Open for extension, closed for modification

```python
# Bad: Must modify class to add new payment method
class PaymentProcessor:
    def process(self, method: str, amount: float):
        if method == "credit_card":
            # Credit card logic
        elif method == "paypal":
            # PayPal logic
        elif method == "bitcoin":  # Must modify existing code!
            # Bitcoin logic

# Good: Extend via new classes
class PaymentMethod:
    def process(self, amount: float): ...

class CreditCardPayment(PaymentMethod):
    def process(self, amount: float): ...

class PayPalPayment(PaymentMethod):
    def process(self, amount: float): ...

class PaymentProcessor:
    def process(self, method: PaymentMethod, amount: float):
        method.process(amount)  # No modification needed!
```

**L - Liskov Substitution Principle**
> Subtypes must be substitutable for their base types

```typescript
// Bad: Violates LSP
class Rectangle {
  width: number;
  height: number;
  setWidth(w: number) { this.width = w; }
  setHeight(h: number) { this.height = h; }
  area(): number { return this.width * this.height; }
}

class Square extends Rectangle {
  setWidth(w: number) {
    this.width = w;
    this.height = w;  // Breaks expected Rectangle behavior!
  }
}

// Good: Composition over inheritance
interface Shape {
  area(): number;
}

class Rectangle implements Shape {
  constructor(private width: number, private height: number) {}
  area(): number { return this.width * this.height; }
}

class Square implements Shape {
  constructor(private side: number) {}
  area(): number { return this.side * this.side; }
}
```

**I - Interface Segregation Principle**
> Clients shouldn't depend on interfaces they don't use

```go
// Bad: Fat interface
type Worker interface {
    Work()
    Eat()
    Sleep()
}

type Robot struct{}

func (r Robot) Work() { /* ... */ }
func (r Robot) Eat() { /* Robots don't eat! */ }
func (r Robot) Sleep() { /* Robots don't sleep! */ }

// Good: Segregated interfaces
type Worker interface {
    Work()
}

type LivingWorker interface {
    Worker
    Eat()
    Sleep()
}

type Robot struct{}
func (r Robot) Work() { /* ... */ }

type Human struct{}
func (h Human) Work() { /* ... */ }
func (h Human) Eat() { /* ... */ }
func (h Human) Sleep() { /* ... */ }
```

**D - Dependency Inversion Principle**
> Depend on abstractions, not concretions

```typescript
// Bad: High-level module depends on low-level module
class MySQLDatabase {
  save(data: string) { /* MySQL specific */ }
}

class UserService {
  private db = new MySQLDatabase();  // Tight coupling!

  saveUser(user: User) {
    this.db.save(JSON.stringify(user));
  }
}

// Good: Both depend on abstraction
interface Database {
  save(data: string): void;
}

class MySQLDatabase implements Database {
  save(data: string) { /* MySQL specific */ }
}

class PostgresDatabase implements Database {
  save(data: string) { /* Postgres specific */ }
}

class UserService {
  constructor(private db: Database) {}  // Depend on interface

  saveUser(user: User) {
    this.db.save(JSON.stringify(user));
  }
}
```

---

### Concept 2: Code Smells

**Common Code Smells**:

| Smell | Description | Fix |
|-------|-------------|-----|
| **Long Method** | Method > 30 lines | Extract smaller methods |
| **Large Class** | Class > 500 lines | Split into multiple classes |
| **Long Parameter List** | > 3-4 parameters | Use object/struct |
| **Duplicated Code** | Same logic in multiple places | Extract to function |
| **Dead Code** | Unused code | Delete it |
| **Magic Numbers** | Hardcoded constants | Use named constants |
| **Nested Conditionals** | If/else > 3 levels deep | Extract guard clauses |
| **Primitive Obsession** | Over-reliance on primitives | Create value objects |
| **Feature Envy** | Method uses another class's data more than its own | Move method |
| **Data Clumps** | Same group of data everywhere | Create a class |

**Examples**:

```python
# Smell: Magic Numbers
def calculate_price(quantity):
    return quantity * 19.99 * 1.08  # What are these?

# Fixed: Named Constants
PRICE_PER_ITEM = 19.99
TAX_RATE = 1.08

def calculate_price(quantity):
    return quantity * PRICE_PER_ITEM * TAX_RATE
```

```typescript
// Smell: Long Parameter List
function createUser(
  name: string,
  email: string,
  age: number,
  address: string,
  phone: string,
  company: string
) { }

// Fixed: Parameter Object
interface UserData {
  name: string;
  email: string;
  age: number;
  address: string;
  phone: string;
  company: string;
}

function createUser(data: UserData) { }
```

```go
// Smell: Nested Conditionals
func processOrder(order Order) error {
    if order.IsValid() {
        if order.HasInventory() {
            if order.PaymentSucceeded() {
                if order.ShippingAvailable() {
                    // Process order
                }
            }
        }
    }
}

// Fixed: Guard Clauses
func processOrder(order Order) error {
    if !order.IsValid() {
        return ErrInvalidOrder
    }
    if !order.HasInventory() {
        return ErrOutOfStock
    }
    if !order.PaymentSucceeded() {
        return ErrPaymentFailed
    }
    if !order.ShippingAvailable() {
        return ErrShippingUnavailable
    }

    // Process order
    return nil
}
```

---

### Concept 3: Code Quality Metrics

**Cyclomatic Complexity**
> Measure of code complexity based on number of independent paths

```python
# Complexity: 1 (simple)
def add(a, b):
    return a + b

# Complexity: 4 (moderate)
def get_discount(user_type, purchase_amount):
    if user_type == "premium":
        if purchase_amount > 100:
            return 0.20
        return 0.10
    elif user_type == "regular":
        if purchase_amount > 100:
            return 0.10
    return 0

# Target: Keep functions < 10 complexity
```

**Code Coverage**
> Percentage of code executed by tests

```bash
# Good coverage targets:
# - Critical business logic: 90%+
# - General codebase: 70-80%
# - UI/Glue code: 50-60%

pytest --cov=myapp --cov-report=html
# coverage: 78% (good!)
```

**Maintainability Index**
> Composite metric: 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(L)
> - V: Halstead Volume (complexity)
> - G: Cyclomatic Complexity
> - L: Lines of Code

| Score | Maintainability |
|-------|-----------------|
| 85-100 | Highly maintainable |
| 65-85 | Moderately maintainable |
| < 65 | Difficult to maintain |

**Code Churn**
> How often files change

```bash
# High churn = potential quality issues
git log --format=format: --name-only | sort | uniq -c | sort -rn | head -10

# Example output:
#  47 src/utils/helpers.py  # Too much churn!
#  12 src/models/user.py    # Acceptable
```

---

## Patterns

### Pattern 1: Readable Code Structure

**Function Length**:
```python
# Bad: Long function (100+ lines)
def process_order(order):
    # 100 lines of mixed concerns

# Good: Small, focused functions
def process_order(order):
    validate_order(order)
    charge_payment(order)
    update_inventory(order)
    send_confirmation(order)

# Each function < 20 lines, single responsibility
```

**Variable Naming**:
```typescript
// Bad: Unclear names
let d: number;  // What is d?
let tmp: string;  // Temporary what?
let data: any[];  // What kind of data?

// Good: Descriptive names
let daysUntilExpiration: number;
let userEmail: string;
let activeOrders: Order[];
```

**Comments**:
```go
// Bad: Redundant comment
// Increment i by 1
i++

// Bad: Outdated comment
// Calculate tax rate (7%)
taxRate := 0.08  // Comment is wrong!

// Good: Explain WHY, not WHAT
// Use exponential backoff to avoid overwhelming the API
// during high traffic periods
time.Sleep(time.Duration(math.Pow(2, retries)) * time.Second)
```

---

### Pattern 2: Error Handling

**Python**:
```python
# Bad: Silently swallowing errors
try:
    user = get_user(user_id)
except:
    pass  # What happened?

# Good: Specific error handling
try:
    user = get_user(user_id)
except UserNotFoundError as e:
    logger.error(f"User {user_id} not found: {e}")
    raise
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    # Try fallback
    user = get_user_from_cache(user_id)
```

**Go**:
```go
// Bad: Ignoring errors
user, _ := getUser(userID)  // What if it fails?

// Good: Explicit error handling
user, err := getUser(userID)
if err != nil {
    return fmt.Errorf("failed to get user %d: %w", userID, err)
}
```

**Rust**:
```rust
// Bad: Unwrapping everywhere
let user = get_user(user_id).unwrap();  // Panics on error!

// Good: Propagating errors
let user = get_user(user_id)?;  // Returns early if error

// Or: Pattern matching
match get_user(user_id) {
    Ok(user) => process_user(user),
    Err(e) => log::error!("Failed to get user: {}", e),
}
```

---

### Pattern 3: Testable Code Design

**Bad: Hard to Test**:
```typescript
class UserService {
  async createUser(email: string): Promise<User> {
    // Hard-coded dependency!
    const db = new MySQLDatabase();
    const emailService = new SendGridEmailService();
    const logger = new FileLogger();

    const user = await db.save({ email });
    await emailService.send(user.email, "Welcome!");
    logger.info(`Created user ${user.id}`);

    return user;
  }
}

// Can't test without real database, email service, file system!
```

**Good: Easy to Test**:
```typescript
interface Database {
  save(data: any): Promise<User>;
}

interface EmailService {
  send(to: string, subject: string): Promise<void>;
}

interface Logger {
  info(message: string): void;
}

class UserService {
  constructor(
    private db: Database,
    private emailService: EmailService,
    private logger: Logger
  ) {}

  async createUser(email: string): Promise<User> {
    const user = await this.db.save({ email });
    await this.emailService.send(user.email, "Welcome!");
    this.logger.info(`Created user ${user.id}`);
    return user;
  }
}

// Easy to test with mocks!
const mockDb = { save: jest.fn() };
const mockEmail = { send: jest.fn() };
const mockLogger = { info: jest.fn() };
const service = new UserService(mockDb, mockEmail, mockLogger);
```

---

### Pattern 4: Code Organization

**Package Structure**:
```
# Bad: Organized by type
src/
  controllers/
    user_controller.py
    order_controller.py
    product_controller.py
  models/
    user.py
    order.py
    product.py
  services/
    user_service.py
    order_service.py
    product_service.py

# Good: Organized by feature/domain
src/
  users/
    controller.py
    model.py
    service.py
    repository.py
  orders/
    controller.py
    model.py
    service.py
    repository.py
  products/
    controller.py
    model.py
    service.py
    repository.py
```

**Module Cohesion**:
```python
# Bad: Low cohesion - unrelated functions
def calculate_tax(amount): ...
def send_email(to, subject): ...
def hash_password(password): ...

# Good: High cohesion - related functions
# tax_calculator.py
def calculate_sales_tax(amount, state): ...
def calculate_income_tax(income, bracket): ...
def get_tax_rate(state): ...

# email_service.py
def send_email(to, subject, body): ...
def send_bulk_email(recipients, subject, body): ...
def validate_email(email): ...

# auth_service.py
def hash_password(password): ...
def verify_password(password, hash): ...
def generate_token(user_id): ...
```

---

## Best Practices

### Code Quality Checklist

**Before Committing**:
- [ ] No commented-out code (delete it, git remembers)
- [ ] No TODO comments (create tickets instead)
- [ ] No magic numbers (use named constants)
- [ ] No functions > 30 lines
- [ ] No classes > 500 lines
- [ ] No duplicate code (DRY principle)
- [ ] Meaningful variable/function names
- [ ] Complex logic has comments explaining WHY

**During Review**:
- [ ] Follows team's style guide
- [ ] Has adequate test coverage
- [ ] No obvious bugs or edge cases
- [ ] Error handling is appropriate
- [ ] Dependencies are necessary
- [ ] Performance is acceptable
- [ ] Security vulnerabilities addressed

---

## Anti-Patterns

### Common Mistakes

```
❌ Over-engineering: Premature abstraction
→ Start simple, refactor when needed

❌ God objects: Classes that do everything
→ Follow Single Responsibility Principle

❌ Premature optimization: Optimizing before profiling
→ Make it work, make it right, make it fast

❌ Copy-paste coding: Duplicating logic
→ Extract to shared functions

❌ Commenting obvious code: // Set x to 5
→ Only comment complex/non-obvious logic

❌ Inconsistent naming: getUserData() vs fetchUser()
→ Pick conventions and stick to them

❌ Deep nesting: If/else 5+ levels deep
→ Use guard clauses, early returns

❌ Ignoring errors: try { } catch { }
→ Handle errors explicitly
```

---

## Tools & Automation

### Static Analysis Tools

**Python**:
```bash
# Linting
flake8 src/
pylint src/

# Type checking
mypy src/

# Code quality
radon cc src/ -a  # Cyclomatic complexity
radon mi src/     # Maintainability index

# Security
bandit -r src/
```

**JavaScript/TypeScript**:
```bash
# Linting
eslint src/

# Type checking
tsc --noEmit

# Code quality
npx complexity-report src/
```

**Go**:
```bash
# Linting
golangci-lint run

# Cyclomatic complexity
gocyclo -over 10 .

# Security
gosec ./...
```

### Quality Gates in CI

```yaml
# .github/workflows/quality.yml
name: Code Quality
on: [pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run linters
        run: |
          flake8 src/ --max-complexity=10
          pylint src/ --fail-under=8.0

      - name: Check test coverage
        run: |
          pytest --cov=src --cov-fail-under=80

      - name: Security scan
        run: |
          bandit -r src/ -ll

      - name: Check complexity
        run: |
          radon cc src/ -a -nb --total-average-threshold=B
```

---

## Related Skills

- **engineering-code-review**: Reviewing code for quality issues
- **engineering-refactoring-patterns**: Improving code quality through refactoring
- **engineering-test-driven-development**: Writing quality code via TDD
- **engineering-technical-debt**: Managing quality trade-offs
- **engineering-design-patterns**: Applying proven design solutions

---

## References

- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Code Smells Catalog](https://refactoring.guru/refactoring/smells)
- [Cyclomatic Complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
