---
name: engineering-test-driven-development
description: Test-Driven Development methodology, red-green-refactor cycle, unit testing best practices, and mocking strategies
---

# Test-Driven Development (TDD)

**Scope**: Comprehensive guide to TDD methodology, red-green-refactor cycle, unit testing, mocking, and test design
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Starting new features or projects from scratch
- Improving test coverage in existing code
- Designing highly testable code
- Establishing testing culture in a team
- Reducing bug rates through disciplined testing
- Clarifying requirements through test cases
- Refactoring with confidence
- Building critical business logic that must be correct

## Core Concepts

### Concept 1: The Red-Green-Refactor Cycle

**The TDD Mantra**: Red → Green → Refactor

```
1. RED: Write a failing test
   ↓
2. GREEN: Write minimal code to make it pass
   ↓
3. REFACTOR: Improve code without changing behavior
   ↓
4. REPEAT
```

**Rules**:
- Don't write production code without a failing test
- Don't write more test than sufficient to fail
- Don't write more production code than sufficient to pass

**Example Cycle**:
```python
# RED: Write failing test
def test_add_two_numbers():
    calculator = Calculator()
    assert calculator.add(2, 3) == 5  # Fails - Calculator doesn't exist

# GREEN: Minimal code to pass
class Calculator:
    def add(self, a, b):
        return 5  # Hardcoded - but test passes!

# RED: Write another test
def test_add_different_numbers():
    calculator = Calculator()
    assert calculator.add(10, 20) == 30  # Fails with hardcoded 5

# GREEN: Real implementation
class Calculator:
    def add(self, a, b):
        return a + b  # Now all tests pass

# REFACTOR: Clean up if needed (none needed here)
```

---

### Concept 2: Test Structure (AAA Pattern)

**Arrange-Act-Assert**:
```python
def test_user_login():
    # Arrange: Set up test data
    user = User(email="test@example.com", password="secret123")
    user.save()

    # Act: Execute the action being tested
    result = authenticate(email="test@example.com", password="secret123")

    # Assert: Verify the result
    assert result.success is True
    assert result.user.email == "test@example.com"
```

**Given-When-Then** (BDD style):
```typescript
describe("User Login", () => {
  it("should authenticate user with correct credentials", () => {
    // Given: A registered user
    const user = createUser({ email: "test@example.com", password: "secret" });

    // When: User attempts to login
    const result = authenticate("test@example.com", "secret");

    // Then: Authentication succeeds
    expect(result.success).toBe(true);
    expect(result.user.email).toBe("test@example.com");
  });
});
```

---

### Concept 3: Test Doubles (Mocks, Stubs, Fakes)

**Stub**: Returns predefined data
```python
class StubEmailService:
    def send(self, to, subject, body):
        return True  # Always succeeds
```

**Mock**: Verifies interactions
```python
mock_email = Mock()
service.send_welcome_email(user)
mock_email.send.assert_called_once_with(
    to="user@example.com",
    subject="Welcome!",
    body="Welcome to our app!"
)
```

**Fake**: Working implementation (simplified)
```python
class FakeDatabase:
    def __init__(self):
        self.data = {}

    def save(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)
```

---

## Patterns

### Pattern 1: Testing Pure Functions (Easiest)

**Pure Function**: Same inputs → Same outputs, no side effects

```python
# RED: Write test first
def test_calculate_tax():
    assert calculate_tax(100, 0.08) == 8.0
    assert calculate_tax(50, 0.10) == 5.0
    assert calculate_tax(0, 0.08) == 0.0

# GREEN: Implement
def calculate_tax(amount: float, rate: float) -> float:
    return amount * rate

# REFACTOR: Add edge case tests
def test_calculate_tax_negative():
    with pytest.raises(ValueError):
        calculate_tax(-100, 0.08)

def calculate_tax(amount: float, rate: float) -> float:
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return amount * rate
```

---

### Pattern 2: Testing with Dependencies (Mocking)

