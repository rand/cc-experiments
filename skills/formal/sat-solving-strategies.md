---
name: formal-sat-solving-strategies
description: Skill for formal sat solving strategies
---



# SAT Solving Strategies

## Metadata
- **Skill ID**: sat-solving-strategies
- **Category**: Formal Methods / SAT Solving
- **Complexity**: Advanced
- **Prerequisites**: Boolean logic, graph algorithms, basic complexity theory
- **Last Updated**: 2025-10-18

## Overview

### Purpose
Master Boolean satisfiability (SAT) solving algorithms, encodings, and heuristics for combinatorial problems and formal verification.

### Scope
**In Scope**:
- DPLL and CDCL algorithms
- CNF encoding techniques
- Cardinality and pseudo-boolean constraints
- Watched literals and clause learning
- Restart and branching heuristics
- SAT solver selection and tuning

**Out of Scope**:
- SMT theories (see z3-solver-basics.md)
- Theorem proving (see lean-theorem-proving.md)
- Constraint programming (see csp-modeling.md)
- Solver implementation (focus on usage)

### When to Use This Skill
**Primary Use Cases**:
- Boolean satisfiability checking
- Combinatorial optimization (via SAT encoding)
- Hardware verification
- Equivalence checking
- Model checking (bounded)
- Test generation

**Choose SAT When**:
- Problem is purely Boolean (no arithmetic)
- Need maximum performance for satisfiability
- Have efficient CNF encoding
- Don't need uninterpreted functions or theories

**Alternatives**:
- **Z3/SMT**: Need arithmetic or arrays (see z3-solver-basics.md)
- **CSP solvers**: Discrete domains, global constraints
- **MILP**: Linear optimization with integers
- **BDDs**: Symbolic state space exploration

## Core Concepts

### 1. SAT Problem Definition
```
Input: Boolean formula φ in CNF (Conjunctive Normal Form)
  CNF = (l₁₁ ∨ l₁₂ ∨ ...) ∧ (l₂₁ ∨ l₂₂ ∨ ...) ∧ ...
  where lᵢⱼ is a literal (variable or its negation)

Output:
  - SAT + assignment if φ is satisfiable
  - UNSAT if no assignment satisfies φ

Example:
  φ = (x₁ ∨ ¬x₂) ∧ (x₂ ∨ x₃) ∧ (¬x₁ ∨ ¬x₃)
  Solution: x₁=T, x₂=T, x₃=F satisfies φ
```

### 2. DPLL Algorithm (Davis-Putnam-Logemann-Loveland)
```
DPLL(φ, assignment):
  1. Unit Propagation:
     - Find unit clauses (single literal)
     - Assign literal to satisfy clause
     - Simplify formula

  2. Pure Literal Elimination:
     - Find variables appearing only positive or only negative
     - Assign to satisfy all occurrences

  3. Base Cases:
     - If φ = ∅ (empty): return SAT
     - If ∅ ∈ φ (empty clause): return UNSAT

  4. Branching:
     - Pick unassigned variable x
     - Try DPLL(φ[x=T], assignment + {x=T})
     - If SAT: return SAT
     - Else: try DPLL(φ[x=F], assignment + {x=F})
```

**Example Trace**:
```
φ = (x₁ ∨ x₂) ∧ (¬x₁ ∨ x₃) ∧ (¬x₂ ∨ ¬x₃) ∧ (x₃)

Step 1: Unit propagation on (x₃)
  Assign x₃ = T
  φ becomes (x₁ ∨ x₂) ∧ (¬x₁ ∨ T) ∧ (¬x₂ ∨ F)
  Simplify: (x₁ ∨ x₂) ∧ (¬x₂)

Step 2: Unit propagation on (¬x₂)
  Assign x₂ = F
  φ becomes (x₁ ∨ F)
  Simplify: (x₁)

Step 3: Unit propagation on (x₁)
  Assign x₁ = T
  φ becomes ∅ (empty formula)
  Return SAT with {x₁=T, x₂=F, x₃=T}
```

### 3. CDCL Algorithm (Conflict-Driven Clause Learning)
```
CDCL extends DPLL with:

1. Implication Graph:
   - Track assignment reasons (decisions vs. implications)
   - Build graph showing variable dependencies

2. Conflict Analysis:
   - When conflict occurs, analyze implication graph
   - Derive "learned clause" (reason for conflict)
   - Add learned clause to formula

3. Non-chronological Backtracking:
   - Backtrack to decision level of learned clause
   - Skip irrelevant decisions

4. Restarts:
   - Periodically restart search with learned clauses
   - Escape bad search space regions
```

