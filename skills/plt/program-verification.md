---
name: program-verification
description: Program verification including Hoare logic, SMT-based verification, refinement types, and proof-carrying code
---

# Program Verification

**Scope**: Hoare logic, weakest preconditions, SMT-based verification, refinement types, separation logic, proof automation
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Proving program correctness formally
- Implementing verified compilers or kernels
- Using tools like Dafny, Frama-C, or Why3
- Designing proof-carrying code systems
- Verifying safety and security properties
- Working with separation logic for memory safety

## Core Concepts

### Hoare Logic

**Hoare triple**: {P} C {Q}
- P: precondition (assertion before C)
- C: command/program
- Q: postcondition (assertion after C)

**Partial correctness**: If P holds before C and C terminates, then Q holds after
**Total correctness**: P holds before C, C terminates, and Q holds after

```python
from dataclasses import dataclass
from typing import Union, Callable

# Assertions (predicates on program state)
Assertion = Callable[[dict], bool]

# Commands
@dataclass
class Skip:
    """skip - do nothing"""
    pass

@dataclass
class Assign:
    """x := e"""
    var: str
    expr: 'Expr'

@dataclass
class Seq:
    """C₁; C₂ - sequential composition"""
    first: 'Command'
    second: 'Command'

@dataclass
class If:
    """if B then C₁ else C₂"""
    cond: 'Expr'
    then_branch: 'Command'
    else_branch: 'Command'

@dataclass
class While:
    """while B do C"""
    cond: 'Expr'
    body: 'Command'

Command = Union[Skip, Assign, Seq, If, While]

# Hoare logic rules
def hoare_skip(P: Assertion) -> bool:
    """
    {P} skip {P}
    Skip preserves any assertion
    """
    return True  # Always valid

def hoare_assign(P: Assertion, var: str, expr) -> Assertion:
    """
    {P[x := e]} x := e {P}
    Weakest precondition: substitute e for x in P
    """
    def precondition(state: dict) -> bool:
        # Evaluate expression in current state
        new_state = state | {var: eval_expr(expr, state)}
        return P(new_state)
    return precondition

def hoare_seq(P: Assertion, C1: Command, C2: Command, Q: Assertion) -> tuple[bool, Assertion]:
    """
    {P} C₁ {R}    {R} C₂ {Q}
    ─────────────────────────
    {P} C₁; C₂ {Q}
    
    Need to find intermediate assertion R
    """
    # R is the weakest precondition of C₂ with respect to Q
    R = weakest_precondition(C2, Q)
    return True, R

def hoare_if(P: Assertion, B, C1: Command, C2: Command, Q: Assertion) -> bool:
    """
    {P ∧ B} C₁ {Q}    {P ∧ ¬B} C₂ {Q}
    ───────────────────────────────────
    {P} if B then C₁ else C₂ {Q}
    """
    # Verify both branches
    def P_and_B(state): return P(state) and eval_expr(B, state)
    def P_and_not_B(state): return P(state) and not eval_expr(B, state)
    
    # Would need to verify {P ∧ B} C₁ {Q} and {P ∧ ¬B} C₂ {Q}
    return True  # Simplified

def hoare_while(I: Assertion, B, C: Command) -> bool:
    """
    {I ∧ B} C {I}
    ────────────────────────
    {I} while B do C {I ∧ ¬B}
    
    I: loop invariant
    Must prove:
    1. I preserved by loop body when B true
    2. After loop, I ∧ ¬B holds
    """
    # Verify loop invariant preservation
    def I_and_B(state): return I(state) and eval_expr(B, state)
    # Would verify {I ∧ B} C {I}
    return True  # Simplified

def eval_expr(expr, state: dict):
    """Evaluate expression in state"""
    # Simplified evaluation
    return expr

# Example: Prove {x = 5} x := x + 1 {x = 6}
def example_assign():
    # Postcondition: x = 6
    Q = lambda state: state['x'] == 6
    
    # Precondition: Q[x := x+1] = (x+1 = 6) = (x = 5)
    P = lambda state: state['x'] + 1 == 6
    
    # Verify
    initial_state = {'x': 5}
    assert P(initial_state)
    
    # Execute x := x + 1
    final_state = {'x': initial_state['x'] + 1}
    assert Q(final_state)
    
    print("Verified: {x = 5} x := x + 1 {x = 6}")

example_assign()
```

