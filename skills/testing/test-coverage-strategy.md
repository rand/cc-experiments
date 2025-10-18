---
name: testing-test-coverage-strategy
description: Determine what code needs testing vs what to skip
---



# Test Coverage Strategy

## When to Use This Skill

Use this skill when you need to:
- Determine what code needs testing vs what to skip
- Interpret coverage metrics (line, branch, mutation)
- Set realistic coverage goals for your project
- Identify untested critical paths
- Implement mutation testing to verify test quality
- Balance coverage goals with development speed
- Audit existing test suites for gaps

**ACTIVATE THIS SKILL**: When planning test strategy, auditing coverage, or setting quality gates

## Core Concepts

### Coverage Metrics

**Line Coverage**: Percentage of lines executed by tests
```python
def calculate_discount(price, discount_percent):
    if discount_percent > 0:           # Line executed
        return price * (1 - discount_percent / 100)  # Line executed
    return price                        # Line NOT executed (100% branch coverage would require this)

# Test only with discount_percent > 0 → 67% line coverage
```

**Branch Coverage**: Percentage of decision branches taken
```python
def validate_age(age):
    if age < 0:          # Branch 1: True path
        return False     # Covered
    elif age < 18:       # Branch 2: True path
        return False     # Covered
    else:                # Branch 3: Else path
        return True      # Covered

# Need 3 tests for 100% branch coverage:
# - age < 0
# - 0 <= age < 18
# - age >= 18
```

**Function Coverage**: Percentage of functions called
```python
def function_a():
    pass

def function_b():
    pass

# Test calls function_a only → 50% function coverage
```

**Path Coverage**: Percentage of unique execution paths
```python
def process(x, y):
    if x > 0:
        if y > 0:
            return "both positive"
        else:
            return "x positive, y not"
    else:
        if y > 0:
            return "y positive, x not"
        else:
            return "both not positive"

# 4 unique paths, need 4 tests for 100% path coverage
```

### Coverage Goals by Project Type

**Libraries** (Public APIs):
- Target: 90-100% coverage
- Critical: All public APIs tested
- Reason: Used by many consumers, high stability need

**Microservices** (Business Logic):
- Target: 80-90% coverage
- Critical: Core business logic, error paths
- Reason: Balance between confidence and speed

**Web Applications** (Full Stack):
- Target: 70-80% coverage
- Critical: Business logic, API endpoints
- Reason: UI changes frequently, focus on backend

**Prototypes/Experiments**:
- Target: 0-50% coverage
- Critical: None
- Reason: Throwaway code, optimize for learning

### What to Test vs Skip

**ALWAYS TEST**:
- Business logic (pricing, validation, calculations)
- Security-critical code (auth, permissions, encryption)
- Data transformations (parsing, serialization)
- Error handling (edge cases, failure modes)
- Public APIs (library interfaces)
- Bug fixes (regression prevention)

**SKIP TESTING**:
- Simple getters/setters (no logic)
- Framework/library code (already tested)
- Configuration files (static data)
- Generated code (build artifacts)
- Trivial delegation (one-line wrappers)
- UI layout code (use visual testing instead)

## Patterns

### Coverage-Guided Test Writing

**Step 1: Run coverage report**:
```bash
# Python
pytest --cov=myapp --cov-report=html tests/

# JavaScript
npm test -- --coverage

# Go
go test -cover ./...

# Rust
cargo tarpaulin --out Html
```

**Step 2: Identify untested code**:
```python
# coverage.py report shows:
# myapp/payment.py     45%    Lines 23-45, 67-89 not covered

# Look at payment.py:
def process_payment(amount, method):
    if method == "credit_card":
        return process_credit_card(amount)  # Tested
    elif method == "paypal":
        return process_paypal(amount)        # NOT TESTED (line 23-45)
    elif method == "bitcoin":
        return process_bitcoin(amount)       # NOT TESTED (line 67-89)
    else:
        raise ValueError("Invalid method")   # NOT TESTED
```

**Step 3: Write tests for critical gaps**:
```python
def test_process_payment_paypal():
    result = process_payment(100, "paypal")
    assert result.status == "success"

def test_process_payment_bitcoin():
    result = process_payment(100, "bitcoin")
    assert result.status == "success"

def test_process_payment_invalid_method():
    with pytest.raises(ValueError):
        process_payment(100, "invalid")
```

**Step 4: Re-run coverage → Improved to 95%**

### Mutation Testing

**Concept**: Introduce bugs (mutations) to verify tests catch them

