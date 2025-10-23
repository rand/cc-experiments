---
name: typed-holes-refactor
description: Refactor codebases using Design by Typed Holes methodology - iterative, test-driven refactoring with formal hole resolution, constraint propagation, and continuous validation. Use when refactoring existing code, optimizing architecture, or consolidating technical debt through systematic hole-driven development.
---

# Typed Holes Refactoring

Systematically refactor codebases using the Design by Typed Holes meta-framework: treat architectural unknowns as typed holes, resolve them iteratively with test-driven validation, and propagate constraints through dependency graphs.

## Core Workflow

### Phase 0: Hole Discovery & Setup

**1. Create safe working branch:**

```bash
git checkout -b refactor/typed-holes-v1
# CRITICAL: Never work in main, never touch .beads/ in main
```

**2. Analyze current state and identify holes:**

```bash
python scripts/discover_holes.py
# Creates REFACTOR_IR.md with hole catalog
```

The Refactor IR documents:
- **Current State Holes**: What's unknown about the current system?
- **Refactor Holes**: What needs resolution to reach the ideal state?
- **Constraints**: What must be preserved/improved/maintained?
- **Dependencies**: Which holes block which others?

**3. Write baseline characterization tests:**

Create `tests/characterization/` to capture exact current behavior:

```python
# tests/characterization/test_current_behavior.py
def test_api_contracts():
    """All public APIs must behave identically post-refactor"""
    for endpoint in discover_public_apis():
        old_result = run_current(endpoint, test_inputs)
        save_baseline(endpoint, old_result)

def test_performance_baselines():
    """Record current performance - don't regress"""
    baselines = measure_all_operations()
    save_json("baselines.json", baselines)
```

Run tests on main branch - they should all pass. These are your safety net.

### Phase 1-N: Iterative Hole Resolution

For each hole (in dependency order):

**1. Select next ready hole:**

```bash
python scripts/next_hole.py
# Shows holes whose dependencies are resolved
```

**2. Write validation tests FIRST (test-driven):**

```python
# tests/refactor/test_h{N}_resolution.py
def test_h{N}_resolved():
    """Define what 'resolved correctly' means"""
    # This should FAIL initially
    assert desired_state_achieved()

def test_h{N}_equivalence():
    """Ensure no behavioral regressions"""
    old_behavior = load_baseline()
    new_behavior = run_refactored()
    assert old_behavior == new_behavior
```

**3. Implement resolution:**

- Refactor code to make tests pass
- Keep characterization tests passing
- Commit incrementally with clear messages

**4. Validate resolution:**

```bash
python scripts/validate_resolution.py H{N}
# Checks: tests pass, constraints satisfied, main untouched
```

**5. Propagate constraints:**

```bash
python scripts/propagate.py H{N}
# Updates dependent holes based on resolution
```

**6. Document and commit:**

```bash
git add .
git commit -m "Resolve H{N}: {description}

- Tests: tests/refactor/test_h{N}_*.py pass
- Constraints: {constraints satisfied}
- Propagates to: {dependent holes}"
```

### Phase Final: Reporting

**Generate comprehensive delta report:**

```bash
python scripts/generate_report.py > REFACTOR_REPORT.md
```

Report includes:
- Hole resolution summary with validation evidence
- Metrics delta (LOC, complexity, coverage, performance)
- Behavioral analysis (intentional changes documented)
- Constraint validation (all satisfied)
- Risk assessment and migration guide

## Key Principles

### 1. Test-Driven Everything

- Write validation criteria BEFORE implementing
- Tests define "correct resolution"
- Characterization tests are sacred - never let them fail

### 2. Hole-Driven Progress

- Resolve holes in dependency order
- Each resolution propagates constraints
- Track everything formally in Refactor IR

### 3. Continuous Validation

Every commit must validate:
- ✅ Characterization tests pass (behavior preserved)
- ✅ Resolution tests pass (hole resolved correctly)
- ✅ Constraints satisfied
- ✅ Main branch untouched
- ✅ `.beads/` intact in main

### 4. Safe by Construction

- Work only in refactor branch
- Main is read-only reference
- Beads are untouchable historical artifacts

### 5. Formal Completeness

Design complete when:
- All holes resolved and validated
- All constraints satisfied
- All phase gates passed
- Metrics improved or maintained

## Common Hole Types

### Architecture Holes

```python
"?R1_target_architecture": "What should the ideal structure be?"
"?R2_module_boundaries": "How should modules be organized?"
"?R3_abstraction_layers": "What layers/interfaces are needed?"
```

**Validation:** Architecture tests, dependency analysis, layer violation checks

### Implementation Holes

```python
"?R4_consolidation_targets": "What code should merge?"
"?R5_extraction_targets": "What code should split out?"
"?R6_elimination_targets": "What code should be removed?"
```

**Validation:** Duplication detection, equivalence tests, dead code analysis

### Quality Holes

```python
"?R7_test_strategy": "How to validate equivalence?"
"?R8_migration_path": "How to safely transition?"
"?R9_rollback_mechanism": "How to undo if needed?"
```