### Weakest Precondition

**wp(C, Q)**: Weakest precondition - most general P such that {P} C {Q}

```python
def weakest_precondition(cmd: Command, Q: Assertion) -> Assertion:
    """
    Compute wp(C, Q) - weakest precondition
    """
    match cmd:
        case Skip():
            # wp(skip, Q) = Q
            return Q
        
        case Assign(var, expr):
            # wp(x := e, Q) = Q[x := e]
            return lambda state: Q(state | {var: eval_expr(expr, state)})
        
        case Seq(C1, C2):
            # wp(C₁; C₂, Q) = wp(C₁, wp(C₂, Q))
            wp_C2 = weakest_precondition(C2, Q)
            return weakest_precondition(C1, wp_C2)
        
        case If(B, C1, C2):
            # wp(if B then C₁ else C₂, Q) = (B ⟹ wp(C₁, Q)) ∧ (¬B ⟹ wp(C₂, Q))
            wp_C1 = weakest_precondition(C1, Q)
            wp_C2 = weakest_precondition(C2, Q)
            return lambda state: (
                (eval_expr(B, state) and wp_C1(state)) or
                (not eval_expr(B, state) and wp_C2(state))
            )
        
        case While(B, body):
            # wp(while B do C, Q) requires loop invariant
            # For now, return Q (simplified)
            return Q

# Example: wp(x := x + 1; y := x * 2, y = 12)
C1 = Assign('x', lambda s: s['x'] + 1)
C2 = Assign('y', lambda s: s['x'] * 2)
program = Seq(C1, C2)
postcondition = lambda s: s['y'] == 12

wp = weakest_precondition(program, postcondition)
# wp should be: x + 1 * 2 = 12, i.e., x = 5

state = {'x': 5, 'y': 0}
print(f"wp holds for x=5: {wp(state)}")
```

### Refinement Types

**Refinement type**: {x:τ | P(x)} - type τ refined by predicate P

```python
@dataclass
class RefinementType:
    """Refinement type: {x:τ | P(x)}"""
    base_type: type
    predicate: Callable[[any], bool]
    
    def check(self, value):
        """Check if value satisfies refinement"""
        if not isinstance(value, self.base_type):
            return False
        return self.predicate(value)

# Examples
Pos = RefinementType(int, lambda x: x > 0)
Nat = RefinementType(int, lambda x: x >= 0)
NonZero = RefinementType(int, lambda x: x != 0)

def safe_div(a: int, b: int) -> int:
    """
    Type: (a:int) → (b:int) → {b ≠ 0} → int
    Requires proof that b ≠ 0
    """
    assert NonZero.check(b), "Division by zero"
    return a // b

# Usage
result = safe_div(10, 2)  # OK
print(f"10 / 2 = {result}")

try:
    result = safe_div(10, 0)  # Error: assertion fails
except AssertionError as e:
    print(f"Error: {e}")

# In Liquid Haskell:
"""
{-@ type Pos = {v:Int | v > 0} @-}
{-@ type NonZero = {v:Int | v /= 0} @-}

{-@ div :: Int -> NonZero -> Int @-}
div :: Int -> Int -> Int
div x y = x `div` y

-- Type checker ensures y ≠ 0 at call sites
"""
```

### SMT-Based Verification

**Using Z3 for verification**:

```python
try:
    from z3 import Int, Solver, sat, And, Or, Not
    
    def verify_program_z3():
        """
        Verify: {x ≥ 0} if x < 10 then y := x else y := 10 {y < 11}
        Using Z3 SMT solver
        """
        x, y, y_out = Int('x'), Int('y'), Int('y_out')
        
        # Precondition: x ≥ 0
        P = x >= 0
        
        # Program semantics
        branch1 = And(x < 10, y_out == x)     # Then: y := x
        branch2 = And(x >= 10, y_out == 10)   # Else: y := 10
        program = Or(branch1, branch2)
        
        # Postcondition: y < 11
        Q = y_out < 11
        
        # Verify: ¬(P ∧ program ⟹ Q)
        # If unsatisfiable, then {P} program {Q} is valid
        solver = Solver()
        solver.add(P)
        solver.add(program)
        solver.add(Not(Q))
        
        if solver.check() == sat:
            print(f"Counterexample: {solver.model()}")
            return False
        else:
            print("Verified: {x ≥ 0} program {y < 11}")
            return True
    
    verify_program_z3()

except ImportError:
    print("Z3 not available, skipping SMT verification example")
```