```python
# Original code
def is_adult(age):
    return age >= 18

# Test
def test_is_adult():
    assert is_adult(18) is True
    assert is_adult(17) is False

# Mutation 1: Change >= to >
def is_adult(age):
    return age > 18  # Mutant

# Run tests: PASSES (but shouldn't!)
# → Test is weak, doesn't catch boundary error

# Improved test
def test_is_adult_boundary():
    assert is_adult(18) is True  # Catches >= vs > mutation
    assert is_adult(17) is False
    assert is_adult(19) is True
```

**Mutation Testing Tools**:
```bash
# Python (mutmut)
pip install mutmut
mutmut run
mutmut results

# JavaScript (Stryker)
npm install --save-dev @stryker-mutator/core
npx stryker run

# Example output:
# Mutant 1: Changed >= to > → SURVIVED (test didn't catch it)
# Mutant 2: Changed >= to == → KILLED (test caught it)
# Mutation Score: 85% (good)
```

### Critical Path Testing

**Identify high-value code paths**:

```python
# E-commerce checkout flow
def checkout(cart, user, payment_method):
    # CRITICAL: Calculate total (money involved)
    total = calculate_total(cart)

    # CRITICAL: Apply discounts (business logic)
    total = apply_discounts(total, user.discount_codes)

    # CRITICAL: Process payment (money exchange)
    payment = process_payment(total, payment_method)
    if not payment.success:
        raise PaymentFailedError()

    # CRITICAL: Create order (data integrity)
    order = create_order(cart, user, total, payment.id)

    # LESS CRITICAL: Send email (nice-to-have)
    send_order_confirmation(user.email, order)

    # LESS CRITICAL: Analytics (optional)
    track_purchase(user.id, total)

    return order

# Test priority:
# 1. calculate_total (business logic)
# 2. apply_discounts (business logic)
# 3. process_payment (integration test)
# 4. create_order (integration test)
# 5. send_order_confirmation (optional)
# 6. track_purchase (optional)
```

### Incremental Coverage Improvement

**Strategy**: Improve coverage over time, focus on new code

```python
# .coveragerc (Python)
[run]
branch = True
source = myapp

[report]
precision = 2
fail_under = 80  # CI fails if coverage drops below 80%

# Track coverage over time
# Week 1: 65%
# Week 2: 70% (added tests for user authentication)
# Week 3: 75% (added tests for payment processing)
# Week 4: 80% (reached goal)
```

**Git hook to prevent coverage regression**:
```bash
#!/bin/bash
# .git/hooks/pre-push

# Run tests with coverage
coverage run -m pytest
coverage report --fail-under=80

if [ $? -ne 0 ]; then
    echo "❌ Coverage below 80%, push rejected"
    exit 1
fi

echo "✅ Coverage check passed"
```

### Coverage Exclusions

**Explicitly exclude code from coverage**:

```python
# Exclude debug code
if DEBUG:  # pragma: no cover
    print(f"Debug: {variable}")

# Exclude abstract methods
class BaseRepository:
    def find_by_id(self, id: int):
        raise NotImplementedError()  # pragma: no cover

# Exclude platform-specific code
if sys.platform == "win32":  # pragma: no cover
    import msvcrt
```

```typescript
// TypeScript/JavaScript (Istanbul)
/* istanbul ignore next */
function debugLog(message: string) {
  console.log(message);
}

/* istanbul ignore else */
if (process.env.NODE_ENV === 'development') {
  console.log('Dev mode');
}
```

## Examples by Language

### Python (coverage.py)

```python
# Install
pip install pytest-cov

# Run with coverage
pytest --cov=myapp --cov-report=term-missing tests/

# Generate HTML report
pytest --cov=myapp --cov-report=html tests/
# Open htmlcov/index.html

# Configuration (.coveragerc)
[run]
source = myapp
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[report]
precision = 2
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

# CI integration (GitHub Actions)
- name: Test with coverage
  run: |
    pytest --cov=myapp --cov-report=xml tests/

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

### TypeScript/JavaScript (Istanbul/c8)

```json
// package.json
{
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  },
  "devDependencies": {
    "@vitest/coverage-v8": "^1.0.0"
  }
}

// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.test.ts',
        '**/*.config.ts',
      ],
      lines: 80,
      branches: 80,
      functions: 80,
      statements: 80,
    },
  },
});
```

```bash
# Run coverage
npm run test:coverage

# Output:
# File         | % Stmts | % Branch | % Funcs | % Lines |
# -------------|---------|----------|---------|---------|
# user.ts      |   85.71 |       75 |     100 |   85.71 |
# payment.ts   |   66.67 |       50 |      75 |   66.67 |
# -------------|---------|----------|---------|---------|
# All files    |   76.19 |    62.50 |   87.50 |   76.19 |
```

### Go

```go
// Run with coverage
go test -cover ./...

