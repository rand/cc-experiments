---
name: formal-smt-theory-applications
description: Skill for formal smt theory applications
---



# SMT Theory Applications

## Metadata
- **Skill ID**: smt-theory-applications
- **Category**: Formal Methods / SMT Applications
- **Complexity**: Advanced
- **Prerequisites**: z3-solver-basics.md, program semantics, logic
- **Last Updated**: 2025-10-18

## Overview

### Purpose
Apply SMT theories to real-world problems: program verification, symbolic execution, test generation, model checking, and scheduling using theory combinations.

### Scope
**In Scope**:
- Theory combinations (arrays + arithmetic, bitvectors + UF)
- Bounded model checking with SMT
- Symbolic execution and path exploration
- Automated test input generation
- Scheduling and resource allocation
- Program equivalence checking
- Invariant generation

**Out of Scope**:
- Pure SAT solving (see sat-solving-strategies.md)
- Z3 API basics (see z3-solver-basics.md)
- Interactive theorem proving (see lean-theorem-proving.md)
- Constraint programming (see csp-modeling.md)

### When to Use This Skill
**Primary Use Cases**:
- Finding bugs in programs (assertion violations)
- Generating test inputs for edge cases
- Verifying program correctness (bounded)
- Checking equivalence of code versions
- Scheduling with resource constraints
- Configuration validation

**Choose SMT When**:
- Need arithmetic reasoning (not just Boolean)
- Have arrays, bitvectors, or uninterpreted functions
- Want automated reasoning (not manual proofs)
- Problem bounded (finite unrolling)

**Alternatives**:
- **SAT**: Pure Boolean problems (see sat-solving-strategies.md)
- **Theorem provers**: Unbounded correctness (Coq, Lean)
- **Abstract interpretation**: Scalable approximation
- **Dynamic testing**: Random/fuzzing for coverage

## Core Concepts

### 1. SMT Theory Landscape
```
Theory               | Domain              | Examples
---------------------|---------------------|--------------------------
QF_LIA               | Linear Int Arith    | x + 2*y <= 10
QF_LRA               | Linear Real Arith   | 0.5*x + y == 3.2
QF_NIA/NRA           | Nonlinear Arith     | x*y == 10, x² + y² <= 1
QF_BV                | Bitvectors          | x & y == 0, x >> 2
QF_UF                | Uninterpreted Funcs | f(x) == f(y) → x == y
Arrays               | Array theory        | A[i] == v, A[i←v][i] == v
Strings              | String operations   | concat(s1, s2), len(s)

Combinations:
QF_AUFLIA = Arrays + UF + Linear Int Arith
QF_AUFBV  = Arrays + UF + Bitvectors
```

### 2. Theory Decision Procedures
```
Theory    | Decidability | Complexity      | Decision Procedure
----------|--------------|-----------------|--------------------
QF_LIA    | Decidable    | NP-complete     | Simplex + Branch & Bound
QF_LRA    | Decidable    | Polynomial      | Simplex
QF_BV     | Decidable    | NP-complete     | Bit-blasting + SAT
Arrays    | Decidable    | NP-complete     | Array property fragment
QF_NIA    | Undecidable  | -               | Incomplete (CAD, intervals)

Combination: Nelson-Oppen framework for disjoint theories
```

### 3. Bounded Model Checking (BMC)
```
Program → Encode k steps → SMT Query → Result

Loop Unrolling:
for (int i = 0; i < n; i++) {
    x += i;
}
assert(x >= 0);

BMC (k=3):
x₀ = 0, i₀ = 0
x₁ = x₀ + i₀, i₁ = i₀ + 1
x₂ = x₁ + i₁, i₂ = i₁ + 1
x₃ = x₂ + i₂, i₃ = i₂ + 1
Check: ¬(x₃ >= 0) at i₃ == 3

Result: UNSAT → No bug within 3 iterations
```

