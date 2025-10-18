---
name: testing-test-driven-development
description: Design APIs and interfaces through tests
---



# Test-Driven Development (TDD)

## When to Use This Skill

Use this skill when you need to:
- Design APIs and interfaces through tests
- Ensure code is testable from the start
- Build confidence before implementation
- Refactor safely with comprehensive test coverage
- Clarify requirements through test examples
- Reduce debugging time with tight feedback loops
- Decide when TDD is appropriate vs when to skip it

**ACTIVATE THIS SKILL**: When starting new features, fixing bugs, or refactoring complex code

## Core Concepts

### The Red-Green-Refactor Cycle

**RED**: Write a failing test
- Test doesn't compile OR test fails
- Defines desired behavior
- Forces you to think about API design

**GREEN**: Make it pass with minimal code
- Simplest implementation that works
- Don't worry about elegance yet
- Just make the test pass

**REFACTOR**: Improve code without changing behavior
- Clean up duplication
- Improve names and structure
- Tests stay green

```
RED → GREEN → REFACTOR → RED → GREEN → REFACTOR → ...
 ↓      ↓         ↓
Fail  Pass    Improve
```

### The Three Laws of TDD (Uncle Bob)

1. **Don't write production code** until you have a failing test
2. **Don't write more of a test** than is sufficient to fail
3. **Don't write more production code** than is sufficient to pass the test

### TDD vs Test-After

**Test-After** (Traditional):
```
Write code → Test it → Fix bugs → Ship
```
Problems: Hard to test, low coverage, bugs found late

**TDD**:
```
Write test → Write code → Refactor → Ship
```
Benefits: Testable design, high coverage, bugs prevented

## Patterns

### Classic TDD: Function Implementation

```python
# Step 1: RED - Write failing test
def test_calculate_discount():
    # Arrange
    original_price = 100
    discount_percent = 10

    # Act
    final_price = calculate_discount(original_price, discount_percent)

    # Assert
    assert final_price == 90

# Run: FAILS - calculate_discount doesn't exist

# Step 2: GREEN - Minimal implementation
def calculate_discount(price: float, discount: float) -> float:
    return price - (price * discount / 100)

# Run: PASSES

# Step 3: REFACTOR - Improve (if needed)
def calculate_discount(price: float, discount_percent: float) -> float:
    """Calculate final price after applying discount percentage."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")

    discount_amount = price * (discount_percent / 100)
    return price - discount_amount

# Add test for edge case
def test_calculate_discount_invalid():
    with pytest.raises(ValueError):
        calculate_discount(100, -10)
```

### TDD for Class Design

```typescript
// Step 1: RED - Define interface through tests
describe('ShoppingCart', () => {
  it('starts empty', () => {
    const cart = new ShoppingCart();
    expect(cart.itemCount).toBe(0);
    expect(cart.total).toBe(0);
  });

  // FAILS: ShoppingCart doesn't exist
});

// Step 2: GREEN - Minimal implementation
class ShoppingCart {
  itemCount = 0;
  total = 0;
}

// Step 3: RED - Next behavior
it('adds items to cart', () => {
  const cart = new ShoppingCart();
  cart.addItem({ name: 'Laptop', price: 1000 });

  expect(cart.itemCount).toBe(1);
  expect(cart.total).toBe(1000);
});

// Step 4: GREEN - Implement
class ShoppingCart {
  private items: Item[] = [];

  get itemCount() {
    return this.items.length;
  }

  get total() {
    return this.items.reduce((sum, item) => sum + item.price, 0);
  }

  addItem(item: Item) {
    this.items.push(item);
  }
}

// Step 5: RED - Add more behavior
it('removes items from cart', () => {
  const cart = new ShoppingCart();
  const item = { name: 'Laptop', price: 1000 };
  cart.addItem(item);
  cart.removeItem(item);

  expect(cart.itemCount).toBe(0);
  expect(cart.total).toBe(0);
});

// Step 6: GREEN - Implement
removeItem(item: Item) {
  const index = this.items.indexOf(item);
  if (index > -1) {
    this.items.splice(index, 1);
  }
}

// Step 7: REFACTOR - Improve (add discount support, etc.)
```

### Outside-In TDD (London School)

**Start with acceptance test, work inward**:

```python
# Step 1: Acceptance test (fails)
def test_user_can_register():
    # Arrange
    api = UserAPI()

    # Act
    response = api.register(
        username="alice",
        email="alice@example.com",
        password="secret123"
    )

    # Assert
    assert response.status_code == 201
    assert response.user_id is not None

# Step 2: Mock dependencies, implement UserAPI
class UserAPI:
    def __init__(self):
        self.user_service = Mock(UserService)
        self.email_service = Mock(EmailService)

    def register(self, username, email, password):
        user = self.user_service.create_user(username, email, password)
        self.email_service.send_welcome_email(user.email)
        return Response(status_code=201, user_id=user.id)

# Step 3: Now test UserService (unit test)
def test_user_service_creates_user():
    repo = Mock(UserRepository)
    service = UserService(repo)

    user = service.create_user("alice", "alice@example.com", "secret123")

    assert user.username == "alice"
    repo.save.assert_called_once_with(user)

# Step 4: Implement UserService
# Step 5: Test UserRepository
# Step 6: Implement UserRepository
```

