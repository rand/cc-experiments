---
name: engineering-code-review-rules
description: Opinionated code review checklist with 50+ actionable rules for security, performance, readability, testing, and error handling
---


# Code Review Rules

**Scope**: Security, performance, readability, testing, error handling, architecture review rules
**Lines**: ~300
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Reviewing pull requests or code changes
- Writing code that will be reviewed by others
- Setting up automated code review tooling
- Establishing team code review standards
- Auditing existing code for quality issues
- Onboarding engineers to review expectations

## Core Concepts

### Security Rules

**SEC-01: No secrets in source code**
Secrets belong in environment variables, vaults, or secret managers. Never in code, configs checked into git, or comments.

```python
# BAD
API_KEY = "sk-live-abc123def456"
db_url = "postgres://admin:password@prod-db:5432/app"

# GOOD
API_KEY = os.environ["API_KEY"]
db_url = os.environ["DATABASE_URL"]
```

**SEC-02: Parameterize all queries**
Never interpolate user input into SQL, LDAP, or shell commands.

```python
# BAD
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**SEC-03: Escape all rendered output**
Every user-supplied value rendered in HTML, JSON, or logs must be escaped for its context.

**SEC-04: Validate and sanitize all input at the boundary**
Reject unexpected types, lengths, and characters before they enter your system. Allowlists beat denylists.

**SEC-05: Enforce authentication before authorization**
Every protected endpoint must verify identity, then check permissions. Never assume upstream middleware handled it.

**SEC-06: Use constant-time comparison for secrets**
String equality on tokens or passwords leaks timing information. Use `hmac.compare_digest` or equivalent.

**SEC-07: Set security headers**
`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`. Missing headers are findings.

**SEC-08: Avoid deserialization of untrusted data**
`pickle.loads`, `yaml.load` (without SafeLoader), `eval`, `unserialize` on user data is remote code execution.

**SEC-09: Enforce least privilege on service accounts**
Database users should have only the permissions they need. Read-only services get read-only credentials.

**SEC-10: Log security events, never secrets**
Log authentication failures, permission denials, input validation failures. Never log passwords, tokens, PII.

**SEC-11: Pin dependencies and audit for CVEs**
Use lockfiles. Run `npm audit`, `pip-audit`, `cargo audit` in CI. Block merges on critical CVEs.

---

### Performance Rules

**PERF-01: Eliminate N+1 queries**
If you fetch a list then query per item, you have an N+1. Use JOINs, eager loading, or batch fetches.

```python
# BAD: N+1
for order in orders:
    items = db.query(Item).filter(Item.order_id == order.id).all()

# GOOD: eager load
orders = db.query(Order).options(joinedload(Order.items)).all()
```

**PERF-02: Bound all queries**
Every query against user-controlled data must have a `LIMIT`. Unbounded `SELECT *` is a production incident waiting to happen.

**PERF-03: Add indexes for query patterns**
If you query by a column, it needs an index. Check `EXPLAIN ANALYZE` output. Missing indexes on foreign keys is common.

**PERF-04: Avoid unnecessary allocations in hot paths**
Pre-allocate collections when size is known. Reuse buffers. Avoid creating objects in tight loops.

**PERF-05: Use pagination, not full collection returns**
APIs that return unbounded lists will eventually crash clients or servers. Cursor-based pagination over offset.

**PERF-06: Cache expensive computations**
If a computation is repeated with the same inputs, cache it. But set TTLs and invalidation strategies upfront.

**PERF-07: Avoid synchronous I/O in async contexts**
Blocking calls in async code starve the event loop. Use async drivers or offload to thread pools.

**PERF-08: Profile before optimizing**
Guessing at bottlenecks is wrong more often than right. Measure first with profiling tools.

---

### Readability Rules

**READ-01: Name things for what they represent, not how they work**
`usersByEmail` not `hashMap`. `retryWithBackoff` not `loopAndSleep`.

**READ-02: Functions should do one thing**
If you need "and" to describe what a function does, split it. Aim for under 30 lines per function.

**READ-03: Limit nesting to 3 levels**
Deep nesting kills readability. Use early returns, extract functions, or invert conditions.

```python
# BAD
def process(data):
    if data:
        if data.valid:
            if data.ready:
                return handle(data)

# GOOD
def process(data):
    if not data:
        return None
    if not data.valid:
        return None
    if not data.ready:
        return None
    return handle(data)
```

**READ-04: No magic numbers or strings**
Extract constants with descriptive names. `MAX_RETRY_ATTEMPTS = 3` not bare `3`.

**READ-05: Delete dead code**
Commented-out code, unreachable branches, unused imports, unused variables. Delete them. Git remembers.

**READ-06: Consistent code style**
Use formatters (prettier, black, rustfmt). Style debates in code review waste everyone's time.

**READ-07: Comments explain why, not what**
If code needs a comment to explain what it does, rewrite the code. Comments should explain non-obvious reasoning.

```python
# BAD
# increment counter by 1
counter += 1

