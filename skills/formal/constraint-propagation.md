---
name: formal-constraint-propagation
description: Pruning search space before backtracking search
---



# Constraint Propagation

**Scope**: Constraint propagation algorithms, arc consistency, domain reduction, inference
**Lines**: ~340
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Pruning search space before backtracking search
- Implementing CSP solvers with preprocessing
- Detecting inconsistencies early in constraint problems
- Reducing domains to simplify problem solving
- Building efficient SAT/CSP solvers
- Implementing forward checking in search
- Understanding arc consistency algorithms (AC-3, AC-4)

## Core Concepts

### Consistency Levels

**Node consistency**: Unary constraints satisfied
- Each variable's domain contains only values satisfying unary constraints
- Simplest form: Remove invalid values from domains
- Example: X ∈ {1, 2, 3, 4, 5}, constraint X > 3 → domain {4, 5}
- Achieved in O(nd) time (n variables, d domain size)

**Arc consistency**: Binary constraints satisfied
- For each pair (Xi, Xj) with constraint, every value in Di has support in Dj
- "Support": Value vj ∈ Dj that satisfies constraint with vi ∈ Di
- Most common consistency level in practice
- AC-3 algorithm: O(ed³) worst case (e edges, d domain size)

**Path consistency**: Extends arc consistency
- For any values in two variables, there exists consistent values for intermediate variables
- More expensive than arc consistency
- Rarely used in practice (high cost, modest benefit)

**Bounds consistency**: For ordered domains
- Only check bounds (min/max) instead of all values
- Useful for large integer domains
- Example: X + Y = 10, X ∈ [1..9], Y ∈ [1..9] → X ∈ [1..9], Y ∈ [1..9]
- Much faster than full arc consistency for numerical domains

### Propagation vs Search

**Pure propagation**: No search, only inference
- Reduces domains using constraints
- May solve problem completely (if propagation is strong enough)
- May leave problem partially solved (domains still have multiple values)

**Propagation + Search**: Hybrid approach
- Propagate to reduce domains
- Search (backtracking) when propagation stops
- Propagate again after each assignment
- Standard approach in CSP solvers

**Trade-offs**:
- More propagation = less search (but higher overhead per node)
- Less propagation = more search (but faster per node)
- Arc consistency usually good balance

---

## Patterns

### Pattern 1: AC-3 Algorithm (Arc Consistency)

```python
from collections import deque

def ac3(variables, domains, constraints):
    """
    AC-3 algorithm for enforcing arc consistency.

    Args:
        variables: List of variable names
        domains: Dict mapping variable to set of values
        constraints: Dict mapping (Xi, Xj) to binary constraint function

    Returns:
        True if consistent, False if inconsistent (no solution)
        Modifies domains in place
    """
    # Initialize queue with all arcs
    queue = deque()
    for (xi, xj) in constraints:
        queue.append((xi, xj))

    while queue:
        (xi, xj) = queue.popleft()

        if revise(xi, xj, domains, constraints):
            # Domain of xi was revised
            if len(domains[xi]) == 0:
                return False  # Inconsistent (no solution)

            # Add arcs (xk, xi) for all xk ≠ xi, xj
            for xk in variables:
                if xk != xi and xk != xj:
                    if (xk, xi) in constraints:
                        queue.append((xk, xi))

    return True  # Consistent

def revise(xi, xj, domains, constraints):
    """
    Make xi arc-consistent with xj.
    Remove values from Di that have no support in Dj.
    """
    revised = False
    constraint = constraints[(xi, xj)]

    # Check each value in xi's domain
    for vi in list(domains[xi]):
        # Find support: value in Dj satisfying constraint
        has_support = False
        for vj in domains[xj]:
            if constraint(vi, vj):
                has_support = True
                break

        if not has_support:
            domains[xi].remove(vi)
            revised = True

    return revised

# Example usage
variables = ['X', 'Y', 'Z']
domains = {
    'X': {1, 2, 3},
    'Y': {1, 2, 3},
    'Z': {1, 2, 3}
}

constraints = {
    ('X', 'Y'): lambda x, y: x != y,  # X ≠ Y
    ('Y', 'X'): lambda y, x: x != y,
    ('Y', 'Z'): lambda y, z: y < z,   # Y < Z
    ('Z', 'Y'): lambda z, y: y < z,
}

is_consistent = ac3(variables, domains, constraints)
print(f"Consistent: {is_consistent}")
print(f"Domains after AC-3: {domains}")
# Output: X: {1,2,3}, Y: {1,2}, Z: {2,3}
```

**When to use**:
- Before backtracking search (preprocessing)
- After each assignment during search
- When domains are small/medium size

### Pattern 2: Forward Checking