### Inside-Out TDD (Chicago School)

**Start with smallest unit, build up**:

```python
# Step 1: Test pure function
def test_hash_password():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert len(hashed) == 60  # bcrypt length

# Step 2: Implement
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Step 3: Test User model
def test_user_creation():
    user = User(username="alice", email="alice@example.com", password_hash="hashed")
    assert user.username == "alice"
    assert user.is_active is True

# Step 4: Implement User
@dataclass
class User:
    username: str
    email: str
    password_hash: str
    is_active: bool = True

# Step 5: Test UserService (using real dependencies)
def test_user_service_creates_user():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    user = service.create_user("alice", "alice@example.com", "secret123")

    assert user.username == "alice"
    assert repo.find_by_username("alice") is not None
```

### TDD for Bug Fixes

```python
# Bug report: "Users can register with duplicate emails"

# Step 1: RED - Write failing test that reproduces bug
def test_cannot_register_duplicate_email():
    service = UserService()

    service.register("alice", "alice@example.com", "pass1")

    with pytest.raises(DuplicateEmailError):
        service.register("bob", "alice@example.com", "pass2")

# Run: FAILS - No DuplicateEmailError raised (bug confirmed)

# Step 2: GREEN - Fix the bug
class UserService:
    def register(self, username, email, password):
        if self.repository.find_by_email(email):
            raise DuplicateEmailError(f"Email {email} already registered")

        user = User(username, email, hash_password(password))
        self.repository.save(user)
        return user

# Run: PASSES - Bug fixed

# Step 3: REFACTOR - Add index to database
# Add migration for unique email constraint
```

### TDD for Refactoring

```python
# Step 1: Ensure comprehensive tests exist
def test_order_total_calculation():
    order = Order()
    order.add_item(Item("Laptop", price=1000, quantity=1))
    order.add_item(Item("Mouse", price=25, quantity=2))

    assert order.calculate_total() == 1050

def test_order_total_with_discount():
    order = Order(discount_code="SAVE10")
    order.add_item(Item("Laptop", price=1000, quantity=1))

    assert order.calculate_total() == 900

# Step 2: All tests GREEN

# Step 3: Refactor (e.g., extract calculation logic)
class OrderCalculator:
    def calculate_total(self, items: List[Item], discount_code: str = None) -> float:
        subtotal = sum(item.price * item.quantity for item in items)

        if discount_code:
            discount = self.get_discount(discount_code)
            subtotal -= subtotal * discount

        return subtotal

class Order:
    def __init__(self, discount_code=None):
        self.items = []
        self.discount_code = discount_code
        self.calculator = OrderCalculator()

    def calculate_total(self):
        return self.calculator.calculate_total(self.items, self.discount_code)

# Step 4: Tests still GREEN - refactor successful
```

## Examples by Language

### Python (pytest)

```python
# Step 1: RED
def test_fizzbuzz_returns_number():
    assert fizzbuzz(1) == "1"
    assert fizzbuzz(2) == "2"

# FAILS: fizzbuzz not defined

# Step 2: GREEN
def fizzbuzz(n: int) -> str:
    return str(n)

# PASSES

# Step 3: RED
def test_fizzbuzz_multiples_of_three():
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(6) == "Fizz"

# FAILS

# Step 4: GREEN
def fizzbuzz(n: int) -> str:
    if n % 3 == 0:
        return "Fizz"
    return str(n)

# Step 5: RED
def test_fizzbuzz_multiples_of_five():
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(10) == "Buzz"

# Step 6: GREEN
def fizzbuzz(n: int) -> str:
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)

# Step 7: RED
def test_fizzbuzz_multiples_of_fifteen():
    assert fizzbuzz(15) == "FizzBuzz"
    assert fizzbuzz(30) == "FizzBuzz"

# Step 8: GREEN
def fizzbuzz(n: int) -> str:
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
```

### Rust

```rust
// Step 1: RED
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_vec_sum_is_zero() {
        let result = sum(vec![]);
        assert_eq!(result, 0);
    }
}

// FAILS: sum not defined

// Step 2: GREEN
pub fn sum(numbers: Vec<i32>) -> i32 {
    0
}

// Step 3: RED
#[test]
fn test_single_number() {
    assert_eq!(sum(vec![5]), 5);
}

// Step 4: GREEN
pub fn sum(numbers: Vec<i32>) -> i32 {
    numbers.iter().sum()
}

// PASSES for all tests

// Step 5: REFACTOR (generic version)
pub fn sum<T: std::iter::Sum>(numbers: Vec<T>) -> T {
    numbers.into_iter().sum()
}
```