**Implication Graph Example**:
```
Decision: x₁ = T (level 1)
  → (¬x₁ ∨ x₂) implies x₂ = T
  → (¬x₂ ∨ x₃) implies x₃ = T

Decision: x₄ = F (level 2)
  → (x₃ ∨ ¬x₄ ∨ x₅) implies x₅ = T
  → (¬x₃ ∨ ¬x₅) CONFLICT!

Learned Clause: (¬x₁ ∨ ¬x₄)
  (If x₁=T and x₄=F, we always get conflict)

Backtrack to level 1 (skipping x₄ decision)
```

### 4. Watched Literals
```
Efficient unit propagation using 2-watched literals per clause:

Clause: (l₁ ∨ l₂ ∨ l₃ ∨ l₄)
Watch: l₁ and l₂

Invariant: If clause has ≥2 unassigned literals, watch 2 of them

When literal becomes false:
  - If clause has another unassigned literal, move watch
  - If only 1 watch remains unassigned, propagate unit
  - If both watches false, conflict

Benefit: Only visit clauses when watched literal changes
  (No need to scan all clauses on every assignment)
```

### 5. Branching Heuristics

**VSIDS (Variable State Independent Decaying Sum)**:
```python
# Each variable has activity score
activity[var] = 0.0
increment = 1.0

# On conflict learning:
for var in learned_clause:
    activity[var] += increment

# Periodic decay
if num_conflicts % 256 == 0:
    for var in variables:
        activity[var] *= 0.95
    increment *= 0.95

# Branching decision
next_var = max(unassigned_vars, key=lambda v: activity[v])
```

**Phase Saving**:
```python
# Remember last assigned value for each variable
last_value[var] = assigned_value

# On branching:
var = pick_var_vsids()
value = last_value[var]  # Try last value first
assign(var, value)
```

## Implementation Patterns

### Pattern 1: Using PySAT (Python SAT Library)
```python
from pysat.solvers import Glucose3
from pysat.formula import CNF

def solve_cnf_file(filename):
    """Solve CNF in DIMACS format"""
    cnf = CNF(from_file=filename)

    with Glucose3(bootstrap_with=cnf) as solver:
        if solver.solve():
            model = solver.get_model()
            print(f"SAT: {model}")
            return model
        else:
            print("UNSAT")
            return None

# Example DIMACS file content:
# p cnf 3 3
# 1 -2 0
# 2 3 0
# -1 -3 0
# (3 variables, 3 clauses)
```

### Pattern 2: Programmatic SAT Construction
```python
from pysat.solvers import Solver

def solve_graph_coloring(edges, num_colors=3):
    """3-coloring of graph using SAT"""
    nodes = set()
    for u, v in edges:
        nodes.add(u)
        nodes.add(v)

    # Variable encoding: x[node][color] = node has color
    # Variable number: node * num_colors + color + 1 (1-indexed)
    def var(node, color):
        return node * num_colors + color + 1

    clauses = []

    # Each node has at least one color
    for node in nodes:
        clauses.append([var(node, c) for c in range(num_colors)])

    # Each node has at most one color
    for node in nodes:
        for c1 in range(num_colors):
            for c2 in range(c1 + 1, num_colors):
                clauses.append([-var(node, c1), -var(node, c2)])

    # Adjacent nodes have different colors
    for u, v in edges:
        for c in range(num_colors):
            clauses.append([-var(u, c), -var(v, c)])

    # Solve
    with Solver(name='glucose3') as solver:
        for clause in clauses:
            solver.add_clause(clause)

        if solver.solve():
            model = solver.get_model()
            coloring = {}
            for node in nodes:
                for c in range(num_colors):
                    if var(node, c) in model:
                        coloring[node] = c
            return coloring
        return None

# Example: Triangle graph
edges = [(0, 1), (1, 2), (2, 0)]
coloring = solve_graph_coloring(edges)
print(coloring)  # {0: 0, 1: 1, 2: 2}
```