```python
def forward_check(var, value, domains, constraints, assignment):
    """
    Apply forward checking after assigning var = value.
    Prunes domains of unassigned variables.

    Returns:
        Updated domains if consistent, None if inconsistent
    """
    # Create copy to allow backtracking
    new_domains = {v: d.copy() for v, d in domains.items()}
    new_domains[var] = {value}  # Assign variable

    # Check constraints with assigned variable
    for other_var in domains:
        if other_var in assignment or other_var == var:
            continue  # Skip assigned variables

        if (var, other_var) in constraints:
            constraint = constraints[(var, other_var)]

            # Remove values from other_var with no support
            for other_value in list(new_domains[other_var]):
                if not constraint(value, other_value):
                    new_domains[other_var].remove(other_value)

            # Check for domain wipeout
            if len(new_domains[other_var]) == 0:
                return None  # Inconsistent

    return new_domains

# Example in backtracking search
def backtrack_with_fc(assignment, domains, variables, constraints):
    """Backtracking search with forward checking."""
    if len(assignment) == len(variables):
        return assignment  # Complete assignment

    # Select unassigned variable
    var = select_unassigned_variable(variables, assignment, domains)

    for value in domains[var]:
        # Try assignment
        new_assignment = assignment.copy()
        new_assignment[var] = value

        # Forward check
        new_domains = forward_check(
            var, value, domains, constraints, new_assignment
        )

        if new_domains is not None:
            # Recursive call with pruned domains
            result = backtrack_with_fc(
                new_assignment, new_domains, variables, constraints
            )
            if result is not None:
                return result

    return None  # No solution
```

**Benefits**:
- Cheaper than full arc consistency (only checks assigned variables)
- Detects failures earlier than plain backtracking
- Good performance/cost trade-off

### Pattern 3: Maintaining Arc Consistency (MAC)

```python
def mac(assignment, domains, variables, constraints):
    """
    Backtracking with Maintaining Arc Consistency.
    Runs AC-3 after each assignment.
    """
    if len(assignment) == len(variables):
        return assignment

    var = select_unassigned_variable(variables, assignment, domains)

    for value in domains[var]:
        new_assignment = assignment.copy()
        new_assignment[var] = value

        # Create new domains with assignment
        new_domains = {v: d.copy() for v, d in domains.items()}
        new_domains[var] = {value}

        # Run AC-3 on remaining variables
        if ac3_with_assignment(
            variables, new_domains, constraints, new_assignment
        ):
            result = mac(
                new_assignment, new_domains, variables, constraints
            )
            if result is not None:
                return result

    return None

def ac3_with_assignment(variables, domains, constraints, assignment):
    """AC-3 that respects current assignments."""
    queue = deque()

    # Only add arcs between unassigned variables
    for (xi, xj) in constraints:
        if xi not in assignment and xj not in assignment:
            queue.append((xi, xj))

    while queue:
        (xi, xj) = queue.popleft()

        if xi in assignment or xj in assignment:
            continue  # Skip if now assigned

        if revise(xi, xj, domains, constraints):
            if len(domains[xi]) == 0:
                return False

            # Re-add affected arcs
            for xk in variables:
                if xk not in assignment and xk != xi and xk != xj:
                    if (xk, xi) in constraints:
                        queue.append((xk, xi))

    return True
```

**When to use**:
- Problems where propagation is very effective
- When search tree is large and pruning saves time
- Trade-off: Higher cost per node, fewer nodes explored

### Pattern 4: Bounds Consistency for Arithmetic

```python
def bounds_consistency_add(x_domain, y_domain, z_domain, constraint):
    """
    Enforce bounds consistency for X + Y = Z.
    Updates domains to be bounds-consistent.

    Args:
        x_domain, y_domain, z_domain: (min, max) tuples
        constraint: 'add' for X + Y = Z

    Returns:
        Updated (x_domain, y_domain, z_domain) or None if inconsistent
    """
    x_min, x_max = x_domain
    y_min, y_max = y_domain
    z_min, z_max = z_domain

    # X bounds from Z - Y
    new_x_min = max(x_min, z_min - y_max)
    new_x_max = min(x_max, z_max - y_min)

    # Y bounds from Z - X
    new_y_min = max(y_min, z_min - x_max)
    new_y_max = min(y_max, z_max - x_min)

    # Z bounds from X + Y
    new_z_min = max(z_min, x_min + y_min)
    new_z_max = min(z_max, x_max + y_max)

    # Check consistency
    if new_x_min > new_x_max or new_y_min > new_y_max or new_z_min > new_z_max:
        return None  # Inconsistent

    return (
        (new_x_min, new_x_max),
        (new_y_min, new_y_max),
        (new_z_min, new_z_max)
    )

# Example
x_domain = (1, 10)
y_domain = (5, 15)
z_domain = (10, 20)

result = bounds_consistency_add(x_domain, y_domain, z_domain, 'add')
print(result)
# ((5, 10), (5, 15), (10, 20))
# X narrowed to [5, 10] because Z - Y_max = 20 - 15 = 5
```

