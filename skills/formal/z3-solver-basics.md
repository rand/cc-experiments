---
name: formal-z3-solver-basics
description: Skill for formal z3 solver basics
---



# Z3 Solver Basics

## Metadata
- **Skill ID**: z3-solver-basics
- **Category**: Formal Methods / SMT Solving
- **Complexity**: Intermediate
- **Prerequisites**: Python programming, basic logic, constraint satisfaction
- **Last Updated**: 2025-10-18

## Overview

### Purpose
Master Z3 SMT solver for constraint solving, program verification, symbolic execution, and optimization problems using the Python API.

### Scope
**In Scope**:
- Z3 Python API fundamentals
- SMT theory selection (QF_LIA, QF_BV, arrays, reals)
- Constraint modeling and encoding
- Solver modes (satisfiability, optimization)
- Tactics and strategies
- Unsat cores and proof extraction

**Out of Scope**:
- Low-level C++ API (use Python bindings)
- Custom theory development
- Advanced proof engineering (see lean-theorem-proving.md)
- SAT-only solving (see sat-solving-strategies.md)

### When to Use This Skill
**Primary Use Cases**:
- Solving constraint satisfaction problems
- Program verification and bug finding
- Test input generation
- Scheduling and planning problems
- Symbolic execution
- Configuration validation

**Choose Z3 When**:
- Need theories beyond Boolean (integers, bitvectors, arrays)
- Require optimization (maximize/minimize objectives)
- Want integrated theory reasoning
- Need unsat core extraction
- Prefer Python API for rapid prototyping

**Alternatives**:
- **MiniSat/CryptoMiniSat**: Pure Boolean SAT (faster for SAT-only)
- **CVC5**: Alternative SMT solver with different strengths
- **Yices2**: Fast for linear arithmetic
- **Constraint programming**: Use OR-Tools for discrete optimization

## Core Concepts

### 1. SMT Theories Hierarchy
```
SMT (Satisfiability Modulo Theories)
├── QF_UF (Uninterpreted Functions)
├── QF_LIA (Linear Integer Arithmetic)
├── QF_LRA (Linear Real Arithmetic)
├── QF_BV (Bitvectors)
├── QF_AUFLIA (Arrays + UF + Linear Integer Arithmetic)
├── QF_AUFBV (Arrays + UF + Bitvectors)
└── Non-quantifier-free theories (with ∀, ∃)
```

**Theory Selection Guide**:
- **QF_LIA**: Integer variables, linear constraints (`x + 2*y <= 10`)
- **QF_LRA**: Real-valued variables, linear constraints
- **QF_BV**: Fixed-width integers, bitwise operations
- **Arrays**: Index-value mappings, read/write operations
- **QF_UF**: Functions without interpretation (symbolic functions)

### 2. Z3 Architecture
```
User Code (Python)
    ↓
Z3 Python Bindings (z3-solver)
    ↓
Z3 Core Engine (C++)
    ├── Preprocessor (simplification)
    ├── Theory Solvers (LIA, BV, Arrays)
    ├── SAT Solver (CDCL core)
    └── Tactic Framework (strategies)
    ↓
Result: sat, unsat, unknown
```

### 3. Solver Modes
**Standard Mode** (check):
```python
from z3 import *

s = Solver()
x = Int('x')
s.add(x > 0)
s.add(x < 10)
result = s.check()  # sat, unsat, unknown
if result == sat:
    print(s.model())  # Solution: x = 1 (or any value in [1, 9])
```

**Optimization Mode** (Optimize):
```python
opt = Optimize()
x = Int('x')
y = Int('y')
opt.add(x + y <= 10)
opt.add(x >= 0, y >= 0)
opt.maximize(x + 2*y)  # Objective function
if opt.check() == sat:
    print(opt.model())  # x=0, y=10 (maximizes objective)
```

### 4. Constraint Types

