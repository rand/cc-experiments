---
name: collaboration-github-pull-requests
description: Pull request workflow, code review, merge strategies, PR checks, and collaboration best practices
---

# GitHub Pull Requests

**Scope**: PR workflow, draft PRs, code review process, merge strategies, PR checks, auto-merge, PR templates, and collaboration best practices

**Lines**: ~320

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating pull requests for code review
- Reviewing code and providing feedback
- Choosing merge strategies (merge commit, squash, rebase)
- Setting up required status checks and CODEOWNERS
- Configuring auto-merge and merge queues
- Creating PR templates and conventions
- Managing PR lifecycle from draft to merged
- Responding to review feedback and resolving conversations

---

## Core Concepts

### Pull Request Lifecycle

```
Feature Branch → Draft PR → Ready for Review → Reviews → Approved → Merged
                    ↓            ↓              ↓          ↓
                Comments    Requested     Changes    Status
                            Changes       Made       Checks
```

**States**:
- **Draft**: Work in progress, not ready for review
- **Open**: Ready for review, awaiting feedback
- **Changes requested**: Reviewer requested modifications
- **Approved**: Reviewer approved changes
- **Merged**: PR integrated into target branch
- **Closed**: PR rejected or abandoned

### Code Review Process

**Review types**:
- **Comment**: General feedback without approval
- **Approve**: Changes look good, ready to merge
- **Request changes**: Must address issues before merging

**Review scope**:
- Code correctness and logic
- Test coverage
- Performance implications
- Security considerations
- Code style and readability
- Documentation completeness

### Merge Strategies

**Merge commit** (preserves full history):
```
feature-branch: A → B → C
                         ↓
main:          D → E → M (merge commit)
```

**Squash merge** (single commit):
```
feature-branch: A → B → C
                         ↓ squash
main:          D → E → S (squashed commit)
```

**Rebase merge** (linear history):
```
feature-branch: A → B → C
                         ↓ rebase
main:          D → E → A' → B' → C'
```

---

## Patterns

### Creating Pull Requests with GitHub CLI

```bash
# Create PR from current branch
gh pr create

# Create with title and body
gh pr create \
  --title "Add user authentication" \
  --body "Implements JWT-based authentication"

# Create from specific branch
gh pr create \
  --base main \
  --head feature/auth

# Create draft PR
gh pr create \
  --draft \
  --title "WIP: Add authentication"

# Create with template
gh pr create \
  --fill    # Use PR template

# Create and assign reviewers
gh pr create \
  --reviewer user1,user2 \
  --assignee @me

# Create with labels
gh pr create \
  --label "enhancement" \
  --label "needs-review"

# Create PR from issue
gh pr create \
  --title "Fix login bug" \
  --body "Closes #123"
```

### Managing Pull Requests

```bash
# List open PRs
gh pr list

# List PRs by state
gh pr list --state merged
gh pr list --state closed

# View PR details
gh pr view 42

# View PR in browser
gh pr view 42 --web

# Check PR status
gh pr status

# Checkout PR locally
gh pr checkout 42

# Update PR
gh pr edit 42 \
  --title "New title" \
  --add-reviewer user3

# Close PR
gh pr close 42

# Reopen PR
gh pr reopen 42
```

### Code Review Workflow

**Requesting reviews**:
```bash
# Request review from users
gh pr edit 42 --add-reviewer user1,user2

# Request review from team
gh api repos/owner/repo/pulls/42/requested_reviewers \
  --method POST \
  --field team_reviewers[]="backend-team"
```

**Providing reviews**:
```bash
# Approve PR
gh pr review 42 --approve

# Request changes
gh pr review 42 --request-changes \
  --body "Please add tests for edge cases"

# Comment without approval
gh pr review 42 --comment \
  --body "Looks good overall, minor suggestions"

# Review with inline comments (interactive)
gh pr review 42
```

**Review best practices**:
```markdown
## Good Review Comment
**Issue**: The error handling doesn't cover network timeouts.

**Suggestion**: Add timeout handling:
```python
try:
    response = requests.get(url, timeout=30)
except requests.Timeout:
    logger.error(f"Timeout fetching {url}")
    raise
```

**Why**: Prevents hanging requests and improves debugging.
```

**Bad review comment**:
```markdown
This is wrong.
```
(No context, no suggestion, not constructive)

