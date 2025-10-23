---
name: constraint-rules
description: Reference guide for constraint propagation rules in typed holes refactoring including dependency tracking and solution space narrowing. Use as reference when propagating constraints between resolved holes.
---

# Constraint Propagation Rules

Complete guide to constraint propagation in typed holes refactoring.

## Overview

When a hole is resolved, its resolution creates constraints that propagate to dependent holes. This narrows the solution space and discovers new requirements.

## Propagation Rule Types

### 1. Interface Resolution → Type Constraints

**Pattern**: Concrete types flow to consumers

**Rule**:
```
IF: Interface hole resolved with type T
THEN: All consumers must handle type T
```

**Example 1: Async Interface**
```python
# Resolution of R3_abstraction_layers
class NodeInterface:
    async def run(self, context: Context) -> Result
    
# Propagates to:
R4_parallel_execution:
    MUST handle async/await
    MUST use asyncio for concurrency
    
R5_error_handling:
    MUST catch async exceptions
    MUST use try/except with async context
    
R7_testing:
    MUST use pytest-asyncio
    MUST test async behavior
```

**Example 2: Generic Types**
```python
# Resolution of R2_module_boundaries  
class Repository(Protocol[T]):
    def get(self, id: str) -> T
    def save(self, entity: T) -> None

# Propagates to:
R4_implementations:
    MUST provide type parameter
    MUST implement both methods with consistent T
    
R7_testing:
    MUST test with concrete types
    MUST verify type safety
```

### 2. Implementation → Performance Constraints

**Pattern**: Resource usage flows to dependent operations

**Rule**:
```
IF: Implementation uses N resources
THEN: Dependent operations share/compete for N resources
```

**Example 1: Concurrency Limits**
```python
# Resolution of R4_parallelization
parallel_executor = {
    "max_concurrent": 3,
    "strategy": "asyncio.gather"
}

# Propagates to:
R8_rate_limiting:
    rate_limit = provider_limit / 3
    
R9_memory_budget:
    memory_per_operation * 3 < total_memory
    
R10_connection_pool:
    pool_size >= 3
    
R7_testing:
    MUST test with max_concurrent operations
    MUST verify no race conditions
```

**Example 2: Cache Size**
```python
# Resolution of R5_caching_strategy
cache = {
    "max_size": 1000,
    "eviction": "LRU",
    "ttl": 3600
}

# Propagates to:
R9_memory_budget:
    cache_memory = 1000 * avg_entry_size
    total_memory >= cache_memory + operation_memory
    
R4_key_design:
    MUST design keys for good hit rate
    MUST handle cache invalidation
    
R7_testing:
    MUST test cache hit/miss scenarios
    MUST test eviction behavior
```

### 3. Validation → Test Requirements

**Pattern**: Test needs flow upstream

**Rule**:
```
IF: Validation requires N test cases
THEN: Test data and metrics must support N cases
```

**Example 1: Optimization Validation**
```python
# Resolution of R8_optimization_testing
validation = {
    "required_examples": 50,
    "statistical_significance": 0.05,
    "comparison_metric": "accuracy"
}

# Propagates to:
R6_test_data:
    MUST collect >= 50 labeled examples
    MUST ensure diversity in examples
    
R7_metrics:
    MUST support batch evaluation
    MUST compute statistical significance
    
R9_infrastructure:
    MUST support running 50+ test cases
    MUST store results for comparison
```

**Example 2: Performance Testing**
```python
# Resolution of R9_performance_validation
perf_tests = {
    "required_scenarios": 20,
    "iterations_per_scenario": 100,
    "metrics": ["latency_p50", "latency_p99", "throughput"]
}

# Propagates to:
R7_test_infrastructure:
    MUST support benchmark harness
    MUST collect timing data
    
R6_test_data:
    MUST have 20 representative scenarios
    
R8_monitoring:
    MUST track same metrics in production
```

### 4. Dependency Resolution → Implementation Constraints

**Pattern**: Chosen dependencies constrain implementations

**Rule**:
```
IF: Dependency D chosen with version V
THEN: Implementation must be compatible with D@V
```

**Example 1: Framework Choice**
```python
# Resolution of R2_testing_framework
testing = {
    "framework": "pytest",
    "version": "7.4.0",
    "plugins": ["pytest-asyncio", "pytest-cov"]
}

# Propagates to:
R7_test_writing:
    MUST use pytest fixtures
    MUST use pytest-asyncio for async tests
    
R8_ci_config:
    MUST install pytest 7.4.0
    MUST run pytest command
    
R4_async_implementation:
    CAN use asyncio (pytest-asyncio supports it)
```

**Example 2: Library Version**
```python
# Resolution of R3_http_client
http = {
    "library": "httpx",
    "version": "0.24.0",
    "features": ["async", "http2"]
}

# Propagates to:
R4_api_implementations:
    MUST use httpx.AsyncClient
    CAN use HTTP/2 features
    
R5_error_handling:
    MUST handle httpx exceptions
    MUST handle httpx.TimeoutException
    
R6_testing:
    MUST mock httpx (not requests)
    CAN use httpx.MockTransport
```

### 5. Architecture → Module Constraints

**Pattern**: Architecture rules flow to all modules

**Rule**:
```
IF: Architecture defines layer L with rules R
THEN: All modules in L must follow R
```