### Go

```go
// Step 1: RED
func TestReverseString(t *testing.T) {
    result := Reverse("hello")
    expected := "olleh"
    if result != expected {
        t.Errorf("got %s, want %s", result, expected)
    }
}

// FAILS: Reverse not defined

// Step 2: GREEN
func Reverse(s string) string {
    runes := []rune(s)
    for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
        runes[i], runes[j] = runes[j], runes[i]
    }
    return string(runes)
}

// PASSES

// Step 3: RED - Edge cases
func TestReverseEmptyString(t *testing.T) {
    assert.Equal(t, "", Reverse(""))
}

func TestReverseUnicode(t *testing.T) {
    assert.Equal(t, "😀👋", Reverse("👋😀"))
}

// PASSES (already handles these cases)
```

### TypeScript (Vitest)

```typescript
// Step 1: RED
describe('Stack', () => {
  it('starts empty', () => {
    const stack = new Stack<number>();
    expect(stack.isEmpty()).toBe(true);
    expect(stack.size()).toBe(0);
  });
});

// FAILS: Stack doesn't exist

// Step 2: GREEN
class Stack<T> {
  isEmpty() {
    return true;
  }

  size() {
    return 0;
  }
}

// Step 3: RED
it('pushes items', () => {
  const stack = new Stack<number>();
  stack.push(1);
  expect(stack.isEmpty()).toBe(false);
  expect(stack.size()).toBe(1);
});

// Step 4: GREEN
class Stack<T> {
  private items: T[] = [];

  isEmpty() {
    return this.items.length === 0;
  }

  size() {
    return this.items.length;
  }

  push(item: T) {
    this.items.push(item);
  }
}

// Continue: pop, peek, etc.
```

## When to Use TDD

### ✅ GOOD Use Cases

**New features with clear requirements**:
- API endpoints with defined contracts
- Business logic with known rules
- Data transformations with examples

**Bug fixes**:
- Write failing test that reproduces bug
- Fix code until test passes
- Prevents regression

**Complex algorithms**:
- TDD helps break down problem
- Tests document expected behavior
- Safe to refactor later

**Refactoring**:
- Comprehensive tests before refactoring
- Tests stay green during refactor
- Confidence in changes

### ❌ Poor Use Cases

**Exploratory coding**:
- Don't know what you're building yet
- Spike first, TDD later

**UI/UX experimentation**:
- Visual design requires iteration
- E2E tests after design settles

**Prototypes and throwaway code**:
- Not worth the overhead
- TDD when productionizing

**Trivial code**:
- Simple getters/setters
- Boilerplate with no logic

## Checklist

**Before Starting TDD**:
- [ ] Requirements are clear (or will be discovered)
- [ ] You know what "done" looks like
- [ ] Test framework is set up
- [ ] You can run tests quickly (< 1 second)

**During TDD Cycle**:
- [ ] Write smallest possible failing test
- [ ] Run test and see it fail (RED)
- [ ] Write simplest code to pass (GREEN)
- [ ] Run test and see it pass
- [ ] Refactor if needed (tests stay GREEN)
- [ ] Commit (green state only)

**Test Quality**:
- [ ] Tests are readable (describe behavior)
- [ ] Tests are independent (no order dependency)
- [ ] Tests are fast (< 100ms unit tests)
- [ ] One concept per test
- [ ] Descriptive test names

**After TDD Session**:
- [ ] All tests passing
- [ ] Code coverage is high (80%+ for TDD'd code)
- [ ] Code is clean (refactored)
- [ ] Tests document behavior
- [ ] No skipped or ignored tests

## Anti-Patterns

```
❌ NEVER: Write production code before test
   → Defeats purpose of TDD

❌ NEVER: Write all tests upfront
   → Too much investment before feedback

❌ NEVER: Skip refactor step
   → Accumulates technical debt

❌ NEVER: Make big leaps (many changes at once)
   → Hard to debug when test fails

❌ NEVER: Keep tests passing by commenting out assertions
   → False confidence

❌ NEVER: Test implementation details
   → Breaks during refactoring

❌ NEVER: Use TDD for everything
   → Wrong tool for exploratory work
```

## Related Skills

**Foundation**:
- `unit-testing-patterns.md` - How to write good unit tests
- `test-coverage-strategy.md` - What to test and coverage goals

**Advanced**:
- `integration-testing.md` - TDD for integration tests
- `refactoring-patterns.md` - Safe refactoring with tests

**Supporting**:
- `mocking-strategies.md` - Mock dependencies in TDD
- `test-doubles.md` - Stubs, mocks, spies, fakes

**Philosophy**:
- Kent Beck: "Test-Driven Development by Example"
- Uncle Bob: "Clean Code" (TDD chapter)
- Martin Fowler: "Is TDD Dead?" series
