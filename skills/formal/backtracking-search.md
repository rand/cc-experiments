---
name: formal-backtracking-search
description: Implementing CSP solvers with systematic search
---



# Backtracking Search

**Scope**: Backtracking search for CSPs, variable ordering heuristics, value ordering, optimization
**Lines**: ~320
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing CSP solvers with systematic search
- Finding all solutions to constraint problems
- Optimizing search with variable/value ordering heuristics
- Solving scheduling, assignment, or configuration problems
- Building puzzle solvers requiring exhaustive search
- Implementing constraint-based optimization
- Understanding CSP search performance tuning

## Core Concepts

### Backtracking Framework

**Basic algorithm**: Depth-first search with constraint checking
1. Select unassigned variable
2. Try each value in variable's domain
3. Check if assignment consistent with constraints
4. Recurse on remaining variables
5. Backtrack if no consistent assignment found

**Completeness**: Explores entire search tree
- Guaranteed to find solution if one exists
- Can prove unsatisfiability by exhausting search space

**Performance**: Exponential worst case O(d^n)
- n variables, d domain size
- Heuristics critical for practical performance

### Variable Ordering Heuristics

**Minimum Remaining Values (MRV)**: Choose variable with fewest legal values
- "Most constrained variable" or "fail-first" heuristic
- Detects failures earlier, prunes search tree
- Example: Sudoku cell with only 2 candidates vs cell with 7

**Degree heuristic**: Tiebreaker for MRV
- Choose variable involved in most constraints with unassigned variables
- Reduces branching factor in future choices

**Dynamic ordering**: Recompute best variable at each step
- More expensive but more effective than static ordering
- Standard approach in modern CSP solvers

### Value Ordering Heuristics

**Least Constraining Value (LCV)**: Try value leaving most choices for other variables
- Choose value that rules out fewest values in other domains
- "Most likely to succeed" heuristic
- Useful when finding any solution (not all solutions)

**Random ordering**: No heuristic
- Useful for unstructured problems
- Simpler to implement

---

## Patterns

### Pattern 1: Basic Backtracking Search

```python
def backtracking_search(variables, domains, constraints):
    """
    Find solution to CSP using backtracking.

    Returns:
        Assignment (dict) if solution found, None otherwise
    """
    return backtrack({}, variables, domains, constraints)

def backtrack(assignment, variables, domains, constraints):
    """Recursive backtracking with constraint checking."""
    # Base case: assignment complete
    if len(assignment) == len(variables):
        return assignment

    # Select unassigned variable
    var = select_unassigned_variable(variables, assignment)

    # Try each value in domain
    for value in order_domain_values(var, domains):
        # Check if assignment consistent
        if is_consistent(var, value, assignment, constraints):
            # Add to assignment
            assignment[var] = value

            # Recurse
            result = backtrack(assignment, variables, domains, constraints)
            if result is not None:
                return result

            # Backtrack: remove assignment
            del assignment[var]

    return None  # No solution found

def is_consistent(var, value, assignment, constraints):
    """Check if var=value consistent with current assignment."""
    for other_var, other_value in assignment.items():
        # Check constraint between var and other_var
        if (var, other_var) in constraints:
            constraint = constraints[(var, other_var)]
            if not constraint(value, other_value):
                return False

        # Check reverse constraint
        if (other_var, var) in constraints:
            constraint = constraints[(other_var, var)]
            if not constraint(other_value, value):
                return False

    return True
```

**When to use**:
- Simple CSP problems
- Educational implementations
- Baseline for comparing optimizations

### Pattern 2: MRV (Minimum Remaining Values) Heuristic

