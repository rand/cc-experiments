---
name: engineering-refactoring-patterns
description: Refactoring techniques, when to refactor, safe refactoring strategies, and code improvement patterns
---

# Refactoring Patterns & Techniques

**Scope**: Comprehensive guide to refactoring techniques, when to refactor, safe strategies, and systematic code improvement
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Improving existing code without changing behavior
- Reducing technical debt in legacy systems
- Preparing code for new features
- Simplifying complex code for maintainability
- Eliminating code smells and anti-patterns
- Standardizing inconsistent codebases
- Making code more testable
- Improving performance through structural changes

## Core Concepts

### Concept 1: When to Refactor

**The Rule of Three**
> First time: Just write it
> Second time: Duplicate it (note the duplication)
> Third time: Refactor it (extract the pattern)

**Refactor When**:
- Adding a feature and code is hard to modify
- Fixing a bug reveals underlying design issues
- Code review identifies improvement opportunities
- Tests are difficult to write
- Making similar changes in multiple places
- Code fails quality checks (complexity, coverage)

**Don't Refactor When**:
- No tests exist (write tests first!)
- Under tight deadline (plan it for later)
- Code is working and rarely changes
- Rewrite would be faster than refactoring
- You don't understand what the code does

---

### Concept 2: Safe Refactoring Process

**The Refactoring Workflow**:
```
1. Ensure tests exist and pass
   ↓
2. Make small, incremental change
   ↓
3. Run tests
   ↓
4. Commit if tests pass
   ↓
5. Repeat until complete
```

**Critical Rules**:
- Never refactor without tests
- Make one change at a time
- Run tests after each change
- Commit frequently
- Don't mix refactoring with new features

---

### Concept 3: Common Refactoring Patterns

**Extract Method/Function**
> Replace code fragment with a named function

**Inline Function**
> Replace function call with function body (when function is trivial)

**Extract Variable**
> Put complex expression result in self-explanatory variable

**Inline Variable**
> Remove variable that's just as clear as expression

**Rename**
> Change name to better reveal intent

**Move Function**
> Move function to class that uses it most

**Replace Conditional with Polymorphism**
> Replace type code with subclasses/interfaces

---

## Patterns

### Pattern 1: Extract Method

**Before**:
```python
def print_owing(invoice):
    print("***********************")
    print("**** Customer Owes ****")
    print("***********************")

    outstanding = 0.0
    for order in invoice.orders:
        outstanding += order.amount

    print(f"Name: {invoice.customer}")
    print(f"Amount: {outstanding}")
```

**After**:
```python
def print_owing(invoice):
    print_banner()
    outstanding = calculate_outstanding(invoice)
    print_details(invoice, outstanding)

def print_banner():
    print("***********************")
    print("**** Customer Owes ****")
    print("***********************")

def calculate_outstanding(invoice):
    return sum(order.amount for order in invoice.orders)

def print_details(invoice, outstanding):
    print(f"Name: {invoice.customer}")
    print(f"Amount: {outstanding}")
```

**Benefits**: Each function has single responsibility, easier to test, reusable

---

### Pattern 2: Replace Magic Numbers with Constants

**Before**:
```typescript
function calculatePrice(quantity: number): number {
  return quantity * 29.99 * 1.08;  // What are these?
}

function checkStock(quantity: number): boolean {
  return quantity < 100;  // What does 100 mean?
}
```

**After**:
```typescript
const PRICE_PER_ITEM = 29.99;
const TAX_RATE = 1.08;
const LOW_STOCK_THRESHOLD = 100;

function calculatePrice(quantity: number): number {
  return quantity * PRICE_PER_ITEM * TAX_RATE;
}

function checkStock(quantity: number): boolean {
  return quantity < LOW_STOCK_THRESHOLD;
}
```

---

### Pattern 3: Replace Nested Conditionals with Guard Clauses

**Before**:
```go
func GetPayAmount(employee Employee) (float64, error) {
    var result float64
    if employee.IsSeparated {
        result = 0
    } else {
        if employee.IsRetired {
            result = employee.Pension
        } else {
            result = employee.Salary
        }
    }
    return result, nil
}
```

**After**:
```go
func GetPayAmount(employee Employee) (float64, error) {
    if employee.IsSeparated {
        return 0, nil
    }
    if employee.IsRetired {
        return employee.Pension, nil
    }
    return employee.Salary, nil
}
```

**Benefits**: Reduces cognitive load, clarifies special cases, easier to read

---

### Pattern 4: Extract Class (Split Large Class)

**Before**:
```python
class User:
    def __init__(self, name, email, address, city, state, zip_code):
        self.name = name
        self.email = email
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code

    def get_full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"

    def validate_address(self):
        # Complex address validation logic
        pass

    def format_address_for_label(self):
        # Complex formatting logic
        pass
```

