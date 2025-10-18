---
name: testing-unit-testing-patterns
description: Write isolated tests for individual functions, classes, or modules
---



# Unit Testing Patterns

## When to Use This Skill

Use this skill when you need to:
- Write isolated tests for individual functions, classes, or modules
- Design testable code with proper separation of concerns
- Choose between mocks, stubs, spies, and fakes
- Test asynchronous code (promises, async/await, callbacks)
- Implement parametrized tests for multiple input scenarios
- Structure test suites for maintainability and clarity
- Debug failing unit tests efficiently

**ACTIVATE THIS SKILL**: When writing or reviewing unit tests in any language

## Core Concepts

### The AAA Pattern (Arrange-Act-Assert)

**Arrange**: Set up test data and dependencies
**Act**: Execute the code under test
**Assert**: Verify the expected outcome

```python
# Python (pytest)
def test_calculate_discount():
    # Arrange
    cart = ShoppingCart()
    cart.add_item(Item("Laptop", price=1000))
    discount_service = DiscountService(rate=0.1)

    # Act
    final_price = discount_service.apply_discount(cart)

    # Assert
    assert final_price == 900
```

```typescript
// TypeScript (Vitest)
describe('calculateDiscount', () => {
  it('applies 10% discount correctly', () => {
    // Arrange
    const cart = new ShoppingCart();
    cart.addItem(new Item('Laptop', 1000));
    const discountService = new DiscountService(0.1);

    // Act
    const finalPrice = discountService.applyDiscount(cart);

    // Assert
    expect(finalPrice).toBe(900);
  });
});
```

### Test Doubles: Mocks vs Stubs vs Spies vs Fakes

**Stub**: Provides canned responses to calls
**Mock**: Verifies behavior (calls, arguments, order)
**Spy**: Wraps real object, records interactions
**Fake**: Working implementation (simpler than real)

```python
# Python (unittest.mock)
from unittest.mock import Mock, patch, MagicMock

# STUB: Returns predetermined values
email_service = Mock()
email_service.send_email.return_value = True

# MOCK: Verifies interactions
email_service = Mock()
user_service.register(user, email_service)
email_service.send_email.assert_called_once_with(
    to=user.email,
    subject="Welcome"
)

# SPY: Wraps real object
with patch('requests.get', wraps=requests.get) as spy:
    response = api_client.fetch_user(123)
    spy.assert_called_with('https://api.example.com/users/123')

# FAKE: In-memory implementation
class FakeUserRepository:
    def __init__(self):
        self.users = {}

    def save(self, user):
        self.users[user.id] = user

    def find_by_id(self, user_id):
        return self.users.get(user_id)
```

```typescript
// TypeScript (Vitest)
import { vi } from 'vitest';

// STUB
const emailService = {
  sendEmail: vi.fn().mockResolvedValue(true)
};

// MOCK
const emailService = {
  sendEmail: vi.fn()
};
await userService.register(user, emailService);
expect(emailService.sendEmail).toHaveBeenCalledWith({
  to: user.email,
  subject: 'Welcome'
});

// SPY
const spy = vi.spyOn(apiClient, 'fetchUser');
await service.getUser(123);
expect(spy).toHaveBeenCalledWith(123);
```

### Parametrized Tests

**Run same test with multiple inputs**

```python
# Python (pytest)
import pytest

@pytest.mark.parametrize("input,expected", [
    (0, 0),
    (1, 1),
    (2, 4),
    (3, 9),
    (-2, 4),
])
def test_square(input, expected):
    assert square(input) == expected

@pytest.mark.parametrize("email", [
    "user@example.com",
    "test.user+tag@domain.co.uk",
    "name_123@test-domain.com",
])
def test_valid_emails(email):
    assert is_valid_email(email) is True

@pytest.mark.parametrize("email", [
    "invalid",
    "@example.com",
    "user@",
    "user space@example.com",
])
def test_invalid_emails(email):
    assert is_valid_email(email) is False
```

```rust
// Rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_square() {
        let cases = vec![
            (0, 0),
            (1, 1),
            (2, 4),
            (3, 9),
            (-2, 4),
        ];

        for (input, expected) in cases {
            assert_eq!(square(input), expected);
        }
    }
}
```

