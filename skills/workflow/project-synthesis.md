---
name: workflow-project-synthesis
description: Synthesize scattered project artifacts (plans, docs, tests, logs) into unified roadmap. Use when projects have accumulated sprawl across multiple planning documents, inconsistent naming, orphaned tests, or Beads issues out of sync with reality. Creates coherent execution plan while preserving research and maintaining referential integrity.
---

# Project Synthesis

Transform projects with accumulated sprawl into clean, coherent execution plans without losing critical work.

## When to Use

**Use this skill when:**
- Multiple competing or fragmented planning documents exist
- Tests and logs are scattered or orphaned
- Beads issues don't match current project reality
- Inconsistent naming schemes across artifacts
- Documentation has drifted from implementation

**Don't use for:**
- Greenfield projects (use standard Work Plan Protocol)
- Well-organized projects needing minor updates

## Overview

Five-phase process:
1. **Discovery** - Scan and inventory all artifacts
2. **Analysis** - Extract concepts, map dependencies
3. **Synthesis** - Create unified plan with normalized naming
4. **Cleanup** - Archive superseded artifacts (non-destructively)
5. **Validation** - Verify integrity and test coverage

## Phase 1: Discovery

### Create Baseline

```bash
# Snapshot current state
git add . && git commit -m "Pre-synthesis snapshot" || true
export BASELINE_COMMIT=$(git rev-parse HEAD)

# Create synthesis workspace
mkdir -p .claude/synthesis/$(date +%Y%m%d_%H%M%S)
export SYNTHESIS_DIR=.claude/synthesis/$(date +%Y%m%d_%H%M%S)

# Run baseline tests
pkill -f "test" 2>/dev/null || true
./run_tests.sh > $SYNTHESIS_DIR/baseline-tests.log 2>&1 & wait $!
echo "Baseline: $BASELINE_COMMIT" > $SYNTHESIS_DIR/baseline.txt
```

### Scan Project

```bash
# Find all planning artifacts
find . -type f \( -name '*plan*.md' -o -name '*roadmap*.md' -o -name '*spec*.md' \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*'

# Find tests
find . -type f \( -name '*test*' -o -name '*spec*' \) \
  \( -name '*.py' -o -name '*.ts' -o -name '*.go' -o -name '*.rs' \) \
  -not -path '*/node_modules/*'

# Check Beads state
bd import -i .beads/issues.jsonl
bd list --json > $SYNTHESIS_DIR/beads-snapshot.json
```

### Extract Concepts

Run `python skills/workflow/project-synthesis/resources/scripts/extract_concepts.py` to identify key concepts across all files:
- Class/function names from code
- Section headers from markdown
- Beads issue descriptions
- Critical architectural decisions

Output: `$SYNTHESIS_DIR/concepts.json`

## Phase 2: Analysis

### Build Dependency Graph

Map dependencies:
- Task dependencies (A must complete before B)
- Code dependencies (module A imports B)
- Beads blocked-by relationships
- Integration points (typed holes)

Output: `$SYNTHESIS_DIR/dependencies.json`

### Identify Parallelization

Mark tasks that are:
- Truly independent (no shared state)
- Safe to execute concurrently
- Have clear integration points

### Create Strategy Document

Document in `$SYNTHESIS_DIR/strategy.md`:
- Which artifacts to consolidate
- Key concepts to preserve
- Naming normalization plan
- Critical path
- Parallel streams

See `skills/workflow/project-synthesis/resources/REFERENCE.md` for strategy template.

## Phase 3: Synthesis

### Generate Unified Plan

Create `plan.md` with:

```markdown
# Project Execution Plan

> Generated: [date]
> Baseline: [commit], tests passing
> Consolidated: [list source documents]

## Critical Path

### Phase 1: [Name] (Timeline)
- [ ] task-1-01-description
- [ ] task-1-02-description

### Phase 2: [Name] (Timeline)
- [ ] task-2-01-description

## Parallel Streams

### Stream A: [Name]
- [ ] task-a-01-description

## Dependencies
- task-2-01 depends on task-1-01, task-1-02

## Integration Points
- [Component A] ↔ [Component B]: Interface X

## Preserved Research
[Key findings from research documents]
```

### Naming Standards

Apply consistently:
- **Phases**: `phase-{n}-{name}` (e.g., phase-1-foundation)
- **Tasks**: `task-{phase}-{number}-{description}` (e.g., task-1-01-setup-auth)
- **Documents**: `plan.md`, `spec.md`, `test-plan.md`, `roadmap.md`
- **Beads**: `[PHASE-N] Task description`

