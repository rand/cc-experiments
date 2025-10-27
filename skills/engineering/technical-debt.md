---
name: engineering-technical-debt
description: Identifying, measuring, tracking, and managing technical debt strategically and systematically
---

# Technical Debt Management

**Scope**: Comprehensive guide to identifying, measuring, prioritizing, and paying down technical debt
**Lines**: ~320
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Evaluating whether to take on technical shortcuts
- Prioritizing refactoring vs new features
- Explaining tech debt costs to stakeholders
- Planning debt paydown sprints
- Auditing codebase health
- Establishing tech debt policies
- Preventing debt accumulation
- Recovering from tech debt crisis

## Core Concepts

### Concept 1: What is Technical Debt?

**Definition**: Code shortcuts that speed up delivery but increase future maintenance costs

**Martin Fowler's Quadrant**:
```
                Reckless         Prudent
Deliberate   | "We don't have | "We must ship now,
             |  time for       | will refactor later"
             |  design"        |
-------------|----------------|------------------
Inadvertent  | "What's        | "Now we know how
             |  layering?"    | we should have
             |                | done it"
```

**Types of Tech Debt**:
- **Code Debt**: Poor code quality, duplication, smells
- **Design Debt**: Wrong abstractions, tight coupling
- **Test Debt**: Missing tests, brittle tests
- **Documentation Debt**: Outdated or missing docs
- **Infrastructure Debt**: Outdated dependencies, poor tooling
- **Architecture Debt**: Scaling issues, monolith problems

---

### Concept 2: Interest vs Principal

**Like Financial Debt**:
- **Principal**: Cost to fix the issue
- **Interest**: Ongoing cost of living with it

```python
# Example: Duplicated validation logic (Principal: 1 day to refactor)

# File 1
def create_user(email):
    if "@" not in email:  # Duplicated
        raise ValueError("Invalid email")
    # ... save user

# File 2
def update_user(email):
    if "@" not in email:  # Duplicated
        raise ValueError("Invalid email")
    # ... update user

# File 3
def invite_user(email):
    if "@" not in email:  # Duplicated
        raise ValueError("Invalid email")
    # ... send invite

# Interest paid:
# - Every bug fix needs 3 changes
# - Every validation enhancement needs 3 updates
# - Risk of inconsistency
# - Slows down all email-related features
```

---

### Concept 3: When to Take On Debt

**Good Reasons** (Deliberate, Prudent):
- MVP to validate market fit
- Time-sensitive opportunity
- Competitive pressure
- Known paydown plan

**Bad Reasons** (Reckless):
- Laziness or lack of skill
- "We'll never come back to this"
- No plan to pay down
- Not understanding implications

---

## Patterns

### Pattern 1: Debt Identification

**Code Smells Checklist**:
```
[ ] Duplicated code (copy-paste)
[ ] Long methods (> 30 lines)
[ ] Large classes (> 500 lines)
[ ] Long parameter lists (> 4 params)
[ ] Divergent change (class changes for multiple reasons)
[ ] Shotgun surgery (one change affects many classes)
[ ] Feature envy (method uses another class more than its own)
[ ] Data clumps (same group of data everywhere)
[ ] Primitive obsession (over-reliance on primitives)
[ ] Comments explaining complex code
```

**Automated Detection**:
```bash
# Python: Code complexity
radon cc src/ -a -nb  # Cyclomatic complexity
radon mi src/         # Maintainability index

# JavaScript: ESLint complexity rules
eslint --max-complexity=10 src/

# Code duplication
jscpd src/  # Copy-paste detector

# Security debt
npm audit
pip-audit
```

---

### Pattern 2: Debt Measurement

**Debt Score Formula**:
```
Debt Score = (Complexity × Impact × Frequency) / Ease of Fix

Complexity: 1-5 (how complex is the problem?)
Impact: 1-5 (how many people/systems affected?)
Frequency: 1-5 (how often is this code touched?)
Ease of Fix: 1-5 (how easy to fix?)
```

