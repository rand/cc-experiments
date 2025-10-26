---
name: beads-context-strategies
description: Skill for beads context strategies
---


# Beads Context Management Strategies

**Use this skill when:** Managing Claude Code context while working with Beads, preventing context bloat, or preserving critical workflow state across sessions

## Overview

When working with Beads (`bd` CLI) across multiple sessions, strategic use of `/context` (preserve) and `/compact` (compress) commands is essential to maintain high-fidelity workflow state without hitting context limits.

## The Context Problem

**Without context management:**
- Verbose `bd` JSON outputs accumulate
- Context fills with repetitive command outputs
- Critical state gets pushed out
- Lose track of complex dependency chains
- Waste time re-discovering workflow state

**With strategic context management:**
- Preserve only critical decisions and state
- Compress routine operations
- Maintain workflow continuity across sessions
- Keep dependency context accessible
- Recover quickly after interruptions

## Two Commands, Two Purposes

### `/context` - Preserve Critical State

**Purpose:** Create a checkpoint that preserves current state for future reference

**Use when:**
- Starting work on complex issues
- After discovering significant new work
- Before major refactoring or architectural changes
- When switching between unrelated issues
- After resolving merge conflicts
- At key decision points

**Pattern:**
```
/context "Brief description of what to preserve"
```

### `/compact` - Compress Verbose State

**Purpose:** Summarize and remove verbose details while keeping essential information

**Use when:**
- After completing an issue
- After routine `bd list`, `bd show` operations
- Context approaching 75% full
- After bulk issue creation
- During long troubleshooting sessions
- After multiple dependency operations

**Pattern:**
```
/compact "What to preserve: [essentials]. What to remove: [verbosity]."
```

## Context Preservation Points

### 1. Session Start

**Trigger:** Beginning a new session

**Action:**
```
# After: bd import + bd ready
/context "Session start: ready work queue [bd-5, bd-10, bd-15], current focus: bd-5 (implement auth), blockers: none"
```

**Preserves:**
- Available work
- Current focus
- Known blockers
- Session context

### 2. Complex Issue Start

**Trigger:** Starting work on issue with 3+ dependencies

**Action:**
```
# After: bd dep tree bd-42
/context "Working on bd-42 (refactor payment system). Depends on: bd-38 (schema), bd-40 (API). Discovered from: bd-35. Plan: [steps]"
```

**Preserves:**
- Issue context
- Dependency tree
- Implementation plan
- Discovery chain

### 3. Significant Discovery

**Trigger:** Discovering 3+ new issues during work

**Action:**
```
# After creating multiple issues
/context "Discovered from bd-50: bd-51 (validation bug, P0), bd-52 (missing tests, P2), bd-53 (docs, P3). Rationale: found during refactoring"
```

**Preserves:**
- Discovery context
- Issue priorities
- Rationale for creation
- Parent issue link

### 4. Architectural Decision

**Trigger:** Before/after major refactoring or design changes

**Action:**
```
/context "Pre-refactor: current architecture uses [X]. Planned changes: migrate to [Y]. Affected issues: bd-60, bd-61, bd-62. Risks: [list]"
```

**Preserves:**
- Current state
- Planned changes
- Impact scope
- Risk assessment

### 5. Issue Switching

**Trigger:** Switching between unrelated issues

**Action:**
```
/context "Switching: bd-70 -> bd-80. bd-70 status: [current state], next: [action]. bd-80 context: [background], plan: [approach]"
```

**Preserves:**
- State of paused issue
- Context for new issue
- Resume points
- Task continuity

### 6. Merge Conflict Resolution

**Trigger:** After resolving Beads merge conflicts

**Action:**
```
/context "Merge resolved: 5 issues remapped (bd-90->bd-95, ...), preserved dependencies, no data loss. New HEAD: [commit]"
```

**Preserves:**
- Remapping record
- Conflict resolution
- Verification steps
- Current state

## Compaction Points

### 1. After Issue Completion

**Trigger:** Closed an issue

**Action:**
```
/compact "Preserve: bd-100 closed (reason: completed auth), unblocked: bd-101, bd-102. Remove: implementation details, verbose outputs."
```

**Result:**
- High-level outcome preserved
- Verbose JSON removed
- Impact preserved
- Details dropped

### 2. Routine Operations

**Trigger:** Multiple `bd list`, `bd show` commands

**Action:**
```
/compact "Preserve: current ready work [bd-110, bd-111], priorities, blockers. Remove: repetitive bd list outputs, unchanged issue details."
```

**Result:**
- Current state summary
- Removed duplication
- Essential info kept

### 3. Context Approaching Limit

**Trigger:** Context > 75% full

**Action:**
```
/compact "Preserve: active issue bd-120, dependencies, next 3 steps. Remove: completed work details, old discovery chains, routine command outputs."
```

**Result:**
- Lean, focused context
- Critical state preserved
- Old context archived

### 4. Bulk Issue Creation

**Trigger:** Created 5+ issues at once