### 4. Symbolic Execution
```
Program Paths → Symbolic States → Path Constraints

Example:
def foo(x, y):
    if x > 0:
        if y < 10:
            return x + y  # Path 1: x > 0 ∧ y < 10
        else:
            return x - y  # Path 2: x > 0 ∧ y >= 10
    else:
        return 0         # Path 3: x <= 0

Symbolic Execution:
Path 1 constraints: x > 0 ∧ y < 10
Path 2 constraints: x > 0 ∧ y >= 10
Path 3 constraints: x <= 0

Generate test inputs: Solve each path constraint
```

### 5. Theory Combination (Nelson-Oppen)
```
Problem: Combine theory solvers for disjoint theories

Example: Arrays + Arithmetic
Formula: A[i] == 5 ∧ A[j] == 10 ∧ i + 1 == j

Step 1: Purify (introduce shared variables)
  a = A[i], b = A[j]
  a == 5 ∧ b == 10 ∧ i + 1 == j

Step 2: Separate theories
  Array theory: A[i] == a ∧ A[j] == b
  Arithmetic: a == 5 ∧ b == 10 ∧ i + 1 == j

Step 3: Exchange equalities
  If arithmetic infers i == j, share with array theory
  If array infers a == b, share with arithmetic

Step 4: Iterate until fixpoint or conflict
```

## Implementation Patterns

### Pattern 1: Bounded Model Checking
```python
from z3 import *

def verify_loop_safety(max_iters=10):
    """Verify loop: for i in 0..n: x += i; assert x >= 0"""
    x = [Int(f'x{i}') for i in range(max_iters + 1)]
    i = [Int(f'i{i}') for i in range(max_iters + 1)]
    n = Int('n')

    s = Solver()

    # Initial state
    s.add(x[0] == 0)
    s.add(i[0] == 0)
    s.add(n >= 0)

    # Transition relation (k iterations)
    for k in range(max_iters):
        s.add(Implies(i[k] < n, And(
            x[k+1] == x[k] + i[k],
            i[k+1] == i[k] + 1
        )))
        s.add(Implies(i[k] >= n, And(
            x[k+1] == x[k],
            i[k+1] == i[k]
        )))

    # Check if assertion can be violated
    for k in range(max_iters + 1):
        s.push()
        s.add(x[k] < 0)  # Negated assertion

        if s.check() == sat:
            m = s.model()
            print(f"Bug found at iteration {k}:")
            print(f"  n={m[n]}, i={m[i[k]]}, x={m[x[k]]}")
            s.pop()
            return False
        s.pop()

    print(f"No bugs found within {max_iters} iterations")
    return True

verify_loop_safety()
```

### Pattern 2: Symbolic Execution Engine
```python
from z3 import *

class SymbolicExecutor:
    def __init__(self):
        self.solver = Solver()
        self.path_constraint = []
        self.symbolic_vars = {}

    def make_symbolic(self, name, sort=IntSort()):
        """Create symbolic variable"""
        var = Const(name, sort)
        self.symbolic_vars[name] = var
        return var

    def add_constraint(self, constraint):
        """Add constraint to current path"""
        self.path_constraint.append(constraint)
        self.solver.add(constraint)

    def fork(self, condition):
        """Fork execution on branch condition"""
        # Try True branch
        true_executor = SymbolicExecutor()
        true_executor.solver.add(self.solver.assertions())
        true_executor.add_constraint(condition)

        # Try False branch
        false_executor = SymbolicExecutor()
        false_executor.solver.add(self.solver.assertions())
        false_executor.add_constraint(Not(condition))

        return true_executor, false_executor

    def is_feasible(self):
        """Check if current path is satisfiable"""
        return self.solver.check() == sat

    def get_model(self):
        """Get concrete input for current path"""
        if self.solver.check() == sat:
            return self.solver.model()
        return None

def symbolic_execution_example():
    """Symbolically execute simple function"""
    def target_function(x, y):
        if x > 0:
            if y < 10:
                return x + y
            else:
                return x - y
        else:
            return 0

    # Symbolic execution
    exec = SymbolicExecutor()
    x = exec.make_symbolic('x')
    y = exec.make_symbolic('y')

    # Explore all paths
    paths = []

    # Initial state
    queue = [exec]

    while queue:
        current = queue.pop(0)

        # Branch 1: x > 0
        true_branch, false_branch = current.fork(x > 0)

        # True branch: x > 0
        if true_branch.is_feasible():
            # Nested branch: y < 10
            path1, path2 = true_branch.fork(y < 10)

            if path1.is_feasible():  # x > 0 ∧ y < 10
                paths.append(('x > 0 ∧ y < 10', path1.get_model()))

            if path2.is_feasible():  # x > 0 ∧ y >= 10
                paths.append(('x > 0 ∧ y >= 10', path2.get_model()))

        # False branch: x <= 0
        if false_branch.is_feasible():
            paths.append(('x <= 0', false_branch.get_model()))

    # Print test inputs for each path
    for path_name, model in paths:
        print(f"Path: {path_name}")
        print(f"  Test input: x={model[x]}, y={model[y]}")

symbolic_execution_example()
```