### Pattern 3: Cardinality Constraints (At-Most-K)
```python
from pysat.card import CardEnc

def at_most_k_constraint(lits, k):
    """At most k of lits can be true"""
    # Encoding options: sequential, ladder, totalizer, etc.
    cnf = CardEnc.atmost(lits, bound=k, encoding=EncType.seqcounter)
    return cnf.clauses

def solve_scheduling(jobs, max_parallel=2):
    """Schedule jobs with at most max_parallel running concurrently"""
    # Variable: x[job][time] = job runs at time
    time_slots = len(jobs)

    def var(job, time):
        return job * time_slots + time + 1

    clauses = []

    # Each job runs exactly once
    for job in range(len(jobs)):
        clauses.append([var(job, t) for t in range(time_slots)])

    # At most max_parallel jobs at each time
    for t in range(time_slots):
        lits = [var(job, t) for job in range(len(jobs))]
        clauses.extend(at_most_k_constraint(lits, max_parallel))

    with Solver() as solver:
        for clause in clauses:
            solver.add_clause(clause)
        if solver.solve():
            return solver.get_model()
    return None
```

### Pattern 4: Pseudo-Boolean Constraints
```python
from pysat.pb import PBEnc

def weighted_constraint(lits, weights, bound):
    """Sum of weights * lits <= bound"""
    cnf = PBEnc.leq(lits, weights, bound)
    return cnf.clauses

def solve_knapsack_sat(items, capacity):
    """0/1 knapsack using SAT encoding"""
    # items = [(weight, value), ...]
    # Variable: x[i] = item i is selected

    clauses = []

    # Weight constraint: sum(weight[i] * x[i]) <= capacity
    lits = [i + 1 for i in range(len(items))]
    weights = [w for w, v in items]
    clauses.extend(weighted_constraint(lits, weights, capacity))

    # Optimize value (manually via binary search on lower bounds)
    # For simplicity, just find feasible solution
    with Solver() as solver:
        for clause in clauses:
            solver.add_clause(clause)
        if solver.solve():
            model = solver.get_model()
            selected = [i for i in range(len(items)) if (i+1) in model]
            total_value = sum(items[i][1] for i in selected)
            return selected, total_value
    return None, 0

items = [(10, 60), (20, 100), (30, 120)]
capacity = 50
result = solve_knapsack_sat(items, capacity)
print(result)
```

### Pattern 5: Incremental SAT with Assumptions
```python
from pysat.solvers import Glucose4

def solve_with_assumptions():
    """Use assumptions for incremental solving"""
    solver = Glucose4()

    # Base clauses
    x1, x2, x3 = 1, 2, 3
    solver.add_clause([x1, x2])
    solver.add_clause([-x1, x3])

    # Try scenario 1: x2 = False
    if solver.solve(assumptions=[-x2]):
        print(f"Scenario 1 SAT: {solver.get_model()}")
    else:
        print("Scenario 1 UNSAT")

    # Try scenario 2: x3 = False (independent)
    if solver.solve(assumptions=[-x3]):
        print(f"Scenario 2 SAT: {solver.get_model()}")
    else:
        print("Scenario 2 UNSAT")

    solver.delete()

solve_with_assumptions()
```

### Pattern 6: Unsat Core Extraction
```python
from pysat.solvers import Glucose3

def find_minimal_unsat_core(clauses):
    """Find minimal subset of clauses that are UNSAT"""
    # Add selector variables to each clause
    selectors = []
    augmented = []

    for i, clause in enumerate(clauses):
        selector = len(clauses) + i + 1  # Fresh variable
        selectors.append(selector)
        augmented.append(clause + [-selector])  # clause ∨ ¬selector

    with Glucose3() as solver:
        for clause in augmented:
            solver.add_clause(clause)

        # Try to satisfy with all selectors true
        if not solver.solve(assumptions=selectors):
            # Get core selectors
            core = solver.get_core()
            core_indices = [selectors.index(s) for s in core if s in selectors]
            return [clauses[i] for i in core_indices]

    return None  # SAT

# Example
clauses = [[1, 2], [-1, 3], [-2, -3], [-3]]
core = find_minimal_unsat_core(clauses)
print(f"UNSAT core: {core}")
# Output: [[-1, 3], [-3]] or similar minimal core
```

### Pattern 7: Restart Strategies
```python
from pysat.solvers import Solver

def solve_with_custom_restarts(clauses, restart_interval=100):
    """SAT solving with periodic restarts"""
    solver = Solver(name='minisat22')

    for clause in clauses:
        solver.add_clause(clause)

    # MiniSat supports restart configuration
    # Other solvers have different APIs
    solver.conf_budget(conflicts=restart_interval)

    iterations = 0
    while iterations < 10:  # Max 10 restarts
        status = solver.solve_limited(expect_interrupt=True)

        if status is True:
            return solver.get_model()
        elif status is False:
            return None  # UNSAT
        else:
            # Interrupted (restart)
            iterations += 1
            solver.conf_budget(conflicts=restart_interval)

    return None  # Timeout

# Note: Modern solvers handle restarts automatically
# This pattern is for custom restart strategies
```