**When to use**:
- Large integer domains (thousands of values)
- Arithmetic constraints (add, multiply, etc.)
- Linear programming relaxations

### Pattern 5: Conflict-Directed Backjumping

```python
def backjump(assignment, domains, variables, constraints):
    """
    Backtracking with conflict-directed backjumping.
    Jumps back to source of conflict instead of immediate predecessor.
    """
    if len(assignment) == len(variables):
        return assignment, set()

    var = select_unassigned_variable(variables, assignment, domains)

    for value in domains[var]:
        new_assignment = assignment.copy()
        new_assignment[var] = value

        # Check conflicts
        conflict_set = get_conflicts(var, value, assignment, constraints)

        if not conflict_set:
            # No conflict: recurse
            result, conf = backjump(
                new_assignment, domains, variables, constraints
            )

            if result is not None:
                return result, set()

            # Conflict deeper in tree
            conflict_set = conf

        # If conflict doesn't involve current variable, backjump
        if var not in conflict_set:
            return None, conflict_set

    # All values failed: return conflict set
    return None, get_all_conflicts(var, assignment, constraints)

def get_conflicts(var, value, assignment, constraints):
    """Return set of variables conflicting with var=value."""
    conflicts = set()

    for other_var, other_value in assignment.items():
        if (var, other_var) in constraints:
            constraint = constraints[(var, other_var)]
            if not constraint(value, other_value):
                conflicts.add(other_var)

    return conflicts
```

**Benefits**:
- Avoids redundant search in branches
- Particularly effective on structured problems
- Can dramatically reduce search tree size

---

## Quick Reference

### Consistency Algorithms Comparison

| Algorithm | Time Complexity | Space | Strength | Use Case |
|-----------|----------------|-------|----------|----------|
| Node Consistency | O(nd) | O(nd) | Weakest | Preprocessing |
| AC-3 | O(ed³) | O(e) | Medium | General CSPs |
| AC-4 | O(ed²) | O(ed²) | Medium | Static CSPs |
| Forward Checking | O(d²) per node | O(nd) | Weak | During search |
| MAC | O(ed³) per node | O(nd) | Strong | Tight constraints |
| Bounds Consistency | O(1) per propagation | O(n) | Medium | Arithmetic constraints |

### Propagation Strategy Selection

```
Small domains (< 10 values):
  → Use AC-3 or MAC

Large domains (> 1000 values):
  → Use bounds consistency

Sparse constraint graph:
  → Forward checking sufficient

Dense constraint graph:
  → MAC more effective

Real-time requirements:
  → Forward checking (lower overhead)

Offline solving:
  → MAC (fewer nodes searched)
```

### Implementation Checklist

```
✅ DO: Implement revise() separately for reuse
✅ DO: Use queue for AC-3 (not recursion)
✅ DO: Copy domains when backtracking
✅ DO: Check domain wipeout immediately
❌ DON'T: Propagate after every single constraint check
❌ DON'T: Use path consistency unless necessary
❌ DON'T: Forget bidirectional arcs (X→Y and Y→X)
❌ DON'T: Re-add arcs unnecessarily to queue
```

---

## Anti-Patterns

❌ **No propagation before search**
```python
# Inefficient: Start search with full domains
def solve_csp(variables, domains, constraints):
    return backtrack({}, domains, variables, constraints)
```
✅ Run AC-3 preprocessing first

❌ **Wrong consistency level for domain size**
```python
# Slow: Full arc consistency on huge domains
domains = {'X': set(range(1, 1000000))}  # 1 million values
ac3(variables, domains, constraints)  # Very slow
```
✅ Use bounds consistency for large integer domains

❌ **Forgetting to add reverse arcs**
```python
# Bug: Only one direction
constraints = {
    ('X', 'Y'): lambda x, y: x < y
    # Missing: ('Y', 'X')
}
```
✅ Add both (Xi, Xj) and (Xj, Xi) to constraints

❌ **Modifying domains during iteration**
```python
# Bug: Modifying set while iterating
for value in domains[var]:  # Set iteration
    domains[var].remove(value)  # Modifies set
```
✅ Iterate over copy: `for value in list(domains[var])`

❌ **Expensive propagation in search**
```python
# Slow: Path consistency at every node
def backtrack_pc(assignment, domains, ...):
    path_consistency(domains)  # Overkill
    # ... rest of search
```
✅ Use lighter propagation (forward checking) during search

---

## Related Skills

- `csp-modeling.md` - Defining CSP problems and constraints
- `backtracking-search.md` - Search algorithms using propagation
- `sat-solving-strategies.md` - Unit propagation in Boolean SAT
- `graph-algorithms.md` - Constraint graph analysis
- `optimization-algorithms.md` - Constraint-based optimization

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
