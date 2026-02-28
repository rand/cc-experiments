---
name: engineering-git-workflows
description: Git workflow mastery including branch strategies, rebase vs merge, commit conventions, conflict resolution, worktree usage, and interactive rebase
---


# Git Workflows

**Scope**: Branch strategies, commit conventions, rebase, merge, worktrees, conflict resolution, hooks
**Lines**: ~280
**Last Updated**: 2026-02-02

## When to Use This Skill

Activate this skill when:
- Setting up Git workflow for a new team or project
- Choosing between rebase and merge strategies
- Writing commit messages and enforcing conventions
- Resolving complex merge conflicts
- Working on multiple tasks in parallel with worktrees
- Cleaning up branch history before merging
- Setting up Git hooks for quality enforcement

## Core Concepts

### Branch Strategies

#### Trunk-Based Development
All developers commit to `main` (or short-lived branches that merge within 1-2 days). Feature flags gate incomplete work.

**When to use**: Small teams, high trust, strong CI, continuous deployment.

```bash
git checkout -b feat/add-search    # branch from main
# work for 1-2 days max
git push -u origin feat/add-search
# open PR, get review, merge same day
```

**Advantages**: Minimal merge conflicts, continuous integration, fast feedback.
**Risks**: Requires strong CI and feature flag discipline.

#### GitHub Flow
Single `main` branch. Feature branches for all changes. PRs for review. Merge to main triggers deploy.

**When to use**: Most teams. Simple, well-understood, works with GitHub/GitLab natively.

```
main ──●──●──●──●──●──●──●──
        \       /
feat/x   ●──●──●
```

#### GitFlow
`main` (production), `develop` (integration), `feature/*`, `release/*`, `hotfix/*` branches.

**When to use**: Versioned software with scheduled releases (mobile apps, SDKs, libraries). Overkill for web services.

```
main    ──●─────────────●──────●──
           \           / \    /
develop     ●──●──●──●    ●──
              \    /
feature/x      ●──
```

**When NOT to use**: Continuous deployment, small teams, web applications. The branch overhead is not worth it.

---

### Commit Message Conventions

Use Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types**:
| Type | When |
|------|------|
| `feat` | New feature (bumps minor version) |
| `fix` | Bug fix (bumps patch version) |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `chore` | Build, CI, tooling changes |

**Rules**:
- Subject line under 72 characters
- Imperative mood: "add feature" not "added feature" or "adds feature"
- Body explains **why**, not **what** (the diff shows what)
- Reference issue numbers in footer: `Closes #123`
- Breaking changes: `feat!:` or `BREAKING CHANGE:` in footer

```bash
# Good
git commit -m "feat(auth): add OAuth2 PKCE flow for mobile clients

Implements RFC 7636 to prevent authorization code interception
on mobile devices where client secrets cannot be kept confidential.

Closes #847"

# Bad
git commit -m "updated stuff"
git commit -m "fix bug"
git commit -m "WIP"
```

---

### Rebase vs Merge

#### When to Rebase
- Updating a feature branch with changes from main
- Cleaning up local commits before opening a PR
- Maintaining linear history on your own branch

```bash
# Update feature branch with latest main
git fetch origin
git rebase origin/main

# If conflicts arise, resolve each commit:
# edit files, then:
git add <resolved-files>
git rebase --continue
```

#### When to Merge
- Incorporating a feature branch into main (via PR merge commit or squash)
- When branch history is shared with others
- When you want to preserve the branching topology

#### The Golden Rule of Rebasing
**Never rebase commits that have been pushed to a shared branch.** Rebase rewrites history. If others have based work on those commits, you will create divergent histories.

```bash
# SAFE: rebase your local feature branch onto main
git rebase origin/main

# DANGEROUS: rebase a branch others are working on
git rebase origin/main shared-feature  # DO NOT
```

---

### Interactive Rebase Patterns

```bash
git rebase -i HEAD~5  # last 5 commits
```

The editor shows:
```
pick abc1234 feat: add user model
pick def5678 fix: typo in user model
pick ghi9012 feat: add user API endpoint
pick jkl3456 WIP debugging
pick mno7890 feat: add user validation
```

**Common operations**:

| Command | Use Case |
|---------|----------|
| `squash` (s) | Combine with previous commit, edit message |
| `fixup` (f) | Combine with previous commit, discard message |
| `reword` (r) | Change commit message |
| `edit` (e) | Stop to amend the commit |
| `drop` (d) | Delete the commit |

**Clean up before PR**:
```
pick abc1234 feat: add user model
fixup def5678 fix: typo in user model
pick ghi9012 feat: add user API endpoint
drop jkl3456 WIP debugging
squash mno7890 feat: add user validation
```

---

### Conflict Resolution Strategies