## Quick Reference

### Installation
```bash
# PySAT (Python SAT library)
pip install python-sat

# Or with uv
uv add python-sat

# CryptoMiniSat (standalone)
pip install pycryptosat

# Verify
python -c "from pysat.solvers import Glucose3; print('OK')"
```

### SAT Solver Comparison
```
Solver         | Speed      | Features           | Use Case
---------------|------------|--------------------|-----------------------
MiniSat        | Fast       | Basic CDCL         | General purpose
Glucose        | Very Fast  | Aggressive learning| Hard instances
CryptoMiniSat  | Fast       | XOR clauses        | Crypto, hashing
Lingeling      | Very Fast  | Preprocessing      | Competitions
Cadical        | Very Fast  | Modern heuristics  | State-of-the-art
```

### DIMACS CNF Format
```
p cnf <num_vars> <num_clauses>
<lit1> <lit2> ... 0
<lit1> <lit2> ... 0
...

Example:
p cnf 3 2
1 -2 3 0
-1 2 0

Explanation:
- Variables: 1, 2, 3
- Clause 1: x₁ ∨ ¬x₂ ∨ x₃
- Clause 2: ¬x₁ ∨ x₂
```

### Common Encoding Patterns
```python
# At-least-one (ALO)
[x1, x2, x3]

# At-most-one (AMO) - pairwise
[-x1, -x2]
[-x1, -x3]
[-x2, -x3]

# Exactly-one (EXO)
ALO + AMO

# Implication: x → y
[-x, y]

# Equivalence: x ↔ y
[-x, y], [x, -y]

# XOR: x ⊕ y
[x, y], [-x, -y]
```

### PySAT API Cheat Sheet
```python
from pysat.solvers import Glucose3
from pysat.formula import CNF

# Create solver
solver = Glucose3()  # or Minisat22, Cadical, etc.

# Add clauses
solver.add_clause([1, -2, 3])
solver.add_clause([-1, 2])

# Solve
if solver.solve():
    model = solver.get_model()  # List of literals
else:
    print("UNSAT")

# Incremental with assumptions
solver.solve(assumptions=[1, -3])

# Get core (if UNSAT)
core = solver.get_core()

# Cleanup
solver.delete()

# Context manager (auto cleanup)
with Glucose3() as s:
    s.add_clause([1, 2])
    s.solve()
```

## Anti-Patterns

### Anti-Pattern 1: Naive CNF Encoding
**Problem**: Tseitin transformation explosion.

```python
# BAD: Direct encoding of (x1 ∧ x2) ∨ (x3 ∧ x4)
# Converts to: (x1 ∨ x3) ∧ (x1 ∨ x4) ∧ (x2 ∨ x3) ∧ (x2 ∨ x4)
# 4 clauses, but loses structure
```

**Solution**: Use Tseitin variables to preserve structure.
```python
# GOOD: Introduce auxiliary variables
# y1 ↔ (x1 ∧ x2)
# y2 ↔ (x3 ∧ x4)
# y1 ∨ y2

# Clauses:
# y1 → x1, y1 → x2, (x1 ∧ x2) → y1
# y2 → x3, y2 → x4, (x3 ∧ x4) → y2
# y1 ∨ y2
```

### Anti-Pattern 2: Inefficient Cardinality Encoding
**Problem**: Quadratic AMO encoding for large sets.

```python
# BAD: Pairwise AMO for 100 variables
# O(n²) clauses: 100 * 99 / 2 = 4950 clauses
lits = list(range(1, 101))
for i in range(len(lits)):
    for j in range(i+1, len(lits)):
        clauses.append([-lits[i], -lits[j]])
```

**Solution**: Use efficient encoding (sequential, commander).
```python
# GOOD: Sequential encoding for AMO
from pysat.card import CardEnc, EncType
cnf = CardEnc.atmost(lits, bound=1, encoding=EncType.seqcounter)
# O(n) clauses and variables
```

### Anti-Pattern 3: Not Using Incremental Solving
**Problem**: Rebuilding solver for each query.

```python
# BAD: Create new solver each time
for scenario in scenarios:
    solver = Glucose3()
    for clause in base_clauses:  # Re-add every time
        solver.add_clause(clause)
    solver.add_clause(scenario)
    solver.solve()
    solver.delete()
```

**Solution**: Use assumptions for incremental queries.
```python
# GOOD: Single solver with assumptions
solver = Glucose3()
for clause in base_clauses:
    solver.add_clause(clause)

for scenario_lit in scenario_lits:
    if solver.solve(assumptions=[scenario_lit]):
        process(solver.get_model())
solver.delete()
```

