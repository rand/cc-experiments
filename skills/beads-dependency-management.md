---
name: beads-dependency-management
description: bd dep add bd-15 bd-10 --type blocks
---


# Beads Dependency Management

**Use this skill when:** Creating relationships between issues, managing blockers, or organizing work hierarchies

## Overview

Beads supports four dependency types that create a directed graph of issue relationships. Understanding when to use each type is critical for effective issue tracking.

## Dependency Types

### 1. `blocks` - Hard Blocker

**Purpose:** Prevents an issue from being "ready" until the blocker is closed

**Use when:** Implementation of X literally cannot proceed without Y being done first

```bash
# bd-15 cannot start until bd-10 is complete
bd dep add bd-15 bd-10 --type blocks

# bd-15 won't appear in `bd ready` until bd-10 is closed
```

**Example Use Cases:**
- Database schema must exist before migration
- Authentication system before protected endpoints
- Core library before dependent features
- Design approval before implementation

**Graph Representation:**
```
bd-10 --> bd-15  (bd-10 blocks bd-15)
```

### 2. `related` - Soft Association

**Purpose:** Creates context link without blocking

**Use when:** Two issues share context but don't block each other

```bash
# bd-20 and bd-18 are contextually related
bd dep add bd-20 bd-18 --type related

# Both can be worked on independently
```

**Example Use Cases:**
- Frontend and backend for same feature
- Documentation for related modules
- Related bug fixes in same area
- Alternative implementation approaches

**Graph Representation:**
```
bd-18 <--> bd-20  (bidirectional soft link)
```

### 3. `parent-child` - Hierarchy

**Purpose:** Creates epic/subtask relationships

**Use when:** Organizing work into epics and subtasks

```bash
# bd-25 is a subtask of epic bd-22
bd dep add bd-25 bd-22 --type parent-child

# Parent: bd-22 (epic)
# Child: bd-25 (subtask)
```

**Example Use Cases:**
- Feature epic with implementation subtasks
- Large refactoring broken into steps
- Release milestone with constituent tasks
- Research spike with exploration tasks

**Graph Representation:**
```
bd-22 (epic)
  ├─ bd-25 (subtask)
  ├─ bd-26 (subtask)
  └─ bd-27 (subtask)
```

### 4. `discovered-from` - Discovery Trail

**Purpose:** Tracks issues discovered during work on another issue

**Use when:** You find new work during execution and want to maintain the discovery chain

```bash
# bd-30 was discovered while working on bd-28
bd dep add bd-30 bd-28 --type discovered-from

# Preserves discovery context
```

**Example Use Cases:**
- Bug found during feature implementation
- Edge case discovered during testing
- Technical debt identified during refactoring
- Missing documentation found during review

**Graph Representation:**
```
bd-28 (working on) --> bd-30 (discovered)
```

## Dependency Commands

### Add Dependency

```bash
# General syntax
bd dep add <target-issue> <source-issue> --type <type>

# Examples
bd dep add bd-5 bd-3 --type blocks
bd dep add bd-10 bd-8 --type related
bd dep add bd-15 bd-12 --type parent-child
bd dep add bd-20 bd-18 --type discovered-from
```

### Remove Dependency

```bash
bd dep remove bd-5 bd-3 --type blocks
```

### View Dependency Tree

```bash
# Show all dependencies for an issue
bd dep tree bd-42

# Show specific dependency type
bd dep tree bd-42 --type blocks
```

### Check for Cycles

```bash
# Detect circular dependencies
bd dep cycles

# Beads prevents invalid cycles when adding dependencies
```

## Practical Patterns

### Pattern 1: Epic with Ordered Subtasks

Create a feature epic with dependencies between subtasks:

```bash
# Create epic
bd create "Implement user authentication" -t epic -p 0 --json
# Returns: bd-100

# Create subtasks
bd create "Design auth schema" -t task -p 0 --json          # bd-101
bd create "Implement JWT tokens" -t task -p 1 --json        # bd-102
bd create "Add login endpoints" -t task -p 1 --json         # bd-103
bd create "Add auth middleware" -t task -p 2 --json         # bd-104

# Link to epic
bd dep add bd-101 bd-100 --type parent-child
bd dep add bd-102 bd-100 --type parent-child
bd dep add bd-103 bd-100 --type parent-child
bd dep add bd-104 bd-100 --type parent-child

# Chain dependencies
bd dep add bd-102 bd-101 --type blocks  # JWT depends on schema
bd dep add bd-103 bd-102 --type blocks  # Endpoints depend on JWT
bd dep add bd-104 bd-103 --type blocks  # Middleware depends on endpoints

# Result: Linear workflow within epic
# bd ready will show: bd-101 (first unblocked)
```