### Merge Strategies

**When to use each strategy**:

**Merge commit** - Use when:
- Preserving detailed commit history matters
- Feature branch has meaningful commit messages
- Need to track when feature was integrated
- Multiple developers collaborated on branch

```bash
# Merge with merge commit
gh pr merge 42 --merge

# Or via API
gh api repos/owner/repo/pulls/42/merge \
  --method PUT \
  --field merge_method=merge
```

**Squash merge** - Use when:
- Feature branch has messy commit history
- Want clean main branch with one commit per feature
- Commit messages like "fix typo", "wip", etc.
- Small features or bug fixes

```bash
# Squash and merge
gh pr merge 42 --squash

# Customize squash commit message
gh pr merge 42 --squash \
  --subject "Add user authentication" \
  --body "Implements JWT-based auth with refresh tokens"
```

**Rebase merge** - Use when:
- Want linear history without merge commits
- Commits are well-crafted and meaningful
- Project requires linear git history
- Each commit is atomic and tested

```bash
# Rebase and merge
gh pr merge 42 --rebase
```

### Auto-Merge Configuration

```bash
# Enable auto-merge when checks pass
gh pr merge 42 --auto --squash

# Auto-merge with merge commit
gh pr merge 42 --auto --merge

# Disable auto-merge
gh api repos/owner/repo/pulls/42 \
  --method DELETE \
  -f auto_merge=null
```

**Auto-merge requirements**:
- All required status checks pass
- Required reviews approved
- No conflicting changes
- Branch is up to date (if required)

### PR Checks and Status

**Required checks** (configure in branch protection):
```yaml
# Example: GitHub Actions workflow
name: PR Checks
on: pull_request

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
```

**Check PR status**:
```bash
# View PR checks
gh pr checks 42

# Wait for checks to complete
gh pr checks 42 --watch

# View specific check logs
gh run view <run-id>
```

### CODEOWNERS File

**Configuration** (.github/CODEOWNERS):
```
# Global owners
* @org/core-team

# Frontend code
/src/frontend/** @org/frontend-team
*.tsx @org/frontend-team
*.css @org/design-team

# Backend code
/src/backend/** @org/backend-team
/src/api/** @org/api-team

# Infrastructure
/infrastructure/** @org/devops-team
/.github/workflows/** @org/devops-team

# Documentation
/docs/** @org/docs-team
*.md @org/docs-team

# Specific files require multiple approvals
/SECURITY.md @org/security-team @org/core-team
/package.json @org/core-team
```

**Benefits**:
- Automatic reviewer assignment
- Ensures domain experts review changes
- Enforces required reviews for critical files
- Distributes review workload

### PR Templates

**Basic PR template** (.github/PULL_REQUEST_TEMPLATE.md):
```markdown
## Description
What does this PR do?

## Motivation and Context
Why is this change needed? What problem does it solve?

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that breaks existing functionality)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## How Has This Been Tested?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing
- [ ] Not applicable

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
<!-- Add screenshots here -->

## Related Issues
Closes #<issue_number>
Related to #<issue_number>
```

**Multiple templates** (.github/PULL_REQUEST_TEMPLATE/):
```
.github/
└── PULL_REQUEST_TEMPLATE/
    ├── feature.md       # For new features
    ├── bugfix.md        # For bug fixes
    └── hotfix.md        # For urgent production fixes
```

**Usage**:
```bash
# Create PR with specific template
gh pr create --template feature.md
```

---

## Quick Reference

### GitHub CLI PR Commands

```bash
# Create and manage
gh pr create [flags]             # Create pull request
gh pr list                       # List open PRs
gh pr view <number>              # View PR details
gh pr checkout <number>          # Check out PR locally
gh pr status                     # Show status of relevant PRs

# Review workflow
gh pr review <number> [flags]    # Review PR (approve/comment/request changes)
gh pr checks <number>            # Show PR status checks
gh pr diff <number>              # View PR diff

# Merge and close
gh pr merge <number> [flags]     # Merge PR (--merge/--squash/--rebase)
gh pr close <number>             # Close PR
gh pr reopen <number>            # Reopen closed PR

# Modifications
gh pr edit <number> [flags]      # Edit PR (title, body, reviewers, etc.)
gh pr ready <number>             # Mark draft PR as ready
```

### Merge Strategy Decision Tree