### Pattern 3: Automated Test Generation
```python
from z3 import *

def generate_tests_for_function(func, num_tests=5):
    """Generate diverse test inputs for function"""
    # Example: func(x, y) with branches on x > 0, y == 0, etc.

    x = Int('x')
    y = Int('y')

    # Define symbolic constraints for different branches
    branch_conditions = [
        (x > 0, y == 0),
        (x > 0, y > 0),
        (x > 0, y < 0),
        (x <= 0, y == 0),
        (x <= 0, y != 0),
    ]

    test_inputs = []
    for conditions in branch_conditions[:num_tests]:
        s = Solver()
        for cond in conditions:
            s.add(cond)

        if s.check() == sat:
            m = s.model()
            test_inputs.append((m[x].as_long(), m[y].as_long()))

    return test_inputs

def divide_safe(x, y):
    """Function to test"""
    if y == 0:
        return None
    elif x > 0 and y > 0:
        return x / y
    else:
        return 0

tests = generate_tests_for_function(divide_safe)
for x_val, y_val in tests:
    result = divide_safe(x_val, y_val)
    print(f"divide_safe({x_val}, {y_val}) = {result}")
```

### Pattern 4: Equivalence Checking
```python
from z3 import *

def check_equivalence(func1, func2, input_vars):
    """Check if two functions are equivalent"""
    # Example: func1(x) = 2*x, func2(x) = x + x

    x = Int('x')

    # Encode both functions symbolically
    out1 = 2 * x
    out2 = x + x

    # Check if outputs can differ
    s = Solver()
    s.add(out1 != out2)

    if s.check() == unsat:
        print("Functions are equivalent")
        return True
    else:
        m = s.model()
        print(f"Functions differ at x={m[x]}")
        print(f"  func1({m[x]}) = {m.evaluate(out1)}")
        print(f"  func2({m[x]}) = {m.evaluate(out2)}")
        return False

check_equivalence(None, None, None)
```

### Pattern 5: Array-Based Program Verification
```python
from z3 import *

def verify_array_initialization():
    """Verify: for i in 0..n: A[i] = 0 initializes array"""
    A_init = Array('A_init', IntSort(), IntSort())
    A_final = Array('A_final', IntSort(), IntSort())
    n = Int('n')
    i = Int('i')

    s = Solver()
    s.add(n >= 0)

    # After loop: A[0..n-1] should all be 0
    # Model loop with array updates (bounded)
    A_temp = A_init
    for k in range(10):  # Bound loop to 10 iterations
        idx = Int(f'idx{k}')
        s.add(idx == k)
        s.add(Implies(idx < n, True))  # Loop condition
        A_temp = Store(A_temp, idx, 0)

    A_final = A_temp

    # Verify: A_final[i] == 0 for all 0 <= i < n
    s.add(i >= 0)
    s.add(i < n)
    s.add(Select(A_final, i) != 0)  # Negated property

    if s.check() == unsat:
        print("Array initialization verified")
    else:
        print(f"Bug: {s.model()}")

verify_array_initialization()
```

