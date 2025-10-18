---
name: beads-workflow
description: go install github.com/steveyegge/beads/cmd/bd@latest
---


# Beads Workflow - Core bd CLI Patterns

**Use this skill when:** Starting a new session with Beads, running bd commands, or managing issue workflow state

## Overview

Beads (`bd` CLI) is a graph-based issue tracker designed for AI coding agents. This skill covers the fundamental workflow patterns for using bd to track work across sessions.

## Session Start Protocol

Every session should begin with this sequence:

```bash
# 1. Update bd CLI (MANDATORY at session start)
go install github.com/steveyegge/beads/cmd/bd@latest

# 2. Verify installation
bd version

# 3. Import existing state (if .beads/issues.jsonl exists)
bd import -i .beads/issues.jsonl

# 4. Check ready work
bd ready --json --limit 5
```

## Core Workflow Pattern

```
Session Start:
  ↓
Import State (bd import)
  ↓
Check Ready Work (bd ready --json)
  ↓
Claim Task (bd update ID --status in_progress --json)
  ↓
Execute Work
  ↓
Complete Task (bd close ID --reason "..." --json)
  ↓
Export State (bd export -o .beads/issues.jsonl)
  ↓
Commit to Git
```

## Essential Commands

### Initialize Project

```bash
# Create .beads/ directory and SQLite database
bd init --prefix projectname
```

### Create Issues

```bash
# Create with all options
bd create "Issue title" -t bug -p 1 --json

# Issue types: bug, task, epic, feature
# Priority: 0 (highest) to 3 (lowest)
```

### Find Ready Work

```bash
# List unblocked issues
bd ready --json --limit 5

# Filter by assignee
bd ready --assignee agent-1 --json

# Filter by priority
bd ready --priority 0 --json
```

### Update Issue Status

```bash
# Claim work
bd update bd-42 --status in_progress --json

# Status values: open, in_progress, blocked, closed
```

### Close Issues

```bash
# Close with reason
bd close bd-42 --reason "Implemented and tested" --json

# The reason documents what was done
```

### List and View Issues

```bash
# List all issues
bd list --json

# Show specific issue
bd show bd-42 --json

# List by status
bd list --status open --json
```

### Export and Import

```bash
# Export to JSONL for git
bd export -o .beads/issues.jsonl

# Import from JSONL (after git pull)
bd import -i .beads/issues.jsonl

# Dry run to preview
bd import -i .beads/issues.jsonl --dry-run

# Resolve collisions automatically
bd import -i .beads/issues.jsonl --resolve-collisions
```

## Git Integration

### Pre-Commit Hook

Always export before committing:

```bash
#!/bin/bash
# .git/hooks/pre-commit
bd export -o .beads/issues.jsonl
git add .beads/issues.jsonl
```

### Post-Merge Hook

Always import after merging:

```bash
#!/bin/bash
# .git/hooks/post-merge
bd import -i .beads/issues.jsonl
```

## Session End Protocol

Every session should end with:

```bash
# 1. Close completed issues
bd close bd-X --reason "..." --json

# 2. Export state
bd export -o .beads/issues.jsonl

# 3. Commit to git
git add .beads/issues.jsonl
git commit -m "Update issue tracker"
```

## Command Patterns

### Always Use --json Flag

Use `--json` for parseable output that works well with AI agents:

```bash
# GOOD
bd ready --json --limit 5
bd create "Task" --json
bd update bd-5 --status in_progress --json

# AVOID (human-readable output)
bd ready
bd list
```

### Issue ID Format

Issue IDs follow the pattern `{prefix}-{number}`:
- `bd-1`, `bd-2`, `bd-3` (default prefix)
- `myapp-1`, `myapp-2` (custom prefix)

Use the full ID in commands:

```bash
bd show bd-42 --json
bd update myapp-15 --status in_progress --json
```

## Common Workflows

### Starting New Work

```bash
# Find what's ready
bd ready --json --limit 5

# Claim an issue
bd update bd-10 --status in_progress --json

# (Do the work...)

# Close when done
bd close bd-10 --reason "Completed implementation" --json
```

### Creating Discovered Work

```bash
# While working on bd-10, discover new issue
bd create "Fix edge case in validation" -t bug -p 1 --json
# Returns: bd-11

# Link discovery (see beads-dependency-management.md)
bd dep add bd-11 bd-10 --type discovered-from
```

### Multi-Agent Coordination

```bash
# Agent 1 claims work
bd ready --json --limit 5
bd update bd-50 --status in_progress --assignee agent-1 --json

# Agent 2 finds their work
bd ready --assignee agent-2 --json

# Both export before commits, import after pulls
```

## Troubleshooting

### Issue: "Database locked"

Multiple bd processes accessing the same database.

**Solution:** Only run one bd command at a time. Use `--json` output for programmatic access.

### Issue: Import shows collisions

Two branches created issues with same ID.

**Solution:** Use `--resolve-collisions` to auto-remap:

```bash
bd import -i .beads/issues.jsonl --resolve-collisions
```

### Issue: Lost issues after import

Stale JSONL file was imported.

**Solution:** Always export before commits, import after pulls. Check git history for latest state.

## Best Practices

1. **Export before every commit** - Never commit code without exporting issues
2. **Import after every pull/merge** - Keep local database synchronized
3. **Use --json consistently** - Better for AI agent parsing
4. **Atomic operations** - One bd command per logical action
5. **Meaningful close reasons** - Document what was accomplished
6. **Prefix consistency** - Use same prefix across project

## Related Skills

- `beads-dependency-management.md` - Managing issue dependencies
- `beads-context-strategies.md` - When to use /context and /compact
- `beads-multi-session-patterns.md` - Long-horizon task patterns

## References

- GitHub: https://github.com/steveyegge/beads
- Full CLI reference: See `beads-context/references/beads_cli_reference.md`
