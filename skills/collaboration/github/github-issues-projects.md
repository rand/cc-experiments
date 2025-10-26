---
name: collaboration-github-issues-projects
description: Issue management, templates, labels, milestones, GitHub Projects, and issue linking workflows
---

# GitHub Issues and Projects

**Scope**: Issue creation and templates, labels and organization, milestones, GitHub Projects (beta), issue linking, Discussions vs Issues, and project automation

**Lines**: ~290

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Creating and managing GitHub issues
- Setting up issue templates for consistent reporting
- Organizing issues with labels and milestones
- Using GitHub Projects for project management
- Linking issues to pull requests and commits
- Choosing between Discussions and Issues
- Automating issue triage and project workflows
- Planning releases with milestones
- Tracking work with project boards

---

## Core Concepts

### Issue Lifecycle

```
Created → Triaged → Assigned → In Progress → PR Linked → Closed
   ↓         ↓          ↓           ↓            ↓          ↓
Labels    Priority   Owner     Development    Review    Resolved
```

**States**:
- **Open**: Active issue requiring attention
- **Closed**: Resolved, won't fix, or duplicate
- **Locked**: Prevents further comments
- **Pinned**: Highlighted at top of issues list

### Label System

**Categories**:
- **Type**: bug, enhancement, documentation, question
- **Priority**: critical, high, medium, low
- **Status**: needs-triage, in-progress, blocked, ready
- **Area**: frontend, backend, api, infrastructure
- **Effort**: good-first-issue, help-wanted, complex

### GitHub Projects Structure

**New Projects (beta)**:
- Table view, board view, roadmap view
- Custom fields (status, priority, size, iteration)
- Automation rules
- Filtering and grouping
- Cross-repository support

---

## Patterns

### Creating Issues with GitHub CLI

```bash
# Create basic issue
gh issue create

# Create with title and body
gh issue create \
  --title "Fix login timeout bug" \
  --body "Users are getting timeout errors after 30 seconds"

# Create with labels and assignees
gh issue create \
  --title "Add dark mode support" \
  --label enhancement,frontend \
  --assignee @me

# Create from template
gh issue create --template bug_report.md

# Create with milestone
gh issue create \
  --title "Optimize database queries" \
  --milestone "v2.0.0"

# Create from file
gh issue create --title "Bug report" --body-file issue.md

# List issues
gh issue list

# List with filters
gh issue list --label bug --state open
gh issue list --assignee @me
gh issue list --milestone "v1.0.0"

# View issue
gh issue view 123

# Close issue
gh issue close 123 --comment "Fixed in PR #456"

# Reopen issue
gh issue reopen 123
```

### Issue Templates

**Bug report template** (.github/ISSUE_TEMPLATE/bug_report.yml):
```yaml
name: Bug Report
description: File a bug report
title: "[Bug]: "
labels: ["bug", "needs-triage"]
assignees:
  - octocat
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!

  - type: input
    id: contact
    attributes:
      label: Contact Details
      description: How can we get in touch with you if we need more info?
      placeholder: ex. email@example.com
    validations:
      required: false

  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us, what did you expect to happen?
      placeholder: Tell us what you see!
      value: "A bug happened!"
    validations:
      required: true

  - type: dropdown
    id: version
    attributes:
      label: Version
      description: What version of our software are you running?
      options:
        - 1.0.2 (Default)
        - 1.0.3 (Edge)
      default: 0
    validations:
      required: true

  - type: dropdown
    id: browsers
    attributes:
      label: What browsers are you seeing the problem on?
      multiple: true
      options:
        - Firefox
        - Chrome
        - Safari
        - Microsoft Edge

  - type: textarea
    id: logs
    attributes:
      label: Relevant log output
      description: Please copy and paste any relevant log output. This will be automatically formatted into code, so no need for backticks.
      render: shell

  - type: checkboxes
    id: terms
    attributes:
      label: Code of Conduct
      description: By submitting this issue, you agree to follow our [Code of Conduct](https://example.com)
      options:
        - label: I agree to follow this project's Code of Conduct
          required: true
```

**Feature request template** (.github/ISSUE_TEMPLATE/feature_request.md):
```markdown
---
name: Feature Request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Problem Statement
A clear description of the problem this feature would solve.
Ex. I'm always frustrated when [...]

## Proposed Solution
A clear description of what you want to happen.

## Alternatives Considered
Any alternative solutions or features you've considered.

## Additional Context
Add any other context, screenshots, or examples about the feature request here.

## Implementation Notes (Optional)
If you have ideas about how to implement this, share them here.
```

**Template chooser** (.github/ISSUE_TEMPLATE/config.yml):
```yaml
blank_issues_enabled: false
contact_links:
  - name: Community Support
    url: https://github.com/org/repo/discussions
    about: Please ask questions and discuss ideas here
  - name: Security Issue
    url: https://github.com/org/repo/security/advisories/new
    about: Report security vulnerabilities privately
```

### Label Management