### Pattern 2: Discovery-Driven Development

Track discovered work during execution:

```bash
# Working on refactoring
bd update bd-50 --status in_progress --json

# Discover issues during work
bd create "Fix user validation bug" -t bug -p 0 --json      # bd-51
bd dep add bd-51 bd-50 --type discovered-from

bd create "Add missing user tests" -t task -p 2 --json      # bd-52
bd dep add bd-52 bd-50 --type discovered-from

bd create "Update user documentation" -t task -p 3 --json   # bd-53
bd dep add bd-53 bd-50 --type discovered-from

# Now you have discovery trail: bd-50 -> bd-51, bd-52, bd-53
# Can work on any discovered issue independently
```

### Pattern 3: Parallel Features with Shared Dependency

Multiple features depend on same foundation:

```bash
# Foundation
bd create "Build base API client" -t task -p 0 --json       # bd-200

# Dependent features
bd create "User profile feature" -t feature -p 1 --json     # bd-201
bd create "Settings feature" -t feature -p 1 --json         # bd-202
bd create "Dashboard feature" -t feature -p 1 --json        # bd-203

# All features blocked by foundation
bd dep add bd-201 bd-200 --type blocks
bd dep add bd-202 bd-200 --type blocks
bd dep add bd-203 bd-200 --type blocks

# Result: Complete bd-200, then all features become ready
```

### Pattern 4: Related Work Clusters

Group related issues without blocking:

```bash
# Create related issues
bd create "Frontend: User profile UI" -t task -p 1 --json   # bd-300
bd create "Backend: User profile API" -t task -p 1 --json   # bd-301
bd create "Docs: User profile guide" -t task -p 3 --json    # bd-302

# Link as related (no blocking)
bd dep add bd-300 bd-301 --type related
bd dep add bd-300 bd-302 --type related
bd dep add bd-301 bd-302 --type related

# Result: All show as ready, can be worked on in any order
# But context is preserved between related issues
```

## Dependency Queries

### Find Blocked Issues

```bash
# List issues that are blocked
bd list --status blocked --json

# Show what's blocking an issue
bd dep tree bd-50 | grep "blocks"
```

### Find Ready Work

```bash
# Ready work = no blocking dependencies
bd ready --json --limit 10

# Ready work for specific priority
bd ready --priority 0 --json
```

### Trace Discovery Chain

```bash
# Find all issues discovered from bd-X
bd dep tree bd-50 --type discovered-from
```

### View Epic Progress

```bash
# Show all subtasks of epic
bd dep tree bd-100 --type parent-child

# Filter by status
bd list --json | jq '.[] | select(.parent == "bd-100")'
```

## Best Practices

### Choosing Dependency Types

```
SITUATION                                   → DEPENDENCY TYPE
─────────────────────────────────────────────────────────────
X must complete before Y can start          → blocks
X and Y are related but independent         → related
Y is subtask of epic X                      → parent-child
Y was discovered while working on X         → discovered-from
```

### Avoiding Cycles

Beads prevents cycles in `blocks` dependencies, but be mindful:

```bash
# INVALID - creates cycle
bd dep add bd-10 bd-5 --type blocks
bd dep add bd-5 bd-10 --type blocks  # Error: would create cycle

# VALID - use related instead
bd dep add bd-10 bd-5 --type related
bd dep add bd-5 bd-10 --type related
```

### Dependency Hygiene

1. **Be specific:** Use `blocks` only when truly necessary
2. **Avoid over-linking:** Don't create dependencies "just in case"
3. **Update dependencies:** Remove obsolete blockers
4. **Document reasoning:** Use issue descriptions to explain dependencies
5. **Review regularly:** Check `bd dep cycles` periodically

## Common Pitfalls

### Overusing `blocks`

**Problem:** Everything blocks everything, nothing is ready

**Solution:** Reserve `blocks` for hard dependencies. Use `related` for soft associations.

### Missing Discovery Links

**Problem:** Lose context of why work was created

**Solution:** Always link discovered work with `discovered-from`

### Orphaned Subtasks

**Problem:** Subtasks not linked to parent epic

**Solution:** Always create `parent-child` link when breaking down epics

## Related Skills

- `beads-workflow.md` - Core bd CLI commands
- `beads-multi-session-patterns.md` - Using dependencies in long-horizon tasks
- `beads-context-strategies.md` - Preserving dependency context

## References

- See `beads-context/references/beads_cli_reference.md` for full `bd dep` command reference