```go
// Go (table-driven tests)
func TestSquare(t *testing.T) {
    tests := []struct {
        name     string
        input    int
        expected int
    }{
        {"zero", 0, 0},
        {"positive", 2, 4},
        {"negative", -2, 4},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Square(tt.input)
            if result != tt.expected {
                t.Errorf("got %d, want %d", result, tt.expected)
            }
        })
    }
}
```

## Patterns

### Testing Async Code

```python
# Python (pytest-asyncio)
import pytest

@pytest.mark.asyncio
async def test_fetch_user():
    # Arrange
    user_id = 123
    mock_api = Mock()
    mock_api.get_user = AsyncMock(return_value={"id": 123, "name": "Alice"})

    # Act
    result = await fetch_user(user_id, mock_api)

    # Assert
    assert result["name"] == "Alice"
    mock_api.get_user.assert_awaited_once_with(123)
```

```typescript
// TypeScript (Vitest)
describe('fetchUser', () => {
  it('fetches user data', async () => {
    // Arrange
    const mockApi = {
      getUser: vi.fn().mockResolvedValue({ id: 123, name: 'Alice' })
    };

    // Act
    const result = await fetchUser(123, mockApi);

    // Assert
    expect(result.name).toBe('Alice');
    expect(mockApi.getUser).toHaveBeenCalledWith(123);
  });

  it('handles fetch errors', async () => {
    // Arrange
    const mockApi = {
      getUser: vi.fn().mockRejectedValue(new Error('Network error'))
    };

    // Act & Assert
    await expect(fetchUser(123, mockApi)).rejects.toThrow('Network error');
  });
});
```

### Testing Error Conditions

```python
# Python
import pytest

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_invalid_input_message():
    with pytest.raises(ValueError, match="must be positive"):
        process_age(-5)

def test_error_handling_returns_none():
    result = safe_divide(10, 0)
    assert result is None
```

```typescript
// TypeScript
describe('error handling', () => {
  it('throws on divide by zero', () => {
    expect(() => divide(10, 0)).toThrow('Division by zero');
  });

  it('returns null on invalid input', () => {
    const result = safeDivide(10, 0);
    expect(result).toBeNull();
  });
});
```

### Fixtures and Setup/Teardown

```python
# Python (pytest fixtures)
import pytest

@pytest.fixture
def user():
    """Provides a test user instance"""
    return User(id=1, name="Alice", email="alice@example.com")

@pytest.fixture
def database():
    """Provides an in-memory database"""
    db = Database(":memory:")
    db.migrate()
    yield db
    db.close()

def test_save_user(database, user):
    database.save(user)
    retrieved = database.find_by_id(user.id)
    assert retrieved.name == user.name

# Fixture scope
@pytest.fixture(scope="module")
def expensive_resource():
    """Created once per test module"""
    resource = ExpensiveResource()
    resource.initialize()
    yield resource
    resource.cleanup()
```

```typescript
// TypeScript (Vitest)
import { describe, it, beforeEach, afterEach } from 'vitest';

describe('UserService', () => {
  let database: Database;
  let userService: UserService;

  beforeEach(() => {
    database = new Database(':memory:');
    database.migrate();
    userService = new UserService(database);
  });

  afterEach(() => {
    database.close();
  });

  it('saves user correctly', () => {
    const user = new User(1, 'Alice', 'alice@example.com');
    userService.save(user);
    const retrieved = userService.findById(1);
    expect(retrieved.name).toBe('Alice');
  });
});
```

### Testing Private Methods (Antipattern)

```python
# ❌ WRONG: Testing private methods directly
def test_private_validate_email():
    service = UserService()
    assert service._validate_email("test@example.com") is True

# ✅ CORRECT: Test through public interface
def test_register_user_validates_email():
    service = UserService()
    with pytest.raises(ValueError, match="Invalid email"):
        service.register("Alice", "invalid-email")
```

### Testing State Changes

```python
# Python
def test_cart_state_changes():
    # Arrange
    cart = ShoppingCart()
    item = Item("Laptop", 1000)

    # Act & Assert: Initial state
    assert cart.item_count == 0
    assert cart.total == 0

    # Act & Assert: After adding item
    cart.add_item(item)
    assert cart.item_count == 1
    assert cart.total == 1000

    # Act & Assert: After removing item
    cart.remove_item(item)
    assert cart.item_count == 0
    assert cart.total == 0
```