### Pattern 6: Scheduling with Resources
```python
from z3 import *

def schedule_tasks(tasks, resources, horizon=10):
    """Schedule tasks on resources with constraints"""
    # tasks = [(duration, resource_type), ...]
    # resources = {resource_type: count}

    opt = Optimize()

    # Variables: start[task] = start time
    start = [Int(f'start{i}') for i in range(len(tasks))]
    end = [Int(f'end{i}') for i in range(len(tasks))]

    # Constraints: end = start + duration
    for i, (duration, _) in enumerate(tasks):
        opt.add(end[i] == start[i] + duration)
        opt.add(start[i] >= 0)
        opt.add(end[i] <= horizon)

    # Resource constraints: at most R tasks of type T at any time
    for resource_type, capacity in resources.items():
        for t in range(horizon):
            # Count tasks of this type active at time t
            active = []
            for i, (duration, rtype) in enumerate(tasks):
                if rtype == resource_type:
                    active.append(If(And(start[i] <= t, end[i] > t), 1, 0))

            if active:
                opt.add(Sum(active) <= capacity)

    # Objective: minimize makespan
    makespan = Int('makespan')
    for e in end:
        opt.add(makespan >= e)
    opt.minimize(makespan)

    if opt.check() == sat:
        m = opt.model()
        schedule = [(m[start[i]].as_long(), m[end[i]].as_long())
                    for i in range(len(tasks))]
        print(f"Makespan: {m[makespan]}")
        return schedule
    return None

tasks = [(2, 'cpu'), (3, 'cpu'), (1, 'gpu'), (2, 'gpu')]
resources = {'cpu': 1, 'gpu': 1}
schedule = schedule_tasks(tasks, resources)
for i, (s, e) in enumerate(schedule):
    print(f"Task {i}: [{s}, {e})")
```

### Pattern 7: Bitvector Reasoning for Low-Level Code
```python
from z3 import *

def verify_bitwise_trick():
    """Verify: x & (x - 1) clears lowest set bit"""
    x = BitVec('x', 32)

    # Property: result has one fewer bit set than x (if x != 0)
    result = x & (x - 1)

    # Count bits (popcount)
    def popcount(bv):
        count = BitVecVal(0, 32)
        for i in range(32):
            count = count + ZeroExt(31, Extract(i, i, bv))
        return count

    s = Solver()
    s.add(x != 0)
    s.add(popcount(result) != popcount(x) - 1)

    if s.check() == unsat:
        print("Bitwise trick verified")
    else:
        m = s.model()
        print(f"Counterexample: x={m[x]}")

verify_bitwise_trick()
```

### Pattern 8: Invariant Generation (Loop Invariants)
```python
from z3 import *

def infer_loop_invariant():
    """Infer invariant for: x = 0; while (x < n) x += 2"""
    x_pre = Int('x_pre')
    x_post = Int('x_post')
    n = Int('n')

    # Candidate invariant: x is even and 0 <= x <= n
    def invariant(x):
        return And(x % 2 == 0, x >= 0, x <= n)

    s = Solver()

    # Check: invariant preserved by loop body
    s.add(invariant(x_pre))  # Assume invariant before iteration
    s.add(x_pre < n)         # Loop condition
    s.add(x_post == x_pre + 2)  # Loop body

    s.add(Not(invariant(x_post)))  # Negated: invariant violated after

    if s.check() == unsat:
        print("Invariant holds: x is even and 0 <= x <= n")
    else:
        print(f"Invariant broken: {s.model()}")

infer_loop_invariant()
```

## Quick Reference

