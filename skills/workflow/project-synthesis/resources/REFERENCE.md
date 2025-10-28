# Project Synthesis Reference

Detailed guidance, templates, and troubleshooting for project synthesis operations.

---

## Strategy Template

Use this template when creating `$SYNTHESIS_DIR/strategy.md`.

### Structure

```markdown
# Synthesis Strategy

**Date**: [YYYY-MM-DD HH:MM:SS]
**Baseline Commit**: [commit hash]
**Baseline Tests**: [passing/failing] ([N] total)

## Discovered Artifacts

### Planning Documents
- `plan.md` - Active, phase 3
- `old-plan.md` - Superseded, contains auth design
- `spec-v1.md` - Superseded, contains API contracts
- `notes/research.md` - Active, rate limiting research
- `TODO.md` - Mixed content

**Total**: 5 planning documents

### Tests
- Unit: 47 files
- Integration: 12 files
- E2E: 3 files
- Orphaned: 12 files (no matching implementation)
- Coverage: 68%

### Documentation
- `README.md` - Current, needs update
- `docs/api.md` - Outdated (references old endpoints)
- `docs/architecture.md` - Current
- `archive/old-docs/` - Historical

### Beads Issues
- Total: 23 issues
- Open: 7
- In Progress: 3
- Blocked: 2
- Done but not archived: 11

## Key Concepts to Preserve

Extract from all sources:

1. **Authentication System**
   - JWT + refresh tokens (from spec-v2.md)
   - Session management (from plan.md)
   - OAuth integration (from notes/research.md)

2. **API Design**
   - RESTful primary (from plan.md)
   - GraphQL for complex queries (from spec-v1.md)
   - Rate limiting: token bucket (from notes/research.md)

3. **Database Schema**
   - Normalized PostgreSQL (from db-design.md)
   - Migration strategy (from old-plan.md)

4. **Research Findings**
   - Evaluated 3 rate limiting approaches (notes/research.md)
   - Abandoned WebSocket real-time (old-plan.md - complexity)
   - Performance benchmarks (notes/perf-tests.md)

## Consolidation Plan

### Create Unified Documents
1. **plan.md** - Merge `plan-v1.md` + `plan-v2.md` + relevant TODO items
2. **spec.md** - Consolidate `spec-v1.md` + auth sections from `old-plan.md`
3. **test-plan.md** - New, based on current test inventory
4. **roadmap.md** - High-level milestones from all plans

### Archive
- `old-plan.md` → `archive/planning/20251027-old-plan.md`
- `spec-v1.md` → `archive/planning/20251027-spec-v1.md`
- `test_prototype.py` → `archive/tests/20251027-test_prototype.py`
- 12 orphaned test files → `archive/tests/`
- Logs older than 7 days → `archive/logs/`

### Naming Normalization

**Current state**: Inconsistent
- Some tasks: "Setup Auth", others: "auth_setup", others: "1-auth"
- Plans numbered randomly: v1, v2, final, new
- Beads issues: no phase prefixes

**Target state**:
- Phases: `phase-1-foundation`, `phase-2-core`, `phase-3-polish`
- Tasks: `task-1-01-setup-auth`, `task-1-02-database-schema`
- Beads: `[PHASE-1] Setup authentication`, `[PHASE-2] API endpoints`
- Documents: `plan.md`, `spec.md`, no version suffixes

## Dependencies Identified

### Critical Path
```
phase-1-foundation (Tasks 1-01 to 1-03)
  ↓
phase-2-core (Tasks 2-01 to 2-05)
  ↓
