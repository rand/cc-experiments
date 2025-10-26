---
name: collaboration-github-repository-management
description: Repository creation, configuration, branch protection, tags, releases, and GitHub CLI operations
---

# GitHub Repository Management

**Scope**: Repository creation and configuration, branch management, branch protection rules, tags and releases, GitHub CLI operations, repository settings and templates

**Lines**: ~280

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating and configuring new GitHub repositories
- Setting up branch protection rules and required reviews
- Managing releases with semantic versioning and release notes
- Using GitHub CLI for repository operations
- Configuring repository settings: webhooks, secrets, environments
- Creating repository, issue, and PR templates
- Setting default branches and branch naming conventions
- Generating changelogs and managing tags

---

## Core Concepts

### Repository Structure

**Key components**:
- **Default branch**: Main development branch (main or master)
- **Protected branches**: Branches with enforcement rules
- **Environments**: Deployment targets with secrets and protection rules
- **Webhooks**: HTTP callbacks for repository events
- **Secrets**: Encrypted environment variables
- **Templates**: Standardized issue and PR formats

```bash
# Repository hierarchy
repository/
├── .github/
│   ├── workflows/          # GitHub Actions
│   ├── ISSUE_TEMPLATE/     # Issue templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml
├── src/                    # Source code
├── README.md
├── LICENSE
└── SECURITY.md
```

### Branch Protection

**Protection rules enforce**:
- Required status checks before merging
- Required reviews (count and approval)
- Dismissal of stale reviews
- Required linear history
- Signed commits
- Administrator enforcement

### GitHub CLI Workflow

```bash
# Authentication flow
gh auth login
gh auth status

# Repository operations
gh repo create → gh repo view → gh repo edit
  ↓
Branch protection → PR workflow → Release
  ↓
Cleanup and archival
```

---

## Patterns

### Creating Repositories with GitHub CLI

```bash
# Create new repository (interactive)
gh repo create my-project

# Create with flags
gh repo create my-project \
  --public \
  --description "Project description" \
  --gitignore Node \
  --license MIT

# Create from template
gh repo create my-project \
  --template owner/template-repo \
  --private

# Create and clone
gh repo create my-project --clone

# Initialize existing directory
cd existing-project
gh repo create --source=. --remote=origin --push
```

### Repository Configuration

```bash
# View repository details
gh repo view owner/repo

# Edit repository settings
gh repo edit owner/repo \
  --description "New description" \
  --homepage "https://example.com" \
  --default-branch main \
  --enable-issues=true \
  --enable-wiki=false

# Archive repository
gh repo archive owner/repo

# Delete repository (careful!)
gh repo delete owner/repo --confirm
```

### Branch Protection Rules

**Via GitHub CLI**:
```bash
# Enable branch protection (requires API)
gh api repos/owner/repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci/build","ci/test"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2}' \
  --field restrictions=null
```

**Via Web UI** (recommended for complex rules):
1. Settings → Branches → Add rule
2. Configure:
   - Require pull request before merging
   - Require approvals: 1-6 reviewers
   - Dismiss stale reviews when new commits pushed
   - Require review from Code Owners
   - Require status checks to pass
   - Require conversation resolution
   - Require signed commits
   - Require linear history

**Protection rule pattern**:
```yaml
# Common protection for main branch
Branch pattern: main
✅ Require pull request reviews (2 approvals)
✅ Dismiss stale reviews
✅ Require review from Code Owners
✅ Require status checks (ci/build, ci/test)
✅ Require branches to be up to date
✅ Require conversation resolution
✅ Include administrators
```

### Tags and Releases

**Creating tags**:
```bash
# Create annotated tag (recommended)
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create lightweight tag
git tag v1.0.0
git push origin v1.0.0

# List tags
git tag -l

# Delete tag
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

**Semantic versioning**:
```
MAJOR.MINOR.PATCH (1.2.3)

MAJOR: Breaking changes (1.x.x → 2.0.0)
MINOR: New features, backward compatible (1.2.x → 1.3.0)
PATCH: Bug fixes, backward compatible (1.2.3 → 1.2.4)

Pre-release: 1.0.0-alpha.1, 1.0.0-beta.2, 1.0.0-rc.1
```

**Creating releases with GitHub CLI**:
```bash
# Create release from tag
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes "Release notes here"