### Theory Selection Guide
```python
# Linear arithmetic (fast)
x, y = Ints('x y')
s.add(x + 2*y <= 10)

# Nonlinear arithmetic (slower, may timeout)
s.add(x * y == 10)

# Bitvectors (for low-level code)
x = BitVec('x', 32)
s.add(x & 0xFF == 0)

# Arrays (for memory/data structures)
A = Array('A', IntSort(), IntSort())
s.add(Select(A, 0) == 5)

# Uninterpreted functions (for abstraction)
f = Function('f', IntSort(), IntSort())
s.add(f(x) == f(y))
s.add(x != y)
```

### Common SMT Patterns
```python
# Bounded model checking
for t in range(k):
    state[t+1] = transition(state[t])
s.add(Or([bad_state(state[t]) for t in range(k)]))

# Symbolic execution
if cond:
    path1_executor.add(cond)
else:
    path2_executor.add(Not(cond))

# Equivalence checking
s.add(func1(inputs) != func2(inputs))
if s.check() == unsat:
    print("Equivalent")

# Test generation
for branch in branches:
    s.push()
    s.add(branch_condition)
    if s.check() == sat:
        tests.append(s.model())
    s.pop()
```

### Z3 Optimization API
```python
opt = Optimize()
opt.add(constraints)

# Minimize/maximize
h = opt.minimize(expr)  # or maximize(expr)

if opt.check() == sat:
    print(f"Optimal value: {opt.model()[expr]}")
    print(f"Bounds: [{opt.lower(h)}, {opt.upper(h)}]")
```

### Performance Tips
```python
# 1. Use appropriate theory
# QF_LIA (linear int) faster than QF_NIA (nonlinear)

# 2. Bound variables when possible
s.add(And(x >= 0, x <= 100))

# 3. Use tactics for hard problems
tactic = Then('simplify', 'solve-eqs', 'qflia')
solver = tactic.solver()

# 4. Incremental solving with push/pop
s.push()
s.add(temporary_constraint)
s.check()
s.pop()

# 5. Quantifier elimination (if supported)
from z3 import Tactic
qe = Tactic('qe')  # Quantifier elimination
```

## Anti-Patterns

### Anti-Pattern 1: Unbounded Quantifiers
**Problem**: SMT solvers struggle with universal quantifiers.

```python
# BAD: Universal quantifier (may not terminate)
x = Int('x')
s = Solver()
s.add(ForAll([x], x + 1 > x))  # True but hard to prove
s.check()  # May timeout
```

**Solution**: Use bounded quantifiers or avoid quantifiers.
```python
# GOOD: Bounded or quantifier-free
for i in range(100):  # Finite unrolling
    x_i = Int(f'x{i}')
    s.add(x_i + 1 > x_i)
```

### Anti-Pattern 2: Wrong Theory for Problem
**Problem**: Using bitvectors for unbounded integers.

```python
# BAD: Bitvector overflow for large numbers
x = BitVec('x', 32)
s.add(x * x > 1000000000)  # May overflow
```

**Solution**: Use appropriate theory.
```python
# GOOD: Use integers for unbounded arithmetic
x = Int('x')
s.add(x * x > 1000000000)
```

### Anti-Pattern 3: Over-Approximating Loops
**Problem**: Unrolling loops too much.

```python
# BAD: Unroll 1000 iterations (huge formula)
for i in range(1000):
    state[i+1] = transition(state[i])
```

**Solution**: Find minimal bound or use abstraction.
```python
# GOOD: Binary search for minimal k
for k in [1, 2, 4, 8, 16, ...]:
    if check_bounded(k) == sat:
        break  # Found counterexample
```

### Anti-Pattern 4: Not Checking Solver Status
**Problem**: Accessing model without checking SAT.

```python
# BAD: May crash if UNSAT or UNKNOWN
result = s.check()
model = s.model()  # Error if result != sat
```

