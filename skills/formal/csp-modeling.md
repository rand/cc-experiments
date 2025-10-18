---
name: formal-csp-modeling
description: Modeling scheduling problems (meetings, courses, jobs)
---



# CSP Modeling

**Scope**: Constraint satisfaction problem modeling, variables, domains, constraints, problem formulation
**Lines**: ~330
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Modeling scheduling problems (meetings, courses, jobs)
- Solving allocation problems (resources, tasks, assignments)
- Implementing puzzle solvers (Sudoku, N-Queens, graph coloring)
- Formulating planning problems with constraints
- Converting real-world problems to CSP representation
- Designing constraint-based optimization systems
- Building configuration or layout generation systems

## Core Concepts

### CSP Components

**Variables**: Decision points in the problem
- Represent unknowns to be assigned values
- Example: Square positions in Sudoku, class time slots
- Choose granularity carefully (too fine = slow, too coarse = inflexible)
- Notation: X = {X₁, X₂, ..., Xₙ}

**Domains**: Possible values for each variable
- Finite set of values each variable can take
- Example: {1-9} for Sudoku, {Mon-Fri} for scheduling
- Can be discrete (integers, colors) or continuous (ranges)
- Notation: D = {D₁, D₂, ..., Dₙ} where Dᵢ is domain for Xᵢ

**Constraints**: Rules limiting variable assignments
- **Unary**: Single variable (X₁ ≠ 5)
- **Binary**: Two variables (X₁ ≠ X₂)
- **N-ary**: Multiple variables (X₁ + X₂ + X₃ = 10)
- **Global**: Complex patterns (AllDifferent, Cardinality)
- Notation: C = {C₁, C₂, ..., Cₘ}

### Constraint Types

**Explicit constraints**: Enumerate allowed/forbidden tuples
```python
# Binary constraint: allowed pairs
constraint = {(1, 2), (1, 3), (2, 3), (2, 4)}
```

**Implicit constraints**: Expressed as functions/predicates
```python
# Mathematical constraint
def constraint(x1, x2):
    return x1 + x2 <= 10
```

**Global constraints**: High-level patterns
- `AllDifferent(X)`: All variables have different values
- `Cardinality(X, v, min, max)`: Value v appears min-max times
- `Cumulative(tasks, resources)`: Resource usage constraints
- More efficient than decomposing into binary constraints

### Constraint Graph

**Structure**: Graph representation of CSP
- Nodes: Variables
- Edges: Binary constraints between variables
- Hyperedges: N-ary constraints (multiple variables)
- Used for algorithm selection and analysis

**Properties**:
- Tree-structured: O(n·d²) solvable
- Width k: Complexity depends on tree decomposition
- Sparse vs dense affects algorithm choice

---

## Patterns

### Pattern 1: N-Queens Problem

```python
from constraint import Problem, AllDifferentConstraint

def solve_n_queens(n):
    """Place n queens on n×n board with no attacks."""
    problem = Problem()

    # Variables: One per queen (row), domain: column positions
    cols = range(n)
    for row in range(n):
        problem.addVariable(row, cols)

    # Constraint: No two queens in same column
    problem.addConstraint(AllDifferentConstraint(), cols)

    # Constraint: No diagonal attacks
    for row1 in range(n):
        for row2 in range(row1 + 1, n):
            # |row1 - row2| != |col1 - col2|
            problem.addConstraint(
                lambda c1, c2, r1=row1, r2=row2:
                    abs(r1 - r2) != abs(c1 - c2),
                (row1, row2)
            )

    return problem.getSolutions()
```

**When to use**:
- Placement problems with non-overlapping constraints
- Board game configuration
- Layout generation with separation rules

### Pattern 2: Sudoku Solver