**Arithmetic Constraints**:
```python
x, y = Ints('x y')
constraints = [
    x + y == 10,           # Linear equality
    2*x - 3*y <= 5,        # Linear inequality
    x * y == 24,           # Nonlinear (switches to NRA theory)
    x % 2 == 0,            # Modulo (integer division)
]
```

**Bitvector Constraints**:
```python
x = BitVec('x', 32)  # 32-bit bitvector
y = BitVec('y', 32)
constraints = [
    x & y == 0,              # Bitwise AND
    x | y == 0xFFFFFFFF,     # Bitwise OR (all bits set)
    x >> 2 == y,             # Logical right shift
    SignExt(16, x) == y,     # Sign extension
]
```

**Array Constraints**:
```python
A = Array('A', IntSort(), IntSort())  # Array: Int -> Int
i, j = Ints('i j')
constraints = [
    Store(A, i, 10)[i] == 10,         # Write then read
    Select(A, i) == Select(A, j),     # Same values at i, j
]
```

## Implementation Patterns

### Pattern 1: Basic Constraint Solving
```python
from z3 import *

# Problem: Find x, y such that x^2 + y^2 = 25 and x > y
def solve_pythagorean():
    s = Solver()
    x = Int('x')
    y = Int('y')

    s.add(x*x + y*y == 25)
    s.add(x > y)

    if s.check() == sat:
        m = s.model()
        print(f"Solution: x={m[x]}, y={m[y]}")
        # Output: x=5, y=0 or x=4, y=3 or x=3, y=-4, etc.
    else:
        print("No solution")

solve_pythagorean()
```

### Pattern 2: Multiple Solutions with Blocking Clauses
```python
def find_all_solutions(solver, variables, max_solutions=10):
    """Find multiple solutions by blocking previous ones"""
    solutions = []

    for _ in range(max_solutions):
        if solver.check() != sat:
            break

        m = solver.model()
        solution = {v: m[v] for v in variables}
        solutions.append(solution)

        # Block this solution
        block = Or([v != m[v] for v in variables])
        solver.add(block)

    return solutions

# Example: Find all x, y pairs where x + y = 5, 0 <= x,y <= 5
s = Solver()
x, y = Ints('x y')
s.add(x + y == 5)
s.add(x >= 0, x <= 5)
s.add(y >= 0, y <= 5)

solutions = find_all_solutions(s, [x, y])
for sol in solutions:
    print(f"x={sol[x]}, y={sol[y]}")
# Output: (0,5), (1,4), (2,3), (3,2), (4,1), (5,0)
```

### Pattern 3: Optimization with Multiple Objectives
```python
def solve_multiobjective():
    """Lexicographic optimization: prioritize objectives"""
    opt = Optimize()
    x, y = Ints('x y')

    # Constraints
    opt.add(x + y <= 10)
    opt.add(x >= 0, y >= 0)

    # Primary objective: maximize x
    h1 = opt.maximize(x)

    # Secondary objective: maximize y (given optimal x)
    h2 = opt.maximize(y)

    if opt.check() == sat:
        print(f"x={opt.model()[x]}, y={opt.model()[y]}")
        print(f"Objective 1: {opt.lower(h1)} <= x <= {opt.upper(h1)}")
        print(f"Objective 2: {opt.lower(h2)} <= y <= {opt.upper(h2)}")
    # Output: x=10, y=0 (maximizes x first, then y)

solve_multiobjective()
```

### Pattern 4: Unsat Core Extraction
```python
def analyze_conflicting_constraints():
    """Find minimal subset of constraints that cause unsat"""
    s = Solver()
    x = Int('x')

    # Create named constraints
    c1 = x > 10
    c2 = x < 5
    c3 = x >= 0
    c4 = x <= 100

    # Add with tracking
    s.assert_and_track(c1, 'c1')
    s.assert_and_track(c2, 'c2')
    s.assert_and_track(c3, 'c3')
    s.assert_and_track(c4, 'c4')

    if s.check() == unsat:
        core = s.unsat_core()
        print(f"Conflicting constraints: {core}")
        # Output: [c1, c2] (x > 10 and x < 5 conflict)

analyze_conflicting_constraints()
```

