---
name: engineering-code-review
description: Code review practices, PR etiquette, constructive feedback, automation tools, and effective review workflows
---

# Code Review Best Practices

**Scope**: Comprehensive guide to code review processes, PR etiquette, constructive feedback, automation, and team collaboration
**Lines**: ~350
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Conducting code reviews for pull requests
- Establishing code review standards for a team
- Training engineers on giving and receiving feedback
- Setting up automated review tools (linters, static analysis)
- Defining PR templates and review checklists
- Resolving code review conflicts or disagreements
- Optimizing review turnaround time
- Balancing thoroughness with velocity

## Core Concepts

### Concept 1: The Purpose of Code Review

**Primary Goals**:
- **Catch bugs**: Find logical errors, edge cases, security issues before production
- **Knowledge sharing**: Spread understanding of codebase across team
- **Maintain quality**: Enforce standards, consistency, best practices
- **Mentorship**: Help junior engineers grow through feedback
- **Collective ownership**: Everyone responsible for code quality

**Not the Goal**:
- Nitpicking style preferences (use automated formatters)
- Asserting dominance or "being right"
- Rewriting code to match your personal style
- Blocking PRs indefinitely over minor issues

### Concept 2: Reviewer Responsibilities

**What to Review**:
1. **Correctness**: Does the code do what it claims?
2. **Testing**: Are there adequate tests? Do they cover edge cases?
3. **Security**: Any vulnerabilities (SQL injection, XSS, auth bypass)?
4. **Performance**: Any obvious bottlenecks (N+1 queries, unnecessary loops)?
5. **Maintainability**: Is the code readable and well-structured?
6. **Documentation**: Are complex parts explained?

**How to Review**:
- Start with the PR description - does it explain the change?
- Review tests first - they document expected behavior
- Read code top-to-bottom, following the logical flow
- Ask questions rather than making demands
- Suggest alternatives, don't just say "this is wrong"
- Approve with minor suggestions rather than blocking

### Concept 3: Author Responsibilities

**Before Submitting**:
- Self-review your own code first
- Run tests locally - all passing
- Update documentation if behavior changed
- Keep PRs small (< 400 lines ideal, < 800 max)
- Write clear PR description with context

**During Review**:
- Respond to feedback promptly
- Ask for clarification if feedback is unclear
- Explain your reasoning without being defensive
- Be open to suggestions - reviewers offer valuable perspective
- Push back respectfully when you disagree

---

## Patterns

### Pattern 1: Effective PR Description Template

**Good Example**:
```markdown
## What Changed
Added user profile photo upload with S3 storage and CloudFront CDN.

## Why
Users have requested profile photos (50+ tickets). Unblocks social
features planned for Q1 2025.

## How
- New `POST /api/users/:id/photo` endpoint
- Uploads to S3 bucket `user-photos-prod`
- CloudFront distribution for fast global delivery
- Max 5MB file size, JPEG/PNG only
- Image resized to 400x400px on upload

## Testing
- Unit tests: upload validation, file type checking
- Integration tests: end-to-end upload flow
- Manual testing: tested on Chrome, Safari, Mobile Safari

## Screenshots
[Attach screenshot of new feature]

## Related
- Closes #1234
- Follow-up: Add photo cropping (tracked in #1235)
```

**Bad Example**:
```markdown
## What Changed
Added profile photos.

## Testing
Tested manually, works fine.
```

**Why Bad**: No context on _why_, no details on implementation, vague testing description.

---

### Pattern 2: Constructive Feedback

**Good Examples**:

```markdown
# Asking Questions
❓ What happens if the user uploads a 20MB file? Should we validate
size on the client side too?

# Suggesting Improvements
💡 Consider extracting this validation logic into a separate function
for reusability:
```python
def validate_photo_upload(file):
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("File too large")
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise ValidationError("Invalid file type")
```

# Pointing Out Issues
⚠️ This could cause a race condition if two uploads happen
simultaneously. Consider using a unique filename:
```python
filename = f"{user_id}_{uuid4()}.jpg"
```

# Praising Good Work
✅ Nice use of the factory pattern here! Makes testing much easier.
```

**Bad Examples**:

```markdown
# Too Vague
This doesn't look right.

# Overly Critical
This is terrible. Did you even test this?

# Nitpicking Without Tools
Please add spaces around operators. (Use automated formatter instead!)

# Making Demands
Change this to use a factory pattern.

# Better Alternative
Consider using a factory pattern here - it would make testing easier
and improve separation of concerns. What do you think?
```

---

### Pattern 3: Review Checklist