# GOOD
# Rate limit resets after 60s, but we add 1s buffer for clock skew
reset_time = rate_limit_reset + 61
```

**READ-08: Group related code, separate unrelated code**
Functions that work together should be near each other. Blank lines separate logical blocks.

**READ-09: Prefer explicit over clever**
Clever one-liners that take 30 seconds to parse cost more than 3 clear lines. Optimize for reading.

**READ-10: Boolean parameters are a code smell**
`render(template, compact=True)` is unclear at the call site. Use enums, separate functions, or configuration objects.

**READ-11: Avoid abbreviations unless universally understood**
`ctx`, `req`, `res`, `err` are fine. `usrAccMgr`, `procHndlr`, `tmpBuf` are not.

---

### Testing Rules

**TEST-01: Tests must be independent**
No test should depend on another test's state or execution order. Each test sets up its own state and tears it down.

**TEST-02: Assert specific values, not truthiness**
`assertEqual(result, 42)` not `assertTrue(result)`. Weak assertions pass when they should fail.

**TEST-03: Test edge cases explicitly**
Empty inputs, null values, boundary values, maximum lengths, unicode, concurrent access. Name the test after the edge case.

**TEST-04: No flaky tests**
A test that fails intermittently is worse than no test. Fix it, quarantine it, or delete it. Never ignore it.

**TEST-05: One assertion per logical concept**
Multiple assertions are fine if they verify one concept. Testing unrelated things in one test obscures failures.

**TEST-06: Test behavior, not implementation**
Tests that break when you refactor internals are coupled to implementation. Test the public contract.

```python
# BAD: tests implementation
assert mock_db.query.call_count == 3

# GOOD: tests behavior
assert len(result.items) == 3
assert result.items[0].name == "expected"
```

**TEST-07: Use factories, not fixtures with shared mutable state**
Shared fixtures create hidden coupling between tests. Factories produce fresh, customizable test data.

**TEST-08: Integration tests should test integration**
If your integration test mocks the thing it integrates with, it is a unit test with extra steps.

**TEST-09: Name tests to describe the scenario and expected outcome**
`test_expired_token_returns_401` not `test_auth` or `test_case_7`.

---

### Error Handling Rules

**ERR-01: Never swallow errors silently**

```python
# BAD
try:
    process(data)
except Exception:
    pass

# GOOD
try:
    process(data)
except ProcessingError as e:
    logger.warning("Processing failed for %s: %s", data.id, e)
    metrics.increment("processing_failures")
```

**ERR-02: Catch specific exceptions**
Broad `catch (Exception)` hides bugs. Catch the specific errors you can handle. Let unexpected errors propagate.

**ERR-03: Clean up resources on error**
Use `try/finally`, context managers, `defer`, or RAII. Resource leaks under error conditions are common.

**ERR-04: Error messages must be actionable**
"Error" is useless. "Failed to connect to database at db.example.com:5432: connection refused" is actionable.

**ERR-05: Do not use exceptions for control flow**
Exceptions are for exceptional conditions. Expected outcomes (user not found, validation failure) should use return values.

**ERR-06: Wrap errors with context when re-raising**
Add context at each layer so the final error message tells the full story.

```python
# BAD
raise

# GOOD
raise OrderProcessingError(f"Failed to process order {order_id}") from e
```

**ERR-07: Validate early, fail fast**
Check preconditions at function entry. The deeper an invalid state travels, the harder it is to debug.

**ERR-08: Define error types for your domain**
`InsufficientBalanceError` is better than `ValueError("not enough money")`. Custom errors enable precise handling.

**ERR-09: Handle partial failures in batch operations**
When processing a list, decide upfront: fail the whole batch, or collect errors and report? Document which.

---

### Architecture Rules

**ARCH-01: Dependencies point inward**
Business logic must not depend on infrastructure. The database adapter depends on the domain, never the reverse.

**ARCH-02: No circular dependencies**
If A depends on B and B depends on A, they are one module or the abstraction is wrong. Extract an interface.

**ARCH-03: Single responsibility at every level**
Functions, classes, modules, and services should each have one reason to change.

**ARCH-04: Prefer composition over inheritance**
Inheritance creates rigid hierarchies. Composition with interfaces allows flexible assembly.

**ARCH-05: Abstract at the right level**
Premature abstraction is as costly as no abstraction. Extract when you see the third instance of a pattern, not the first.

**ARCH-06: API boundaries are contracts**
Changing a public API breaks consumers. Design APIs deliberately. Use versioning. Deprecate before removing.

**ARCH-07: Keep shared mutable state minimal**
Every piece of shared mutable state is a potential race condition and a coupling point. Prefer immutable data and message passing.

---

## Anti-patterns

- **Rubber stamp reviews**: Approving without reading. If you cannot describe what changed, you did not review it.
- **Style nitpicking over substance**: Formatters handle style. Reviewers handle logic, security, and design.
- **Blocking on preferences**: "I would have done it differently" is not a blocking comment unless the approach has concrete downsides.
- **Review scope creep**: Review the diff. Refactoring adjacent code belongs in a separate PR.
- **Skipping tests in review**: Tests are code. Review them with the same rigor as production code.

---

## Checklists

### Quick Review Checklist
- [ ] No secrets or credentials in the diff
- [ ] All user input is validated and sanitized
- [ ] Queries are parameterized and bounded
- [ ] Error paths are handled, not swallowed
- [ ] Tests cover the new behavior and edge cases
- [ ] No N+1 queries or unbounded allocations
- [ ] Function and variable names are clear
- [ ] No dead code, no commented-out code
- [ ] Public API changes are intentional and documented

### Deep Review Checklist
- [ ] All items from Quick Review
- [ ] Authentication and authorization are enforced
- [ ] Resource cleanup happens on all paths (success and error)
- [ ] Concurrency is handled correctly (locks, atomics, message passing)
- [ ] Database migrations are backward-compatible
- [ ] Logging is sufficient for debugging without leaking PII
- [ ] Performance implications considered for hot paths
- [ ] Dependency changes are justified and audited

---

## Related Skills

- `code-quality.md` -- General code quality patterns
- `test-driven-development.md` -- TDD workflow
- `refactoring-patterns.md` -- Safe refactoring techniques
- `code-review.md` -- Code review process and culture