phase-3-polish (Tasks 3-01 to 3-03)
```

### Specific Dependencies
- task-2-01 (API endpoints) depends on task-1-01 (auth) + task-1-02 (database)
- task-2-03 (integration) depends on task-2-01 + task-2-02
- task-3-01 (optimization) depends on all phase-2 tasks

### Parallelizable Work

**Stream A: Documentation** (throughout all phases)
- Can run parallel to implementation
- No blocking dependencies
- Tasks: API docs, user guides, architecture diagrams

**Stream B: Test Infrastructure** (phase 1)
- Parallel with initial setup
- Tasks: CI/CD, coverage tooling, test framework config

## Quality Gates

Before marking synthesis complete:

- [ ] All tests still passing (status unchanged)
- [ ] No concepts lost (compare with concepts.json)
- [ ] All references valid (no broken links)
- [ ] Naming consistent throughout
- [ ] Archive structure created with reference map
- [ ] Beads issues synchronized (count matches plan)
- [ ] Documentation updated (README, docs/)
- [ ] Synthesis report generated

## Risk Assessment

**Low Risk**:
- Documentation updates
- Archiving old logs
- Beads synchronization

**Medium Risk**:
- Moving test files (verify no imports broken)
- Updating references in code
- Renaming conventions

**High Risk**:
- None identified (all changes non-destructive with baseline)

## Timeline Estimate

- Phase 1 (Discovery): 30 minutes
- Phase 2 (Analysis): 45 minutes
- Phase 3 (Synthesis): 1 hour
- Phase 4 (Cleanup): 45 minutes
- Phase 5 (Validation): 30 minutes

**Total**: ~3.5 hours

## Success Criteria

Synthesis successful when:
1. Single unified `plan.md` exists
2. All key concepts documented
3. Naming normalized
4. Superseded artifacts archived
5. Tests pass with same coverage
6. Beads issues match plan
7. Documentation current
8. Report generated and reviewed
```

---

## Troubleshooting Guide

### Tests Fail After Synthesis

**Symptoms**: Test suite fails where it passed before synthesis

**Cause**: Reference or dependency broken during cleanup

**Solution**:
```bash
# Revert to baseline - intentional recovery procedure
git reset --hard $BASELINE_COMMIT

# Review what changed
git diff synthesis/cleanup-YYYYMMDD

# Fix specific issue without re-running full synthesis
```

### Beads Issues Out of Sync

**Symptoms**: Beads issues don't match unified plan

**Cause**: Manual changes after synthesis or incomplete sync

**Solution**:
```bash
# Re-export current state
bd export -o .beads/issues.jsonl

# Manually reconcile differences
bd list --json | jq '.[] | select(.status == "open")'

# Create missing issues from plan
grep '^\- \[ \] task-' plan.md # Compare with Beads output
```

### Missing Key Concept

**Symptoms**: Important concept from old plan not in unified plan

**Cause**: Extraction script missed it or concept in unscanned location

**Solution**:
```bash
# Manually search for concept
grep -r "concept-name" archive/planning/

# Add to concepts.json
jq '.key_concepts += ["concept-name"]' $SYNTHESIS_DIR/concepts.json

# Update plan.md to include it
# Document in synthesis report
```

### Broken References

**Symptoms**: Links in markdown point to non-existent files

**Cause**: File moved but reference not updated

**Solution**:
```bash
# Find all references to moved file
grep -r "old-filename" --include="*.md"

# Update with sed
sed -i 's|old-filename|archive/planning/20251027-old-filename|g' affected-file.md

# Or update manually in editor
```

### Can't Find Archive

**Symptoms**: Archived file needed but can't locate

**Cause**: Unclear archive organization

**Solution**:
```bash
# Check reference map
cat $SYNTHESIS_DIR/reference-map.json

# Search archives
find archive/ -name "*keyword*"

# Check git history
git log --all --full-history -- "**/old-filename"
```

### Script Execution Fails

**Symptoms**: One of the bundled scripts errors

**Cause**: Missing dependencies or environment issue

**Solution**:
```bash
# Ensure Python 3.8+
python --version

# Check script has execution permissions
chmod +x skills/workflow/project-synthesis/resources/scripts/extract_concepts.py

# Run with explicit interpreter if needed
python skills/workflow/project-synthesis/resources/scripts/extract_concepts.py
```

### Synthesis Takes Too Long

**Symptoms**: Process running for hours

**Cause**: Very large codebase or inefficient scanning