**Example Scoring**:
```python
# Debt Item: Duplicated email validation (3 places)
Complexity = 2  # Simple validation logic
Impact = 4      # Used in 10+ features
Frequency = 5   # Changed weekly
Ease of Fix = 4 # Easy - extract to function

Debt Score = (2 × 4 × 5) / 4 = 10

# Debt Item: Monolithic architecture
Complexity = 5  # Very complex to split
Impact = 5      # Affects entire system
Frequency = 3   # Changes monthly
Ease of Fix = 1 # Very difficult

Debt Score = (5 × 5 × 3) / 1 = 75  # High priority!
```

---

### Pattern 3: Debt Tracking

**Debt Register** (track in `TECH_DEBT.md`):
```markdown
# Technical Debt Register

## High Priority (Score > 50)

### TD-001: Monolithic Database
- **Debt Score**: 75
- **Principal**: 4 weeks
- **Interest**: 1 day/week (slow queries, deployment bottleneck)
- **Paydown Plan**: Split into microservices over Q2
- **Status**: Planned

## Medium Priority (Score 20-50)

### TD-002: Missing Integration Tests
- **Debt Score**: 30
- **Principal**: 2 weeks
- **Interest**: 2 hours/week (manual testing)
- **Paydown Plan**: Add tests incrementally with each feature
- **Status**: In Progress

## Low Priority (Score < 20)

### TD-003: Outdated Dependencies
- **Debt Score**: 12
- **Principal**: 1 day
- **Interest**: 30 min/month (security patches)
- **Paydown Plan**: Update in Q3 maintenance sprint
- **Status**: Backlog
```

---

### Pattern 4: Debt Paydown Strategies

**Boy Scout Rule**: Leave code better than you found it
```python
# Every PR: Small improvements
# Before
def process_user(email, name, age, address, phone):  # Too many params
    # ... 50 lines of code

# After (in PR for unrelated feature)
class UserData:
    def __init__(self, email, name, age, address, phone):
        self.email = email
        self.name = name
        # ...

def process_user(user_data: UserData):  # Better!
    # ... same logic
```

**Debt Sprints**: Dedicated time to pay down debt
```
Sprint 10: Features (80%) + Debt (20%)
  - Feature: User dashboard
  - Debt: Extract shared validation logic

Sprint 11: Features (80%) + Debt (20%)
  - Feature: Payment integration
  - Debt: Add integration tests for auth

Sprint 15: Debt Sprint (100%)
  - Upgrade all dependencies
  - Refactor monolithic service
  - Add missing documentation
```

**Strangler Fig Pattern**: Gradually replace old system
```
1. Identify module to replace
2. Build new implementation alongside old
3. Route new requests to new code
4. Migrate existing data gradually
5. Remove old code when fully migrated

Example:
┌─────────────────┐
│ Old Auth System │ ←─┐
└─────────────────┘   │
                      ├─ Route new users to new system
┌─────────────────┐   │  Migrate old users gradually
│ New Auth System │ ←─┘
└─────────────────┘
```

---

### Pattern 5: Preventing Debt

**Definition of Done** (include quality checks):
```markdown
## Definition of Done

Code Complete:
- [ ] Feature implemented
- [ ] Unit tests written (80%+ coverage)
- [ ] Integration tests added
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] No TODO/FIXME comments (create tickets instead)
- [ ] No copy-paste code
- [ ] Cyclomatic complexity < 10
- [ ] No security vulnerabilities
```

**Pre-Commit Hooks**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black  # Formatting

  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8  # Linting
        args: [--max-complexity=10]

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy  # Type checking
```

**Quality Gates in CI**:
```yaml
# .github/workflows/quality.yml
- name: Check code quality
  run: |
    radon cc src/ -a -nb --total-average-threshold=B
    radon mi src/ --min=C

- name: Check test coverage
  run: |
    pytest --cov=src --cov-fail-under=80

- name: Check for code duplication
  run: |
    jscpd src/ --threshold 5  # Fail if > 5% duplication
```

---

## Debt Communication

### Explaining to Stakeholders

**Avoid**: "We have technical debt" (vague, no context)

**Better**: Use analogies and business impact

```
"Our authentication system is like a house built without a foundation.
It works today, but:
- Every new feature takes 2x longer to build
- Security fixes require changes in 5 different places
- We have 3 critical bugs per month due to inconsistency