```bash
# Create label
gh label create "priority:high" \
  --description "High priority issue" \
  --color "d73a4a"

# List labels
gh label list

# Edit label
gh label edit "bug" --color "ff0000"

# Delete label
gh label delete "old-label"

# Add labels to issue
gh issue edit 123 --add-label "bug,priority:high"

# Remove labels
gh issue edit 123 --remove-label "needs-triage"
```

**Standard label set**:
```
Type:
  bug           (d73a4a - red)
  enhancement   (a2eeef - blue)
  documentation (0075ca - dark blue)
  question      (d876e3 - purple)

Priority:
  priority:critical  (b60205 - dark red)
  priority:high      (d93f0b - orange)
  priority:medium    (fbca04 - yellow)
  priority:low       (0e8a16 - green)

Status:
  needs-triage      (ffffff - white)
  in-progress       (1d76db - blue)
  blocked           (e99695 - light red)
  ready-for-review  (c2e0c6 - light green)

Effort:
  good-first-issue  (7057ff - purple)
  help-wanted       (008672 - teal)
  complex           (c5def5 - light blue)
```

### Milestones

```bash
# Create milestone
gh api repos/owner/repo/milestones \
  --method POST \
  --field title="v2.0.0" \
  --field description="Major release with new features" \
  --field due_on="2025-12-31T23:59:59Z"

# List milestones
gh api repos/owner/repo/milestones

# Assign issue to milestone
gh issue edit 123 --milestone "v2.0.0"

# View milestone progress
gh api repos/owner/repo/milestones | \
  jq '.[] | {title, open_issues, closed_issues}'
```

**Milestone planning**:
```
v1.0.0 (MVP)
├── Authentication system
├── Core API endpoints
├── Basic UI components
└── Initial documentation

v1.1.0 (Enhancements)
├── Advanced search
├── Export functionality
├── Performance improvements
└── Expanded docs

v2.0.0 (Major Release)
├── New architecture
├── Breaking API changes
├── Modern UI redesign
└── Migration guide
```

### GitHub Projects (New Beta)

**Creating a project** (via Web UI):
1. Click "Projects" → "New project"
2. Choose template: Board, Table, Roadmap
3. Add custom fields:
   - Status (Todo, In Progress, Done)
   - Priority (Low, Medium, High, Critical)
   - Size (S, M, L, XL)
   - Iteration (Sprint 1, Sprint 2, etc.)

**Adding items**:
```bash
# Add issue to project (requires project ID)
gh project item-add <project-id> --owner @me --url https://github.com/owner/repo/issues/123

# Or via web UI:
# 1. Open project
# 2. Click "Add item"
# 3. Search for issues/PRs
```

**Automation example**:
```yaml
# Auto-add issues to project
# Settings → Actions → New workflow
name: Add to project
on:
  issues:
    types: [opened]

jobs:
  add-to-project:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/add-to-project@v0.5.0
        with:
          project-url: https://github.com/orgs/org/projects/1
          github-token: ${{ secrets.ADD_TO_PROJECT_PAT }}
```

**Project views**:
- **Table**: Spreadsheet-like view with custom fields
- **Board**: Kanban board grouped by status
- **Roadmap**: Timeline view with date fields

### Issue Linking

**Link issues to PRs**:
```bash
# In PR description or commit message
Closes #123
Fixes #456
Resolves #789

# Multiple issues
Closes #123, #456, #789

# Cross-repository
Fixes owner/other-repo#123
```

**Keywords that auto-close issues**:
- `close`, `closes`, `closed`
- `fix`, `fixes`, `fixed`
- `resolve`, `resolves`, `resolved`

**Example PR description**:
```markdown
## Summary
Adds rate limiting to API endpoints.

## Changes
- Implements Redis-based rate limiter
- Adds configuration for limits per endpoint
- Includes tests

Closes #456
Related to #123, #234
```

**Link issues to commits**:
```bash
git commit -m "Add rate limiting

Implements Redis-based rate limiter to prevent API abuse.

Fixes #456"
```

### Discussions vs Issues

**Use Discussions for**:
- Questions and answers
- Ideas and brainstorming
- Announcements
- Community conversation
- Open-ended topics

**Use Issues for**:
- Bug reports
- Specific feature requests
- Actionable tasks
- Trackable work items
- Release planning

```bash
# Create discussion (via Web UI)
# Discussions tab → New discussion
# Choose category: Announcements, General, Ideas, Q&A, Show and tell

# Convert issue to discussion
gh issue close 123 --comment "Moving to Discussions"
# Then manually create discussion
```

---

## Quick Reference

### GitHub CLI Issue Commands

```bash
# Create and manage
gh issue create [flags]          # Create issue
gh issue list [flags]            # List issues
gh issue view <number>           # View issue details
gh issue edit <number> [flags]   # Edit issue

# Workflow
gh issue close <number>          # Close issue
gh issue reopen <number>         # Reopen issue
gh issue pin <number>            # Pin issue
gh issue unpin <number>          # Unpin issue

# Labels and milestones
gh label create <name> [flags]   # Create label
gh label list                    # List labels
```