**Solution**: Always check status.
```python
# GOOD: Check before accessing model
if s.check() == sat:
    model = s.model()
elif result == unsat:
    print("Proven UNSAT")
else:
    print("UNKNOWN (timeout or incomplete)")
```

### Anti-Pattern 5: Ignoring Timeouts
**Problem**: No timeout on hard problems.

```python
# BAD: May run forever on undecidable formula
s.check()
```

**Solution**: Set timeout.
```python
# GOOD: Timeout after 5 seconds
s.set('timeout', 5000)
result = s.check()
if result == unknown:
    print("Timeout or incomplete")
```

## Real-World Applications

### Application 1: Web Application Security Analysis
```python
def check_sql_injection_vulnerability():
    """Detect SQL injection in query builder"""
    from z3 import *

    # Symbolic user input
    user_input = String('user_input')

    # Query template: SELECT * FROM users WHERE name = '<user_input>'
    query = Concat(String("SELECT * FROM users WHERE name = '"),
                   user_input,
                   String("'"))

    s = Solver()

    # Example SQL injection attack payload - for security validation only
    # Attacker goal: inject '; DROP TABLE users; --
    malicious = String("'; DROP TABLE users; --")

    # Check if query can contain DROP TABLE (detecting injection vulnerability)
    s.add(Contains(query, String("DROP TABLE")))

    if s.check() == sat:
        m = s.model()
        print(f"SQL injection possible with input: {m[user_input]}")
    else:
        print("No SQL injection found")

# Note: Z3 string support is limited; use specialized tools for real security
```

### Application 2: Compiler Optimization Verification
```python
def verify_dead_code_elimination():
    """Verify dead code elimination preserves semantics"""
    from z3 import *

    x = Int('x')
    y = Int('y')

    # Original code:
    # if (x > 0) { y = x + 1; } else { y = 0; }
    # z = y * 2;  // Dead if y = 0
    # return y;

    # Optimized code (eliminates z computation when y = 0):
    # if (x > 0) { y = x + 1; z = y * 2; } else { y = 0; }
    # return y;

    # Check equivalence of return values
    s = Solver()

    # Original
    y_orig = If(x > 0, x + 1, 0)

    # Optimized
    y_opt = If(x > 0, x + 1, 0)

    # Should be equivalent
    s.add(y_orig != y_opt)

    if s.check() == unsat:
        print("Optimization preserves semantics")
    else:
        print(f"Bug in optimization: {s.model()}")

verify_dead_code_elimination()
```

## Related Skills
- **z3-solver-basics.md**: Z3 API fundamentals, basic constraints
- **sat-solving-strategies.md**: Boolean SAT solving, CDCL
- **lean-theorem-proving.md**: Interactive theorem proving
- **program-analysis.md**: Static analysis techniques
- **abstract-interpretation.md**: Scalable program analysis

## References
- Z3 Guide: https://microsoft.github.io/z3guide/
- SMT-LIB: http://smtlib.cs.uiowa.edu/
- Book: "Decision Procedures" by Kroening & Strichman
- SAGE (Symbolic Execution): Microsoft Research
- KLEE Symbolic Execution Engine

## Troubleshooting

**Problem**: Solver returns UNKNOWN
- **Cause**: Nonlinear arithmetic, quantifiers, or timeout
- **Fix**: Increase timeout, simplify formula, or use approximations

**Problem**: Symbolic execution path explosion
- **Cause**: Too many branches or loops
- **Fix**: Use concolic testing (mix concrete + symbolic), bound loops, prune infeasible paths

**Problem**: Equivalence check times out
- **Cause**: Complex functions or large state space
- **Fix**: Use abstractions, bound inputs, or compositional verification

**Problem**: Test generation misses edge cases
- **Cause**: Incomplete path coverage
- **Fix**: Use coverage-guided symbolic execution, add assertions for edge cases

**Problem**: Array theory too slow
- **Cause**: Large array or complex constraints
- **Fix**: Use array axioms selectively, abstract arrays, or bound indices
