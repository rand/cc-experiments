# Test-Driven Development (TDD) - Comprehensive Reference

## Table of Contents
1. [TDD Fundamentals](#tdd-fundamentals)
2. [The Red-Green-Refactor Cycle](#the-red-green-refactor-cycle)
3. [Test-First Development Principles](#test-first-development-principles)
4. [Unit Test Design Patterns](#unit-test-design-patterns)
5. [Test Doubles and Mocking](#test-doubles-and-mocking)
6. [TDD Approaches: Inside-Out vs Outside-In](#tdd-approaches-inside-out-vs-outside-in)
7. [ATDD: Acceptance Test-Driven Development](#atdd-acceptance-test-driven-development)
8. [BDD: Behavior-Driven Development](#bdd-behavior-driven-development)
9. [TDD with Different Paradigms](#tdd-with-different-paradigms)
10. [Common TDD Mistakes and Solutions](#common-tdd-mistakes-and-solutions)
11. [Refactoring Safely with Tests](#refactoring-safely-with-tests)
12. [TDD Metrics and Benefits](#tdd-metrics-and-benefits)
13. [TDD in Different Contexts](#tdd-in-different-contexts)
14. [Advanced TDD Techniques](#advanced-tdd-techniques)
15. [TDD Anti-Patterns](#tdd-anti-patterns)

---

## TDD Fundamentals

### What is Test-Driven Development?

Test-Driven Development (TDD) is a software development methodology where tests are written before the production code. The fundamental principle is simple: write a failing test, make it pass with the simplest code possible, then refactor.

### The Three Laws of TDD (Uncle Bob Martin)

1. **First Law**: You may not write production code until you have written a failing unit test
2. **Second Law**: You may not write more of a unit test than is sufficient to fail (compilation failures are failures)
3. **Third Law**: You may not write more production code than is sufficient to pass the currently failing test

### Core Benefits

**Design Benefits**:
- Forces consideration of API design before implementation
- Encourages modular, loosely coupled code
- Creates testable architectures naturally
- Promotes interface-based design

**Quality Benefits**:
- High test coverage by definition
- Immediate feedback on regressions
- Living documentation through tests
- Confidence in refactoring

**Development Benefits**:
- Shorter debug cycles
- Reduced integration issues
- Clear definition of "done"
- Rhythm and momentum in development

### When to Use TDD

**Best Suited For**:
- Business logic and algorithms
- API design
- Library and framework development
- Complex domain models
- Refactoring legacy code

**Less Suited For** (though still possible):
- UI layout and styling (use visual regression testing)
- Exploratory prototyping (spike first, then TDD)
- Simple CRUD operations (consider cost-benefit)
- Configuration and deployment scripts

---

## The Red-Green-Refactor Cycle

### Phase 1: Red (Write a Failing Test)

**Objective**: Write the smallest test that fails for the right reason.

**Steps**:
1. Think about what you want the code to do
2. Write a test that would pass if the behavior existed
3. Run the test and verify it fails
4. Verify it fails for the expected reason (not syntax error)

**Example** (Python):
```python
def test_calculate_discount_for_premium_customer():
    """Premium customers should receive 20% discount"""
    calculator = PriceCalculator()
    original_price = 100.0

    discounted_price = calculator.calculate_discount(
        price=original_price,
        customer_type="premium"
    )

    assert discounted_price == 80.0
```

**Red Phase Checklist**:
- [ ] Test compiles/parses
- [ ] Test fails for the right reason
- [ ] Test is focused on one behavior
- [ ] Test name describes the behavior
- [ ] Failure message is clear

### Phase 2: Green (Make it Pass)

**Objective**: Write the simplest code to make the test pass.

**Strategies**:
1. **Fake It**: Return a hard-coded value
2. **Obvious Implementation**: If the solution is clear, implement it
3. **Triangulation**: Use multiple tests to force generalization

**Example** (Fake It):
```python
class PriceCalculator:
    def calculate_discount(self, price: float, customer_type: str) -> float:
        return 80.0  # Fake it to make test pass
```

**Example** (Obvious Implementation):
```python
class PriceCalculator:
    def calculate_discount(self, price: float, customer_type: str) -> float:
        if customer_type == "premium":
            return price * 0.8
        return price
```

**Green Phase Checklist**:
- [ ] Test passes
- [ ] Only wrote enough code to pass
- [ ] Didn't add extra features
- [ ] Code is simple (can be ugly)
- [ ] All previous tests still pass

### Phase 3: Refactor (Improve the Design)

**Objective**: Improve code quality while keeping tests green.

**What to Refactor**:
- Remove duplication
- Improve naming
- Extract methods/functions
- Simplify conditionals
- Apply design patterns

**Example** (Before Refactor):
```python
class PriceCalculator:
    def calculate_discount(self, price: float, customer_type: str) -> float:
        if customer_type == "premium":
            return price * 0.8
        elif customer_type == "gold":
            return price * 0.9
        elif customer_type == "silver":
            return price * 0.95
        return price
```

**Example** (After Refactor):
```python
class PriceCalculator:
    DISCOUNT_RATES = {
        "premium": 0.20,
        "gold": 0.10,
        "silver": 0.05,
    }

    def calculate_discount(self, price: float, customer_type: str) -> float:
        discount_rate = self.DISCOUNT_RATES.get(customer_type, 0.0)
        return price * (1 - discount_rate)
```

**Refactor Phase Checklist**:
- [ ] Tests still pass
- [ ] Code is more readable
- [ ] Duplication removed
- [ ] Names are clear
- [ ] Design is cleaner

### Cycle Timing

**Recommended Rhythm**:
- Red phase: 30 seconds - 2 minutes
- Green phase: 1 - 5 minutes
- Refactor phase: 1 - 5 minutes
- Full cycle: 2 - 10 minutes

**If cycles take longer**:
- Tests may be too large
- Steps may be too big
- Problem may need decomposition

---

## Test-First Development Principles

### Start with the Simplest Test

Begin with the easiest, most obvious test case.

**Example**: Testing a sorting function
```python
# Start here (simplest case)
def test_sort_empty_list():
    assert sort([]) == []

# Not here (complex case)
def test_sort_mixed_numbers_with_duplicates():
    assert sort([3, 1, 4, 1, 5, 9, 2, 6]) == [1, 1, 2, 3, 4, 5, 6, 9]
```

### Test Behavior, Not Implementation

Focus on what the code does, not how it does it.

**Bad** (testing implementation):
```python
def test_uses_quicksort_algorithm():
    sorter = Sorter()
    assert sorter.algorithm == "quicksort"
```

**Good** (testing behavior):
```python
def test_sorts_numbers_in_ascending_order():
    result = sort([3, 1, 2])
    assert result == [1, 2, 3]
```

### One Assert Per Test (Generally)

Each test should verify one logical concept.

**Acceptable** (single concept):
```python
def test_valid_email_address():
    validator = EmailValidator()
    assert validator.is_valid("user@example.com") == True
    assert validator.is_valid("invalid.email") == False
```

**Better** (split tests):
```python
def test_accepts_valid_email_address():
    validator = EmailValidator()
    assert validator.is_valid("user@example.com") == True

def test_rejects_invalid_email_address():
    validator = EmailValidator()
    assert validator.is_valid("invalid.email") == False
```

### Test Names Should Describe Behavior

Use descriptive names that explain what should happen.

**Naming Patterns**:
1. **should_ExpectedBehavior_When_StateUnderTest**
   - `should_return_true_when_email_is_valid`
2. **Given_Precondition_When_Action_Then_Outcome**
   - `given_valid_email_when_validated_then_returns_true`
3. **MethodName_Scenario_ExpectedResult**
   - `validate_valid_email_returns_true`

**Example**:
```python
def test_should_apply_premium_discount_when_customer_is_premium():
    pass

def test_should_throw_error_when_price_is_negative():
    pass

def test_should_return_zero_when_cart_is_empty():
    pass
```

### Arrange-Act-Assert Pattern

Structure tests with three clear sections.

```python
def test_calculate_total_with_tax():
    # Arrange: Set up test data and dependencies
    calculator = TaxCalculator(tax_rate=0.1)
    items = [10.0, 20.0, 30.0]

    # Act: Execute the behavior being tested
    total = calculator.calculate_total_with_tax(items)

    # Assert: Verify the outcome
    assert total == 66.0  # (10 + 20 + 30) * 1.1
```

### Incremental Development

Add one test at a time, making each pass before adding the next.

**Example Sequence**:
1. Test: Empty input → Implementation → Refactor
2. Test: Single item → Implementation → Refactor
3. Test: Multiple items → Implementation → Refactor
4. Test: Edge case → Implementation → Refactor

---

## Unit Test Design Patterns

### Test Fixture Pattern

Set up common test data and objects.

**Example** (Python with pytest):
```python
import pytest

@pytest.fixture
def sample_user():
    return User(
        id=1,
        name="John Doe",
        email="john@example.com"
    )

@pytest.fixture
def user_repository():
    return InMemoryUserRepository()

def test_save_user(sample_user, user_repository):
    user_repository.save(sample_user)
    assert user_repository.count() == 1

def test_find_user_by_id(sample_user, user_repository):
    user_repository.save(sample_user)
    found = user_repository.find_by_id(1)
    assert found.name == "John Doe"
```

### Parameterized Tests

Test multiple scenarios with the same structure.

**Example** (Python with pytest):
```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (0, 0),
    (1, 1),
    (2, 4),
    (3, 9),
    (-2, 4),
])
def test_square_function(input, expected):
    assert square(input) == expected
```

**Example** (TypeScript with Jest):
```typescript
describe.each([
    [0, 0],
    [1, 1],
    [2, 4],
    [3, 9],
    [-2, 4],
])('square(%i)', (input, expected) => {
    test(`returns ${expected}`, () => {
        expect(square(input)).toBe(expected);
    });
});
```

### Builder Pattern for Test Data

Create complex test objects with a fluent API.

```python
class UserBuilder:
    def __init__(self):
        self._id = 1
        self._name = "Default User"
        self._email = "user@example.com"
        self._role = "user"

    def with_id(self, id: int):
        self._id = id
        return self

    def with_name(self, name: str):
        self._name = name
        return self

    def with_email(self, email: str):
        self._email = email
        return self

    def with_role(self, role: str):
        self._role = role
        return self

    def build(self):
        return User(self._id, self._name, self._email, self._role)

# Usage in tests
def test_admin_can_delete_users():
    admin = UserBuilder().with_role("admin").build()
    regular_user = UserBuilder().with_id(2).build()

    assert admin.can_delete(regular_user) == True
```

### Object Mother Pattern

Factory methods for common test objects.

```python
class UserMother:
    @staticmethod
    def create_admin():
        return User(id=1, name="Admin", role="admin")

    @staticmethod
    def create_regular_user():
        return User(id=2, name="User", role="user")

    @staticmethod
    def create_premium_customer():
        return User(id=3, name="Premium", role="premium_customer")

def test_admin_privileges():
    admin = UserMother.create_admin()
    assert admin.can_delete_users() == True
```

### Test Spy Pattern

Record calls to verify interactions.

```python
class EmailServiceSpy:
    def __init__(self):
        self.sent_emails = []

    def send(self, to: str, subject: str, body: str):
        self.sent_emails.append({
            'to': to,
            'subject': subject,
            'body': body
        })

def test_sends_welcome_email_on_registration():
    email_service = EmailServiceSpy()
    user_service = UserService(email_service)

    user_service.register("newuser@example.com", "password123")

    assert len(email_service.sent_emails) == 1
    assert email_service.sent_emails[0]['to'] == "newuser@example.com"
    assert email_service.sent_emails[0]['subject'] == "Welcome!"
```

---

## Test Doubles and Mocking

### Types of Test Doubles

**1. Dummy**: Objects passed around but never used
```python
def test_user_repository_count():
    dummy_logger = None  # Never used
    repository = UserRepository(logger=dummy_logger)
    assert repository.count() == 0
```

**2. Stub**: Provides canned answers to calls
```python
class StubPaymentGateway:
    def charge(self, amount: float) -> bool:
        return True  # Always succeeds

def test_order_completion_with_successful_payment():
    gateway = StubPaymentGateway()
    order = Order(payment_gateway=gateway)
    assert order.complete() == True
```

**3. Spy**: Records calls for verification
```python
class SpyEmailService:
    def __init__(self):
        self.send_count = 0
        self.last_recipient = None

    def send(self, to: str, subject: str, body: str):
        self.send_count += 1
        self.last_recipient = to

def test_sends_confirmation_email():
    email_spy = SpyEmailService()
    order_service = OrderService(email_spy)

    order_service.place_order("customer@example.com")

    assert email_spy.send_count == 1
    assert email_spy.last_recipient == "customer@example.com"
```

**4. Mock**: Pre-programmed with expectations
```python
from unittest.mock import Mock

def test_processes_payment_with_correct_amount():
    payment_gateway = Mock()
    order = Order(payment_gateway=payment_gateway, total=100.0)

    order.process_payment()

    payment_gateway.charge.assert_called_once_with(100.0)
```

**5. Fake**: Working implementation with shortcuts
```python
class FakeUserRepository:
    def __init__(self):
        self._users = {}
        self._next_id = 1

    def save(self, user: User):
        if user.id is None:
            user.id = self._next_id
            self._next_id += 1
        self._users[user.id] = user

    def find_by_id(self, id: int) -> User:
        return self._users.get(id)

def test_user_service_creates_user():
    repository = FakeUserRepository()
    service = UserService(repository)

    user = service.create_user("John Doe")

    assert user.id is not None
    assert repository.find_by_id(user.id).name == "John Doe"
```

### Mocking Best Practices

**1. Don't Mock What You Don't Own**

Avoid mocking third-party libraries directly.

**Bad**:
```python
def test_fetches_user_data():
    mock_requests = Mock()
    mock_requests.get.return_value.json.return_value = {"name": "John"}
    # Testing requests library, not your code
```

**Good**:
```python
class HttpClient:
    def get_json(self, url: str) -> dict:
        return requests.get(url).json()

class FakeHttpClient:
    def get_json(self, url: str) -> dict:
        return {"name": "John"}

def test_fetches_user_data():
    client = FakeHttpClient()
    service = UserService(client)
    user = service.fetch_user(1)
    assert user.name == "John"
```

**2. Verify Behavior, Not Implementation**

Mock at the boundary, not internal details.

**Bad**:
```python
def test_order_processing():
    inventory = Mock()
    inventory.check_stock.return_value = True
    inventory.reserve_items.return_value = True
    # Too many implementation details
```

**Good**:
```python
def test_order_processing():
    inventory = FakeInventory(stock={"item1": 10})
    order = Order(inventory, items={"item1": 1})
    assert order.process() == True
```

**3. Keep Mocks Simple**

Complex mocks indicate design problems.

**Smell**:
```python
mock_service = Mock()
mock_service.method1.return_value.method2.return_value.method3.return_value = "result"
# Law of Demeter violation
```

**Better**: Redesign to reduce coupling

---

## TDD Approaches: Inside-Out vs Outside-In

### Inside-Out (Classic TDD)

Start with low-level components and build up.

**Characteristics**:
- Bottom-up approach
- Start with domain logic
- Focus on unit tests
- Discover high-level design
- More refactoring at integration

**Example Workflow**:
1. Test and implement `Customer` class
2. Test and implement `Order` class
3. Test and implement `OrderService`
4. Test integration between components

**Advantages**:
- Simple to start
- Fast feedback
- Good for known domains
- Strong unit test coverage

**Disadvantages**:
- May build unnecessary components
- Integration issues discovered late
- API may not fit actual needs

### Outside-In (London School TDD)

Start with high-level behavior and work down.

**Characteristics**:
- Top-down approach
- Start with acceptance tests
- Heavy use of mocks
- Discover interfaces through use
- Design emerges from needs

**Example Workflow**:
1. Write acceptance test for order placement
2. Discover need for `OrderService` (mock it)
3. Test and implement `OrderService`
4. Discover need for `PaymentGateway` (mock it)
5. Test and implement `PaymentGateway`

**Example** (Outside-In):
```python
# Step 1: Acceptance test (outside)
def test_customer_can_place_order():
    app = Application()
    order_id = app.place_order(
        customer_id=1,
        items=[{"sku": "ABC", "quantity": 2}]
    )
    assert order_id is not None
    order = app.get_order(order_id)
    assert order.status == "confirmed"

# Step 2: Discover OrderService (mock it)
def test_application_uses_order_service():
    order_service = Mock()
    order_service.place_order.return_value = 123
    app = Application(order_service=order_service)

    order_id = app.place_order(1, [{"sku": "ABC", "quantity": 2}])

    assert order_id == 123

# Step 3: Test OrderService
def test_order_service_creates_order():
    repository = Mock()
    service = OrderService(repository)

    order = service.place_order(1, [{"sku": "ABC", "quantity": 2}])

    repository.save.assert_called_once()
```

**Advantages**:
- Build only what's needed
- API designed for actual use
- Early integration validation
- Clear acceptance criteria

**Disadvantages**:
- More mocking complexity
- Tests coupled to design
- Harder to refactor
- Learning curve

### Choosing an Approach

**Use Inside-Out when**:
- Domain is well understood
- Building reusable libraries
- Team is new to TDD
- Working with algorithms

**Use Outside-In when**:
- Requirements are unclear
- Building user-facing features
- Need to discover API design
- Working on new projects

**Hybrid Approach**:
Many teams combine both:
1. Start outside-in for features
2. Use inside-out for algorithms
3. Minimize mocking
4. Use integration tests at boundaries

---

## ATDD: Acceptance Test-Driven Development

### What is ATDD?

ATDD extends TDD to include customer-level acceptance tests written before implementation.

**Flow**:
```
User Story → Acceptance Tests → Unit Tests → Implementation
```

### ATDD Process

**Step 1: Define Acceptance Criteria**
```gherkin
Feature: Shopping Cart Checkout
  As a customer
  I want to checkout my shopping cart
  So that I can complete my purchase

Scenario: Successful checkout with valid payment
  Given I have items in my cart totaling $100
  And I have a valid credit card
  When I proceed to checkout
  Then I should see an order confirmation
  And my cart should be empty
  And I should be charged $100
```

**Step 2: Write Automated Acceptance Test**
```python
def test_successful_checkout_with_valid_payment():
    # Given
    app = Application()
    customer = app.register_customer("john@example.com")
    app.add_to_cart(customer.id, item="widget", price=100.0)

    # When
    result = app.checkout(
        customer_id=customer.id,
        payment_method="credit_card",
        card_number="4111111111111111"
    )

    # Then
    assert result.success == True
    assert result.order_id is not None
    assert app.get_cart(customer.id).is_empty() == True
    assert result.amount_charged == 100.0
```

**Step 3: TDD Implementation**

Use TDD to build components needed for acceptance test.

### Given-When-Then Structure

**Pattern**:
- **Given**: Preconditions and state setup
- **When**: Action or event
- **Then**: Expected outcome

**Example**:
```python
def test_discount_applied_for_bulk_orders():
    # Given a customer with a cart containing 100 items
    cart = Cart()
    cart.add_items("widget", quantity=100)

    # When calculating the total
    total = cart.calculate_total()

    # Then a 10% bulk discount should be applied
    expected = 100 * 10.0 * 0.9  # 10% off
    assert total == expected
```

### ATDD with BDD Tools

**Cucumber (Gherkin syntax)**:
```gherkin
Feature: User Authentication

Scenario: User logs in with valid credentials
  Given a user exists with email "user@example.com" and password "secret123"
  When the user attempts to login with email "user@example.com" and password "secret123"
  Then the user should be logged in
  And the user should see their dashboard
```

**Step Definitions** (Python with behave):
```python
from behave import given, when, then

@given('a user exists with email "{email}" and password "{password}"')
def step_impl(context, email, password):
    context.user = User.create(email=email, password=password)
    context.user_repository.save(context.user)

@when('the user attempts to login with email "{email}" and password "{password}"')
def step_impl(context, email, password):
    context.auth_result = context.auth_service.login(email, password)

@then('the user should be logged in')
def step_impl(context):
    assert context.auth_result.success == True
```

---

## BDD: Behavior-Driven Development

### BDD Principles

BDD is TDD with a focus on behavior described in business language.

**Key Concepts**:
1. Use ubiquitous language (domain terms)
2. Focus on behavior, not tests
3. Executable specifications
4. Collaboration between technical and non-technical

### BDD Layers

**Layer 1: Specifications** (Gherkin)
```gherkin
Feature: Account Balance Management

Scenario: Withdrawing money reduces balance
  Given an account with balance $100
  When I withdraw $30
  Then the account balance should be $70
```

**Layer 2: Step Definitions** (Glue code)
```python
@given('an account with balance ${amount:d}')
def create_account_with_balance(context, amount):
    context.account = Account(balance=amount)

@when('I withdraw ${amount:d}')
def withdraw_from_account(context, amount):
    context.account.withdraw(amount)

@then('the account balance should be ${expected:d}')
def verify_balance(context, expected):
    assert context.account.balance == expected
```

**Layer 3: Implementation** (TDD)
```python
def test_withdraw_reduces_balance():
    account = Account(balance=100)
    account.withdraw(30)
    assert account.balance == 70

class Account:
    def __init__(self, balance: float):
        self.balance = balance

    def withdraw(self, amount: float):
        self.balance -= amount
```

### BDD Best Practices

**1. Keep Scenarios Declarative**

**Bad** (imperative):
```gherkin
Given I navigate to the login page
And I enter "user@example.com" in the email field
And I enter "password123" in the password field
And I click the "Login" button
Then I should see "Welcome"
```

**Good** (declarative):
```gherkin
Given I am not logged in
When I login as "user@example.com"
Then I should be on my dashboard
```

**2. One Scenario, One Behavior**

Each scenario should test one specific behavior.

**3. Use Scenario Outlines for Similar Cases**

```gherkin
Scenario Outline: Password validation
  Given a user enters password "<password>"
  When the password is validated
  Then it should be "<result>"

Examples:
  | password | result  |
  | short    | invalid |
  | medium123| valid   |
  | long1234!| valid   |
```

---

## TDD with Different Paradigms

### TDD with Object-Oriented Programming

**Focus**: Class responsibilities and collaborations

**Example**:
```python
# Test
def test_order_calculates_total():
    order = Order()
    order.add_item(Item("Widget", price=10.0))
    order.add_item(Item("Gadget", price=20.0))
    assert order.total() == 30.0

# Implementation
class Order:
    def __init__(self):
        self._items = []

    def add_item(self, item: Item):
        self._items.append(item)

    def total(self) -> float:
        return sum(item.price for item in self._items)

class Item:
    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price
```

### TDD with Functional Programming

**Focus**: Pure functions and transformations

**Example** (Python functional style):
```python
# Test
def test_calculate_total_from_items():
    items = [
        {"name": "Widget", "price": 10.0},
        {"name": "Gadget", "price": 20.0},
    ]
    assert calculate_total(items) == 30.0

# Implementation
def calculate_total(items: list[dict]) -> float:
    return sum(item["price"] for item in items)

# Test composition
def test_calculate_total_with_discount():
    items = [{"name": "Widget", "price": 100.0}]
    discounted = apply_discount(items, 0.1)
    assert calculate_total(discounted) == 90.0

# Implementation
def apply_discount(items: list[dict], rate: float) -> list[dict]:
    return [
        {**item, "price": item["price"] * (1 - rate)}
        for item in items
    ]
```

### TDD with Property-Based Testing

**Focus**: Properties that should hold for all inputs

**Example** (using Hypothesis):
```python
from hypothesis import given, strategies as st

# Property: Reversing a list twice returns original
@given(st.lists(st.integers()))
def test_reverse_twice_returns_original(xs):
    assert reverse(reverse(xs)) == xs

# Property: Sorting is idempotent
@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs):
    assert sort(sort(xs)) == sort(xs)

# Property: Adding item increases length
@given(st.lists(st.integers()), st.integers())
def test_adding_item_increases_length(xs, x):
    original_length = len(xs)
    xs.append(x)
    assert len(xs) == original_length + 1
```

---

## Common TDD Mistakes and Solutions

### Mistake 1: Writing Tests After Code

**Problem**: Defeats the purpose of TDD, reduces design benefits.

**Solution**: Discipline. Write test first, always.

### Mistake 2: Tests Too Large

**Problem**:
```python
def test_entire_user_registration_flow():
    # Tests validation, database, email, logging, etc.
    # 200 lines of test code
    pass
```

**Solution**: Break into focused tests:
```python
def test_validates_email_format():
    pass

def test_saves_user_to_database():
    pass

def test_sends_welcome_email():
    pass
```

### Mistake 3: Testing Implementation Details

**Problem**:
```python
def test_uses_bubble_sort():
    sorter = Sorter()
    assert sorter.algorithm == "bubble_sort"
```

**Solution**: Test behavior:
```python
def test_sorts_numbers_ascending():
    result = sort([3, 1, 2])
    assert result == [1, 2, 3]
```

### Mistake 4: Too Many Mocks

**Problem**:
```python
def test_order_processing():
    mock_inventory = Mock()
    mock_payment = Mock()
    mock_shipping = Mock()
    mock_notification = Mock()
    mock_logging = Mock()
    # Test becomes fragile and coupled
```

**Solution**: Use fakes or integration tests:
```python
def test_order_processing():
    app = TestApplication()  # Real components with fake I/O
    order_id = app.place_order(customer_id=1, items=[...])
    assert app.get_order(order_id).status == "confirmed"
```

### Mistake 5: Not Running Tests Frequently

**Problem**: Long feedback loops, hard to identify breaking changes.

**Solution**: Run tests after every change, use watch mode:
```bash
pytest --watch
npm test -- --watch
cargo watch -x test
```

### Mistake 6: Ignoring Failing Tests

**Problem**: "It's a flaky test, ignore it."

**Solution**: Fix or delete:
- If test is valuable but flaky, fix it
- If test is not valuable, delete it
- Never ignore failures

### Mistake 7: Not Refactoring

**Problem**: Tests pass but code is ugly and duplicated.

**Solution**: Refactor is part of the cycle. Always clean up.

---

## Refactoring Safely with Tests

### Refactoring Patterns with TDD

**Pattern 1: Extract Method**

Before:
```python
def test_calculate_total():
    order = Order()
    order.items = [
        {"price": 10, "quantity": 2},
        {"price": 20, "quantity": 1},
    ]
    total = 0
    for item in order.items:
        total += item["price"] * item["quantity"]
    assert total == 40

class Order:
    def __init__(self):
        self.items = []
```

After Refactor (tests still pass):
```python
def test_calculate_total():
    order = Order()
    order.add_item(price=10, quantity=2)
    order.add_item(price=20, quantity=1)
    assert order.total() == 40

class Order:
    def __init__(self):
        self.items = []

    def add_item(self, price: float, quantity: int):
        self.items.append({"price": price, "quantity": quantity})

    def total(self) -> float:
        return sum(
            item["price"] * item["quantity"]
            for item in self.items
        )
```

**Pattern 2: Replace Conditional with Polymorphism**

Before:
```python
def test_discount_calculation():
    assert calculate_discount("regular", 100) == 0
    assert calculate_discount("premium", 100) == 10
    assert calculate_discount("vip", 100) == 20

def calculate_discount(customer_type: str, amount: float) -> float:
    if customer_type == "regular":
        return 0
    elif customer_type == "premium":
        return amount * 0.1
    elif customer_type == "vip":
        return amount * 0.2
```

After Refactor:
```python
def test_discount_calculation():
    assert RegularCustomer().calculate_discount(100) == 0
    assert PremiumCustomer().calculate_discount(100) == 10
    assert VIPCustomer().calculate_discount(100) == 20

class Customer:
    def calculate_discount(self, amount: float) -> float:
        raise NotImplementedError

class RegularCustomer(Customer):
    def calculate_discount(self, amount: float) -> float:
        return 0

class PremiumCustomer(Customer):
    def calculate_discount(self, amount: float) -> float:
        return amount * 0.1

class VIPCustomer(Customer):
    def calculate_discount(self, amount: float) -> float:
        return amount * 0.2
```

### Refactoring Workflow

1. **Ensure tests are green**
2. **Make a small refactoring change**
3. **Run tests immediately**
4. **If red, undo and try smaller step**
5. **If green, continue or commit**

### Test-Driven Refactoring

When refactoring reveals missing tests:

**Step 1: Identify missing test**
```python
# Refactoring reveals edge case
def calculate_price(quantity: int, unit_price: float) -> float:
    if quantity <= 0:  # Wait, is this tested?
        raise ValueError("Quantity must be positive")
    return quantity * unit_price
```

**Step 2: Add test**
```python
def test_negative_quantity_raises_error():
    with pytest.raises(ValueError):
        calculate_price(-1, 10.0)
```

**Step 3: Continue refactoring**

---

## TDD Metrics and Benefits

### Code Coverage

**What to Measure**:
- Line coverage: % of lines executed
- Branch coverage: % of decision branches taken
- Path coverage: % of execution paths tested

**Tools**:
```bash
# Python
pytest --cov=myapp --cov-report=html

# JavaScript
npm test -- --coverage

# Rust
cargo tarpaulin --out Html
```

**Targets**:
- Critical path: 90%+
- Business logic: 80%+
- UI layer: 60%+
- Overall: 70%+

**Warning**: 100% coverage doesn't mean bug-free. Quality > quantity.

### Defect Density

Track bugs found per KLOC (thousand lines of code).

**Expected with TDD**:
- Pre-TDD: 10-50 bugs/KLOC
- With TDD: 1-5 bugs/KLOC

### Development Velocity

**Initial Slowdown**:
- First 1-2 sprints: 20-30% slower
- Learning curve for TDD

**Long-term Speedup**:
- After 3-4 sprints: Same or faster velocity
- Fewer bugs = less rework
- Confident refactoring

### Design Metrics

**Coupling**: TDD reduces coupling
- Testable code requires loose coupling
- Mock points become interfaces

**Cohesion**: TDD increases cohesion
- Focused tests → focused classes
- Single Responsibility Principle emerges

### Time Metrics

**Cycle Time**:
- Time from commit to production
- TDD reduces by catching bugs early

**Debug Time**:
- Time spent debugging
- TDD reduces by 40-90%

### Quality Metrics

**Regression Rate**:
- % of bugs that are regressions
- TDD dramatically reduces

**Defect Escape Rate**:
- % of bugs found in production
- TDD catches more pre-release

---

## TDD in Different Contexts

### TDD for Web APIs

**Example** (FastAPI with TDD):
```python
# Test
def test_create_user():
    client = TestClient(app)
    response = client.post("/users", json={
        "email": "user@example.com",
        "name": "John Doe"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"

def test_get_user():
    client = TestClient(app)
    # Create user first
    create_response = client.post("/users", json={
        "email": "user@example.com",
        "name": "John Doe"
    })
    user_id = create_response.json()["id"]

    # Get user
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "John Doe"

# Implementation
from fastapi import FastAPI

app = FastAPI()

@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    user_id = db.save_user(user)
    return {"id": user_id, **user.dict()}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = db.get_user(user_id)
    return user
```

### TDD for Frontend/React

**Example** (React with Testing Library):
```typescript
// Test
import { render, screen, fireEvent } from '@testing-library/react';
import Counter from './Counter';

test('increments counter on button click', () => {
  render(<Counter />);

  const button = screen.getByRole('button', { name: /increment/i });
  const count = screen.getByText(/count: 0/i);

  fireEvent.click(button);

  expect(screen.getByText(/count: 1/i)).toBeInTheDocument();
});

// Implementation
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}

export default Counter;
```

### TDD for Databases

**Example** (Repository pattern with TDD):
```python
# Test
def test_save_and_retrieve_user():
    db = TestDatabase()
    repository = UserRepository(db)

    user = User(name="John", email="john@example.com")
    user_id = repository.save(user)

    retrieved = repository.find_by_id(user_id)
    assert retrieved.name == "John"
    assert retrieved.email == "john@example.com"

def test_find_by_email():
    db = TestDatabase()
    repository = UserRepository(db)

    user = User(name="John", email="john@example.com")
    repository.save(user)

    found = repository.find_by_email("john@example.com")
    assert found.name == "John"

# Implementation
class UserRepository:
    def __init__(self, db):
        self.db = db

    def save(self, user: User) -> int:
        return self.db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            user.name, user.email
        ).last_insert_id

    def find_by_id(self, id: int) -> User:
        row = self.db.query_one(
            "SELECT * FROM users WHERE id = ?", id
        )
        return User(id=row.id, name=row.name, email=row.email)

    def find_by_email(self, email: str) -> User:
        row = self.db.query_one(
            "SELECT * FROM users WHERE email = ?", email
        )
        return User(id=row.id, name=row.name, email=row.email)
```

### TDD for CLI Tools

**Example** (Click CLI with TDD):
```python
# Test
from click.testing import CliRunner
from myapp.cli import greet

def test_greet_with_name():
    runner = CliRunner()
    result = runner.invoke(greet, ['--name', 'John'])

    assert result.exit_code == 0
    assert 'Hello, John!' in result.output

def test_greet_without_name_uses_default():
    runner = CliRunner()
    result = runner.invoke(greet, [])

    assert result.exit_code == 0
    assert 'Hello, World!' in result.output

# Implementation
import click

@click.command()
@click.option('--name', default='World', help='Name to greet')
def greet(name):
    click.echo(f'Hello, {name}!')
```

---

## Advanced TDD Techniques

### Mutation Testing

Test your tests by introducing bugs.

**Tool**: mutmut (Python)
```bash
pip install mutmut
mutmut run
mutmut results
```

**Example**:
```python
# Original code
def is_adult(age: int) -> bool:
    return age >= 18

# Mutant 1: >= becomes >
def is_adult(age: int) -> bool:
    return age > 18  # Should be caught by test_is_adult_at_18

# Test
def test_is_adult_at_18():
    assert is_adult(18) == True  # Catches mutant 1
```

### Contract Testing

Test boundaries between services.

**Example** (Pact):
```python
# Consumer test
def test_get_user_from_provider():
    pact.given("user 123 exists") \
        .upon_receiving("a request for user 123") \
        .with_request(method="GET", path="/users/123") \
        .will_respond_with(status=200, body={"id": 123, "name": "John"})

    with pact:
        client = UserClient("http://localhost:1234")
        user = client.get_user(123)
        assert user.name == "John"

# Provider test
def test_honors_consumer_contract():
    pact.verify("UserProvider", "UserConsumer")
```

### Approval Testing (Golden Master)

Test against approved output.

**Example**:
```python
from approvaltests import verify

def test_generate_report():
    data = get_sample_data()
    report = generate_report(data)
    verify(report)  # Compares to approved file
```

### TDD for Legacy Code (Characterization Tests)

**Process**:
1. Write test that captures current behavior
2. Refactor with tests as safety net
3. Improve tests as you understand code

**Example**:
```python
# Legacy code (don't understand it yet)
def mystery_function(x, y, z):
    # Complex logic
    return result

# Characterization test
def test_mystery_function_behavior():
    # Document what it currently does
    assert mystery_function(1, 2, 3) == 42
    assert mystery_function(0, 0, 0) == 0
    assert mystery_function(-1, 5, 2) == 17
    # Now safe to refactor
```

---

## TDD Anti-Patterns

### The Free Ride

**Problem**: Asserting too much in one test
```python
def test_user_registration():
    user = register_user("john@example.com", "password")
    assert user.email == "john@example.com"  # Testing this
    assert user.is_active == True  # Free riding
    assert user.created_at is not None  # Free riding
```

**Solution**: Separate tests for separate concerns

### The Liar

**Problem**: Test passes but doesn't actually test behavior
```python
def test_sends_email():
    service = EmailService()
    service.send("user@example.com", "Subject", "Body")
    # No assertion! Test always passes
```

**Solution**: Always assert something

### The Mockery

**Problem**: Over-mocking leads to testing mocks, not code
```python
def test_process_order():
    inventory = Mock()
    payment = Mock()
    shipping = Mock()
    inventory.check.return_value = True
    payment.charge.return_value = True
    shipping.ship.return_value = True
    # Testing mocks, not real behavior
```

**Solution**: Use fakes or integration tests

### The Inspector

**Problem**: Testing internal state instead of behavior
```python
def test_cache_size():
    cache = Cache()
    cache.put("key", "value")
    assert len(cache._internal_dict) == 1  # Don't inspect internals
```

**Solution**: Test through public API only

### The Slowpoke

**Problem**: Tests take too long to run
```python
def test_slow_operation():
    time.sleep(5)  # Simulating slow operation
    # Tests should be fast
```

**Solution**: Mock slow dependencies, use test doubles

---

## Conclusion

Test-Driven Development is a discipline that requires practice but offers substantial benefits:

1. **Design**: Better APIs, loose coupling, clear responsibilities
2. **Quality**: Fewer bugs, regression safety, living documentation
3. **Confidence**: Refactor fearlessly, deploy safely, change quickly
4. **Rhythm**: Short feedback loops, clear progress, sustainable pace

**Key Principles**:
- Write test first, always
- Keep tests small and focused
- Refactor continuously
- Run tests frequently
- Test behavior, not implementation

**Remember**:
- TDD is a design technique, not just testing
- The three laws are non-negotiable
- Red-Green-Refactor is the heartbeat
- Tests are first-class code
- Practice makes perfect

**Start Simple**:
- Begin with one function
- Master the cycle
- Build the habit
- Expand gradually

The investment in learning TDD pays dividends throughout your career. Start small, practice consistently, and watch your design skills grow.