**Pre-Merge Checklist**:
```markdown
## Functionality
- [ ] Code does what PR description claims
- [ ] Edge cases handled (null, empty, large inputs)
- [ ] Error cases handled gracefully

## Testing
- [ ] Unit tests added for new logic
- [ ] Integration tests for new endpoints
- [ ] Tests actually test the behavior (not just mocks)
- [ ] All tests passing in CI

## Security
- [ ] No SQL injection vulnerabilities
- [ ] Input validation on all user data
- [ ] Authentication/authorization checked
- [ ] Sensitive data not logged

## Performance
- [ ] No N+1 query problems
- [ ] Database queries indexed
- [ ] No blocking operations in hot paths
- [ ] Large datasets paginated

## Maintainability
- [ ] Code is readable and well-organized
- [ ] Complex logic documented
- [ ] No TODO/FIXME comments (create tickets instead)
- [ ] Naming is clear and consistent

## Documentation
- [ ] API documentation updated
- [ ] README updated if needed
- [ ] Migration guide if breaking change
```

---

### Pattern 4: PR Size Guidelines

**Ideal PR Sizes**:

| Size | Lines Changed | Review Time | Quality |
|------|---------------|-------------|---------|
| Tiny | 1-50 | 5-10 min | Excellent |
| Small | 51-200 | 15-30 min | Good |
| Medium | 201-400 | 30-60 min | Acceptable |
| Large | 401-800 | 1-2 hours | Risky |
| Huge | 800+ | 2+ hours | Avoid |

**Breaking Down Large PRs**:

```python
# Bad: One massive PR
PR #1: "Implement entire authentication system" (2000 lines)
  - Database models
  - API endpoints
  - Frontend components
  - Tests
  - Documentation

# Good: Multiple focused PRs
PR #1: "Add User and Session database models" (150 lines)
PR #2: "Add authentication API endpoints" (200 lines)
PR #3: "Add login/signup UI components" (180 lines)
PR #4: "Add authentication integration tests" (120 lines)
```

**Benefits**:
- Faster review turnaround
- More thorough review (not overwhelming)
- Easier to revert if issues found
- Better git history for debugging

---

### Pattern 5: Automated Review Tools

**Pre-Commit Hooks**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    hooks:
      - id: black  # Python formatter

  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8  # Python linter

  - repo: https://github.com/pre-commit/mirrors-eslint
    hooks:
      - id: eslint  # JavaScript linter
```

**GitHub Actions CI**:
```yaml
# .github/workflows/pr-checks.yml
name: PR Checks
on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run linters
        run: |
          npm run lint
          npm run type-check

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: npm test

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Security scan
        uses: snyk/actions/node@master
```

**Code Coverage Requirements**:
```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 80%  # Fail PR if coverage drops below 80%
        threshold: 2%  # Allow 2% decrease
```

---

### Pattern 6: Handling Disagreements

**Escalation Path**:

```
1. Discuss in PR comments
   ↓ (if no resolution)
2. Hop on quick call/screenshare
   ↓ (if still no resolution)
3. Tag tech lead or architect
   ↓ (if still no resolution)
4. Document both approaches, ship one, revisit later
```

**Example Disagreement Resolution**:

```markdown
# Original Feedback
@reviewer: This should use dependency injection instead of direct
instantiation.

# Author Response
@author: I considered that, but this is a one-off utility function
that's only called in tests. Adding DI feels like over-engineering.
What's the specific benefit you see?

# Reviewer Clarification
@reviewer: Fair point. My concern is if we later need to mock this in
other tests, but you're right that's not needed today. Let's ship this
and refactor if that need arises. Approved!
```

---

## Best Practices

### For Reviewers

1. **Review within 24 hours** - Don't block teammates
2. **Start with what's good** - Praise before criticism
3. **Be specific** - Link to docs, provide examples
4. **Ask, don't tell** - "What do you think about X?" vs "Do X"
5. **Approve with suggestions** - Don't block on minor issues
6. **Review in small batches** - Better focus, faster feedback

### For Authors

1. **Self-review first** - Catch your own mistakes
2. **Keep PRs small** - < 400 lines when possible
3. **Write context** - Help reviewers understand the change
4. **Respond promptly** - Don't let PRs go stale
5. **Be grateful** - Reviewers are helping you improve
6. **Push back respectfully** - You know the code best

### For Teams

1. **Define standards** - Document what to review
2. **Automate style** - Don't waste human time on formatting
3. **Rotate reviewers** - Spread knowledge, prevent bottlenecks
4. **Track metrics** - PR size, review time, bug escape rate
5. **Celebrate good reviews** - Recognize thorough, helpful feedback

---

## Anti-Patterns

### Common Mistakes

```
❌ Reviewing 2000-line PRs
→ Break into smaller PRs

❌ Nitpicking style without automation
→ Use formatters (black, prettier, gofmt)

❌ Blocking PRs over minor issues
→ Approve with suggestions for follow-up

❌ Reviewing only for bugs
→ Also review for maintainability, performance, security

❌ Being overly critical without praise
→ Balance criticism with appreciation

❌ Reviewing too slowly (> 48 hours)
→ Review within 24 hours or reassign

❌ Rubber-stamping without reading
→ Actually review the code