**After**:
```python
class Address:
    def __init__(self, street, city, state, zip_code):
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code

    def get_full_address(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"

    def validate(self):
        # Validation logic
        pass

    def format_for_label(self):
        # Formatting logic
        pass

class User:
    def __init__(self, name, email, address: Address):
        self.name = name
        self.email = email
        self.address = address
```

**Benefits**: Single responsibility, address logic encapsulated, reusable

---

### Pattern 5: Replace Type Code with Polymorphism

**Before**:
```typescript
class Employee {
  type: string;  // "engineer", "manager", "salesperson"

  getBonus(): number {
    if (this.type === "engineer") {
      return this.salary * 0.10;
    } else if (this.type === "manager") {
      return this.salary * 0.20;
    } else if (this.type === "salesperson") {
      return this.salary * 0.15 + this.commission;
    }
    return 0;
  }
}
```

**After**:
```typescript
abstract class Employee {
  constructor(protected salary: number) {}
  abstract getBonus(): number;
}

class Engineer extends Employee {
  getBonus(): number {
    return this.salary * 0.10;
  }
}

class Manager extends Employee {
  getBonus(): number {
    return this.salary * 0.20;
  }
}

class Salesperson extends Employee {
  constructor(salary: number, private commission: number) {
    super(salary);
  }

  getBonus(): number {
    return this.salary * 0.15 + this.commission;
  }
}
```

**Benefits**: Open/closed principle, easier to add new types, type-safe

---

### Pattern 6: Introduce Parameter Object

**Before**:
```python
def create_invoice(customer_name, customer_email, customer_address,
                  item_name, item_price, item_quantity,
                  tax_rate, discount_rate):
    # 8 parameters is too many!
    pass
```

**After**:
```python
from dataclasses import dataclass

@dataclass
class Customer:
    name: str
    email: str
    address: str

@dataclass
class LineItem:
    name: str
    price: float
    quantity: int

@dataclass
class InvoiceOptions:
    tax_rate: float
    discount_rate: float

def create_invoice(customer: Customer, item: LineItem, options: InvoiceOptions):
    # Much cleaner!
    pass
```

---

### Pattern 7: Replace Conditional with Strategy Pattern

**Before**:
```go
func CalculateShipping(order Order, method string) float64 {
    if method == "standard" {
        return order.Weight * 0.50
    } else if method == "express" {
        return order.Weight * 1.50 + 10.00
    } else if method == "overnight" {
        return order.Weight * 3.00 + 25.00
    }
    return 0
}
```

**After**:
```go
type ShippingStrategy interface {
    Calculate(order Order) float64
}

type StandardShipping struct{}
func (s StandardShipping) Calculate(order Order) float64 {
    return order.Weight * 0.50
}

type ExpressShipping struct{}
func (e ExpressShipping) Calculate(order Order) float64 {
    return order.Weight * 1.50 + 10.00
}

type OvernightShipping struct{}
func (o OvernightShipping) Calculate(order Order) float64 {
    return order.Weight * 3.00 + 25.00
}

func CalculateShipping(order Order, strategy ShippingStrategy) float64 {
    return strategy.Calculate(order)
}
```

---

### Pattern 8: Remove Dead Code

**Before**:
```python
def process_payment(amount):
    # Old implementation - keeping just in case
    # def old_process_payment():
    #     charge_credit_card(amount)
    #     send_receipt()

    # Current implementation
    result = payment_gateway.process(amount)
    if result.success:
        send_receipt()
    return result

# Unused function - was replaced 6 months ago
def legacy_process_payment(amount):
    pass
```

**After**:
```python
def process_payment(amount):
    result = payment_gateway.process(amount)
    if result.success:
        send_receipt()
    return result

# Old code deleted - it's in git history if needed!
```

---

## Refactoring Techniques

### Simplifying Expressions

**Decompose Conditional**:
```python
# Before
if date.before(SUMMER_START) or date.after(SUMMER_END):
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# After
if is_winter(date):
    charge = winter_charge(quantity)
else:
    charge = summer_charge(quantity)
```

**Consolidate Duplicate Conditional Fragments**:
```typescript
// Before
if (isSpecialDeal()) {
  total = price * 0.95;
  send();
} else {
  total = price * 0.98;
  send();
}

// After
if (isSpecialDeal()) {
  total = price * 0.95;
} else {
  total = price * 0.98;
}
send();  // Extracted from both branches
```

---

### Simplifying Method Calls

**Replace Parameter with Method Call**:
```python
# Before
base_price = quantity * item_price
discount = get_discount(base_price, season)

# After
discount = get_discount(quantity, item_price, season)

def get_discount(quantity, item_price, season):
    base_price = quantity * item_price
    # Calculate discount
```

**Preserve Whole Object**:
```go
// Before
low := daysTempRange.GetLow()
high := daysTempRange.GetHigh()
withinPlan := plan.WithinRange(low, high)

// After
withinPlan := plan.WithinRange(daysTempRange)
```