### Pattern 5: Theory-Specific Tactics
```python
def solve_with_tactics():
    """Use tactics for performance tuning"""
    x, y = Ints('x y')
    formula = And(x + y == 10, x - y == 2)

    # Strategy: simplify, then solve with LIA solver
    tactic = Then('simplify', 'qflia')  # Quantifier-free LIA
    solver = tactic.solver()
    solver.add(formula)

    if solver.check() == sat:
        print(solver.model())
    # Output: x=6, y=4

solve_with_tactics()
```

### Pattern 6: Incremental Solving
```python
def incremental_solving():
    """Efficient solving with push/pop for backtracking"""
    s = Solver()
    x, y = Ints('x y')

    # Base constraints
    s.add(x + y <= 10)

    # Try scenario 1: x > 5
    s.push()
    s.add(x > 5)
    if s.check() == sat:
        print(f"Scenario 1: {s.model()}")
    s.pop()

    # Try scenario 2: y > 5 (independent of scenario 1)
    s.push()
    s.add(y > 5)
    if s.check() == sat:
        print(f"Scenario 2: {s.model()}")
    s.pop()

incremental_solving()
```

### Pattern 7: Array Reasoning
```python
def verify_array_swap():
    """Verify swap operation using array theory"""
    A = Array('A', IntSort(), IntSort())
    i, j = Ints('i j')

    # Swap operation
    A_swap = Store(Store(A, i, Select(A, j)), j, Select(A, i))

    # Verify: after swap, A[i] == old_A[j] and A[j] == old_A[i]
    s = Solver()
    s.add(Select(A_swap, i) != Select(A, j))  # Should be unsat

    if s.check() == unsat:
        print("Swap verified correct")
    else:
        print(f"Bug found: {s.model()}")

verify_array_swap()
```

### Pattern 8: Bitvector Reasoning
```python
def check_overflow():
    """Detect integer overflow in bitvector arithmetic"""
    x = BitVec('x', 8)  # 8-bit unsigned integer
    y = BitVec('y', 8)

    s = Solver()
    s.add(x + y > 255)  # Overflow condition
    s.add(ULT(x + y, x))  # Result < x (overflow check)

    if s.check() == sat:
        m = s.model()
        print(f"Overflow: {m[x]} + {m[y]} = {m.evaluate(x + y)}")
        # Example: 200 + 100 = 44 (mod 256)

check_overflow()
```

## Quick Reference

### Installation
```bash
# Python Z3
pip install z3-solver

# Or with uv
uv add z3-solver

# Verify
python -c "import z3; print(z3.get_version_string())"
```

### Common Types
```python
# Integer variables
x = Int('x')
x, y, z = Ints('x y z')

# Real variables
r = Real('r')

# Boolean variables
b = Bool('b')

# Bitvectors
bv = BitVec('bv', 32)  # 32-bit

# Arrays
A = Array('A', IntSort(), IntSort())  # Int -> Int
B = Array('B', BitVecSort(32), IntSort())  # BitVec(32) -> Int
```

### Constraint Operations
```python
# Logical
And(c1, c2, c3)
Or(c1, c2)
Not(c)
Implies(c1, c2)
Xor(c1, c2)

# Arithmetic
x + y, x - y, x * y, x / y  # Division is integer division for Int
x % y  # Modulo
x ** 2  # Exponentiation (switches to nonlinear)

# Comparison
x == y, x != y
x < y, x <= y, x > y, x >= y

# Bitvector
x & y, x | y, x ^ y  # Bitwise AND, OR, XOR
~x  # Bitwise NOT
x << n, x >> n  # Shifts
ZeroExt(n, x), SignExt(n, x)  # Extension
Extract(high, low, x)  # Bit extraction

# Array
Select(A, i)  # Read A[i]
Store(A, i, v)  # Write A[i] = v
```