**Action:**
```
/compact "Preserve: created issues [bd-130 to bd-135] with priorities [P0, P1, P1, P2, P3, P3], dependencies summarized. Remove: verbose JSON payloads."
```

**Result:**
- Issue list preserved
- Metadata summarized
- Verbose JSON removed

### 5. Long Troubleshooting

**Trigger:** Extended debugging session

**Action:**
```
/compact "Preserve: current hypothesis [X], tested approaches [A, B, C], next: try [D]. Remove: failed attempt details, verbose error outputs."
```

**Result:**
- Current understanding
- Progress preserved
- Dead ends summarized

## Strategic Workflow Pattern

Complete multi-session workflow with context management:

```
SESSION START:
┌─────────────────────────────────────────────┐
│ 1. bd import -i .beads/issues.jsonl         │
│ 2. bd ready --json --limit 5                │
│ 3. /context "Session start: [summary]"      │
└─────────────────────────────────────────────┘
                    ↓
CLAIM WORK:
┌─────────────────────────────────────────────┐
│ 1. bd update bd-X --status in_progress      │
│ 2. bd dep tree bd-X                         │
│ 3. /context "Working on bd-X: [context]"    │
└─────────────────────────────────────────────┘
                    ↓
DURING WORK:
┌─────────────────────────────────────────────┐
│ Execute, discover, create sub-issues        │
│ At major checkpoints:                       │
│   /context "Checkpoint: [brief desc]"       │
│ After routine operations:                   │
│   /compact "Preserve: [key], Remove: [...]" │
└─────────────────────────────────────────────┘
                    ↓
COMPLETE WORK:
┌─────────────────────────────────────────────┐
│ 1. bd close bd-X --reason "..."             │
│ 2. /compact "Preserve: outcome, Remove: ..." │
└─────────────────────────────────────────────┘
                    ↓
SESSION END:
┌─────────────────────────────────────────────┐
│ 1. /context "Session summary: [...]"        │
│ 2. bd export -o .beads/issues.jsonl         │
│ 3. git add + commit                         │
└─────────────────────────────────────────────┘
```

## Context Fidelity Triggers

### High-Fidelity Required

Maintain detailed context when:
- Complex issue with 3+ dependencies
- Multi-file refactoring with intricate relationships
- Debugging subtle interaction bugs
- Architectural decisions in progress
- Resolving difficult merge conflicts
- First time working on codebase area

**Action:** Use `/context` with full details

### Compaction Acceptable

Compress context when:
- Routine CRUD operations
- Simple bug fixes with clear solutions
- Repetitive issue creation/updates
- Status reviews on multiple issues
- After completing straightforward tasks
- Context >75% full

**Action:** Use `/compact` to summarize

## Anti-Patterns

### ❌ Never Compact Without Preserving Key State

**Wrong:**
```
/compact "Remove everything from last hour"
```

**Right:**
```
/compact "Preserve: current issue bd-X, dependencies [list], next steps [list]. Remove: command outputs, completed work details"
```

### ❌ Never Context Everything

**Wrong:**
```
# After every single bd command
bd list --json
/context "Listed issues"
bd show bd-5 --json
/context "Showed bd-5"
```

**Right:**
```
# Only at decision points
bd list --json
bd show bd-5 --json
bd dep tree bd-5
/context "Working on bd-5 (auth feature). Blocked by bd-3 (schema). Plan: [implementation steps]"
```

### ❌ Never Lose Discovery Context

**Wrong:**
```
# Create issues without linking
bd create "Bug found" --json
bd create "Another bug" --json
# ... context lost
```

**Right:**
```
bd create "Bug in validation" --json  # bd-100
bd dep add bd-100 bd-95 --type discovered-from
/context "Discovered bd-100 from bd-95: validation fails on edge case [X]"
```

## Recovery Patterns

### Lost Context Recovery

**Situation:** Context lost after session interruption

**Recovery:**
```bash
# 1. Import latest state
bd import -i .beads/issues.jsonl

# 2. Find last worked issue
bd list --status in_progress --json

# 3. Reconstruct context
bd dep tree bd-X
/context "Resuming bd-X: [reconstruct from dependencies and git history]"
```

### Context Bloat Recovery

**Situation:** Context nearly full, losing critical state

**Recovery:**
```
# 1. Identify essentials
# - Current active issue
# - Immediate dependencies
# - Next 2-3 steps

# 2. Aggressive compaction
/compact "PRESERVE ONLY: active issue bd-X, dependencies [bd-Y, bd-Z], next steps [A, B, C]. REMOVE: all completed work, all routine outputs, all discovery history except current chain."
```

## Metrics for Context Health

Monitor these indicators:

- **Context fullness:** Should stay 30-70%
- **Active issues:** 1-3 maximum
- **Preserved decisions:** Key architectural choices
- **Command output ratio:** >80% should be compacted

## Related Skills

- `beads-workflow.md` - Core bd commands
- `beads-dependency-management.md` - Dependency patterns to preserve
- `beads-multi-session-patterns.md` - Long-horizon task context

## References

- See `beads-context/references/context_examples.md` for real-world examples