**Solution**:
- Exclude node_modules, vendor directories explicitly
- Run concept extraction on subset first
- Consider manual synthesis for extremely large projects
- Use `find` with `-maxdepth` to limit traversal

### Recovery Protocol

If synthesis fails catastrophically:

1. **STOP** - Don't make more changes
2. **REVERT** - `git reset --hard $BASELINE_COMMIT`  <!-- Intentional recovery step -->
3. **DIAGNOSE** - Review logs in `$SYNTHESIS_DIR/`
4. **FIX** - Address root cause
5. **RESTART** - Begin synthesis again from Phase 1

---

## Examples

### Example: Small Web App Synthesis

**Before**:
```
/
├── plan.md (outdated, references deleted features)
├── roadmap-2024.md (current quarter)
├── spec-auth.md (auth design)
├── notes/database-ideas.md (research)
├── TODO.md (mixed tasks)
└── tests/
    ├── test_old_feature.py (orphaned)
    └── test_auth.py (current)
```

**After**:
```
/
├── plan.md (unified, 3 phases, 12 tasks)
├── test-plan.md (coverage targets, test inventory)
├── archive/
│   └── planning/
│       ├── 20251027-plan-old.md
│       ├── 20251027-spec-auth.md
│       └── 20251027-TODO.md
├── .claude/synthesis/20251027_143022/
│   ├── baseline.txt
│   ├── concepts.json
│   ├── dependencies.json
│   ├── strategy.md
│   └── SYNTHESIS-REPORT.md
└── tests/
    └── test_auth.py
```

**Key Concepts Preserved**:
- JWT authentication strategy
- PostgreSQL schema decisions
- Rate limiting research (token bucket algorithm)

**Artifacts Consolidated**: 5 → 2 (plan.md + test-plan.md)

**Tests**: All passing, coverage unchanged (72%)

---

## Report Template

```markdown
# Synthesis Report

**Date**: [YYYY-MM-DD HH:MM:SS]
**Baseline Commit**: [hash]
**Synthesis Branch**: synthesis/cleanup-YYYYMMDD

## Summary

Consolidated [N] fragmented planning documents into unified execution plan while preserving [N] key concepts and archiving [N] superseded artifacts.

## Artifacts Processed

### Consolidated
- `plan.md` ← plan-v1.md, plan-v2.md, TODO.md
- `spec.md` ← spec-auth.md, notes/api-design.md
- `test-plan.md` ← NEW (from test inventory)

### Archived
- `archive/planning/` - 5 files
- `archive/tests/` - 12 orphaned test files
- `archive/logs/` - 23 log files

### Deleted
- None (all archived for reference)

## Key Concepts Preserved

1. **Authentication**: JWT + OAuth2 integration
2. **Database**: PostgreSQL schema with migrations
3. **API**: RESTful with GraphQL subset
4. **Rate Limiting**: Token bucket algorithm
5. **Deployment**: Blue-green strategy

## Naming Normalization

- Phases: phase-1-foundation, phase-2-core, phase-3-polish
- Tasks: task-{phase}-{number}-{description}
- Beads: [PHASE-N] prefix added to all issues

## Dependencies Mapped

- Critical path: 3 phases, 12 tasks
- Parallel streams: 2 (docs, testing)
- Integration points: 4 (auth/api, api/db, db/cache, api/frontend)

## Validation Results

✅ Tests: All passing (72% coverage, unchanged)
✅ References: All valid (0 broken links)
✅ Beads: Synchronized (12 issues match plan)
✅ Naming: Normalized throughout
✅ Archive: Complete with reference map

## Next Steps

1. Review unified `plan.md`
2. Begin phase-1-foundation (3 tasks)
3. Execute Work Plan Protocol from checkpoint
4. Monitor `.beads/issues.jsonl` for task state

## Files Changed

- Created: `plan.md`, `test-plan.md`
- Updated: `README.md`, `.beads/issues.jsonl`
- Moved: 40 files to `archive/`

**Total Time**: 2.5 hours
```

---

**Last Updated**: 2025-10-27