```python
def select_unassigned_variable_mrv(variables, assignment, domains):
    """
    Select variable with MRV heuristic.
    Choose variable with fewest remaining legal values.
    """
    unassigned = [v for v in variables if v not in assignment]

    # Count remaining values for each variable
    def count_values(var):
        # If using domain reduction, count current domain size
        return len(domains[var])

    # Choose variable with minimum remaining values
    mrv_var = min(unassigned, key=count_values)

    return mrv_var

def select_unassigned_variable_mrv_degree(
    variables, assignment, domains, constraints
):
    """
    MRV with degree heuristic as tiebreaker.
    Degree = number of constraints with unassigned variables.
    """
    unassigned = [v for v in variables if v not in assignment]

    def mrv_degree_key(var):
        # Primary: MRV (fewer values better, so positive count)
        mrv = len(domains[var])

        # Secondary: Degree (more constraints better, so negative count)
        degree = -sum(
            1 for other_var in unassigned
            if other_var != var and (
                (var, other_var) in constraints or
                (other_var, var) in constraints
            )
        )

        return (mrv, degree)

    return min(unassigned, key=mrv_degree_key)

# Example usage
variables = ['A', 'B', 'C', 'D']
domains = {
    'A': {1, 2, 3},      # 3 values
    'B': {1, 2},         # 2 values (MRV chooses this)
    'C': {1, 2, 3, 4},   # 4 values
    'D': {1, 2, 3}       # 3 values
}
assignment = {}

var = select_unassigned_variable_mrv(variables, assignment, domains)
print(var)  # 'B'
```

**Benefits**:
- Prunes search tree earlier
- 10-100x speedup on many problems
- Nearly always beneficial

### Pattern 3: LCV (Least Constraining Value) Heuristic

```python
def order_domain_values_lcv(var, assignment, domains, constraints):
    """
    Order values using LCV heuristic.
    Try value that rules out fewest choices for other variables first.
    """
    def count_conflicts(value):
        """Count how many values ruled out in other domains."""
        conflicts = 0

        for other_var in domains:
            if other_var in assignment or other_var == var:
                continue  # Skip assigned and self

            # Count values in other_var ruled out by var=value
            for other_value in domains[other_var]:
                if (var, other_var) in constraints:
                    constraint = constraints[(var, other_var)]
                    if not constraint(value, other_value):
                        conflicts += 1

        return conflicts

    # Sort values by number of conflicts (ascending)
    values = sorted(domains[var], key=count_conflicts)
    return values

# Example
def backtrack_with_heuristics(assignment, variables, domains, constraints):
    """Backtracking with MRV and LCV."""
    if len(assignment) == len(variables):
        return assignment

    # MRV: Select most constrained variable
    var = select_unassigned_variable_mrv(variables, assignment, domains)

    # LCV: Try least constraining values first
    values = order_domain_values_lcv(var, assignment, domains, constraints)

    for value in values:
        if is_consistent(var, value, assignment, constraints):
            assignment[var] = value
            result = backtrack_with_heuristics(
                assignment, variables, domains, constraints
            )
            if result is not None:
                return result
            del assignment[var]

    return None
```

**When to use**:
- Finding single solution (not all solutions)
- Domains have many values
- Constraints are tight

### Pattern 4: Backtracking with Forward Checking

```python
def backtrack_fc(assignment, domains, variables, constraints):
    """Backtracking with forward checking (domain pruning)."""
    if len(assignment) == len(variables):
        return assignment

    var = select_unassigned_variable_mrv(variables, assignment, domains)

    for value in domains[var]:
        if is_consistent(var, value, assignment, constraints):
            # Save current domains
            saved_domains = {v: d.copy() for v, d in domains.items()}

            # Assign and forward check
            assignment[var] = value
            domains[var] = {value}

            # Prune domains of unassigned variables
            pruned = forward_check(var, value, domains, constraints, assignment)

            if pruned:  # No domain wipeout
                result = backtrack_fc(
                    assignment, domains, variables, constraints
                )
                if result is not None:
                    return result

            # Restore domains and backtrack
            domains.update(saved_domains)
            del assignment[var]

    return None

def forward_check(var, value, domains, constraints, assignment):
    """
    Prune domains after assigning var=value.
    Returns False if any domain becomes empty.
    """
    for other_var in domains:
        if other_var in assignment or other_var == var:
            continue

        if (var, other_var) in constraints:
            constraint = constraints[(var, other_var)]

            # Remove inconsistent values from other_var
            to_remove = []
            for other_value in domains[other_var]:
                if not constraint(value, other_value):
                    to_remove.append(other_value)

            for v in to_remove:
                domains[other_var].discard(v)

            # Check for domain wipeout
            if len(domains[other_var]) == 0:
                return False

    return True
```

**Benefits**:
- Detects failures earlier than plain backtracking
- Reduces search tree size significantly
- Standard optimization in CSP solvers

