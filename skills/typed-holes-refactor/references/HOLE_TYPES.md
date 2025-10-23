---
name: hole-types
description: Reference taxonomy of refactoring hole types including current state holes, architecture holes, and implementation holes. Use as reference during typed holes refactoring for identifying and categorizing unknowns.
---

# Hole Types Reference

Complete taxonomy of refactoring holes with validation patterns.

## Table of Contents

1. [Current State Holes](#current-state-holes)
2. [Architecture Holes](#architecture-holes)
3. [Implementation Holes](#implementation-holes)
4. [Quality Holes](#quality-holes)
5. [Migration Holes](#migration-holes)

---

## Current State Holes

These holes represent unknowns about the existing system. Resolve before refactoring.

### H0_codebase_inventory

**Type**: `Dict[str, FileMetadata]`

**Question**: What files exist and what do they do?

**Resolution**:
```python
inventory = {
    "src/module.py": {
        "purpose": "Core business logic",
        "dependencies": ["config.py", "utils.py"],
        "public_api": ["process", "validate"],
        "dead_code": ["old_process"]
    }
}
```

**Validation**:
- AST analysis complete
- All public APIs documented
- Import graph generated

### H0_dependency_graph

**Type**: `DirectedGraph`

**Question**: What depends on what?

**Resolution**: Generate dependency graph with cycle detection

**Validation**:
- No circular dependencies (or documented)
- Critical path identified
- Bottlenecks highlighted

### H0_test_landscape

**Type**: `TestCoverage`

**Question**: What's already tested?

**Resolution**:
```python
coverage = {
    "line_coverage": 0.65,
    "branch_coverage": 0.42,
    "uncovered_critical": ["auth.py", "payment.py"]
}
```

**Validation**:
- Coverage report generated
- Critical gaps identified
- Test quality assessed

---

## Architecture Holes

### R1_target_architecture

**Type**: `ArchitectureSpec`

**Question**: What should the ideal structure be?

**Resolution**:
```python
architecture = {
    "layers": ["presentation", "domain", "data"],
    "modules": {
        "presentation": ["api", "cli"],
        "domain": ["core", "services"],
        "data": ["repositories", "models"]
    },
    "rules": [
        "presentation can call domain",
        "domain cannot call presentation",
        "data can only be called by domain"
    ]
}
```

**Validation Tests**:
```python
def test_no_layer_violations():
    violations = check_architecture_rules()
    assert len(violations) == 0

def test_dependency_direction():
    for module in domain_modules:
        deps = get_dependencies(module)
        assert not any(d in presentation_modules for d in deps)
```

### R2_module_boundaries

**Type**: `Dict[str, ModuleDef]`

**Question**: How should modules be organized?

**Resolution**:
```python
modules = {
    "auth": {
        "responsibility": "Authentication & authorization",
        "public_interface": ["authenticate", "authorize"],
        "private": ["hash_password", "validate_token"]
    }
}
```

**Validation**:
- Each module has single responsibility
- Cohesion > 0.7
- Coupling < 0.3

### R3_abstraction_layers

**Type**: `List[Layer]`

**Question**: What interfaces/protocols are needed?

**Resolution**:
```python
class Repository(Protocol):
    def get(self, id: str) -> Entity: ...
    def save(self, entity: Entity) -> None: ...

class Service(Protocol):
    def execute(self, command: Command) -> Result: ...
```

**Validation**:
- All implementations satisfy protocols
- Type checker passes
- No leaked abstractions

---

## Implementation Holes

### R4_consolidation_targets

**Type**: `List[ConsolidationPlan]`

**Question**: What duplicate code should merge?

**Resolution**:
```python
consolidations = [
    {
        "targets": ["parse_v1.py", "parse_v2.py", "parse_v3.py"],
        "unified": "parser.py",
        "reason": "Same logic with minor variations",
        "strategy": "Single function with mode parameter"
    }
]
```

**Validation Tests**:
```python
def test_consolidated_equivalence():
    """New unified function equals all old functions"""
    for old_func, test_cases in [(parse_v1, cases1), ...]:
        for case in test_cases:
            old_result = old_func(case)
            new_result = unified_parse(case)
            assert old_result == new_result

def test_no_remaining_duplicates():
    clones = find_code_clones(threshold=0.8)
    assert len(clones) == 0
```

### R5_extraction_targets

**Type**: `List[ExtractionPlan]`

**Question**: What code should split out?

**Resolution**:
```python
extractions = [
    {
        "source": "monolith.py:process_and_send",
        "extract": ["process", "send"],
        "reason": "Two responsibilities",
        "new_modules": ["processor.py", "sender.py"]
    }
]
```

**Validation**:
- Each extracted module has single responsibility
- Original behavior preserved
- Dependencies reduced

### R6_elimination_targets

**Type**: `List[str]`

**Question**: What dead code should be removed?

**Resolution**:
```python
dead_code = [
    "old_api.py",  # Replaced by new_api.py
    "legacy_parser.py",  # No callers
    "deprecated_utils.py"  # Unused for 6 months
]
```

**Validation**:
```python
def test_no_callers():
    """Ensure code marked dead has no callers"""
    for dead_file in dead_code:
        callers = find_callers(dead_file)
        assert len(callers) == 0, f"{dead_file} still called by {callers}"
```

---

## Quality Holes

### R7_test_strategy

**Type**: `TestStrategy`

**Question**: How do we validate equivalence?

**Resolution**:
```python
strategy = {
    "characterization": {
        "coverage": "All public APIs",
        "location": "tests/characterization/",
        "approach": "Capture current behavior as baselines"
    },
    "refactor_validation": {
        "coverage": "Each hole resolution",
        "location": "tests/refactor/",
        "approach": "TDD - write tests before refactoring"
    },
    "integration": {
        "coverage": "End-to-end workflows",
        "location": "tests/integration/",
        "approach": "Compare old vs new on real scenarios"
    }
}
```

**Validation**:
- Test coverage > 80%
- All characterization tests pass
- Performance tests don't regress

### R8_migration_path

**Type**: `MigrationPlan`

**Question**: How do we safely transition?

**Resolution**:
```python
plan = {
    "phase1": "Deploy refactored code behind feature flag",
    "phase2": "Enable for 10% traffic, monitor",
    "phase3": "Ramp to 100% over 2 weeks",
    "rollback": "Disable feature flag, revert deployment"
}
```

**Validation**:
- Dry-run migration succeeds
- Feature flag tested
- Rollback tested

### R9_rollback_mechanism

**Type**: `RollbackStrategy`

**Question**: How do we undo if needed?

**Resolution**:
```python
rollback = {
    "code": "Keep old branch, feature flag controls routing",
    "data": "No schema changes during refactor",
    "config": "Feature flag toggle takes effect immediately"
}
```

**Validation**:
```python
def test_rollback():
    """Ensure can revert to old version"""
    enable_refactor()
    assert uses_new_code()
    
    disable_refactor()
    assert uses_old_code()
    
    # Both versions produce same results
    assert old_results == new_results
```

---

## Migration Holes

### M1_feature_flags

**Type**: `FeatureFlagSchema`

**Question**: How to control rollout?

**Resolution**:
```python
flags = {
    "use_refactored_parser": {
        "type": "boolean",
        "default": False,
        "rollout_strategy": "percentage",
        "monitoring": ["error_rate", "latency"]
    }
}
```

### M2_backward_compatibility

**Type**: `CompatibilityMatrix`

**Question**: What must remain compatible?

**Resolution**:
```python
compatibility = {
    "api": "All endpoints preserve signatures",
    "data": "No schema changes",
    "config": "All existing configs supported",
    "behavior": "Same outputs for same inputs"
}
```

**Validation**:
```python
def test_api_compatibility():
    """All old API calls work identically"""
    for endpoint, test_cases in api_tests.items():
        for case in test_cases:
            old = call_old_api(endpoint, case)
            new = call_new_api(endpoint, case)
            assert old == new
```

### M3_monitoring

**Type**: `MonitoringPlan`

**Question**: How do we detect regressions?

**Resolution**:
```python
monitoring = {
    "metrics": [
        "request_latency_p50",
        "request_latency_p99", 
        "error_rate",
        "throughput"
    ],
    "alerts": [
        "error_rate > baseline * 1.1",
        "latency_p99 > baseline * 1.2"
    ]
}
```

---

## Hole Resolution Checklist

For any hole:

- [ ] Type annotation defined
- [ ] Validation criteria specified
- [ ] Dependencies identified
- [ ] Constraints documented
- [ ] Tests written (failing initially)
- [ ] Resolution implemented
- [ ] Tests passing
- [ ] Constraints propagated
- [ ] Documentation updated
- [ ] Committed with clear message
