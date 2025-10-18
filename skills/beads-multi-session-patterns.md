---
name: beads-multi-session-patterns
description: bd create "Implement user authentication" -t epic -p 0 --json
---


# Beads Multi-Session Task Patterns

**Use this skill when:** Working on complex tasks spanning multiple sessions, managing long-horizon work chains, or coordinating parallel work streams

## Overview

Beads excels at maintaining state across multiple sessions. This skill covers patterns for breaking down complex work into manageable chains that persist across days, weeks, or months.

## Long-Horizon Task Chain Pattern

For complex multi-step workflows:

### Step 1: Create Epic and Subtasks

```bash
# Create parent epic
bd create "Implement user authentication" -t epic -p 0 --json
# Returns: bd-100

# Create ordered subtasks
bd create "Design auth schema" -t task -p 0 --json          # bd-101
bd create "Implement JWT tokens" -t task -p 1 --json        # bd-102
bd create "Add login endpoints" -t task -p 1 --json         # bd-103
bd create "Add auth middleware" -t task -p 2 --json         # bd-104
bd create "Write auth tests" -t task -p 2 --json            # bd-105
```

### Step 2: Build Dependency Chain

```bash
# Link all to epic
for id in 101 102 103 104 105; do
  bd dep add bd-$id bd-100 --type parent-child
done

# Chain sequential dependencies
bd dep add bd-102 bd-101 --type blocks  # JWT needs schema
bd dep add bd-103 bd-102 --type blocks  # Endpoints need JWT
bd dep add bd-104 bd-103 --type blocks  # Middleware needs endpoints
bd dep add bd-105 bd-104 --type blocks  # Tests need middleware
```

### Step 3: Work Session by Session

```bash
# Session 1
bd ready --json  # Shows: bd-101 (design schema)
bd update bd-101 --status in_progress --json
# ... work on schema ...
bd close bd-101 --reason "Schema designed and documented" --json
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl && git commit -m "Complete bd-101: auth schema"

# Session 2 (days later)
bd import -i .beads/issues.jsonl
bd ready --json  # Shows: bd-102 (implement JWT) - unblocked!
bd update bd-102 --status in_progress --json
# ... work continues ...
```

### Step 4: Context Management Strategy

```bash
# At session start: Load full tree
bd dep tree bd-100
/context "Auth epic bd-100: 5 subtasks, currently on bd-102 (JWT implementation), completed: bd-101 (schema), remaining: 3 tasks"

# Between sessions: Compact to essentials
/compact "Preserve: epic bd-100 progress (2/5 complete), current task bd-102, next tasks [bd-103, bd-104, bd-105]. Remove: completed task details"
```

## Discovery-Driven Pattern

For exploratory work where scope emerges during execution:

### Workflow

```bash
# Start with single task
bd create "Refactor user service" -t task -p 1 --json  # bd-200
bd update bd-200 --status in_progress --json

# Discover issues during work
bd create "Fix user validation bug" -t bug -p 0 --json         # bd-201
bd dep add bd-201 bd-200 --type discovered-from

bd create "Add missing user tests" -t task -p 2 --json         # bd-202
bd dep add bd-202 bd-200 --type discovered-from

bd create "Update user docs" -t task -p 3 --json               # bd-203
bd dep add bd-203 bd-200 --type discovered-from

# Context preservation
/context "Discovered from bd-200: bd-201 (validation bug, must fix), bd-202 (tests, can defer), bd-203 (docs, low priority). Will address in order P0, P1, P2, P3"

# Work prioritized discovered issues
bd update bd-201 --status in_progress --json
# ... fix bug ...
bd close bd-201 --reason "Fixed validation for edge case X" --json

# Eventually close parent
bd close bd-200 --reason "Refactored + addressed discovered issues" --json
```

### Context Strategy

```bash
# After discovering 3+ issues
/context "Discovery chain from bd-200: [list with priorities and brief descriptions], plan to address in priority order"

# When completing parent with discoveries still open
bd close bd-200 --reason "Main refactoring complete, discovered issues tracked separately" --json
/compact "Preserve: bd-200 complete, spawned issues [bd-201: closed, bd-202: open, bd-203: open]. Remove: refactoring implementation details"
```

## Parallel Work Streams Pattern

For coordinating multiple independent streams:

### Setup

```bash
# Stream 1: Frontend work
bd create "Frontend Epic" -t epic -p 1 --json                  # bd-300
bd create "User profile UI" -t task -p 1 --json                # bd-301
bd create "Settings UI" -t task -p 1 --json                    # bd-302
bd dep add bd-301 bd-300 --type parent-child
bd dep add bd-302 bd-300 --type parent-child

# Stream 2: Backend work
bd create "Backend Epic" -t epic -p 1 --json                   # bd-310
bd create "User profile API" -t task -p 1 --json               # bd-311
bd create "Settings API" -t task -p 1 --json                   # bd-312
bd dep add bd-311 bd-310 --type parent-child
bd dep add bd-312 bd-310 --type parent-child

# Stream 3: Infrastructure
bd create "Infrastructure Epic" -t epic -p 0 --json            # bd-320
bd create "Deploy staging" -t task -p 0 --json                 # bd-321
bd create "Set up monitoring" -t task -p 1 --json              # bd-322
bd dep add bd-321 bd-320 --type parent-child
bd dep add bd-322 bd-320 --type parent-child

# Cross-stream dependencies
bd dep add bd-301 bd-311 --type blocks  # UI needs API
bd dep add bd-302 bd-312 --type blocks  # Settings UI needs API
```