**Before TDD** (hard to test):
```python
class UserService:
    def create_user(self, email):
        db = PostgresDatabase()  # Hard-coded dependency!
        email_service = SendGridEmailService()  # Another one!

        user = db.save({"email": email})
        email_service.send(user.email, "Welcome!")
        return user
```

**TDD Approach** (test first drives design):
```python
# RED: Write test with mocks
def test_create_user():
    mock_db = Mock()
    mock_email = Mock()
    mock_db.save.return_value = User(id=1, email="test@example.com")

    service = UserService(db=mock_db, email_service=mock_email)
    user = service.create_user("test@example.com")

    # Verify interactions
    mock_db.save.assert_called_once_with({"email": "test@example.com"})
    mock_email.send.assert_called_once_with("test@example.com", "Welcome!")
    assert user.email == "test@example.com"

# GREEN: Implement with dependency injection
class UserService:
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service

    def create_user(self, email):
        user = self.db.save({"email": email})
        self.email_service.send(user.email, "Welcome!")
        return user
```

**TDD Forced Good Design**: Dependency injection makes code testable!

---

### Pattern 3: Table-Driven Tests (Go Style)

```go
func TestCalculateDiscount(t *testing.T) {
    tests := []struct {
        name     string
        amount   float64
        userType string
        want     float64
    }{
        {"Premium user, large purchase", 1000, "premium", 200},
        {"Premium user, small purchase", 50, "premium", 5},
        {"Regular user, large purchase", 1000, "regular", 100},
        {"Regular user, small purchase", 50, "regular", 0},
        {"Guest user", 1000, "guest", 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := CalculateDiscount(tt.amount, tt.userType)
            if got != tt.want {
                t.Errorf("CalculateDiscount(%v, %v) = %v, want %v",
                    tt.amount, tt.userType, got, tt.want)
            }
        })
    }
}
```

---

### Pattern 4: Testing Async Code

**Python (async/await)**:
```python
import pytest

@pytest.mark.asyncio
async def test_fetch_user_data():
    # Arrange
    user_id = "123"
    mock_api = AsyncMock()
    mock_api.get_user.return_value = {"id": "123", "name": "John"}

    service = UserService(api=mock_api)

    # Act
    user = await service.fetch_user_data(user_id)

    # Assert
    assert user["name"] == "John"
    mock_api.get_user.assert_called_once_with(user_id)
```

**TypeScript (Promises)**:
```typescript
describe("fetchUserData", () => {
  it("should fetch user from API", async () => {
    // Arrange
    const mockApi = {
      getUser: jest.fn().mockResolvedValue({ id: "123", name: "John" }),
    };
    const service = new UserService(mockApi);

    // Act
    const user = await service.fetchUserData("123");

    // Assert
    expect(user.name).toBe("John");
    expect(mockApi.getUser).toHaveBeenCalledWith("123");
  });
});
```

---

### Pattern 5: Testing Error Conditions

```python
def test_divide_by_zero():
    calculator = Calculator()
    with pytest.raises(ZeroDivisionError):
        calculator.divide(10, 0)

def test_invalid_email():
    with pytest.raises(ValidationError) as exc_info:
        create_user(email="invalid-email")

    assert "Invalid email format" in str(exc_info.value)

def test_user_not_found():
    result = find_user(user_id="nonexistent")
    assert result is None  # Or raises UserNotFoundError
```

---

### Pattern 6: Parameterized Tests