### Solver API
```python
s = Solver()
s.add(constraint)  # Add constraint
s.check()  # Returns sat, unsat, or unknown
s.model()  # Get model if sat
s.push()  # Save state
s.pop()  # Restore state
s.reset()  # Clear all constraints

# Optimization
opt = Optimize()
opt.add(constraint)
h = opt.maximize(expr)  # or minimize(expr)
opt.check()
opt.model()
opt.lower(h), opt.upper(h)  # Objective bounds
```

### Tactics
```python
# Common tactics
tactics = [
    'simplify',      # Algebraic simplification
    'solve-eqs',     # Gaussian elimination
    'qflia',         # Quantifier-free linear integer arithmetic
    'qfbv',          # Quantifier-free bitvectors
    'qfnra',         # Quantifier-free nonlinear real arithmetic
    'sat',           # SAT solver
    'smt',           # Full SMT solver
]

# Use tactic
tactic = Then('simplify', 'qflia')
solver = tactic.solver()
```

### Performance Tips
```python
# 1. Set timeout (milliseconds)
s = Solver()
s.set('timeout', 5000)  # 5 seconds

# 2. Enable parallel mode
set_param('parallel.enable', True)

# 3. Use appropriate theory
# QF_LIA faster than general arithmetic
# Use bitvectors for bounded integers

# 4. Simplify before solving
from z3 import simplify
formula = simplify(complex_formula)
s.add(formula)

# 5. Incremental solving with push/pop
s.push()
s.add(temporary_constraint)
s.check()
s.pop()
```

## Anti-Patterns

### Anti-Pattern 1: Over-Constraining
**Problem**: Adding redundant or conflicting constraints.

```python
# BAD: Redundant constraints slow down solver
s = Solver()
x = Int('x')
s.add(x > 0)
s.add(x > 1)  # Implies x > 0 (redundant)
s.add(x >= 2)  # Also redundant
```

**Solution**: Simplify constraints first.
```python
# GOOD: Minimal constraint set
s = Solver()
x = Int('x')
s.add(x >= 2)  # Sufficient (implies x > 0 and x > 1)
```

### Anti-Pattern 2: Wrong Theory Selection
**Problem**: Using nonlinear arithmetic when linear suffices.

```python
# BAD: Nonlinear (slower)
x, y = Reals('x y')
s = Solver()
s.add(x * y == 10)  # Nonlinear
```

**Solution**: Reformulate as linear when possible.
```python
# GOOD: Linear (if y is constant)
x = Real('x')
y_value = 2.0
s = Solver()
s.add(x == 10 / y_value)  # Linear
```

### Anti-Pattern 3: Ignoring Solver Status
**Problem**: Accessing model without checking satisfiability.

```python
# BAD: May crash if unsat
s = Solver()
s.add(False)
m = s.model()  # Error: solver is unsat
```

**Solution**: Always check status first.
```python
# GOOD: Check before model access
if s.check() == sat:
    m = s.model()
else:
    print("No solution exists")
```

### Anti-Pattern 4: Inefficient Blocking Clauses
**Problem**: Expensive enumeration of solutions.

```python
# BAD: Blocks each variable separately (exponential clauses)
for _ in range(100):
    if s.check() == sat:
        m = s.model()
        for v in variables:
            s.add(v != m[v])  # Wrong: adds 1 clause per variable
```

**Solution**: Block entire solution at once.
```python
# GOOD: Single blocking clause per solution
for _ in range(100):
    if s.check() == sat:
        m = s.model()
        s.add(Or([v != m[v] for v in variables]))  # 1 clause
```

### Anti-Pattern 5: Not Using Push/Pop
**Problem**: Recreating solver for each scenario.

```python
# BAD: Recreates solver (slow)
for scenario in scenarios:
    s = Solver()  # New solver each time
    s.add(base_constraints)
    s.add(scenario)
    s.check()
```