### Multi-Session Execution

```bash
# Session 1: Infrastructure focus
bd ready --json  # Shows: bd-321 (deploy staging)
bd update bd-321 --status in_progress --json
# ... deploy ...
bd close bd-321 --reason "Staging deployed" --json
/context "Completed bd-321 (staging), next: bd-322 (monitoring). Frontend/backend work still blocked on APIs"

# Session 2: Backend focus
bd ready --json  # Shows: bd-311, bd-312 (APIs now unblocked)
bd update bd-311 --status in_progress --json
# ... implement API ...
bd close bd-311 --reason "Profile API complete" --json
/context "Completed bd-311 (profile API), unblocked: bd-301 (profile UI). Next: bd-312 or bd-301"

# Session 3: Frontend + Backend in parallel
bd ready --json  # Shows: bd-301 (UI), bd-312 (settings API), bd-322 (monitoring)
# Pick bd-301 (frontend)
bd update bd-301 --status in_progress --json
# ... work ...
```

### Context Strategy

```bash
# Track progress across epics
/context "Epic status: Frontend 1/2 (bd-301 in progress), Backend 1/2 (bd-311 done, bd-312 ready), Infrastructure 1/2 (bd-321 done, bd-322 ready)"

# When switching streams
/context "Switching: Frontend (bd-301) paused at [state] -> Backend (bd-312) starting with [plan]"
```

## Merge Conflict Pattern

For handling concurrent work in different branches:

### Scenario

```bash
# Branch A creates: bd-400, bd-401, bd-402
# Branch B creates: bd-400, bd-401, bd-403 (collision on IDs!)
# Both branches merged to main
```

### Resolution

```bash
# After merge conflict in .beads/issues.jsonl
git merge feature-branch
# Conflict in .beads/issues.jsonl

# Preview collision
bd import -i .beads/issues.jsonl --dry-run

# Auto-resolve with remapping
bd import -i .beads/issues.jsonl --resolve-collisions

# Document resolution
/context "Merge resolved: Branch A bd-400->bd-404, bd-401->bd-405. Branch B kept bd-400, bd-401. All dependencies preserved. Verified: bd dep cycles returns clean"

# Export clean state
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "Resolve Beads merge conflict"
```

## Multi-Agent Coordination Pattern

For parallel work by multiple agents/developers:

### Setup

```bash
# Agent 1 claims backend work
bd ready --json
bd update bd-500 --status in_progress --assignee agent-1 --json

# Agent 2 claims frontend work
bd ready --assignee agent-2 --json
bd update bd-501 --status in_progress --assignee agent-2 --json
```

### Synchronization

```bash
# Agent 1 workflow
# ... work ...
bd close bd-500 --reason "API complete" --json
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "Agent 1: Complete bd-500"
git push

# Agent 2 workflow (parallel)
# ... work ...
bd close bd-501 --reason "UI complete" --json
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
git commit -m "Agent 2: Complete bd-501"
git pull  # Might have conflicts
bd import -i .beads/issues.jsonl --resolve-collisions
git push
```

### Context Strategy

```bash
# Each agent maintains separate context
# Agent 1:
/context "Agent 1 perspective: working on backend epic bd-500, completed API endpoints, next: bd-502 (database migration)"

# Agent 2:
/context "Agent 2 perspective: working on frontend epic bd-501, waiting on bd-500 completion, next: bd-503 (integration)"
```

## Best Practices for Long-Horizon Work

### 1. Progressive Refinement

Start broad, refine as you go:

```bash
# Week 1: Create epic and high-level tasks
bd create "Build payment system" -t epic -p 0 --json  # bd-600

# Week 2: Break down first task
bd create "Design payment schema" -t task -p 0 --json  # bd-601
bd dep add bd-601 bd-600 --type parent-child

# Week 3: Discover subtasks during implementation
bd create "Add Stripe integration" -t task -p 1 --json  # bd-602
bd dep add bd-602 bd-601 --type discovered-from
```

### 2. Milestone Tracking

Use epics as milestones:

```bash
# Quarterly milestones
bd create "Q1 2025: Core Features" -t epic -p 0 --json
bd create "Q2 2025: Performance" -t epic -p 1 --json
bd create "Q3 2025: Scale & Deploy" -t epic -p 2 --json
```

### 3. Session Continuity

Always end sessions cleanly:

```bash
# End of session
bd export -o .beads/issues.jsonl
/context "Session end: completed [bd-X, bd-Y], in progress [bd-Z at 70%], next session: finish bd-Z, start bd-W"
git add .beads/issues.jsonl
git commit -m "Session end: progress update"
```

### 4. Dependency Audits

Periodically review dependency health:

```bash
# Check for cycles
bd dep cycles

# Review blocked issues
bd list --status blocked --json | jq '.[] | {id, title, blocked_by}'

# Clean up stale dependencies
bd dep remove bd-OLD bd-STALE --type blocks
```

## Related Skills

- `beads-workflow.md` - Core bd commands
- `beads-dependency-management.md` - Dependency patterns
- `beads-context-strategies.md` - Context management for long sessions

## References

- See `beads-context/references/context_examples.md` for real multi-session examples