**Example 1: Layered Architecture**
```python
# Resolution of R1_target_architecture
architecture = {
    "layers": ["api", "domain", "data"],
    "rules": {
        "api": {
            "can_import": ["domain"],
            "cannot_import": ["data"]
        },
        "domain": {
            "can_import": [],
            "cannot_import": ["api", "data"]
        },
        "data": {
            "can_import": ["domain"],
            "cannot_import": ["api"]
        }
    }
}

# Propagates to:
R2_all_modules:
    MUST respect layer import rules
    
R4_new_modules:
    MUST be assigned to a layer
    MUST follow that layer's rules
    
R7_testing:
    MUST test layer violation detection
    test_no_layer_violations()
```

**Example 2: Dependency Direction**
```python
# Resolution of R1_dependency_flow
flow = {
    "direction": "top-down",
    "rule": "Higher layers depend on lower, never reverse"
}

# Propagates to:
R4_all_implementations:
    abstractions in lower layers
    implementations in higher layers
    
R5_interfaces:
    defined in lower layers
    consumed by higher layers
```

## Constraint Discovery

Sometimes resolving a hole discovers NEW constraints:

**Example: Discovering Resource Limits**
```python
# Resolution of R4_parallelization
# Attempts max_concurrent=10

# During testing, discovers:
- Provider rate limit = 30 req/min
- Memory per operation = 500MB
- Total memory = 4GB

# This DISCOVERS new constraints:
R4_updated:
    max_concurrent <= min(
        30 / requests_per_operation,  # Rate limit
        4000 / 500,  # Memory limit (=8)
        10  # Desired
    ) = 8

# And PROPAGATES:
R8_rate_limiting:
    MUST implement backoff for rate limits
    
R9_memory_management:
    MUST monitor memory usage
    MUST fail fast if memory exceeded
```

## Contradiction Detection

If constraints contradict, stop and resolve:

**Example: Conflicting Requirements**
```python
# R4_performance resolved
constraint_1 = "latency < 100ms"

# R5_security resolved  
constraint_2 = "encrypt all data (adds 150ms overhead)"

# CONFLICT DETECTED:
# Cannot satisfy both constraints simultaneously

# Resolution options:
1. Relax performance: latency < 200ms
2. Optimize encryption: use hardware acceleration
3. Parallelize: encrypt async, don't block main path
4. Compromise: encrypt at rest, not in transit

# Document decision in REFACTOR_IR.md
```

## Propagation Algorithm

```python
def propagate_constraints(resolved_hole, resolution):
    """Propagate constraints from resolved hole to dependents"""
    
    # 1. Extract constraints from resolution
    new_constraints = extract_constraints(resolution)
    
    # 2. Find dependent holes
    dependents = get_dependent_holes(resolved_hole)
    
    # 3. For each dependent
    for dependent in dependents:
        # Apply each propagation rule
        for constraint in new_constraints:
            rule = match_propagation_rule(constraint, dependent)
            if rule:
                # Add constraint to dependent
                dependent.constraints.add(
                    apply_rule(rule, constraint)
                )
                
                # Narrow solution space
                dependent.solution_space = filter(
                    dependent.solution_space,
                    lambda s: satisfies(s, constraint)
                )
        
        # Check if dependent is now over-constrained
        if is_unsatisfiable(dependent):
            raise ContradictionError(dependent, new_constraints)
        
        # Update dependent documentation
        update_refactor_ir(dependent)
    
    # 4. Check for newly resolvable holes
    newly_ready = find_ready_holes()
    return newly_ready
```

## Practical Examples

### Full Propagation Chain

```python
# Resolve R1: target_architecture
resolution_R1 = {
    "layers": ["api", "domain", "infrastructure"],
    "principle": "dependency inversion"
}

# Propagates to R2: module_boundaries
constraint_R2 = "domain must not depend on infrastructure"

# Resolve R2: module_boundaries
resolution_R2 = {
    "domain": ["core", "services", "interfaces"],
    "infrastructure": ["repositories", "external_apis"]
}

# Propagates to R3: abstraction_layers
constraint_R3 = "domain defines repository interfaces"

# Resolve R3: abstraction_layers
resolution_R3 = {
    "RepositoryProtocol": "defined in domain/interfaces"
}

# Propagates to R4: implementations
constraint_R4 = "infrastructure implements RepositoryProtocol"

# Resolve R4: implementations
resolution_R4 = {
    "PostgresRepository": "implements RepositoryProtocol in infrastructure"
}

# Propagates to R7: testing
constraint_R7 = "test domain with mock repositories"

# Full chain:
R1 → R2 → R3 → R4 → R7
```

## Constraint Validation

After propagation, validate all constraints:

```python
def validate_all_constraints():
    """Check that all constraints are satisfiable"""
    
    for hole in all_holes:
        # Check local constraint satisfaction
        if not are_satisfiable(hole.constraints):
            raise ContradictionError(hole)
        
        # Check global constraint interaction
        for other_hole in all_holes:
            if conflicts(hole.constraints, other_hole.constraints):
                raise GlobalContradictionError(hole, other_hole)
    
    return True
```

---

## Summary

Constraint propagation is the heart of typed holes refactoring:

1. **Extract** constraints from each resolution
2. **Propagate** to dependent holes via rules
3. **Narrow** solution spaces
4. **Discover** new constraints
5. **Detect** contradictions early
6. **Validate** continuously

This ensures that each hole resolution is informed by all previous decisions, maintaining global consistency throughout the refactoring process.