### Issue Linking Keywords

```
Auto-close keywords:
  close, closes, closed
  fix, fixes, fixed
  resolve, resolves, resolved

Usage in PRs or commits:
  Closes #123
  Fixes #456
  Resolves owner/repo#789

Reference only (no auto-close):
  Related to #123
  See also #456
  Part of #789
```

### Project Management Best Practices

```
✅ DO: Use templates for consistent issue reporting
✅ DO: Triage new issues within 24-48 hours
✅ DO: Apply labels for categorization and filtering
✅ DO: Use milestones for release planning
✅ DO: Link PRs to issues for traceability
✅ DO: Close stale issues with explanation
✅ DO: Pin important issues for visibility

❌ DON'T: Leave issues unlabeled
❌ DON'T: Create duplicate issues without checking
❌ DON'T: Use issues for questions (use Discussions)
❌ DON'T: Close issues without resolution or explanation
❌ DON'T: Ignore issue templates
```

---

## Anti-Patterns

### ❌ No Issue Templates

```markdown
# WRONG: Users create inconsistent issues
Title: it doesn't work
Body: when I click the button nothing happens
```

**Problems**:
- Missing critical information
- Time wasted asking for details
- Difficult to reproduce bugs
- Inconsistent issue quality

```markdown
# CORRECT: Use structured templates
Title: [Bug] Login button unresponsive on mobile Safari

**Environment:**
- OS: iOS 17.0
- Browser: Safari 17.0
- App Version: 1.2.3

**Steps to Reproduce:**
1. Open app on iPhone
2. Navigate to login page
3. Tap "Login" button
4. Nothing happens

**Expected:** Login modal appears
**Actual:** No response to tap

**Console Errors:**
TypeError: Cannot read property 'addEventListener' of null
```

### ❌ Poor Label Organization

```bash
# WRONG: Random, inconsistent labels
bug1, bug2, needs work, todo, urgent, ASAP, help
```

**Problems**:
- Can't filter effectively
- No consistent categorization
- Unclear priorities
- Difficult to track progress

```bash
# CORRECT: Structured label system
Type:        bug, enhancement, documentation
Priority:    priority:critical, priority:high, priority:medium, priority:low
Status:      needs-triage, in-progress, blocked
Area:        frontend, backend, api, infrastructure
Effort:      good-first-issue, help-wanted
```

### ❌ Issues Not Linked to PRs

```bash
# WRONG: PR merged without closing issue
# Issue #123 remains open
# No connection between fix and issue
```

**Problems**:
- Issues stay open after fix
- No audit trail
- Difficult to find related code changes
- Duplicated work

```bash
# CORRECT: Link PRs to issues
# In PR description:
Fixes #123

# Or in commit message:
git commit -m "Add rate limiting

Implements Redis-based rate limiter.

Closes #123"

# Result: Issue automatically closed when PR merges
```

### ❌ Ignoring Stale Issues

```bash
# WRONG: 500 open issues, many years old
# No activity on 300+ issues
# Overwhelms actual work
```

**Problems**:
- Can't see what's actually active
- Outdated issues confuse contributors
- No clear priorities
- Looks unmaintained

```bash
# CORRECT: Manage stale issues
# 1. Use Stale bot or GitHub Actions
# 2. Close inactive issues after 60-90 days
# 3. Add "stale" label after 30 days warning
# 4. Allow "keep-alive" label to prevent closure

# Example workflow:
# .github/workflows/stale.yml
name: Close stale issues
on:
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  stale:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/stale@v8
        with:
          stale-issue-message: 'This issue is stale because it has been open 60 days with no activity. Remove stale label or comment or this will be closed in 7 days.'
          close-issue-message: 'Closing due to inactivity.'
          days-before-stale: 60
          days-before-close: 7
          exempt-issue-labels: 'keep-alive,roadmap'
```

### ❌ Using Issues for Discussions

```bash
# WRONG: Creating issues for questions
Title: How do I configure the API?
Body: I don't understand the documentation...
```

**Problems**:
- Clutters issue tracker
- Not actionable work items
- Difficult to search for bugs
- Wastes project management overhead

```bash
# CORRECT: Use Discussions for questions
# Enable Discussions in repository
# Settings → Features → Discussions

# Create categories:
# - Q&A: Questions and answers
# - Ideas: Feature brainstorming
# - General: Community chat
# - Announcements: Project updates

# Use Issues only for:
# - Bug reports
# - Specific feature requests
# - Actionable tasks
```

---

## Related Skills

- `collaboration/github/github-pull-requests.md` - Linking PRs to issues
- `collaboration/github/github-repository-management.md` - Issue and PR templates setup
- `collaboration/github/github-actions-workflows.md` - Automating issue workflows
- `project-management/agile-workflows.md` - Sprint planning with milestones
- `documentation/technical-writing.md` - Writing clear issue descriptions

---

**Last Updated**: 2025-10-25

**Format Version**: 1.0 (Atomic)