# Create release with assets
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes-file CHANGELOG.md \
  dist/*.tar.gz dist/*.zip

# Create draft release
gh release create v1.0.0 \
  --draft \
  --title "Version 1.0.0" \
  --notes "Draft release"

# Generate release notes automatically
gh release create v1.0.0 --generate-notes

# List releases
gh release list

# View specific release
gh release view v1.0.0

# Download release assets
gh release download v1.0.0
```

### Repository Templates

**Issue template** (.github/ISSUE_TEMPLATE/bug_report.md):
```markdown
---
name: Bug Report
about: Report a bug to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Environment
- OS: [e.g., macOS 14.0]
- Browser: [e.g., Chrome 120]
- Version: [e.g., 1.2.3]

## Additional Context
Screenshots, logs, or other context.
```

**Pull request template** (.github/PULL_REQUEST_TEMPLATE.md):
```markdown
## Summary
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated

## Related Issues
Closes #123
Related to #456
```

### Repository Secrets and Environments

**Managing secrets with GitHub CLI**:
```bash
# Set repository secret
gh secret set API_KEY < api_key.txt

# Set secret with value
echo "secret-value" | gh secret set SECRET_NAME

# List secrets
gh secret list

# Delete secret
gh secret delete SECRET_NAME

# Set environment secret
gh secret set API_KEY --env production
```

**Configuring environments** (via Web UI):
1. Settings → Environments → New environment
2. Configure:
   - Environment protection rules
   - Required reviewers before deployment
   - Wait timer (delay before deployment)
   - Environment secrets
   - Deployment branches (limit to specific branches)

### Webhooks Configuration

```bash
# Create webhook via API
gh api repos/owner/repo/hooks \
  --method POST \
  --field name=web \
  --field config[url]=https://example.com/webhook \
  --field config[content_type]=json \
  --field events[]="push" \
  --field events[]="pull_request"

# List webhooks
gh api repos/owner/repo/hooks

# Delete webhook
gh api repos/owner/repo/hooks/123 --method DELETE
```

---

## Quick Reference

### GitHub CLI Commands

```bash
# Authentication
gh auth login                    # Authenticate with GitHub
gh auth status                   # Check authentication status
gh auth logout                   # Log out

# Repository operations
gh repo create [name]            # Create repository
gh repo clone owner/repo         # Clone repository
gh repo view [owner/repo]        # View repository details
gh repo edit [owner/repo]        # Edit repository settings
gh repo fork owner/repo          # Fork repository
gh repo sync owner/repo          # Sync fork with upstream

# Release management
gh release create <tag>          # Create release
gh release list                  # List releases
gh release view <tag>            # View release details
gh release download <tag>        # Download release assets
gh release delete <tag>          # Delete release

# Secret management
gh secret set <name>             # Set secret
gh secret list                   # List secrets
gh secret delete <name>          # Delete secret
```

### Semantic Versioning Quick Guide

```
Version format: MAJOR.MINOR.PATCH

Breaking change:     1.0.0 → 2.0.0
New feature:         1.2.0 → 1.3.0
Bug fix:             1.2.3 → 1.2.4

Pre-release tags:
- alpha: 1.0.0-alpha.1
- beta:  1.0.0-beta.1
- rc:    1.0.0-rc.1
```

### Branch Protection Checklist

```
✅ DO: Protect main/production branches
✅ DO: Require 1-2 approvals for PRs
✅ DO: Require status checks to pass
✅ DO: Dismiss stale reviews on new commits
✅ DO: Require conversation resolution
✅ DO: Require linear history for clean git log

❌ DON'T: Allow direct pushes to protected branches
❌ DON'T: Skip status checks for administrators (unless necessary)
❌ DON'T: Allow force pushes to protected branches
```

---

## Anti-Patterns

### ❌ No Branch Protection

```bash
# WRONG: Allow direct pushes to main
# Anyone can push without review
git push origin main
```

**Problems**:
- No code review process
- Untested code reaches production
- No audit trail

```bash
# CORRECT: Require PRs and reviews
# Settings → Branches → Add rule for main
# ✅ Require pull request reviews (2 approvals)
# ✅ Require status checks
```

### ❌ Hardcoded Secrets in Repository

```yaml
# WRONG: Secrets in workflow file
env:
  API_KEY: "sk-abc123xyz"
  DATABASE_PASSWORD: "password123"
```

**Problems**:
- Secrets visible in git history
- Security breach risk
- Difficult to rotate credentials

```yaml
# CORRECT: Use GitHub Secrets
env:
  API_KEY: ${{ secrets.API_KEY }}
  DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}

# Set via CLI
gh secret set API_KEY < api_key.txt
```

### ❌ No Release Process

```bash
# WRONG: Push tags without documentation
git tag v1.0.0 && git push origin v1.0.0
# No release notes, no changelog
```

**Problems**:
- Users don't know what changed
- No downloadable assets
- Difficult to track versions

```bash
# CORRECT: Create proper releases
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes-file CHANGELOG.md \
  dist/*.tar.gz

# Include:
# - Version number (semantic versioning)
# - Release notes (what changed)
# - Downloadable assets (binaries, archives)
```

### ❌ Missing Templates

**Problems**:
- Inconsistent issue reports
- Missing information in PRs
- Wasted time asking for details

```bash
# CORRECT: Create templates
mkdir -p .github/ISSUE_TEMPLATE

# Add bug report template
# Add feature request template
# Add pull request template

# Commit templates
git add .github/
git commit -m "Add issue and PR templates"
```

### ❌ Default Branch Named 'master'

```bash
# WRONG: Using outdated default branch name
# main branch is called 'master'
```

```bash
# CORRECT: Use 'main' as default branch
# Rename existing repository
git branch -m master main
git push -u origin main

# Update default branch on GitHub
gh repo edit owner/repo --default-branch main

# Delete old remote branch
git push origin --delete master
```

---

## Related Skills

- `collaboration/github/github-pull-requests.md` - PR workflow and code review process
- `collaboration/github/github-actions-workflows.md` - CI/CD automation with branch protection
- `collaboration/github/github-security-features.md` - Security settings and dependency management
- `collaboration/github/github-issues-projects.md` - Issue templates and project management
- `cicd/ci-security.md` - Secret management best practices
- `version-control/git-branching-strategies.md` - Branch naming and workflow strategies

---

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)