### Update Beads

```bash
# Sync with unified plan
bd import -i .beads/issues.jsonl

# Archive obsolete issues
bd list --status done --json | jq -r '.[] | .id' | \
  xargs -I {} bd update {} --status archived --json

# Create issues from plan
grep '^\- \[ \] task-' plan.md | while read line; do
  task_id=$(echo "$line" | grep -oP 'task-\d+-\d+')
  desc=$(echo "$line" | sed 's/.*task-[0-9]+-[0-9]+-//')
  phase=$(echo "$task_id" | cut -d- -f2)
  bd create "[PHASE-$phase] $desc" --type feature --priority "$phase" --json
done

bd export -o .beads/issues.jsonl
```

### Create Test Plan

Generate `test-plan.md`:
- Current coverage baseline
- Tests to preserve/update/archive
- New tests needed for unified plan
- Coverage targets by phase

## Phase 4: Cleanup

### Archive Non-Destructively

```bash
# Create archive structure
mkdir -p archive/{planning,research,tests,logs}

# Move superseded artifacts
for file in old-plan.md spec-v1.md; do
  mv "$file" "archive/planning/$(date +%Y%m%d)-$file"
done

# Move old logs
find . -name "*.log" -type f -mtime +7 -exec mv {} archive/logs/ \;
```

**Critical**: Create `$SYNTHESIS_DIR/reference-map.json` tracking all moves:
```json
{
  "moved": [
    {"from": "old-plan.md", "to": "archive/planning/20251027-old-plan.md"}
  ]
}
```

### Update References

Find and fix all references to moved files (scan markdown files for broken links).

### Update Documentation

Update `README.md` with:
- Link to new `plan.md`
- Current phase and status
- Link to `archive/` for history

## Phase 5: Validation

### Verify Integrity

```bash
# Test that nothing broke
pkill -f "test" 2>/dev/null || true
./run_tests.sh > $SYNTHESIS_DIR/post-synthesis-tests.log 2>&1 & wait $!
POST_TEST_STATUS=$?

# Compare with baseline
if [ $POST_TEST_STATUS -eq $BASELINE_TEST_STATUS ]; then
  echo "✅ Tests unchanged"
else
  echo "❌ Tests changed - investigate"
  exit 1
fi
```

### Quality Gates

All must pass:
- [ ] Tests status unchanged from baseline
- [ ] All references valid (no broken links)
- [ ] Key concepts preserved in unified plan
- [ ] Naming normalized throughout
- [ ] Archive structure created with reference map
- [ ] Beads synchronized
- [ ] Documentation updated

### Generate Report

Create `$SYNTHESIS_DIR/SYNTHESIS-REPORT.md`:
- What was consolidated
- What was archived
- Key concepts preserved
- Dependencies and sequencing
- Validation results
- Next steps

### Commit

```bash
git checkout -b synthesis/cleanup-$(date +%Y%m%d)
git add plan.md test-plan.md README.md docs/ archive/ .beads/
git commit -m "Synthesis: unified plan and cleanup

Consolidated [N] docs, archived [N] superseded artifacts
Tests: passing, coverage unchanged
See: .claude/synthesis/[timestamp]/SYNTHESIS-REPORT.md"

git push -u origin synthesis/cleanup-$(date +%Y%m%d)
```

## Bundled Scripts

The skill includes scripts in `skills/workflow/project-synthesis/resources/scripts/`:

- **extract_concepts.py** - Extract key concepts from all files

Run scripts with: `python skills/workflow/project-synthesis/resources/scripts/<script-name>.py`

## Reference Documentation

For detailed guidance, see `skills/workflow/project-synthesis/resources/REFERENCE.md` which includes:

- **Strategy Template** - Structure for strategy document
- **Troubleshooting Guide** - Common issues and solutions
- **Examples** - Detailed examples of synthesis runs

## Integration Notes

This synthesis operates at project level. After synthesis completes, resume normal Work Plan Protocol with the unified `plan.md`.

Synthesis preserves all multi-agent checkpoints and Beads state - no disruption to ongoing workflow.

---

## Related Skills

- `beads-workflow.md` - Core Beads commands and session patterns
- `beads-multi-session-patterns.md` - Multi-session work coordination
- `beads-dependency-management.md` - Managing task dependencies
- `beads-context-strategies.md` - Context management across sessions

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