**Validation:** Test coverage metrics, migration dry-runs, rollback tests

See [HOLE_TYPES.md](references/HOLE_TYPES.md) for complete catalog.

## Constraint Propagation Rules

### Rule 1: Interface Resolution → Type Constraints

```
When: Interface hole resolved with concrete types
Then: Propagate type requirements to all consumers

Example:
  Resolve R6: NodeInterface = BaseNode with async run()
  Propagates to:
    → R4: Parallel execution must handle async
    → R5: Error recovery must handle async exceptions
```

### Rule 2: Implementation → Performance Constraints

```
When: Implementation resolved with resource usage
Then: Propagate limits to dependent holes

Example:
  Resolve R4: Parallelization with max_concurrent=3
  Propagates to:
    → R8: Rate limit = provider_limit / 3
    → R7: Memory budget = 3 * single_operation_memory
```

### Rule 3: Validation → Test Requirements

```
When: Validation resolved with test requirements
Then: Propagate data needs upstream

Example:
  Resolve R9: Testing needs 50 examples
  Propagates to:
    → R7: Metrics must support batch evaluation
    → R8: Test data collection strategy needed
```

See [CONSTRAINT_RULES.md](references/CONSTRAINT_RULES.md) for complete propagation rules.

## Success Indicators

### Weekly Progress

- 2-4 holes resolved
- All tests passing
- Constraints satisfied
- Measurable improvements

### Red Flags (Stop & Reassess)

- ❌ Characterization tests fail
- ❌ Hole can't be resolved within constraints
- ❌ Constraints contradict each other
- ❌ No progress for 3+ days
- ❌ Main branch accidentally modified

## Validation Gates

| Gate | Criteria | Check |
|------|----------|-------|
| Gate 1: Discovery Complete | All holes cataloged, dependencies mapped | `python scripts/check_discovery.py` |
| Gate 2: Foundation Holes | Core interfaces resolved, tests pass | `python scripts/check_foundation.py` |
| Gate 3: Implementation | All refactor holes resolved, metrics improved | `python scripts/check_implementation.py` |
| Gate 4: Production Ready | Migration tested, rollback verified | `python scripts/check_production.py` |

## Scripts Reference

All scripts are in `scripts/`:

- `discover_holes.py` - Analyze codebase and generate REFACTOR_IR.md
- `next_hole.py` - Show next resolvable holes based on dependencies
- `validate_resolution.py` - Check if hole resolution satisfies constraints
- `propagate.py` - Update dependent holes after resolution
- `generate_report.py` - Create comprehensive delta report
- `check_completeness.py` - Verify all holes resolved
- `visualize_graph.py` - Generate hole dependency visualization

Run any script with `--help` for detailed usage.

## Meta-Consistency

This skill uses its own principles:

| Typed Holes Principle | Application to Refactoring |
|-----------------------|----------------------------|
| Typed Holes | Architectural unknowns cataloged with types |
| Constraint Propagation | Design constraints flow through dependency graph |
| Iterative Refinement | Hole-by-hole resolution cycles |
| Test-Driven Validation | Tests define correctness |
| Formal Completeness | Gates verify design completeness |

**We use the system to refactor the system.**

## Advanced Topics

For complex scenarios, see:

- [HOLE_TYPES.md](references/HOLE_TYPES.md) - Detailed hole taxonomy
- [CONSTRAINT_RULES.md](references/CONSTRAINT_RULES.md) - Complete propagation rules
- [VALIDATION_PATTERNS.md](references/VALIDATION_PATTERNS.md) - Test patterns for different hole types
- [EXAMPLES.md](references/EXAMPLES.md) - Complete worked examples

## Quick Start Example

```bash
# 1. Setup
git checkout -b refactor/typed-holes-v1
python scripts/discover_holes.py

# 2. Write baseline tests
# Create tests/characterization/test_*.py

# 3. Resolve first hole
python scripts/next_hole.py  # Shows H1 is ready
# Write tests/refactor/test_h1_*.py (fails initially)
# Refactor code until tests pass
python scripts/validate_resolution.py H1
python scripts/propagate.py H1
git commit -m "Resolve H1: ..."

# 4. Repeat for each hole
# ...

# 5. Generate report
python scripts/generate_report.py > REFACTOR_REPORT.md
```

## Troubleshooting

**Characterization tests fail:**
- Revert changes, investigate what behavior changed
- Determine if change is intentional
- If intentional, update baselines with clear documentation
- If unintentional, fix the regression

**Hole can't be resolved:**
- Check if dependencies are actually resolved
- Review constraints - are they contradictory?
- Consider splitting hole into smaller holes
- Consult dependency graph for alternatives

**No progress:**
- Review REFACTOR_IR.md - are holes well-defined?
- Run `visualize_graph.py` - identify bottlenecks
- Consider pair programming or review
- Reassess if hole resolution is feasible

---

**Begin with Phase 0: Discovery. Always work in a branch. Test first, refactor second.**
