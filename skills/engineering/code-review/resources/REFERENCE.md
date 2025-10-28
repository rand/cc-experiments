# Code Review Reference Guide

> Comprehensive guide to effective code review practices, processes, and tools

## Table of Contents

1. [Introduction](#introduction)
2. [Code Review Fundamentals](#code-review-fundamentals)
3. [What to Look For](#what-to-look-for)
4. [Writing Effective Review Comments](#writing-effective-review-comments)
5. [Review Checklist](#review-checklist)
6. [Common Code Smells](#common-code-smells)
7. [Handling Disagreements](#handling-disagreements)
8. [Review Automation](#review-automation)
9. [GitHub PR Workflows](#github-pr-workflows)
10. [Metrics and Measurement](#metrics-and-measurement)

---

## Introduction

Code review is a systematic examination of source code intended to find and fix mistakes, improve code quality, share knowledge, and maintain consistency. This reference guide synthesizes best practices from Google Engineering Practices, industry standards, and battle-tested workflows.

### Benefits of Code Review

- **Quality Assurance**: Catch bugs, security issues, and design flaws early
- **Knowledge Sharing**: Spread understanding of codebase across team
- **Mentorship**: Help junior developers learn from senior developers
- **Consistency**: Maintain coding standards and architectural patterns
- **Documentation**: Create audit trail of why decisions were made
- **Reduced Bus Factor**: Ensure multiple people understand each area

### Types of Code Review

1. **Pre-commit Review**: Review before code is merged (most common)
2. **Post-commit Review**: Review after merge (for fast-moving teams)
3. **Pair Programming**: Real-time collaborative review
4. **Over-the-shoulder**: Informal review with direct discussion
5. **Tool-assisted Review**: Automated checks with human oversight

---

## Code Review Fundamentals

### The Standard of Code Review

**Primary Principle**: A reviewer should approve a change if the CL (changelist/PR) improves the overall code health of the system, even if it isn't perfect.

**Key Points**:
- There is no such thing as "perfect" code - only better code
- Reviewers should not seek perfection
- Balance: make progress while improving quality
- Don't block changes because they don't match your personal style

### Reviewer Responsibilities

1. **Review promptly** (within 1 business day for most teams)
2. **Provide constructive feedback** (not just criticism)
3. **Approve when appropriate** (don't nitpick)
4. **Escalate when needed** (security, architecture concerns)
5. **Teach and mentor** (explain the "why" behind suggestions)

### Author Responsibilities

1. **Write clear descriptions** (what, why, how)
2. **Keep changes small** (easier to review, faster to merge)
3. **Test thoroughly** (before requesting review)
4. **Respond to feedback** (constructively and promptly)
5. **Ask questions** (if feedback is unclear)

### Review Size Guidelines

- **Optimal**: 200-400 lines of code
- **Maximum**: 1000 lines (beyond this, review quality drops significantly)
- **Strategy**: Break large changes into multiple PRs
- **Exception**: Generated code, refactoring tools (but note in description)

---

## What to Look For

### 1. Design

**Questions to Ask**:
- Does this change belong in this codebase?
- Is it integrated well with the rest of the system?
- Is it the right time to add this functionality?
- Does it follow system architecture principles?

**Red Flags**:
- Violates single responsibility principle
- Adds unnecessary complexity
- Duplicates existing functionality
- Couples unrelated components
- Ignores established patterns without justification

**Example Review Comments**:
```
❌ Bad: "This design is wrong."

✅ Good: "This creates a circular dependency between modules A and B.
Consider introducing an interface in module C that both can depend on,
following the dependency inversion principle we use elsewhere (e.g.,
auth/interfaces.py)."
```

### 2. Functionality

**Questions to Ask**:
- Does the code do what the author intended?
- Is what the author intended good for users?
- Are edge cases handled?
- Will this work correctly for all input types?

**Areas to Check**:
- Input validation (null, empty, extreme values)
- Error handling (exceptions, return codes)
- Concurrency issues (race conditions, deadlocks)
- Resource management (files, connections, memory)
- Security vulnerabilities (injection, XSS, CSRF)

**Example Test Cases to Consider**:
```python
# Check if reviewer should ask about:
- What happens if input is None?
- What happens if list is empty?
- What happens if concurrent requests arrive?
- What happens if file doesn't exist?
- What happens if network fails?
- What happens if memory is low?
```

### 3. Complexity

**Questions to Ask**:
- Is the code more complex than necessary?
- Could another developer understand this quickly?
- Will the author remember what this does in 6 months?

**Complexity Warning Signs**:
- Functions longer than 50 lines
- Deeply nested conditionals (>3 levels)
- Complex boolean expressions
- Clever tricks instead of clear code
- Lack of intermediate variables with descriptive names

**Simplification Strategies**:
```python
# Before: Complex and unclear
if ((user.role == 'admin' or user.role == 'superuser') and
    user.permissions.can_edit and not user.suspended and
    (resource.owner == user.id or resource.visibility == 'public')):
    allow_access()

# After: Clear with named intermediates
is_privileged_user = user.role in ['admin', 'superuser']
has_edit_permission = user.permissions.can_edit
is_active = not user.suspended
can_access_resource = (resource.owner == user.id or
                       resource.visibility == 'public')

if is_privileged_user and has_edit_permission and is_active and can_access_resource:
    allow_access()
```

### 4. Tests

**Questions to Ask**:
- Are there tests for new functionality?
- Are tests correct and useful?
- Do tests cover edge cases?
- Are tests maintainable?

**Test Coverage Requirements**:
- New features: 80%+ coverage
- Bug fixes: Test that reproduces the bug
- Refactoring: Existing tests still pass
- Critical paths: 90%+ coverage

**Test Quality Indicators**:
```python
# Good test characteristics:
✅ Tests one thing at a time
✅ Clear arrange-act-assert structure
✅ Descriptive test names
✅ Tests behavior, not implementation
✅ Uses realistic test data
✅ Covers happy path and error cases

# Example:
def test_user_cannot_delete_others_posts():
    """Users should only be able to delete their own posts."""
    user = create_user(id=1)
    other_user = create_user(id=2)
    post = create_post(author=other_user)

    with pytest.raises(PermissionError):
        delete_post(post.id, user=user)
```

### 5. Naming

**Questions to Ask**:
- Are names descriptive and unambiguous?
- Are names consistent with the codebase?
- Are names appropriate for their scope?

**Naming Guidelines**:
```python
# Bad names
x = get_data()          # Too vague
flag = True             # Meaningless
tmp = calculate()       # Unclear purpose
mgr = Manager()         # Unnecessary abbreviation

# Good names
active_users = get_active_users()
should_retry = True
payment_total = calculate_payment_total()
payment_manager = PaymentManager()
```

**Scope-based Naming**:
- **Short scope** (1-2 lines): `i`, `j`, `x` acceptable
- **Function scope**: descriptive names
- **Module/class scope**: very descriptive names
- **Global scope**: highly descriptive, prefixed if needed

### 6. Comments

**Questions to Ask**:
- Are comments necessary (or is the code self-explanatory)?
- Do comments explain WHY, not WHAT?
- Are comments up-to-date with the code?

**When to Comment**:
```python
# ❌ Bad: Explaining obvious code
i = i + 1  # Increment i

# ✅ Good: Explaining WHY
i = i + 1  # Skip header row in CSV

# ✅ Good: Explaining complex logic
# Use binary search because user_list is sorted and can be large (>100k).
# Linear search would be O(n) and too slow for real-time lookups.
index = binary_search(user_list, target_user)

# ✅ Good: Warning about gotchas
# Note: This must run before init_database() or foreign keys will fail.
setup_extensions()

# ✅ Good: Documenting decisions
# We tried LRU cache but it caused memory issues with large datasets.
# Simple dict with manual cleanup works better for our access patterns.
cache = {}
```

### 7. Style and Consistency

**Questions to Ask**:
- Does the code follow the team's style guide?
- Is formatting consistent?
- Are patterns consistent with the rest of the codebase?

**Style Guide Priority**:
1. **Automated**: Let tools handle (Prettier, Black, gofmt)
2. **Documented**: Follow team style guide
3. **Inferred**: Match surrounding code
4. **Personal preference**: Not worth discussing in review

### 8. Documentation

**Questions to Ask**:
- Are public APIs documented?
- Is the README updated if needed?
- Are breaking changes noted?
- Is the changelog updated?

**Documentation Requirements**:
```python
# Public API: Full docstring required
def calculate_payment_total(items: list[Item], tax_rate: float) -> Decimal:
    """
    Calculate total payment including items and tax.

    Args:
        items: List of items in cart (must not be empty)
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)

    Returns:
        Total payment amount including tax, rounded to 2 decimal places

    Raises:
        ValueError: If items is empty or tax_rate is negative

    Example:
        >>> items = [Item(price=10.00), Item(price=20.00)]
        >>> calculate_payment_total(items, 0.08)
        Decimal('32.40')
    """
    if not items:
        raise ValueError("items cannot be empty")
    if tax_rate < 0:
        raise ValueError("tax_rate cannot be negative")

    subtotal = sum(item.price for item in items)
    total = subtotal * (1 + tax_rate)
    return round(total, 2)

# Private function: Brief comment sufficient
def _validate_items(items: list[Item]) -> None:
    """Ensure all items have valid prices."""
    # Implementation...
```

---

## Writing Effective Review Comments

### Tone and Courtesy

**Principles**:
1. **Be kind**: Assume positive intent
2. **Be specific**: Point to exact lines and issues
3. **Offer alternatives**: Don't just criticize
4. **Explain why**: Help the author learn
5. **Praise good work**: Positive reinforcement matters

### Comment Structure

**Effective Pattern**:
```
[Observation] + [Impact] + [Suggestion] + [Rationale]

Example:
"This function loads the entire user table into memory (observation),
which will cause OOM errors when we have >10k users (impact).
Consider using pagination or a cursor-based approach (suggestion),
similar to what we do in reports.py (rationale)."
```

### Severity Levels

**Use Prefixes to Indicate Priority**:

```
🔴 BLOCKING: Must fix before merge
"BLOCKING: This SQL query is vulnerable to injection attacks.
Use parameterized queries instead (see security-guide.md)."

🟡 IMPORTANT: Should fix before merge
"IMPORTANT: This doesn't handle network timeouts. We've had
production incidents from similar code (incident-457)."

🔵 SUGGESTION: Nice to have
"SUGGESTION: Consider using dataclasses here for automatic
__init__ and __repr__ methods."

💭 QUESTION: Asking for clarification
"QUESTION: Why are we using a dict here instead of our usual
UserPreferences model?"

💡 LEARNING: Educational, not required
"LEARNING: Python 3.10+ supports structural pattern matching
which could make this match/case cleaner (not required for this PR)."

✅ PRAISE: Acknowledge good work
"PRAISE: Nice use of context manager here - makes the resource
cleanup much clearer!"
```

### Good vs Bad Comments

```
❌ Bad Comments:
- "This is wrong."
- "Why did you do it this way?"
- "I would have done X instead."
- "This is bad code."
- "Read the docs."

✅ Good Comments:
- "This approach works, but it will be slow for large datasets.
   Consider using a generator instead (example: data_pipeline.py)."

- "I'm not sure I understand the purpose of this class.
   Could you add a docstring explaining the use case?"

- "I usually prefer X because Y, but if you have a reason for Z,
   that's fine too. What do you think?"

- "This doesn't match our error handling pattern. See style-guide.md
   section 4.2 for our standard approach."

- "The docs at [link] cover this pattern in detail. The key point
   is [summary]."
```

### Offering Alternatives

**Pattern**:
```
Instead of just saying what's wrong, show what's better:

❌ "This is inefficient."

✅ "This loads all records into memory which will be slow for large
   datasets. Consider:

   Option 1 (recommended): Use pagination
   ```python
   def get_users(page_size=100):
       offset = 0
       while True:
           batch = query_users(limit=page_size, offset=offset)
           if not batch:
               break
           yield from batch
           offset += page_size
   ```

   Option 2: Use database cursor
   ```python
   def get_users():
       with db.cursor() as cursor:
           cursor.execute("SELECT * FROM users")
           for row in cursor:
               yield User.from_row(row)
   ```

   I prefer Option 1 because it's simpler and works with our ORM."
```

### Asking Questions

**Effective Questions**:
```
✅ Open-ended, curious:
"What was your thinking behind using approach X here?"
"Have you considered approach Y? I'm curious about the tradeoffs."
"Could you help me understand why we need this extra layer?"

✅ Leading to learning:
"Did you know about functools.lru_cache for this use case?"
"Have you seen the pattern we use in module X? Would that apply here?"

❌ Rhetorical, judgmental:
"Why on earth would you do it this way?"
"Don't you know about Y?"
"Didn't you read the style guide?"
```

---

## Review Checklist

### Security Review

**Authentication & Authorization**:
- [ ] All endpoints require authentication where appropriate
- [ ] Authorization checks happen on every privileged operation
- [ ] User can only access their own data (no IDOR vulnerabilities)
- [ ] Session management is secure (timeouts, invalidation)
- [ ] Password handling uses bcrypt/scrypt/Argon2 (never plain text)

**Input Validation**:
- [ ] All user input is validated (type, length, format)
- [ ] SQL queries use parameterization (no string concatenation)
- [ ] File uploads are restricted (type, size, content)
- [ ] URLs are validated before redirects (no open redirect)
- [ ] JSON/XML parsing is safe (no XXE attacks)

**Data Protection**:
- [ ] Sensitive data is encrypted at rest
- [ ] Sensitive data is encrypted in transit (TLS/HTTPS)
- [ ] Secrets are not hardcoded (use environment variables)
- [ ] PII is handled according to privacy requirements
- [ ] Logs don't contain sensitive information

**Common Vulnerabilities**:
- [ ] No SQL injection (use ORM or parameterized queries)
- [ ] No XSS (escape output, use CSP headers)
- [ ] No CSRF (use tokens, SameSite cookies)
- [ ] No path traversal (validate file paths)
- [ ] No command injection (avoid shell=True)
- [ ] No insecure deserialization (validate before deserialize)

**Dependencies**:
- [ ] All dependencies are up-to-date
- [ ] No known vulnerabilities in dependencies (run `npm audit`, `pip-audit`)
- [ ] Dependency versions are pinned
- [ ] Licenses are compatible with project

### Performance Review

**Efficiency**:
- [ ] No N+1 queries (use eager loading, batch queries)
- [ ] Database queries have appropriate indexes
- [ ] Caching is used where appropriate
- [ ] Large datasets are paginated or streamed
- [ ] Expensive operations are async or background jobs

**Resource Usage**:
- [ ] Files and connections are properly closed
- [ ] Memory usage is bounded (no unbounded caches)
- [ ] CPU usage is reasonable (no unnecessary loops)
- [ ] Network calls are minimized and batched

**Scalability**:
- [ ] Code works with large datasets (tested with realistic data)
- [ ] No hardcoded limits that will cause issues at scale
- [ ] Concurrent access is handled correctly
- [ ] Rate limiting is implemented where needed

### Maintainability Review

**Code Quality**:
- [ ] Functions are small and focused (<50 lines)
- [ ] Classes have clear, single responsibilities
- [ ] Code is DRY (no copy-paste duplication)
- [ ] Complexity is justified (no premature optimization)
- [ ] Magic numbers are named constants

**Testability**:
- [ ] Code is testable (dependencies can be mocked)
- [ ] Tests exist and are meaningful
- [ ] Tests cover edge cases
- [ ] Tests are fast (<1s for unit tests)
- [ ] Tests are deterministic (no flaky tests)

**Documentation**:
- [ ] Public APIs have docstrings
- [ ] Complex logic has explanatory comments
- [ ] README is updated if needed
- [ ] Breaking changes are documented
- [ ] Migration guide exists if needed

**Error Handling**:
- [ ] Errors are handled appropriately (not swallowed)
- [ ] Error messages are helpful
- [ ] Logging is appropriate (not too much or too little)
- [ ] Failures are observable (metrics, alerts)

### Architecture Review

**Design Patterns**:
- [ ] Appropriate design patterns are used
- [ ] No anti-patterns (god objects, spaghetti code)
- [ ] Dependencies point in the right direction
- [ ] Abstractions are at the right level

**Integration**:
- [ ] New code fits with existing architecture
- [ ] No circular dependencies
- [ ] Interfaces are well-defined
- [ ] Backward compatibility is maintained (or migration plan exists)

**Future-proofing**:
- [ ] Code is extensible (new features won't require refactoring)
- [ ] Configuration is externalized
- [ ] Hard dependencies are minimal
- [ ] Code can be deployed incrementally

---

## Common Code Smells

### 1. Long Method

**Symptom**: Function longer than 50 lines

**Problems**:
- Hard to understand
- Hard to test
- Likely doing too much
- High cognitive load

**Fix**: Extract smaller functions
```python
# Before
def process_order(order):
    # 100 lines of code doing validation, calculation, persistence, notification

# After
def process_order(order):
    validate_order(order)
    total = calculate_total(order)
    save_order(order, total)
    send_confirmation(order)
```

### 2. Large Class

**Symptom**: Class with many methods/fields (>500 lines)

**Problems**:
- Multiple responsibilities
- Hard to understand
- High coupling

**Fix**: Split into multiple classes
```python
# Before
class UserManager:
    def create_user(self): ...
    def delete_user(self): ...
    def send_email(self): ...
    def log_activity(self): ...
    def generate_report(self): ...

# After
class UserService:
    def create_user(self): ...
    def delete_user(self): ...

class NotificationService:
    def send_email(self): ...

class AuditService:
    def log_activity(self): ...

class ReportService:
    def generate_report(self): ...
```

### 3. Long Parameter List

**Symptom**: Function with >3-4 parameters

**Problems**:
- Hard to remember order
- Hard to test
- Likely doing too much

**Fix**: Use parameter object or builder pattern
```python
# Before
def create_user(name, email, age, address, phone, preferences, role):
    ...

# After
@dataclass
class UserData:
    name: str
    email: str
    age: int
    address: str
    phone: str
    preferences: dict
    role: str

def create_user(user_data: UserData):
    ...
```

### 4. Duplicate Code

**Symptom**: Same logic in multiple places

**Problems**:
- Hard to maintain (fix in multiple places)
- Inconsistent behavior
- Bugs multiply

**Fix**: Extract common code
```python
# Before
def process_payment_card(card):
    validate_card(card)
    charge = calculate_charge(card.amount)
    log_transaction("card", card.amount)
    return charge

def process_payment_bank(bank):
    validate_bank(bank)
    charge = calculate_charge(bank.amount)
    log_transaction("bank", bank.amount)
    return charge

# After
def process_payment(payment_method, amount):
    payment_method.validate()
    charge = calculate_charge(amount)
    log_transaction(payment_method.type, amount)
    return charge
```

### 5. Primitive Obsession

**Symptom**: Using primitives instead of domain objects

**Problems**:
- Lack of type safety
- Validation scattered
- Unclear intent

**Fix**: Create value objects
```python
# Before
def send_email(to: str, subject: str, body: str):
    # What if 'to' is invalid email?
    # What if 'subject' is too long?
    ...

# After
@dataclass
class Email:
    address: str

    def __post_init__(self):
        if '@' not in self.address:
            raise ValueError(f"Invalid email: {self.address}")

@dataclass
class Subject:
    text: str

    def __post_init__(self):
        if len(self.text) > 100:
            raise ValueError("Subject too long")

def send_email(to: Email, subject: Subject, body: str):
    # Types guarantee validity
    ...
```

### 6. Feature Envy

**Symptom**: Method uses another class more than its own

**Problems**:
- Wrong responsibility
- High coupling

**Fix**: Move method to appropriate class
```python
# Before
class Order:
    def __init__(self, customer):
        self.customer = customer

class OrderProcessor:
    def calculate_discount(self, order):
        # Uses customer data heavily
        if order.customer.is_premium:
            if order.customer.years_active > 5:
                return 0.20
            return 0.10
        return 0

# After
class Customer:
    def calculate_discount(self):
        if self.is_premium:
            if self.years_active > 5:
                return 0.20
            return 0.10
        return 0

class OrderProcessor:
    def calculate_discount(self, order):
        return order.customer.calculate_discount()
```

### 7. Shotgun Surgery

**Symptom**: One change requires many small edits across codebase

**Problems**:
- Easy to miss locations
- High maintenance burden

**Fix**: Consolidate related code
```python
# Before: Tax rate in 10 different files
TAX_RATE = 0.08  # In file1.py
TAX = 0.08       # In file2.py
tax = 0.08       # In file3.py

# After: Single source of truth
# config.py
class Config:
    TAX_RATE = 0.08

# All files import from config
from config import Config
total = subtotal * (1 + Config.TAX_RATE)
```

### 8. Data Clumps

**Symptom**: Same group of variables appear together repeatedly

**Problems**:
- Unclear relationships
- Parameter list explosion

**Fix**: Group into object
```python
# Before
def draw_rectangle(x, y, width, height, color, border_color, border_width):
    ...

def move_rectangle(x, y, width, height, dx, dy):
    ...

# After
@dataclass
class Rectangle:
    x: int
    y: int
    width: int
    height: int
    color: str
    border_color: str
    border_width: int

    def draw(self):
        ...

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
```

---

## Handling Disagreements

### When You Disagree with the Author

**Step 1: Understand Their Perspective**
```
"I see you chose approach X. Can you help me understand
the reasoning? I'm wondering about Y because Z."
```

**Step 2: Explain Your Concern**
```
"My concern with X is [specific issue]. In my experience,
this has led to [specific problem]. Have you considered [alternative]?"
```

**Step 3: Seek Common Ground**
```
"I think we both want [shared goal]. What if we [compromise]?"
```

**Step 4: Escalate if Needed**
```
"I think we need a second opinion on this. Let's ask
[architect/tech lead] about the tradeoffs."
```

### When Author Disagrees with You

**Step 1: Listen to Their Reasoning**
```
Author: "I disagree with your suggestion because..."
You: "That's a good point I hadn't considered."
```

**Step 2: Reevaluate Your Position**
- Is this really important or just personal preference?
- Do they have information I don't have?
- Is their solution "good enough" even if not ideal?

**Step 3: Decide on Importance**
```
CRITICAL (block merge):
- Security vulnerabilities
- Data loss risks
- Breaking changes without migration
- Violates core architecture principles

IMPORTANT (strong suggestion):
- Performance issues
- Maintainability concerns
- Testing gaps

PREFERENCE (let it go):
- Code style (if automated tools don't catch it)
- Variable naming (if not misleading)
- Different but valid approach
```

**Step 4: Accept or Escalate**
```
Accept: "Fair enough, your reasoning makes sense. Approving."

Escalate: "I still have concerns about [specific issue].
Let's get input from [tech lead]."
```

### Resolving Disagreements

**Techniques**:

1. **Data-Driven**: Run benchmarks, write tests
```
"Let's write a quick benchmark to compare performance of X vs Y."
```

2. **Precedent**: Look at similar code
```
"Let's look at how we handled similar cases in modules A and B."
```

3. **Documentation**: Check team standards
```
"According to our style guide section 4.2, we should..."
```

4. **Time-boxing**: Agree to revisit
```
"Let's ship this now and revisit in sprint retro.
If issues arise, we'll refactor."
```

5. **A/B Testing**: Try both approaches
```
"Let's deploy both behind feature flags and measure."
```

### When to Compromise

**Compromise When**:
- Issue is stylistic, not functional
- Both approaches are valid
- Perfect is enemy of good
- Timeline is critical
- You've already raised multiple issues

**Don't Compromise On**:
- Security vulnerabilities
- Data integrity issues
- Breaking changes to public APIs
- Violations of team agreements

---

## Review Automation

### Linters and Formatters

#### Python

**Ruff** (fast, modern linter and formatter):
```bash
# Install
pip install ruff

# Configuration (pyproject.toml)
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "UP"]
ignore = ["E501"]  # Line too long (formatter handles it)

# Run
ruff check .                    # Lint
ruff check --fix .              # Auto-fix
ruff format .                   # Format
```

**mypy** (type checking):
```bash
# Install
pip install mypy

# Configuration (pyproject.toml)
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

# Run
mypy src/
```

#### JavaScript/TypeScript

**ESLint**:
```bash
# Install
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin

# Configuration (.eslintrc.json)
{
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "no-console": "warn",
    "@typescript-eslint/no-unused-vars": "error"
  }
}

# Run
npx eslint . --ext .ts,.tsx
```

**Prettier** (formatting):
```bash
# Install
npm install -D prettier

# Configuration (.prettierrc)
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5"
}

# Run
npx prettier --write .
```

#### Rust

**Clippy** (linter):
```bash
# Install (included with rustup)
rustup component add clippy

# Run
cargo clippy -- -D warnings
```

**rustfmt** (formatter):
```bash
# Install (included with rustup)
rustup component add rustfmt

# Run
cargo fmt
```

#### Go

**golangci-lint** (meta-linter):
```bash
# Install
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Configuration (.golangci.yml)
linters:
  enable:
    - gofmt
    - goimports
    - govet
    - errcheck
    - staticcheck

# Run
golangci-lint run
```

**gofmt** (formatter):
```bash
# Format
gofmt -w .

# Check formatting
gofmt -l .
```

### Security Scanners

**Bandit** (Python security):
```bash
pip install bandit
bandit -r src/
```

**npm audit** (JavaScript dependencies):
```bash
npm audit
npm audit fix
```

**Trivy** (container security):
```bash
trivy image myimage:latest
```

### Pre-commit Hooks

**Setup** (.pre-commit-config.yaml):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.54.0
    hooks:
      - id: eslint
        files: \.[jt]sx?$
        types: [file]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
```

**Install**:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Test
```

---

## GitHub PR Workflows

### Pull Request Template

**Create** `.github/PULL_REQUEST_TEMPLATE.md`:
```markdown
## Description
<!-- What does this PR do? Why is it needed? -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature that breaks existing functionality)
- [ ] Documentation update

## Testing
<!-- How was this tested? -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
- [ ] Dependent changes merged

## Related Issues
<!-- Link related issues: Fixes #123, Related to #456 -->

## Screenshots
<!-- If applicable, add screenshots -->

## Deployment Notes
<!-- Any special deployment considerations? -->
```

### GitHub Actions Workflow

**Create** `.github/workflows/pr-checks.yml`:
```yaml
name: PR Checks

on:
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy

      - name: Run Ruff
        run: ruff check .

      - name: Run mypy
        run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r src/ -f json -o bandit-report.json

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: bandit-report.json
```

### Branch Protection Rules

**Recommended Settings** (GitHub repo settings):
```
Require pull request reviews before merging
  - Required approvals: 1 (or 2 for critical code)
  - Dismiss stale reviews when new commits are pushed
  - Require review from Code Owners

Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Status checks: lint, test, security

Require conversation resolution before merging

Require linear history (optional, enforces rebase/squash)

Include administrators (apply rules to admins too)
```

### CODEOWNERS File

**Create** `.github/CODEOWNERS`:
```
# Default owners for everything
* @team-leads

# Frontend code
/src/frontend/ @frontend-team
*.tsx @frontend-team
*.css @frontend-team

# Backend code
/src/api/ @backend-team
/src/database/ @backend-team

# Infrastructure
/deploy/ @devops-team
Dockerfile @devops-team
*.tf @devops-team

# Security-sensitive
/src/auth/ @security-team @backend-team
/src/crypto/ @security-team
```

---

## Metrics and Measurement

### Key Metrics

#### Review Turnaround Time
**Definition**: Time from PR creation to first review

**Targets**:
- P0 (urgent): <2 hours
- P1 (high): <4 hours
- P2 (normal): <1 business day
- P3 (low): <2 business days

**How to Measure**:
```python
pr_created_at = pr.created_at
first_review_at = pr.reviews[0].submitted_at
turnaround = first_review_at - pr_created_at
```

#### Review Depth
**Definition**: Number of comments per 100 lines of code

**Targets**:
- 2-5 comments per 100 lines (sweet spot)
- <1: Too shallow (rubber stamping)
- >10: Too nitpicky or complex code

**How to Measure**:
```python
comments_per_100_lines = (review.comments / pr.lines_changed) * 100
```

#### Approval Time
**Definition**: Time from PR creation to approval

**Targets**:
- Small PRs (<200 lines): <4 hours
- Medium PRs (200-500 lines): <1 day
- Large PRs (>500 lines): <2 days

#### Defect Escape Rate
**Definition**: Bugs found in production that weren't caught in review

**Target**: <5% of PRs result in production bugs

**How to Track**:
```python
bugs_from_pr = bugs.filter(introduced_by_pr=pr.id)
escape_rate = bugs_from_pr.count() / total_prs
```

#### Review Iteration Count
**Definition**: Number of review cycles before approval

**Targets**:
- 1-2 iterations: Good
- 3-4 iterations: Acceptable
- >5 iterations: Problem (unclear requirements or poor initial quality)

### Tracking Dashboard

**Metrics to Display**:
```
Weekly Review Stats:
- Average turnaround time: 4.2 hours
- PRs reviewed: 47
- Average PR size: 284 lines
- Review depth: 3.1 comments/100 lines
- Approval time: 8.7 hours
- Iteration count: 2.1 average

Reviewer Leaderboard:
1. Alice: 12 reviews, 3.5hr avg turnaround
2. Bob: 10 reviews, 4.2hr avg turnaround
3. Carol: 9 reviews, 5.1hr avg turnaround

PR Age Report:
- Waiting for review: 5 PRs (oldest: 2 days)
- Waiting for author: 3 PRs (oldest: 4 days)
- Waiting for CI: 1 PR
```

### Automation for Metrics

**GitHub API Script**:
```python
from github import Github
from datetime import datetime, timedelta

g = Github("your-token")
repo = g.get_repo("org/repo")

def analyze_pr_metrics(days=7):
    since = datetime.now() - timedelta(days=days)
    prs = repo.get_pulls(state='closed', sort='updated', direction='desc')

    metrics = {
        'total_prs': 0,
        'total_turnaround': 0,
        'total_comments': 0,
        'total_lines': 0,
    }

    for pr in prs:
        if pr.updated_at < since:
            break

        metrics['total_prs'] += 1
        metrics['total_lines'] += pr.additions + pr.deletions

        reviews = pr.get_reviews()
        if reviews.totalCount > 0:
            first_review = reviews[0]
            turnaround = (first_review.submitted_at - pr.created_at).total_seconds() / 3600
            metrics['total_turnaround'] += turnaround

        comments = pr.get_review_comments()
        metrics['total_comments'] += comments.totalCount

    # Calculate averages
    avg_turnaround = metrics['total_turnaround'] / metrics['total_prs']
    comments_per_100_lines = (metrics['total_comments'] / metrics['total_lines']) * 100

    return {
        'avg_turnaround_hours': avg_turnaround,
        'comments_per_100_lines': comments_per_100_lines,
        'total_prs': metrics['total_prs'],
    }
```

---

## Conclusion

Effective code review is both an art and a science. It requires:

1. **Technical Skills**: Understanding code, architecture, and best practices
2. **Communication Skills**: Giving constructive feedback with kindness
3. **Process Discipline**: Following checklists and standards consistently
4. **Time Management**: Balancing thoroughness with speed
5. **Continuous Learning**: Staying updated on tools and practices

**Key Takeaways**:
- Approve changes that improve code health, even if not perfect
- Be kind, specific, and offer alternatives in comments
- Use automation for mechanical checks (formatting, linting, security)
- Focus human review on design, architecture, and logic
- Measure and improve review process continuously
- Handle disagreements with respect and escalate when needed

**Remember**: Code review is not about finding fault - it's about building great software together.

---

## References

- [Google Engineering Practices: Code Review](https://google.github.io/eng-practices/review/)
- [Conventional Comments](https://conventionalcomments.org/)
- [Code Review Developer Guide](https://github.com/google/eng-practices)
- [Refactoring: Improving the Design of Existing Code](https://martinfowler.com/books/refactoring.html) by Martin Fowler
- [Clean Code](https://www.oreilly.com/library/view/clean-code-a/9780136083238/) by Robert C. Martin
- [The Art of Readable Code](https://www.oreilly.com/library/view/the-art-of/9781449318482/) by Dustin Boswell