```python
from constraint import Problem, AllDifferentConstraint

def solve_sudoku(grid):
    """Solve 9×9 Sudoku puzzle."""
    problem = Problem()

    # Variables: Each cell (row, col)
    cells = [(r, c) for r in range(9) for c in range(9)]

    for r, c in cells:
        if grid[r][c] == 0:
            # Empty cell: domain 1-9
            problem.addVariable((r, c), range(1, 10))
        else:
            # Pre-filled cell: fixed value
            problem.addVariable((r, c), [grid[r][c]])

    # Row constraints
    for r in range(9):
        problem.addConstraint(
            AllDifferentConstraint(),
            [(r, c) for c in range(9)]
        )

    # Column constraints
    for c in range(9):
        problem.addConstraint(
            AllDifferentConstraint(),
            [(r, c) for r in range(9)]
        )

    # 3×3 box constraints
    for box_r in range(3):
        for box_c in range(3):
            cells_in_box = [
                (r, c)
                for r in range(box_r * 3, box_r * 3 + 3)
                for c in range(box_c * 3, box_c * 3 + 3)
            ]
            problem.addConstraint(
                AllDifferentConstraint(),
                cells_in_box
            )

    solutions = problem.getSolutions()
    return solutions[0] if solutions else None
```

**Benefits**:
- Declarative problem specification
- Automatic constraint propagation
- Easy to add new constraint types

### Pattern 3: Graph Coloring

```python
from constraint import Problem, AllDifferentConstraint

def color_graph(graph, num_colors):
    """Assign colors to graph nodes (no adjacent same color)."""
    problem = Problem()

    # Variables: Graph nodes
    nodes = list(graph.keys())
    colors = range(num_colors)

    for node in nodes:
        problem.addVariable(node, colors)

    # Constraints: Adjacent nodes different colors
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            if node < neighbor:  # Avoid duplicate constraints
                problem.addConstraint(
                    lambda c1, c2: c1 != c2,
                    (node, neighbor)
                )

    return problem.getSolutions()

# Example: Map coloring
us_map = {
    'WA': ['OR', 'ID'],
    'OR': ['WA', 'ID', 'NV', 'CA'],
    'CA': ['OR', 'NV', 'AZ'],
    # ... more states
}

solutions = color_graph(us_map, num_colors=4)
```

**When to use**:
- Register allocation in compilers
- Frequency assignment in wireless networks
- Time slot assignment avoiding conflicts

### Pattern 4: Scheduling with OR-Tools

```python
from ortools.sat.python import cp_model

def schedule_jobs(jobs, machines):
    """Schedule jobs on machines minimizing makespan."""
    model = cp_model.CpModel()

    # Variables: start_time and machine for each job
    starts = {}
    machines_assigned = {}

    for job_id, duration in jobs.items():
        starts[job_id] = model.NewIntVar(0, 1000, f'start_{job_id}')
        machines_assigned[job_id] = model.NewIntVar(
            0, len(machines) - 1, f'machine_{job_id}'
        )

    # Constraint: Jobs on same machine don't overlap
    intervals_per_machine = [[] for _ in machines]

    for job_id, duration in jobs.items():
        for machine_id in range(len(machines)):
            # Create interval for job on this machine
            interval = model.NewOptionalIntervalVar(
                starts[job_id],
                duration,
                starts[job_id] + duration,
                machines_assigned[job_id] == machine_id,
                f'interval_{job_id}_{machine_id}'
            )
            intervals_per_machine[machine_id].append(interval)

    # NoOverlap constraint per machine
    for machine_id in range(len(machines)):
        model.AddNoOverlap(intervals_per_machine[machine_id])

    # Objective: Minimize makespan
    makespan = model.NewIntVar(0, 1000, 'makespan')
    for job_id, duration in jobs.items():
        model.Add(makespan >= starts[job_id] + duration)

    model.Minimize(makespan)

    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL:
        schedule = {
            job_id: {
                'start': solver.Value(starts[job_id]),
                'machine': solver.Value(machines_assigned[job_id])
            }
            for job_id in jobs
        }
        return schedule, solver.Value(makespan)

    return None, None
```

**Benefits**:
- Optimization objectives (minimize/maximize)
- Optional intervals for flexible scheduling
- Built-in NoOverlap global constraint

### Pattern 5: Resource Allocation