❌ Rewriting code to match your style
→ Respect author's approach if it's reasonable
```

---

## Code Examples

### Python: Good vs Bad PR Structure

**Bad: Too Large**:
```python
# PR: Implement entire user management system (1500 lines)
# - User model, authentication, authorization, profile, settings
# - Impossible to review thoroughly
```

**Good: Focused PRs**:
```python
# PR 1: Add User model and migrations (100 lines)
class User(models.Model):
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

# PR 2: Add authentication endpoints (150 lines)
@api.post("/auth/login")
def login(email: str, password: str) -> Token:
    user = User.get_by_email(email)
    if not user or not user.verify_password(password):
        raise AuthenticationError()
    return create_token(user.id)

# PR 3: Add profile endpoints (120 lines)
# PR 4: Add integration tests (100 lines)
```

---

### Go: Reviewable Test Structure

**Bad: Unclear Test**:
```go
func TestUser(t *testing.T) {
    // What is this testing?
    u := User{Email: "test@example.com"}
    if u.Email != "test@example.com" {
        t.Fail()
    }
}
```

**Good: Clear Test with Table-Driven Approach**:
```go
func TestUserEmailValidation(t *testing.T) {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {name: "valid email", email: "user@example.com", wantErr: false},
        {name: "missing @", email: "userexample.com", wantErr: true},
        {name: "empty", email: "", wantErr: true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            u := User{Email: tt.email}
            err := u.Validate()
            if (err != nil) != tt.wantErr {
                t.Errorf("got error %v, wantErr %v", err, tt.wantErr)
            }
        })
    }
}
```

---

### TypeScript: Reviewable Component Structure

**Bad: God Component**:
```typescript
// Bad: 800-line component doing everything
export function UserDashboard() {
  // Authentication logic
  // Data fetching
  // Form handling
  // Validation
  // Rendering
  // Hard to review!
}
```

**Good: Separated Concerns**:
```typescript
// Good: Small, focused components
export function UserDashboard() {
  const { user } = useAuth();
  const { profile, loading } = useUserProfile(user.id);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <ProfileHeader profile={profile} />
      <ProfileForm profile={profile} onSave={handleSave} />
    </div>
  );
}

// Each component is small, testable, reviewable
```

---

## Level 3: Resources

For deep-dive learning and production-ready tools, see the `resources/` directory:

### Reference Materials
- **REFERENCE.md** (~900 lines): Comprehensive code review guide
  - Complete review checklist (design, functionality, complexity, tests, naming, comments)
  - Writing effective review comments (tone, structure, severity levels)
  - Handling disagreements and conflict resolution
  - Common code smells and fixes
  - Review automation (linters, formatters, security scanners for Python, JavaScript, TypeScript, Rust, Go)
  - GitHub PR workflows and branch protection
  - Review metrics (turnaround time, review depth, defect escape rate)

### Scripts (`resources/scripts/`)
- **review_pr.py**: Automated PR review script
  - Runs linters, checks tests, analyzes diff
  - Detects common issues (debug statements, secrets, TODOs)
  - Generates human or JSON reports
  - CLI: `./review_pr.py --base main --json`

- **analyze_review_metrics.py**: GitHub PR metrics analyzer
  - Tracks turnaround time, review depth, iteration count
  - Reviewer leaderboard
  - PR size distribution
  - CLI: `./analyze_review_metrics.py --repo owner/repo --days 30 --json`

- **generate_review_checklist.sh**: Custom checklist generator
  - Creates checklists by PR type (feature, bugfix, security, refactor, docs)
  - Language-specific checks (Python, JavaScript, TypeScript, Rust, Go)
  - Markdown or JSON output
  - CLI: `./generate_review_checklist.sh --type security --lang python --output checklist.md`

### Examples (`resources/examples/`)
- **github/PULL_REQUEST_TEMPLATE.md**: Production-ready PR template
- **github/code-review-workflow.yml**: Complete GitHub Actions workflow
  - Linting, security scanning, test execution
  - PR size analysis with automated comments
  - Reviewer assignment based on CODEOWNERS
- **python/automated_review_checks.py**: Python code reviewer
  - Checks imports, function length, complexity, documentation, naming, anti-patterns, security
- **checklists/security-review.md**: Comprehensive security checklist
  - Authentication, authorization, input validation, data protection, common vulnerabilities
- **checklists/performance-review.md**: Performance optimization checklist
  - Database queries, algorithms, memory, network I/O, frontend performance

All scripts are executable, documented, and production-ready.

---

## Related Skills

- **engineering-code-quality**: SOLID principles, code smells, metrics
- **engineering-refactoring-patterns**: When and how to refactor
- **engineering-test-driven-development**: Writing testable code
- **engineering-technical-debt**: Managing and prioritizing tech debt
- **engineering-continuous-integration**: Automating review checks

---

## References

- [Google Engineering Practices](https://google.github.io/eng-practices/review/)
- [Microsoft Code Review Guidelines](https://learn.microsoft.com/en-us/azure/devops/repos/git/review-pull-requests)
- [Conventional Comments](https://conventionalcomments.org/)
- [GitHub PR Best Practices](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests)