**Python (pytest)**:
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("WORLD", "WORLD"),
    ("TeSt", "TEST"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert uppercase(input) == expected
```

**TypeScript (Jest)**:
```typescript
test.each([
  [1, 1, 2],
  [2, 2, 4],
  [5, 3, 8],
])("add(%i, %i) should return %i", (a, b, expected) => {
  expect(add(a, b)).toBe(expected);
});
```

---

### Pattern 7: Test Fixtures and Setup

**Python (pytest fixtures)**:
```python
@pytest.fixture
def sample_user():
    """Create a test user for multiple tests"""
    return User(email="test@example.com", name="Test User")

@pytest.fixture
def database():
    """Set up and tear down test database"""
    db = create_test_database()
    yield db
    db.drop_all()

def test_save_user(database, sample_user):
    database.save(sample_user)
    assert database.count() == 1

def test_find_user(database, sample_user):
    database.save(sample_user)
    found = database.find_by_email("test@example.com")
    assert found.name == "Test User"
```

**TypeScript (Jest)**:
```typescript
describe("UserService", () => {
  let service: UserService;
  let mockDb: Database;

  beforeEach(() => {
    mockDb = createMockDatabase();
    service = new UserService(mockDb);
  });

  afterEach(() => {
    mockDb.clear();
  });

  it("should save user", () => {
    const user = { email: "test@example.com" };
    service.save(user);
    expect(mockDb.count()).toBe(1);
  });
});
```

---

### Pattern 8: Testing Private Methods (Don't!)

**Bad Approach**:
```python
# DON'T: Testing private methods directly
def test_private_validation():
    obj = MyClass()
    assert obj._validate_input("test") is True  # Testing private method
```

**Good Approach**:
```python
# DO: Test through public interface
def test_public_method_with_valid_input():
    obj = MyClass()
    result = obj.process("test")  # Public method
    assert result.success is True  # Private validation tested indirectly

def test_public_method_with_invalid_input():
    obj = MyClass()
    result = obj.process("")  # Public method
    assert result.success is False  # Private validation tested indirectly
```

**Principle**: Tests should verify behavior, not implementation details

---

## TDD Workflow Examples

### Example 1: Building a String Calculator (Classic Kata)

**Requirement**: Create a calculator that adds numbers in a string

```python
# Iteration 1: Empty string
def test_empty_string_returns_zero():
    assert string_calculator("") == 0

def string_calculator(numbers):
    return 0  # Minimal code to pass

# Iteration 2: Single number
def test_single_number():
    assert string_calculator("5") == 5

def string_calculator(numbers):
    if not numbers:
        return 0
    return int(numbers)

# Iteration 3: Two numbers
def test_two_numbers():
    assert string_calculator("1,2") == 3

def string_calculator(numbers):
    if not numbers:
        return 0
    return sum(int(n) for n in numbers.split(","))

# Iteration 4: Multiple numbers
def test_multiple_numbers():
    assert string_calculator("1,2,3,4") == 10
    # Already passes with current implementation!

# Iteration 5: New line delimiter
def test_newline_delimiter():
    assert string_calculator("1\n2,3") == 6

def string_calculator(numbers):
    if not numbers:
        return 0
    numbers = numbers.replace("\n", ",")
    return sum(int(n) for n in numbers.split(","))

# Iteration 6: Negative numbers throw exception
def test_negative_numbers_throw():
    with pytest.raises(ValueError, match="Negatives not allowed: -2, -5"):
        string_calculator("1,-2,3,-5")

def string_calculator(numbers):
    if not numbers:
        return 0
    numbers = numbers.replace("\n", ",")
    nums = [int(n) for n in numbers.split(",")]

    negatives = [n for n in nums if n < 0]
    if negatives:
        raise ValueError(f"Negatives not allowed: {', '.join(map(str, negatives))}")

    return sum(nums)
```

**TDD Benefits Demonstrated**:
- Requirements clarified through tests
- Code grows organically
- Always working (green) state
- Refactoring is safe

---

### Example 2: TDD for API Endpoints

```python
# RED: Test first
def test_create_user_endpoint(client):
    response = client.post("/users", json={
        "email": "test@example.com",
        "name": "Test User"
    })

    assert response.status_code == 201
    assert response.json["email"] == "test@example.com"
    assert "id" in response.json

# GREEN: Implement minimal endpoint
@app.post("/users")
def create_user(request):
    data = request.json
    user = User(email=data["email"], name=data["name"])
    db.save(user)
    return {"id": user.id, "email": user.email}, 201

# RED: Test validation
def test_create_user_invalid_email(client):
    response = client.post("/users", json={
        "email": "invalid-email",
        "name": "Test"
    })

    assert response.status_code == 400
    assert "Invalid email" in response.json["error"]

# GREEN: Add validation
@app.post("/users")
def create_user(request):
    data = request.json

    if not is_valid_email(data["email"]):
        return {"error": "Invalid email format"}, 400

    user = User(email=data["email"], name=data["name"])
    db.save(user)
    return {"id": user.id, "email": user.email}, 201
```

---

## Best Practices

### TDD Guidelines

**Do's**:
- Write tests first (red → green → refactor)
- Keep tests simple and focused
- Test behavior, not implementation
- Use descriptive test names
- One assertion per test (when practical)
- Run tests frequently (every few minutes)
- Commit after each green state

**Don'ts**:
- Don't skip the refactor step
- Don't test private methods
- Don't write tests after implementation (that's not TDD!)
- Don't make tests depend on each other
- Don't test framework code
- Don't write overly complex test setups

---

### Test Naming Conventions

**Good Test Names**:
```python
def test_add_returns_sum_of_two_numbers()
def test_divide_raises_error_when_divisor_is_zero()
def test_create_user_saves_to_database()
def test_authenticate_fails_with_invalid_password()
```

**Pattern**: `test_[method]_[scenario]_[expected_result]`

---

## Anti-Patterns

### Common TDD Mistakes

```
❌ Writing all tests upfront
→ Write one test at a time, see it fail, make it pass

❌ Testing getters/setters
→ Test actual behavior, not trivial code

❌ Overly complex test setup
→ Simplify with fixtures or factory functions

❌ Tests that depend on each other
→ Each test should be independent

❌ Not seeing tests fail first
→ Always see red before green (ensures test works)

❌ Skipping refactor step
→ Refactor to keep code clean

❌ Testing implementation details
→ Test through public interface

❌ Slow tests
→ Use mocks/stubs for fast unit tests
```

---

## Tools & Frameworks

### Python
```bash
# pytest: Most popular Python test framework
pytest tests/

# Coverage
pytest --cov=src --cov-report=html

# Watch mode (rerun on changes)
pytest-watch

# Mocking
from unittest.mock import Mock, patch
```

### TypeScript/JavaScript
```bash
# Jest: Popular testing framework
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# Mocking
jest.mock('./module')
```

### Go
```bash
# Built-in testing
go test ./...

# Coverage
go test -cover ./...

# Table-driven tests (idiomatic Go)
```

### Test Runners
```bash
# Continuous testing
npm install -g wallaby.js  # IDE integration
npm install -g jest --watch  # CLI watch mode
```

---

## Level 3: Resources

### Comprehensive Reference

**Location**: `skills/engineering/test-driven-development/resources/REFERENCE.md` (~900 lines)

Complete reference covering:
- TDD fundamentals and the three laws
- Red-Green-Refactor cycle in depth
- Test-first development principles
- Unit test design patterns (fixtures, builders, object mothers)
- Test doubles and mocking strategies (dummies, stubs, spies, mocks, fakes)
- Inside-Out vs Outside-In TDD approaches
- ATDD (Acceptance Test-Driven Development)
- BDD (Behavior-Driven Development)
- TDD with different paradigms (OOP, functional, property-based)
- Common TDD mistakes and solutions
- Refactoring safely with tests
- TDD metrics and benefits (coverage, defect density, velocity)
- TDD in different contexts (Web APIs, frontend, databases, CLI tools)
- Advanced TDD techniques (mutation testing, contract testing, characterization tests)
- TDD anti-patterns (Free Ride, The Liar, The Mockery, The Inspector, The Slowpoke)

### Scripts

**Location**: `skills/engineering/test-driven-development/resources/scripts/`

**1. TDD Session Tracker** (`tdd_session.py`)
- Interactive tracker for Red-Green-Refactor cycles
- Times each phase (RED, GREEN, REFACTOR)
- Tracks cycle metrics and session statistics
- Identifies slow phases and suggests improvements
- Exports session data to JSON for analysis
```bash
# Start interactive TDD session
./tdd_session.py start

# Analyze completed session
./tdd_session.py analyze --session-file session.json

# Get session statistics
./tdd_session.py stats --session-file session.json --json
```

**2. TDD Metrics Analyzer** (`analyze_tdd_metrics.py`)
- Calculate test-to-code ratios
- Analyze coverage trends and progression
- Detect test smells and anti-patterns
- Generate TDD health scores (0-100)
- Track metrics across git history
```bash
# Calculate test-to-code ratio
./analyze_tdd_metrics.py ratio --source-dir src/ --test-dir tests/

# Analyze TDD health
./analyze_tdd_metrics.py health --source-dir src/ --test-dir tests/ --coverage-file .coverage

# Track metrics across commits
./analyze_tdd_metrics.py history --repo-dir . --commits 10 --json
```

**3. Test Template Generator** (`generate_test_template.sh`)
- Generate language-specific test templates
- Support for Python (pytest), TypeScript (Jest), Rust, Go
- BDD (Given-When-Then) or AAA (Arrange-Act-Assert) styles
- Includes fixtures, parameterized tests, and best practices
```bash
# Python pytest template
./generate_test_template.sh python Calculator --framework pytest

# TypeScript Jest template with BDD style
./generate_test_template.sh typescript UserService --style bdd

# Rust test template
./generate_test_template.sh rust string_utils

# Go table-driven test template
./generate_test_template.sh go Validator
```

### Examples

**Location**: `skills/engineering/test-driven-development/resources/examples/`

**Python** (`python/tdd_example.py`)
- String Calculator kata showing full TDD progression
- Before/after comparison (implementation-first vs test-first)
- Complete Red-Green-Refactor cycles for each requirement
- Demonstrates incremental development and continuous refactoring
- Test suite evolution from simple to comprehensive

**TypeScript** (`typescript/tdd_example.test.ts`)
- Bowling Game kata in TypeScript with Jest
- Shows TDD rhythm in a stateful object
- Demonstrates test organization with describe blocks
- Helper functions to reduce test duplication
- Complete progression from gutter game to perfect game

**Rust** (`rust/tdd_example.rs`)
- Stack implementation showing TDD with Rust's type system
- Demonstrates Result<T, E> error handling in tests
- Shows how ownership/borrowing influences test design
- Property-based testing examples (with proptest)
- Nested test modules for organization

**Workflow Guide** (`workflows/tdd-workflow.md`)
- Daily TDD workflow (morning routine, core cycle, end of day)
- Project setup for TDD (frameworks, configuration, IDE setup)
- Feature development step-by-step guide
- Debugging workflow when tests fail
- Refactoring workflow with TDD safety net
- Code review checklist for TDD
- Common scenarios (new feature, bug fix, validation, legacy code, external dependencies)

### Usage

**Start a TDD session**:
```bash
cd skills/engineering/test-driven-development/resources
./scripts/tdd_session.py start
```

**Generate test template for new feature**:
```bash
./scripts/generate_test_template.sh python UserAuthentication --framework pytest --style bdd
```

**Check TDD health**:
```bash
./scripts/analyze_tdd_metrics.py health \
  --source-dir ../../../src \
  --test-dir ../../../tests \
  --coverage-file ../../../.coverage
```

**Study examples**:
```bash
# Python example with full TDD progression
cat examples/python/tdd_example.py

# TypeScript kata
cat examples/typescript/tdd_example.test.ts

# Rust with type system
cat examples/rust/tdd_example.rs

# Complete workflow guide
cat examples/workflows/tdd-workflow.md
```

---

## Related Skills

- **engineering-code-review**: Reviewing tests in PRs
- **engineering-refactoring-patterns**: Refactoring with test safety net
- **engineering-code-quality**: Tests improve code quality
- **engineering-continuous-integration**: Automating test execution
- **engineering-design-patterns**: Testing pattern implementations

---

## References

- [Test Driven Development by Kent Beck](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [Growing Object-Oriented Software, Guided by Tests](https://www.amazon.com/Growing-Object-Oriented-Software-Guided-Tests/dp/0321503627)
- [Pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [Go Testing Package](https://pkg.go.dev/testing)