### Separation Logic

**Heap assertions**: P * Q (P and Q hold on disjoint heap parts)

```python
@dataclass
class PointsTo:
    """x ↦ v - heap location x contains value v"""
    location: str
    value: any

@dataclass
class SeparatingConjunction:
    """P * Q - P and Q hold on disjoint heaps"""
    left: 'HeapAssertion'
    right: 'HeapAssertion'

@dataclass
class Emp:
    """emp - empty heap"""
    pass

HeapAssertion = Union[PointsTo, SeparatingConjunction, Emp]

# Frame rule (key rule in separation logic):
"""
{P} C {Q}
─────────────────── (Frame)
{P * R} C {Q * R}

If R describes heap C doesn't touch, it's preserved
"""

def frame_rule_example():
    """
    Example: {x ↦ 5} *p := 10 {x ↦ 5}
    where p and x are different locations
    
    Frame rule:
    {emp} *p := 10 {p ↦ 10}
    ─────────────────────────────── (Frame)
    {emp * x ↦ 5} *p := 10 {p ↦ 10 * x ↦ 5}
    """
    print("Frame rule: Unmodified heap portions preserved")

frame_rule_example()
```

---

## Patterns

### Pattern 1: Loop Invariants

```python
def verify_loop_invariant():
    """
    Verify: {n ≥ 0} i := 0; s := 0; while i < n do (s := s + i; i := i + 1) {s = n*(n-1)/2}
    
    Loop invariant: s = i*(i-1)/2 ∧ i ≤ n
    """
    # Precondition: n ≥ 0
    # After i := 0; s := 0: s = 0 ∧ i = 0 (implies invariant)
    # Invariant: s = i*(i-1)/2 ∧ i ≤ n
    # Body preserves invariant when i < n
    # After loop: i = n ∧ s = i*(i-1)/2 = n*(n-1)/2
    print("Loop invariant: s = i*(i-1)/2 ∧ i ≤ n")

verify_loop_invariant()
```

### Pattern 2: Verification Conditions

```python
def generate_verification_conditions(cmd: Command, Q: Assertion) -> list:
    """
    Generate verification conditions (VCs) for program
    VCs are formulas to prove for correctness
    """
    vcs = []
    
    # Example: for loop, generate:
    # 1. Invariant initially true
    # 2. Invariant preserved by body
    # 3. Invariant + ¬condition implies postcondition
    
    match cmd:
        case While(cond, body):
            # Would generate 3 VCs above
            pass
    
    return vcs
```

---

## Quick Reference

### Hoare Logic Rules

```
{P} skip {P}                                    (Skip)

{P[x := e]} x := e {P}                          (Assign)

{P} C₁ {R}    {R} C₂ {Q}
────────────────────────                        (Seq)
{P} C₁; C₂ {Q}

{P ∧ B} C₁ {Q}    {P ∧ ¬B} C₂ {Q}
──────────────────────────────────              (If)
{P} if B then C₁ else C₂ {Q}

{I ∧ B} C {I}
────────────────────────                        (While)
{I} while B do C {I ∧ ¬B}
```

### Weakest Precondition

```
wp(skip, Q) = Q
wp(x := e, Q) = Q[x := e]
wp(C₁; C₂, Q) = wp(C₁, wp(C₂, Q))
wp(if B then C₁ else C₂, Q) = (B ⟹ wp(C₁, Q)) ∧ (¬B ⟹ wp(C₂, Q))
```

---

## Anti-Patterns

❌ **Forgetting loop invariants**: Can't verify loops without them
✅ Find invariant that: (1) holds initially, (2) preserved by body, (3) + ¬condition implies post

❌ **Over-specifying preconditions**: Weakest precondition is most general
✅ Use wp() to find most permissive precondition

❌ **Ignoring frame**: Assuming entire heap in Hoare triple
✅ Use separation logic to reason about heap portions

---

## Related Skills

- `lambda-calculus.md` - Formal semantics foundation
- `type-systems.md` - Type soundness proofs
- `curry-howard.md` - Proofs as programs
- `operational-semantics.md` - Program execution model
- `formal/z3-solver-basics.md` - SMT solving for verification
- `formal/lean-proof-basics.md` - Interactive theorem proving

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