// Generate coverage profile
go test -coverprofile=coverage.out ./...

// View coverage in browser
go tool cover -html=coverage.out

// Coverage for specific package
go test -cover -coverprofile=coverage.out ./pkg/user

// Coverage threshold (CI)
#!/bin/bash
go test -coverprofile=coverage.out ./...
coverage=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
threshold=80

if (( $(echo "$coverage < $threshold" | bc -l) )); then
    echo "Coverage $coverage% is below threshold $threshold%"
    exit 1
fi
```

### Rust (tarpaulin)

```bash
# Install
cargo install cargo-tarpaulin

# Run coverage
cargo tarpaulin --out Html

# Output to terminal
cargo tarpaulin --out Stdout

# Configuration (Cargo.toml or tarpaulin.toml)
[tarpaulin]
ignore-tests = true
exclude-files = [
    "src/generated/*",
    "tests/*"
]
```

## Mutation Testing Examples

### Python (mutmut)

```bash
# Install
pip install mutmut

# Run mutation testing
mutmut run

# View results
mutmut results

# Show surviving mutants
mutmut show

# Example output:
# Mutant 1 (SURVIVED):
# --- src/calculator.py
# +++ mutant
# @@ -5,7 +5,7 @@
#  def add(a, b):
# -    return a + b
# +    return a - b

# This survived because no test verifies add(2, 3) == 5
# Add test:
def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
```

### JavaScript (Stryker)

```bash
# Install
npm install --save-dev @stryker-mutator/core

# Initialize
npx stryker init

# Run
npx stryker run

# Example stryker.conf.json
{
  "mutate": ["src/**/*.ts"],
  "testRunner": "vitest",
  "coverageAnalysis": "perTest",
  "thresholds": {
    "high": 80,
    "low": 60,
    "break": 60
  }
}

# Output:
# Mutant killed   | 45
# Mutant survived | 5
# Mutation score  | 90%
```

## Checklist

**Setting Coverage Strategy**:
- [ ] Define coverage goals by project type (library: 90%+, app: 70-80%)
- [ ] Identify critical paths to prioritize
- [ ] Decide what to exclude (generated code, debug code)
- [ ] Choose coverage metrics (line + branch minimum)
- [ ] Set up coverage reporting in CI/CD

**Measuring Coverage**:
- [ ] Run coverage report locally
- [ ] Identify untested lines/branches
- [ ] Prioritize gaps by business criticality
- [ ] Write tests for critical gaps
- [ ] Verify coverage improvement

**Coverage Quality**:
- [ ] Use mutation testing to verify test effectiveness
- [ ] Check branch coverage (not just line coverage)
- [ ] Review surviving mutants (weak tests)
- [ ] Test error paths and edge cases
- [ ] Avoid testing for coverage sake (test behavior)

**CI/CD Integration**:
- [ ] Fail builds if coverage drops below threshold
- [ ] Upload coverage reports (Codecov, Coveralls)
- [ ] Track coverage trends over time
- [ ] Require coverage for new code (diff coverage)
- [ ] Set realistic thresholds (don't aim for 100%)

## Anti-Patterns

```
❌ NEVER: Aim for 100% coverage on everything
   → Waste time testing trivial code

❌ NEVER: Write tests just to increase coverage
   → Tests without assertions, useless tests

❌ NEVER: Only measure line coverage
   → Miss untested branches/paths

❌ NEVER: Ignore coverage in code review
   → Coverage regression over time

❌ NEVER: Test private implementation details
   → Brittle tests, false coverage confidence

❌ NEVER: Exclude all error handling from coverage
   → Untested failure modes

❌ NEVER: Use coverage as only quality metric
   → High coverage ≠ good tests
```

## Related Skills

**Foundation**:
- `unit-testing-patterns.md` - How to write testable code
- `test-driven-development.md` - TDD workflow for coverage

**Advanced**:
- `mutation-testing.md` - Advanced mutation testing patterns
- `property-based-testing.md` - Generate test cases automatically

**Integration**:
- `integration-testing.md` - Coverage for integration tests
- `e2e-testing.md` - Coverage for E2E tests

**Tools**:
- Python: coverage.py, mutmut
- TypeScript: c8, Stryker
- Go: Built-in coverage tool
- Rust: tarpaulin, cargo-mutants

**Coverage Services**:
- Codecov: Cross-language coverage tracking
- Coveralls: GitHub integration
- SonarQube: Comprehensive code quality