### Anti-Pattern 4: Ignoring Preprocessing
**Problem**: Not simplifying formula before solving.

```python
# BAD: Directly solve complex formula
solver.add_clause([1, 2, 3])
solver.add_clause([1, 2, -3])  # Subsumes to [1, 2]
solver.solve()
```

**Solution**: Use preprocessor or simplify manually.
```python
# GOOD: Simplify first
from pysat.formula import CNF
cnf = CNF()
cnf.append([1, 2, 3])
cnf.append([1, 2, -3])

# Subsumption: [1, 2, 3] subsumed by [1, 2]
simplified = CNF()
simplified.append([1, 2])  # Only keep simplified clause

solver.add_clause([1, 2])
solver.solve()
```

### Anti-Pattern 5: Wrong Solver Choice
**Problem**: Using general SAT for special structure.

```python
# BAD: SAT for pure arithmetic
# Problem: x + y + z <= 2 (encoded as CNF)
# Explosion of clauses for cardinality constraint
```

**Solution**: Use SMT solver for arithmetic.
```python
# GOOD: Use Z3 for arithmetic
from z3 import *
x, y, z = Ints('x y z')
s = Solver()
s.add(x + y + z <= 2)
s.check()
# More natural and efficient
```

## Real-World Applications

### Application 1: N-Queens SAT Encoding
```python
from pysat.solvers import Glucose3

def solve_n_queens(n):
    """Solve N-Queens using SAT encoding"""
    def var(row, col):
        return row * n + col + 1

    clauses = []

    # Each row has exactly one queen
    for row in range(n):
        clauses.append([var(row, col) for col in range(n)])
        for c1 in range(n):
            for c2 in range(c1+1, n):
                clauses.append([-var(row, c1), -var(row, c2)])

    # Each column has at most one queen
    for col in range(n):
        for r1 in range(n):
            for r2 in range(r1+1, n):
                clauses.append([-var(r1, col), -var(r2, col)])

    # Diagonals have at most one queen
    for r1 in range(n):
        for c1 in range(n):
            for r2 in range(r1+1, n):
                for c2 in range(n):
                    # Same diagonal: |r1-r2| == |c1-c2|
                    if abs(r1-r2) == abs(c1-c2):
                        clauses.append([-var(r1, c1), -var(r2, c2)])

    with Glucose3() as solver:
        for clause in clauses:
            solver.add_clause(clause)
        if solver.solve():
            model = solver.get_model()
            board = [[0]*n for _ in range(n)]
            for lit in model:
                if lit > 0:
                    row, col = divmod(lit-1, n)
                    board[row][col] = 1
            return board
    return None

# Solve 8-Queens
board = solve_n_queens(8)
for row in board:
    print(row)
```

### Application 2: Bounded Model Checking
```python
def bounded_model_check(initial, transition, bad, k):
    """BMC: Check if bad state reachable in k steps"""
    # Variables: state[time][var]
    def var(time, state_var):
        return time * num_state_vars + state_var + 1

    clauses = []

    # Initial state
    clauses.extend(initial(0))

    # Transition relation for k steps
    for t in range(k):
        clauses.extend(transition(t, t+1))

    # Check if bad state reachable
    for t in range(k+1):
        solver = Glucose3()
        for clause in clauses:
            solver.add_clause(clause)
        clauses.extend(bad(t))

        if solver.solve():
            return t, solver.get_model()  # Bug found at step t
        solver.delete()

    return None, None  # No bug found within k steps
```

## Related Skills
- **z3-solver-basics.md**: SMT solving with theories
- **smt-theory-applications.md**: Advanced SMT applications
- **csp-modeling.md**: Constraint satisfaction problems
- **model-checking.md**: Formal verification techniques

## References
- Handbook of Satisfiability (2nd ed.)
- MiniSat: http://minisat.se/
- PySAT: https://pysathq.github.io/
- SAT Competition: http://www.satcompetition.org/

## Troubleshooting

**Problem**: Solver too slow
- **Fix**: Try different solver (Glucose, Cadical), enable preprocessing, use better encoding

**Problem**: Memory explosion
- **Fix**: Reduce auxiliary variables, use efficient cardinality encoding, solve incrementally

**Problem**: UNKNOWN result
- **Fix**: Increase timeout, check for quantifiers (use SMT instead), simplify formula

**Problem**: Encoding too large
- **Fix**: Use Tseitin transformation, sequential counters, or switch to SMT