**Solution**: Use incremental solving.
```python
# GOOD: Reuse solver with push/pop
s = Solver()
s.add(base_constraints)
for scenario in scenarios:
    s.push()
    s.add(scenario)
    s.check()
    s.pop()
```

## Real-World Applications

### Application 1: Sudoku Solver
```python
def solve_sudoku(grid):
    """Solve 9x9 Sudoku using Z3"""
    cells = [[Int(f"c_{i}_{j}") for j in range(9)] for i in range(9)]

    s = Solver()

    # Each cell in [1, 9]
    for i in range(9):
        for j in range(9):
            s.add(And(cells[i][j] >= 1, cells[i][j] <= 9))

    # Row constraints
    for i in range(9):
        s.add(Distinct([cells[i][j] for j in range(9)]))

    # Column constraints
    for j in range(9):
        s.add(Distinct([cells[i][j] for i in range(9)]))

    # 3x3 box constraints
    for box_i in range(3):
        for box_j in range(3):
            box = [cells[i][j]
                   for i in range(box_i*3, box_i*3+3)
                   for j in range(box_j*3, box_j*3+3)]
            s.add(Distinct(box))

    # Add initial grid values
    for i in range(9):
        for j in range(9):
            if grid[i][j] != 0:
                s.add(cells[i][j] == grid[i][j])

    if s.check() == sat:
        m = s.model()
        return [[m.evaluate(cells[i][j]).as_long() for j in range(9)]
                for i in range(9)]
    return None
```

### Application 2: Program Verification
```python
def verify_binary_search(arr_size=10):
    """Verify binary search finds element if present"""
    A = Array('A', IntSort(), IntSort())
    target = Int('target')
    low, high, mid = Ints('low high mid')

    s = Solver()

    # Array is sorted
    for i in range(arr_size - 1):
        s.add(Select(A, i) <= Select(A, i+1))

    # Target exists at some index
    exists_idx = Int('exists_idx')
    s.add(And(exists_idx >= 0, exists_idx < arr_size))
    s.add(Select(A, exists_idx) == target)

    # Binary search logic (simplified)
    s.add(low == 0)
    s.add(high == arr_size - 1)
    s.add(mid == (low + high) / 2)

    # After one iteration, mid should narrow search
    found = Select(A, mid) == target
    go_left = Select(A, mid) > target
    go_right = Select(A, mid) < target

    # Check: we always make progress
    s.add(Not(Or(found, And(go_left, exists_idx < mid),
                       And(go_right, exists_idx > mid))))

    if s.check() == unsat:
        print("Binary search verified: always makes progress")
    else:
        print(f"Bug found: {s.model()}")

verify_binary_search()
```

## Related Skills
- **sat-solving-strategies.md**: Pure Boolean SAT solving, CDCL algorithms
- **smt-theory-applications.md**: Advanced SMT applications, theory combinations
- **constraint-propagation.md**: CSP techniques, arc consistency
- **lean-theorem-proving.md**: Interactive theorem proving
- **program-analysis.md**: Static analysis, abstract interpretation

## References
- Z3 Tutorial: https://ericpony.github.io/z3py-tutorial/guide-examples.htm
- Z3 API Docs: https://z3prover.github.io/api/html/namespacez3py.html
- SMT-LIB Standard: http://smtlib.cs.uiowa.edu/
- Book: "Decision Procedures" by Kroening & Strichman

## Troubleshooting

**Problem**: Solver returns "unknown"
- **Cause**: Nonlinear constraints, quantifiers, or timeout
- **Fix**: Simplify formula, increase timeout, or use approximations

**Problem**: Slow solving
- **Cause**: Wrong theory, over-constraining, or poor variable ordering
- **Fix**: Use tactics, simplify constraints, or enable parallel mode

**Problem**: Unexpected model values
- **Cause**: Under-constrained problem (multiple solutions)
- **Fix**: Add more constraints or enumerate all solutions

**Problem**: ImportError for z3
- **Cause**: Not installed or wrong environment
- **Fix**: `pip install z3-solver` or `uv add z3-solver`