---

### Organizing Data

**Replace Array with Object**:
```typescript
// Before
const row = ["Liverpool", 15];
const name = row[0];
const wins = row[1];

// After
interface Team {
  name: string;
  wins: number;
}

const team: Team = { name: "Liverpool", wins: 15 };
const name = team.name;
const wins = team.wins;
```

**Encapsulate Field**:
```python
# Before
class Person:
    name: str  # Public field

person.name = "John"

# After
class Person:
    def __init__(self):
        self._name: str = ""

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not value:
            raise ValueError("Name cannot be empty")
        self._name = value

person.name = "John"
```

---

## Best Practices

### Refactoring Checklist

**Before Starting**:
- [ ] Tests exist and pass
- [ ] Create feature branch
- [ ] Understand what code does
- [ ] Identify specific smell/issue
- [ ] Plan the refactoring steps

**During Refactoring**:
- [ ] Make one small change at a time
- [ ] Run tests after each change
- [ ] Commit after each successful change
- [ ] Don't add new features
- [ ] Don't change behavior

**After Completing**:
- [ ] All tests still pass
- [ ] Code is more readable
- [ ] Complexity reduced
- [ ] Documentation updated
- [ ] Create PR with "refactor:" prefix

---

### Refactoring in Legacy Code

**The Legacy Code Dilemma**:
> "We need tests to refactor safely, but we need to refactor to make code testable"

**Solution: Characterization Tests**
```python
# Step 1: Write tests that capture current behavior (even if wrong)
def test_legacy_payment_calculation():
    # Document current behavior, even if buggy
    result = calculate_payment(100, "premium")
    assert result == 95  # Current output (may be wrong!)

# Step 2: Now you can refactor safely
def calculate_payment(amount, tier):
    # Refactor with confidence - tests will catch breaks
    pass

# Step 3: Fix bugs in separate commits
def test_legacy_payment_calculation():
    result = calculate_payment(100, "premium")
    assert result == 90  # Fixed bug
```

**Strangler Fig Pattern**:
```
1. Identify module to replace
2. Create new implementation alongside old
3. Route new requests to new code
4. Gradually migrate existing data
5. Remove old code when fully migrated
```

---

## Anti-Patterns

### Refactoring Mistakes

```
❌ Big Bang Refactoring
→ Rewrite entire system at once (high risk!)
✅ Incremental refactoring (continuous improvement)

❌ Refactoring Without Tests
→ No safety net, likely to break things
✅ Write tests first, then refactor

❌ Mixing Refactoring and Features
→ Hard to review, hard to revert
✅ Separate commits: refactor, then feature

❌ Premature Optimization
→ Refactoring for imaginary performance issues
✅ Profile first, optimize hot paths only

❌ Over-Engineering
→ Introducing unnecessary abstractions
✅ Simplest thing that works

❌ Refactoring Under Deadline
→ Rushed refactoring introduces bugs
✅ Plan refactoring time explicitly
```

---

## Tools & Automation

### IDE Refactoring Tools

**PyCharm / VS Code**:
- Rename (Shift+F6)
- Extract Method (Ctrl+Alt+M)
- Extract Variable (Ctrl+Alt+V)
- Inline (Ctrl+Alt+N)
- Move (F6)

**Automated Refactoring**:
```bash
# Python: Rename symbol across codebase
rope --refactor rename old_name new_name

# Python: Extract method
rope --refactor extract_method

# Go: Rename
gopls rename -w old_name new_name

# TypeScript: Automated refactorings
npx ts-migrate rename old_name new_name
```

---

### Testing During Refactoring

**Mutation Testing** (verify tests actually test):
```bash
# Python
pip install mutmut
mutmut run

# Check if tests catch intentional bugs
# If mutation score is low, tests are weak!
```

**Snapshot Testing** (ensure output unchanged):
```python
def test_invoice_output_unchanged(snapshot):
    invoice = create_test_invoice()
    output = render_invoice(invoice)
    snapshot.assert_match(output)  # Fails if output changes
```

---

## Related Skills

- **engineering-code-quality**: Identifying code smells to refactor
- **engineering-code-review**: Reviewing refactorings safely
- **engineering-test-driven-development**: Tests enable safe refactoring
- **engineering-technical-debt**: Prioritizing refactoring work
- **engineering-design-patterns**: Refactoring toward patterns

---

## References

- [Refactoring by Martin Fowler](https://refactoring.com/)
- [Working Effectively with Legacy Code by Michael Feathers](https://www.amazon.com/Working-Effectively-Legacy-Michael-Feathers/dp/0131177052)
- [Refactoring Catalog](https://refactoring.guru/refactoring/catalog)
- [Extract Method](https://refactoring.com/catalog/extractFunction.html)
