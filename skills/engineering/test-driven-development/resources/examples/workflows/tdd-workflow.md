# TDD Workflow: Step-by-Step Guide

Complete guide to practicing Test-Driven Development from project setup through delivery. Follow this workflow for consistent, high-quality TDD practice.

## Table of Contents

1. [Daily TDD Workflow](#daily-tdd-workflow)
2. [Project Setup](#project-setup)
3. [Feature Development](#feature-development)
4. [Debugging Workflow](#debugging-workflow)
5. [Refactoring Workflow](#refactoring-workflow)
6. [Code Review Checklist](#code-review-checklist)
7. [Common Scenarios](#common-scenarios)

---

## Daily TDD Workflow

### Morning Routine

```bash
# 1. Pull latest changes
git pull origin main

# 2. Run full test suite to verify clean slate
npm test  # or pytest, cargo test, go test, etc.

# 3. Review your task board
bd ready --json --limit 5  # If using Beads

# 4. Pick ONE small task to start
# Remember: Small steps, tight feedback loops
```

### During Development

**The Core Cycle** (repeat every 5-10 minutes):

```
┌─────────────────┐
│   1. RED        │  Write failing test (30 sec - 2 min)
│   Write Test    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   2. GREEN      │  Make test pass (1 - 5 min)
│   Implement     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   3. REFACTOR   │  Improve design (1 - 5 min)
│   Clean Code    │
└────────┬────────┘
         │
         ▼
    (Commit)
         │
         └──────> Next Test
```

### End of Day

```bash
# 1. Ensure all tests pass
npm test

# 2. Commit any work in progress
git add .
git commit -m "WIP: Feature X progress"

# 3. Push to remote (if on feature branch)
git push origin feature/your-feature

# 4. Update task tracking
bd export -o .beads/issues.jsonl

# 5. Quick reflection
# - How many cycles completed?
# - What went well?
# - What to improve tomorrow?
```

---

## Project Setup

### Initial Setup for TDD

**1. Choose Testing Framework**

```bash
# Python
pip install pytest pytest-cov pytest-watch
# or with uv:
uv add --dev pytest pytest-cov pytest-watch

# TypeScript/JavaScript
npm install --save-dev jest @types/jest ts-jest
# or
npm install --save-dev vitest

# Rust
# Already included in cargo

# Go
# Already included in go toolchain
```

**2. Configure Test Runner**

Python (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src --cov-report=html --cov-report=term"
```

TypeScript (`jest.config.js`):
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  collectCoverageFrom: ['src/**/*.ts'],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  }
};
```

**3. Set Up Watch Mode**

```bash
# Python
pytest-watch

# JavaScript/TypeScript
npm test -- --watch

# Rust
cargo watch -x test

# Go
# Use tools like gotest or create a watch script
```

**4. Configure IDE for TDD**

VS Code (`settings.json`):
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "jest.autoRun": "watch"
}
```

**5. Create Project Structure**

```
project/
├── src/               # Production code
│   ├── module1/
│   └── module2/
├── tests/             # Test code
│   ├── test_module1.py
│   └── test_module2.py
├── README.md
├── pyproject.toml     # or package.json, Cargo.toml, etc.
└── .gitignore
```

---

## Feature Development

### Step-by-Step Feature Development with TDD

**Example**: Adding user authentication to an API

#### Phase 1: Plan the Feature

```markdown
Feature: User Authentication

Requirements:
- User can register with email and password
- User can login with credentials
- Password must be hashed
- Invalid credentials return error
- Login returns JWT token

Break down into small tests:
1. ✓ User can be created with email
2. ✓ Password is hashed on creation
3. ✓ User can authenticate with valid credentials
4. ✓ Authentication fails with invalid password
5. ✓ Authentication returns JWT token
```

#### Phase 2: First Test (User Creation)

**RED - Write failing test**:

```python
# tests/test_user.py
def test_user_can_be_created_with_email():
    """Given an email, when creating user, then user has that email"""
    # Arrange
    email = "user@example.com"

    # Act
    user = User.create(email=email, password="secret123")

    # Assert
    assert user.email == email
```

**Run test** (should fail - User doesn't exist):
```bash
pytest tests/test_user.py::test_user_can_be_created_with_email
```

**GREEN - Minimal implementation**:

```python
# src/user.py
class User:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    @classmethod
    def create(cls, email: str, password: str):
        return cls(email, password)
```

**Run test** (should pass):
```bash
pytest tests/test_user.py::test_user_can_be_created_with_email
```

**REFACTOR** (if needed):
- Code is simple, no refactoring needed yet

**COMMIT**:
```bash
git add .
git commit -m "feat: Add User.create method with email"
```

#### Phase 3: Second Test (Password Hashing)

**RED**:

```python
def test_password_is_hashed_on_creation():
    """Given a password, when creating user, then password is hashed"""
    # Arrange
    plain_password = "secret123"

    # Act
    user = User.create(email="user@example.com", password=plain_password)

    # Assert
    assert user.password != plain_password
    assert user.password.startswith("$2b$")  # bcrypt hash prefix
```

**GREEN**:

```python
import bcrypt

class User:
    def __init__(self, email: str, password_hash: str):
        self.email = email
        self.password = password_hash

    @classmethod
    def create(cls, email: str, password: str):
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        return cls(email, password_hash)
```

**REFACTOR**:

```python
class User:
    def __init__(self, email: str, password_hash: str):
        self.email = email
        self._password_hash = password_hash

    @classmethod
    def create(cls, email: str, password: str):
        password_hash = cls._hash_password(password)
        return cls(email, password_hash)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
```

**COMMIT**:
```bash
git add .
git commit -m "feat: Hash user passwords with bcrypt"
```

#### Phase 4: Continue with Remaining Tests

Follow the same pattern for each requirement:
1. Write failing test (RED)
2. Make it pass (GREEN)
3. Refactor
4. Commit
5. Next test

---

## Debugging Workflow

### When a Test Fails

**DON'T**:
- ❌ Immediately jump to fixing code
- ❌ Change test to make it pass
- ❌ Add debugging prints everywhere

**DO**:

**1. Understand the Failure**

```bash
# Run with verbose output
pytest -v tests/test_user.py::test_authentication

# Look at the assertion error
# Expected: True
# Actual: False
```

**2. Verify Test is Correct**

Ask yourself:
- Is this test testing the right thing?
- Is the expected value correct?
- Are the test inputs valid?

**3. Isolate the Problem**

```python
# Add a debugging test
def test_debug_authentication():
    user = User.create("test@example.com", "password123")
    print(f"User password hash: {user._password_hash}")

    result = user.authenticate("password123")
    print(f"Authentication result: {result}")

    # Manually verify each step
    assert user._password_hash is not None
    assert result is True
```

**4. Use Debugger**

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use IDE debugger
# Set breakpoint and run in debug mode
```

**5. Fix Smallest Thing**

Make the minimal change to fix the issue.

**6. Verify Fix**

```bash
# Run the specific test
pytest tests/test_user.py::test_authentication

# Run all tests to ensure no regression
pytest
```

**7. Clean Up**

- Remove debugging code
- Remove temporary tests
- Commit the fix

```bash
git add .
git commit -m "fix: Correct password verification in authentication"
```

---

## Refactoring Workflow

### Safe Refactoring with TDD

**Prerequisites**:
- ✅ All tests passing
- ✅ Tests are comprehensive
- ✅ Version control is clean

**Process**:

**1. Ensure Green State**

```bash
# All tests MUST pass before refactoring
pytest
# ✓ All tests passed
```

**2. Identify Refactoring Opportunity**

Common triggers:
- Code duplication
- Long methods
- Unclear names
- Complex conditionals
- God classes

**3. Make Small Change**

```python
# Before: Duplication
def calculate_discount_for_premium(price):
    if price > 100:
        return price * 0.8
    return price

def calculate_discount_for_gold(price):
    if price > 100:
        return price * 0.9
    return price

# After: Extract common pattern
DISCOUNT_RATES = {
    'premium': 0.20,
    'gold': 0.10,
}

def calculate_discount(price, customer_type):
    if price <= 100:
        return price
    rate = DISCOUNT_RATES.get(customer_type, 0.0)
    return price * (1 - rate)
```

**4. Run Tests Immediately**

```bash
pytest
```

**5. If Red, Undo and Try Smaller Step**

```bash
git checkout -- .
# Try a smaller refactoring
```

**6. If Green, Continue or Commit**

```bash
git add .
git commit -m "refactor: Extract discount calculation into common function"
```

**7. Repeat**

Continue refactoring in small steps, testing after each change.

---

## Code Review Checklist

### TDD Code Review Guidelines

**For Reviewers**:

**Tests**:
- [ ] Every new feature has tests
- [ ] Tests are clear and readable
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] Test names describe behavior
- [ ] No commented-out tests
- [ ] No skipped tests without reason
- [ ] Tests are independent (no order dependency)
- [ ] Tests are deterministic (no random data without seeds)

**Production Code**:
- [ ] Code is simple and clear
- [ ] No premature optimization
- [ ] Public API is intuitive
- [ ] Error handling is appropriate
- [ ] No TODO/FIXME comments (create issues instead)
- [ ] Documentation is adequate

**Coverage**:
- [ ] Critical paths have >90% coverage
- [ ] Business logic has >80% coverage
- [ ] New code doesn't decrease coverage

**Design**:
- [ ] Code is loosely coupled
- [ ] Responsibilities are clear
- [ ] No code duplication
- [ ] Names are meaningful
- [ ] Functions are small and focused

**Process**:
- [ ] Commits are logical and well-described
- [ ] Tests were written first (check git history)
- [ ] No giant commits (suggests non-TDD approach)

**Questions to Ask**:
- "What test drove this code?"
- "Can this be simpler?"
- "Is this testable?"
- "What edge cases are missing?"

---

## Common Scenarios

### Scenario 1: Starting a New Feature

```
1. Create feature branch
   git checkout -b feature/user-search

2. Write first test
   # Start with simplest case
   def test_search_returns_empty_for_no_matches():
       results = search_users("nonexistent")
       assert results == []

3. Run test (should fail)
   pytest tests/test_search.py

4. Implement minimal code
   def search_users(query):
       return []

5. Run test (should pass)
   pytest tests/test_search.py

6. Commit
   git commit -m "feat: Add basic user search (empty results)"

7. Next test
   def test_search_finds_user_by_name():
       ...
```

### Scenario 2: Fixing a Bug

```
1. Write a test that reproduces the bug
   def test_handle_null_input():
       # This currently fails
       result = process(None)
       assert result is not None

2. Verify test fails
   pytest tests/test_process.py::test_handle_null_input
   # Should fail, reproducing the bug

3. Fix the bug
   def process(input):
       if input is None:
           return default_value()
       # ... rest of code

4. Verify test passes
   pytest tests/test_process.py::test_handle_null_input

5. Run all tests
   pytest

6. Commit
   git commit -m "fix: Handle null input in process()"
```

### Scenario 3: Adding Validation

```
1. Test invalid input
   def test_rejects_invalid_email():
       with pytest.raises(ValueError):
           create_user(email="invalid")

2. Implement validation
   def create_user(email):
       if not is_valid_email(email):
           raise ValueError(f"Invalid email: {email}")
       # ...

3. Test edge cases
   @pytest.mark.parametrize("email", [
       "",
       "no-at-sign",
       "@no-local",
       "no-domain@",
       "spaces in@email.com",
   ])
   def test_rejects_malformed_emails(email):
       with pytest.raises(ValueError):
           create_user(email=email)
```

### Scenario 4: Refactoring Legacy Code

```
1. Add characterization tests
   # Document current behavior (even if wrong)
   def test_current_behavior():
       result = legacy_function(input)
       assert result == <whatever it currently returns>

2. Build comprehensive test suite
   # Test all code paths
   # Use code coverage to find gaps

3. Refactor incrementally
   # Small changes
   # Run tests after each change
   # Keep tests passing

4. Fix bugs with new tests
   # Now that you have safety net
   # Write test for correct behavior
   # Fix implementation
```

### Scenario 5: Working with External Dependencies

```
1. Create abstraction
   class EmailService:
       def send(self, to, subject, body):
           raise NotImplementedError

2. Test with fake
   class FakeEmailService(EmailService):
       def __init__(self):
           self.sent_emails = []

       def send(self, to, subject, body):
           self.sent_emails.append((to, subject, body))

   def test_sends_welcome_email():
       email_service = FakeEmailService()
       user_service = UserService(email_service)

       user_service.register("user@example.com")

       assert len(email_service.sent_emails) == 1
       assert email_service.sent_emails[0][0] == "user@example.com"

3. Implement real service
   class SMTPEmailService(EmailService):
       def send(self, to, subject, body):
           # Real SMTP implementation
           pass
```

---

## Tips for Success

### Maintain Rhythm

- **Short cycles**: 2-10 minutes per Red-Green-Refactor
- **Commit often**: After each passing test
- **Take breaks**: Pomodoro technique works well with TDD

### When Stuck

1. **Step is too big**: Break into smaller test
2. **Design unclear**: Spike to explore, then delete and TDD
3. **Test hard to write**: Design problem, reconsider approach
4. **All tests passing but feature incomplete**: Missing test case

### Keep Tests Fast

- Unit tests: < 100ms each
- Integration tests: < 1s each
- Use test doubles for slow operations
- Parallel test execution

### Test Quality

- One assertion per test (generally)
- No logic in tests
- Tests are examples
- Test the interface, not the implementation

### Remember

> "The code you write without a test is legacy code from the moment you write it" - Michael Feathers

> "TDD is not about testing, it's about design" - Sandi Metz

> "Make it work, make it right, make it fast" - Kent Beck