Investment: 2 weeks to refactor
Payoff: 50% faster feature development, 90% fewer auth bugs
ROI: Pays for itself in 2 months"
```

**Debt Dashboard** (visualize for stakeholders):
```
Tech Debt Metrics Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Debt: 12 weeks
Interest Cost: 8 hours/week

High Priority Debt: [██████----] 60%
Test Coverage:      [████------] 45%
Code Duplication:   [██████----] 15%
Complexity:         [████████--] 80%

Trend: ↑ Increasing (action needed!)
```

---

## Best Practices

### Debt Management Guidelines

**Do's**:
- Track debt explicitly (don't hide it)
- Measure debt objectively
- Pay down incrementally
- Prevent new debt
- Communicate impact to stakeholders
- Schedule regular debt sprints
- Use automated tools

**Don'ts**:
- Don't ignore growing debt
- Don't pay all debt at once (balance with features)
- Don't blame individuals
- Don't take on debt without plan
- Don't use "tech debt" as excuse for poor work
- Don't let debt compound

---

## Anti-Patterns

### Common Debt Management Mistakes

```
❌ "We'll fix it later" (Never happens)
→ Fix now or create explicit paydown plan

❌ Ignoring debt until crisis
→ Track and pay down incrementally

❌ Only paying principal, ignoring interest
→ Prioritize high-interest debt first

❌ 100% features, 0% debt paydown
→ Allocate 20% of sprint to debt

❌ Rewriting from scratch
→ Refactor incrementally (strangler fig)

❌ Not measuring debt
→ Quantify to prioritize effectively

❌ Debt as excuse for poor quality
→ Deliberate, prudent debt only
```

---

## Decision Framework

### Should We Take On This Debt?

```
IF time_pressure AND short_term_need AND have_paydown_plan:
    TAKE_ON_DEBT
    DOCUMENT(why, when_fix, cost)
    SCHEDULE_PAYDOWN
ELSE:
    DO_IT_RIGHT
```

**Example Decision Matrix**:
| Situation | Take Debt? | Condition |
|-----------|------------|-----------|
| MVP launch | ✅ Yes | Must have paydown plan |
| Competitive threat | ✅ Yes | Document & schedule fix |
| Learning new tech | ✅ Yes | First time doing X |
| Lack of skill | ❌ No | Learn or ask for help |
| Laziness | ❌ No | Do it right |
| No plan to fix | ❌ No | Schedule paydown or don't ship |

---

## Code Examples

### Before (High Debt):
```python
# Duplicated validation everywhere
def create_user(email, password):
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    if len(password) < 8:
        raise ValueError("Password too short")
    # ... create user

def update_email(user_id, email):
    if not email or "@" not in email:  # Duplicated!
        raise ValueError("Invalid email")
    # ... update email

def send_invite(email):
    if not email or "@" not in email:  # Duplicated!
        raise ValueError("Invalid email")
    # ... send invite
```

### After (Debt Paid):
```python
# Extracted validation (DRY)
class EmailValidator:
    @staticmethod
    def validate(email: str) -> None:
        if not email or "@" not in email:
            raise ValueError("Invalid email")

class PasswordValidator:
    @staticmethod
    def validate(password: str) -> None:
        if len(password) < 8:
            raise ValueError("Password too short")

def create_user(email, password):
    EmailValidator.validate(email)
    PasswordValidator.validate(password)
    # ... create user

def update_email(user_id, email):
    EmailValidator.validate(email)
    # ... update email

def send_invite(email):
    EmailValidator.validate(email)
    # ... send invite
```

---

## Related Skills

- **engineering-refactoring-patterns**: Techniques for paying down debt
- **engineering-code-quality**: Preventing debt through quality
- **engineering-code-review**: Catching debt in reviews
- **engineering-test-driven-development**: Preventing test debt
- **engineering-continuous-integration**: Automated debt detection

---

## References

- [Technical Debt by Martin Fowler](https://martinfowler.com/bliki/TechnicalDebt.html)
- [Managing Technical Debt by Steve McConnell](https://www.construx.com/blog/managing-technical-debt/)
- [The Human Cost of Tech Debt](https://stackoverflow.blog/2023/02/27/the-human-cost-of-tech-debt/)
- [Tech Debt Quadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