## Examples by Language

### Python (pytest)

```python
# test_calculator.py
import pytest
from calculator import Calculator

class TestCalculator:
    def test_add(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_subtract(self):
        calc = Calculator()
        assert calc.subtract(5, 3) == 2

    @pytest.mark.parametrize("a,b,expected", [
        (2, 3, 6),
        (5, 4, 20),
        (0, 10, 0),
        (-2, 3, -6),
    ])
    def test_multiply(self, a, b, expected):
        calc = Calculator()
        assert calc.multiply(a, b) == expected

# Run with: pytest test_calculator.py -v
```

### Rust

```rust
// lib.rs
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    #[should_panic(expected = "overflow")]
    fn test_overflow() {
        add(i32::MAX, 1);
    }

    #[test]
    fn test_multiple_cases() {
        let cases = vec![
            (2, 3, 5),
            (0, 0, 0),
            (-1, 1, 0),
        ];

        for (a, b, expected) in cases {
            assert_eq!(add(a, b), expected);
        }
    }
}
```

### Go

```go
// calculator_test.go
package calculator

import "testing"

func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", result)
    }
}

func TestSubtract(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 5, 3, 2},
        {"negative", 3, 5, -2},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Subtract(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("got %d, want %d", result, tt.expected)
            }
        })
    }
}
```

### TypeScript (Vitest)

```typescript
// calculator.test.ts
import { describe, it, expect } from 'vitest';
import { Calculator } from './calculator';

describe('Calculator', () => {
  it('adds two numbers', () => {
    const calc = new Calculator();
    expect(calc.add(2, 3)).toBe(5);
  });

  it.each([
    [2, 3, 6],
    [5, 4, 20],
    [0, 10, 0],
    [-2, 3, -6],
  ])('multiplies %i and %i to get %i', (a, b, expected) => {
    const calc = new Calculator();
    expect(calc.multiply(a, b)).toBe(expected);
  });
});
```

## Checklist

**Before Writing Tests**:
- [ ] Understand what behavior you're testing (not implementation)
- [ ] Identify dependencies to mock/stub
- [ ] Plan test cases (happy path, edge cases, errors)
- [ ] Choose appropriate test double (mock/stub/spy/fake)

**Writing Tests**:
- [ ] Follow AAA pattern (Arrange, Act, Assert)
- [ ] One assertion concept per test
- [ ] Descriptive test names (test_should_X_when_Y)
- [ ] Test behavior, not implementation details
- [ ] Use parametrized tests for multiple inputs
- [ ] Handle async code properly (await, done callbacks)

**Test Quality**:
- [ ] Tests are independent (no shared state)
- [ ] Tests are repeatable (same result every time)
- [ ] Tests are fast (< 100ms for unit tests)
- [ ] Mock external dependencies (DB, API, filesystem)
- [ ] Clear failure messages

**After Writing Tests**:
- [ ] All tests pass
- [ ] Tests fail when code is broken (verify test validity)
- [ ] No flaky tests (intermittent failures)
- [ ] Tests run in CI/CD pipeline

## Anti-Patterns

```
❌ NEVER: Test implementation details
   → Breaks when refactoring internal code

❌ NEVER: Share state between tests
   → Causes flaky tests, order dependencies

❌ NEVER: Test private methods directly
   → Test through public interface instead

❌ NEVER: Multiple unrelated assertions in one test
   → Hard to diagnose failures

❌ NEVER: Use real external services in unit tests
   → Slow, flaky, expensive

❌ NEVER: Ignore test failures
   → Technical debt accumulates

❌ NEVER: Write tests without making them fail first
   → Can't verify test validity
```

## Related Skills

**Foundation**:
- `test-driven-development.md` - TDD workflow and red-green-refactor
- `test-coverage-strategy.md` - What to test and coverage goals

**Integration**:
- `integration-testing.md` - Testing component interactions
- `e2e-testing.md` - Full system testing

**Advanced**:
- `performance-testing.md` - Load and stress testing
- `testing-databases.md` - Database-specific testing patterns

**Language-Specific**:
- Python: pytest, unittest.mock, pytest-asyncio
- TypeScript: Vitest, Jest, Testing Library
- Rust: Built-in test framework, mockall
- Go: testing package, testify, gomock