```python
from constraint import Problem, ExactSumConstraint

def allocate_resources(tasks, resources, capacity):
    """Assign tasks to resources respecting capacity limits."""
    problem = Problem()

    # Variables: Resource assignment per task
    for task in tasks:
        problem.addVariable(task, resources)

    # Constraint: Each resource has capacity limit
    for resource in resources:
        # Count tasks assigned to this resource
        tasks_on_resource = [
            task for task in tasks
        ]

        # Custom constraint checking capacity
        def capacity_constraint(*assignments):
            count = sum(1 for a in assignments if a == resource)
            return count <= capacity[resource]

        problem.addConstraint(
            capacity_constraint,
            tasks_on_resource
        )

    return problem.getSolutions()

# Example usage
tasks = ['T1', 'T2', 'T3', 'T4', 'T5']
resources = ['R1', 'R2', 'R3']
capacity = {'R1': 2, 'R2': 2, 'R3': 1}

solutions = allocate_resources(tasks, resources, capacity)
```

**When to use**:
- Server assignment with load limits
- Classroom allocation for courses
- Worker assignment to shifts

---

## Quick Reference

### CSP Formulation Checklist

```
1. Identify variables: What are you deciding?
2. Define domains: What values can each variable take?
3. Specify constraints:
   - Unary: Variable must/cannot be X
   - Binary: Relationships between pairs
   - N-ary: Relationships among groups
   - Global: High-level patterns
4. Choose optimization objective (if needed)
5. Select appropriate solver library
```

### Common Global Constraints

| Constraint | Meaning | Use Case |
|------------|---------|----------|
| `AllDifferent(X)` | All variables different | Sudoku, N-Queens |
| `AllEqual(X)` | All variables equal | Consistent labeling |
| `Cardinality(X, v, min, max)` | Value v appears min-max times | Workforce limits |
| `Sum(X) = k` | Variables sum to k | Budget constraints |
| `NoOverlap(intervals)` | Intervals don't overlap | Scheduling |
| `Cumulative(tasks, limit)` | Resource usage ≤ limit | Machine capacity |
| `Element(index, array, value)` | array[index] = value | Lookup constraints |

### Modeling Guidelines

```
✅ DO: Use global constraints when possible (more efficient)
✅ DO: Minimize domain sizes (smaller = faster)
✅ DO: Add redundant constraints if they prune search space
✅ DO: Choose variable granularity carefully
❌ DON'T: Model everything as binary constraints
❌ DON'T: Use variables when constants suffice
❌ DON'T: Ignore problem structure (tree, bipartite, etc.)
❌ DON'T: Over-constrain (making problem unsatisfiable)
```

---

## Anti-Patterns

❌ **Over-constraining**: Adding contradictory constraints
```python
# Problem has no solution
problem.addConstraint(lambda x: x > 10)
problem.addConstraint(lambda x: x < 5)
```
✅ Check constraint consistency before solving

❌ **Decomposing global constraints unnecessarily**
```python
# Inefficient: AllDifferent as pairwise inequality
for i in range(n):
    for j in range(i + 1, n):
        problem.addConstraint(lambda xi, xj: xi != xj, (i, j))
```
✅ Use `AllDifferentConstraint()` directly

❌ **Wrong variable choice**
```python
# Bad: Boolean variables for multi-valued decisions
# is_blue, is_red, is_green (3 variables per item)
```
✅ Use single variable with domain {blue, red, green}

❌ **Ignoring problem symmetry**
```python
# N-Queens: All solutions are rotations/reflections
# Returns 92 solutions for 8-Queens (only 12 unique)
```
✅ Add symmetry-breaking constraints or post-process

❌ **Missing implied constraints**
```python
# Scheduling: Only NoOverlap constraint
# Missing: Task precedence, resource limits
```
✅ Add all relevant constraints for complete model

---

## Related Skills

- `constraint-propagation.md` - Reducing domains using constraints
- `backtracking-search.md` - Searching for CSP solutions
- `sat-solving-strategies.md` - Boolean satisfiability (special case of CSP)
- `optimization-modeling.md` - Adding objective functions to CSPs
- `graph-algorithms.md` - Graph coloring and CSP structure

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