```
Do commits have meaningful messages?
├─ Yes: Preserve them?
│  ├─ Yes: merge commit or rebase
│  └─ No:  squash
└─ No:  squash

Need to track when feature was merged?
├─ Yes: merge commit
└─ No:  squash or rebase

Project requires linear history?
├─ Yes: rebase (or squash)
└─ No:  any strategy works
```

### Review Best Practices

```
✅ DO: Be specific about what needs to change
✅ DO: Provide code suggestions when possible
✅ DO: Explain why changes are needed
✅ DO: Acknowledge good code
✅ DO: Ask questions instead of demanding changes
✅ DO: Review within 24-48 hours

❌ DON'T: Use vague comments like "this is wrong"
❌ DON'T: Nitpick over minor style issues (use linters)
❌ DON'T: Block PRs for personal preferences
❌ DON'T: Approve without actually reviewing
❌ DON'T: Request changes without explanation
```

---

## Anti-Patterns

### ❌ Large, Monolithic PRs

```bash
# WRONG: 50 files changed, 5000 lines added
# Touches frontend, backend, database, and infrastructure
# Impossible to review effectively
```

**Problems**:
- Difficult to review thoroughly
- Higher chance of bugs slipping through
- Long review cycles
- Merge conflicts likely

```bash
# CORRECT: Break into smaller PRs
# PR 1: Database schema changes
# PR 2: Backend API updates
# PR 3: Frontend integration
# PR 4: Documentation updates

# Each PR: 3-5 files, 200-400 lines
```

**Guidelines**:
- Keep PRs under 400 lines of code
- One feature/fix per PR
- Split large features into incremental PRs
- Use feature flags for incomplete features

### ❌ No PR Description

```markdown
# WRONG
Title: Update code
Description: (empty)
```

**Problems**:
- Reviewers don't understand context
- No record of why changes were made
- Difficult to search git history later

```markdown
# CORRECT
Title: Add rate limiting to API endpoints

Description:
Implements rate limiting to prevent API abuse.

- Adds Redis-based rate limiter
- Configurable limits per endpoint
- Returns 429 status when exceeded
- Includes tests for rate limit enforcement

Closes #456
Related to #123
```

### ❌ Ignoring Review Feedback

```bash
# WRONG: Mark PR as ready without addressing comments
# Reviewer: "Please add error handling"
# Author: (ignores feedback and merges)
```

**Problems**:
- Disrespects reviewer's time
- Introduces known issues
- Damages team collaboration
- Defeats purpose of code review

```bash
# CORRECT: Address all feedback
# 1. Make requested changes
# 2. Respond to comments
# 3. Request re-review
# 4. Wait for approval

# If you disagree:
# - Explain your reasoning
# - Discuss alternatives
# - Seek consensus
# - Don't merge until resolved
```

### ❌ Force Pushing After Reviews

```bash
# WRONG: Rewrite history after review started
git push --force origin feature/auth
```

**Problems**:
- Invalidates existing reviews
- Reviewers lose context
- Inline comments become orphaned
- Difficult to see what changed

```bash
# CORRECT: Add fixup commits during review
git commit -m "Address review feedback: add tests"
git push origin feature/auth

# Squash when merging (if using squash merge)
gh pr merge 42 --squash
```

### ❌ Merging Without Status Checks

```bash
# WRONG: Override failing checks and merge
# Tests failing, linter errors, build broken
# Merge anyway because "it works on my machine"
```

**Problems**:
- Breaks main branch
- Blocks other developers
- Erodes confidence in CI/CD
- Creates firefighting situations

```bash
# CORRECT: Fix issues before merging
# 1. Ensure all status checks pass
# 2. Fix failing tests
# 3. Resolve linter errors
# 4. Update branch if behind main
# 5. Merge only when green

# Enable branch protection to prevent this
# Settings → Branches → Require status checks
```

---

## Related Skills

- `collaboration/github/github-repository-management.md` - Branch protection and CODEOWNERS setup
- `collaboration/github/github-actions-workflows.md` - CI/CD checks for PRs
- `collaboration/github/github-issues-projects.md` - Linking PRs to issues
- `version-control/git-branching-strategies.md` - Feature branch workflows
- `cicd/ci-testing-strategy.md` - Running tests in PR checks
- `code-review/effective-code-review.md` - Code review best practices

---

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)