### Pattern 5: Finding All Solutions

```python
def find_all_solutions(variables, domains, constraints):
    """Find all solutions to CSP."""
    solutions = []

    def backtrack_all(assignment):
        if len(assignment) == len(variables):
            # Found complete assignment
            solutions.append(assignment.copy())
            return

        var = select_unassigned_variable_mrv(variables, assignment, domains)

        for value in domains[var]:
            if is_consistent(var, value, assignment, constraints):
                assignment[var] = value
                backtrack_all(assignment)  # Don't return early
                del assignment[var]

    backtrack_all({})
    return solutions

# Example: All 4-Queens solutions
variables = list(range(4))
domains = {i: {0, 1, 2, 3} for i in range(4)}

def no_attack_constraint(col1, col2, row1, row2):
    """Queens don't attack each other."""
    return (col1 != col2 and  # Different columns
            abs(row1 - row2) != abs(col1 - col2))  # Not diagonal

constraints = {
    (i, j): (lambda c1, c2, r1=i, r2=j:
             no_attack_constraint(c1, c2, r1, r2))
    for i in range(4) for j in range(i + 1, 4)
}

all_solutions = find_all_solutions(variables, domains, constraints)
print(f"Found {len(all_solutions)} solutions")  # 2 solutions
```

**When to use**:
- Generating all puzzle solutions
- Enumerating configurations
- Checking solution uniqueness

---

## Quick Reference

### Heuristic Combinations

| Variable Order | Value Order | Use Case | Performance |
|----------------|-------------|----------|-------------|
| Static | Static | Baseline | Worst |
| MRV | Static | Medium problems | Good |
| MRV + Degree | Static | Tight constraints | Better |
| MRV | LCV | Single solution | Best |
| MRV + Degree | LCV | Complex CSPs | Best |

### Search Enhancements

```
Technique               | Overhead | Benefit        | When to Use
------------------------|----------|----------------|------------------
Forward Checking        | Low      | Medium         | Always
Maintaining Arc-3       | Medium   | High           | Tight constraints
Conflict Backjumping    | Medium   | High           | Deep search trees
Symmetry Breaking       | Low      | Problem-dep    | Symmetric problems
Randomization + Restart | Low      | Problem-dep    | Heavy-tailed dist
```

### Implementation Tips

```
✅ DO: Use MRV heuristic (almost always helps)
✅ DO: Implement forward checking
✅ DO: Copy domains when backtracking (not references)
✅ DO: Use degree heuristic as MRV tiebreaker
❌ DON'T: Recompute static information in loops
❌ DON'T: Use LCV when finding all solutions (overhead wasted)
❌ DON'T: Forget to restore state when backtracking
❌ DON'T: Use recursion depth for very large problems (use iterative)
```

---

## Anti-Patterns

❌ **Static variable ordering**
```python
# Inefficient: Always tries variables in same order
for var in variables:
    if var not in assignment:
        return var
```
✅ Use MRV to choose most constrained variable

❌ **No domain pruning**
```python
# Slow: Checks all constraints at assignment time only
if is_consistent(var, value, assignment, constraints):
    assignment[var] = value
```
✅ Use forward checking to prune domains early

❌ **Computing LCV for all solutions**
```python
# Wasteful: LCV overhead without benefit
def backtrack_all(assignment):
    # ... finding all solutions
    values = order_domain_values_lcv(var, ...)  # Wasted work
```
✅ Use LCV only when finding single solution

❌ **Modifying shared domain objects**
```python
# Bug: Modifying domain affects all branches
domains[var].remove(value)  # Side effect!
backtrack(assignment, domains, ...)
```
✅ Copy domains before modification

❌ **Deep recursion without iterative alternative**
```python
# Risk: Stack overflow on large problems
def backtrack(assignment, ...):
    return backtrack(assignment, ...)  # 1000+ levels
```
✅ Implement iterative version or increase stack limit

---

## Related Skills

- `csp-modeling.md` - Defining CSP problems and variables
- `constraint-propagation.md` - Domain reduction techniques
- `sat-solving-strategies.md` - Boolean constraint solving
- `optimization-algorithms.md` - Optimization with constraints
- `graph-algorithms.md` - Graph coloring and constraint graphs

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