**Step 1**: Understand both sides before editing. Run:
```bash
git log --merge --oneline         # commits causing conflict
git diff --name-only --diff-filter=U  # conflicting files
```

**Step 2**: For each file, choose a strategy:
- **Ours wins**: Our changes are correct, discard theirs
- **Theirs wins**: Their changes are correct, discard ours
- **Manual merge**: Both sides have needed changes, combine them

```bash
# Accept ours for a specific file
git checkout --ours path/to/file
git add path/to/file

# Accept theirs for a specific file
git checkout --theirs path/to/file
git add path/to/file
```

**Step 3**: After resolving, verify:
```bash
git diff --staged     # review the resolution
# run tests
git rebase --continue  # or git merge --continue
```

**Prevention**: Rebase frequently. Small PRs. Avoid long-lived branches. Communicate about shared files.

---

### Git Worktrees for Parallel Work

Worktrees let you check out multiple branches simultaneously without stashing or switching.

```bash
# Create a worktree for a hotfix while working on a feature
git worktree add ../hotfix-payment hotfix/payment-bug

# Work in the hotfix directory
cd ../hotfix-payment
# fix, commit, push, open PR

# Return to feature work
cd ../main-repo

# Clean up when done
git worktree remove ../hotfix-payment
```

**Use cases**:
- Urgent fix while mid-feature
- Running tests on one branch while coding on another
- Reviewing a PR locally without disrupting your work
- Comparing behavior across branches

**Rules**:
- Each worktree must be on a different branch
- Share the same `.git` directory (disk efficient)
- Worktree branches cannot be checked out elsewhere simultaneously

---

### Cherry-Pick and Bisect

#### Cherry-Pick
Apply a specific commit from one branch to another.

```bash
# Apply a single commit
git cherry-pick abc1234

# Apply without committing (stage only)
git cherry-pick --no-commit abc1234

# Cherry-pick a range
git cherry-pick abc1234..def5678
```

**Use case**: Backporting a fix to a release branch without merging everything.

#### Bisect
Binary search through history to find which commit introduced a bug.

```bash
git bisect start
git bisect bad                    # current commit is broken
git bisect good v1.2.0            # this tag was working
# Git checks out a middle commit
# Test it, then:
git bisect good  # or  git bisect bad
# Repeat until Git identifies the culprit
git bisect reset                  # return to original state
```

**Automate bisect with a test script**:
```bash
git bisect start HEAD v1.2.0
git bisect run ./test-script.sh   # exit 0 = good, exit 1 = bad
```

---

### Git Hooks

Hooks run scripts at specific points in the Git workflow.

| Hook | Trigger | Common Use |
|------|---------|------------|
| `pre-commit` | Before commit is created | Lint, format, type check |
| `commit-msg` | After message is written | Enforce message format |
| `pre-push` | Before push to remote | Run tests |
| `prepare-commit-msg` | Before editor opens | Template insertion |

**Setup with a framework** (recommended):
```bash
# Using pre-commit (Python)
pip install pre-commit
# .pre-commit-config.yaml in repo root
pre-commit install

# Using husky (Node)
npx husky init
```

**Example pre-commit config**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: no-commit-to-branch
        args: ['--branch', 'main']
```

---

## Anti-patterns

- **Force pushing to shared branches**: Rewrites others' history. Use `--force-with-lease` at minimum, but prefer not force-pushing shared branches at all.
- **Massive commits**: 2000-line commits are unreviewable. Commit logical units of work. One concern per commit.
- **Merge commits in feature branches**: `git pull` on a feature branch creates unnecessary merge commits. Use `git pull --rebase` or configure `pull.rebase = true`.
- **Long-lived feature branches**: Branches older than a week diverge painfully. Merge frequently or use feature flags.
- **WIP commits on main**: Clean your history before merging. Squash or fixup WIP commits.
- **Committing generated files**: Build artifacts, compiled output, `node_modules`. Use `.gitignore`.
- **Skipping hooks with `--no-verify`**: Hooks exist for a reason. Fix the issue instead of bypassing the check.

---

## Checklists

### Before Opening a PR
- [ ] Rebased on latest main
- [ ] Commit history is clean (no WIP, fixup, or "oops" commits)
- [ ] Each commit has a clear conventional commit message
- [ ] All commits pass tests individually (if using rebase workflow)
- [ ] No unintended files in the diff
- [ ] Branch name follows team convention

### Before Merging
- [ ] CI passes
- [ ] Required reviews obtained
- [ ] Conflicts resolved
- [ ] Commit messages are final (squash if needed)
- [ ] No TODOs left unaddressed in the diff

---

## Related Skills

- `ci-cd-pipelines.md` -- CI/CD integration with Git workflows
- `code-review.md` -- Code review process
- `../collaboration/github/github-pull-requests.md` -- GitHub PR workflows
- `code-review-rules.md` -- Review checklist rules
