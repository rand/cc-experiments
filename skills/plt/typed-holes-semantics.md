---
name: typed-holes-semantics
description: Advanced typed holes semantics - hole closures, pattern matching with holes, type error localization, polymorphism, gradual guarantees, blame tracking
---

# Typed Holes: Advanced Semantics

**Scope**: Hole closures, pattern matching, error localization (POPL 2024), polymorphism (TFP 2024), gradual guarantees, blame
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Designing advanced type systems with holes
- Implementing pattern matching with incomplete patterns
- Building sophisticated error localization and recovery
- Adding polymorphic holes to type systems
- Ensuring gradual typing guarantees
- Implementing blame tracking for hole-induced errors

## Core Concepts

### Hole Closures and Closure Types

**Hole closure**: Hole with captured environment (from contextual modal type theory)

```python
from dataclasses import dataclass
from typing import Union, Optional, Dict

# Closure representation
@dataclass
class Closure:
    """Value closure: function with captured environment"""
    param: str
    body: 'Expr'
    env: Dict[str, 'Value']  # Captured environment

    def __repr__(self):
        return f"⟨λ{self.param}.{self.body}, {list(self.env.keys())}⟩"

@dataclass
class HoleClosure:
    """Hole with captured environment (from CMTT)"""
    hole_name: str
    expected_type: 'Type'
    env: Dict[str, 'Value']  # What's in scope

    def __repr__(self):
        return f"⟨?{self.hole_name} : {self.expected_type}, {list(self.env.keys())}⟩"

# Example: Nested scope with hole
def example_hole_closure():
    """
    (λx. λy. ?h) 5

    After applying to 5:
      λy. ?h  where  x=5 captured

    Hole closure:
      ⟨?h : τ, {x: 5, y: ...}⟩
    """
    x_val = 5
    hole = HoleClosure(
        hole_name="h",
        expected_type=TString(),
        env={'x': x_val}  # x captured, y not yet bound
    )
    return hole

# Contextual modal type theory notation
"""
⊢ e : A | Ω    (e has type A with free holes Ω)

Ω ::= · | Ω, u:A[Γ]

u:A[Γ] means: hole u expects type A with variables Γ available
"""

print("Hole closures capture environment for later filling")
```

### Pattern Matching with Typed Holes (POPL 2023)

**Pattern holes**: Incomplete patterns that still type-check

```python
# Patterns with holes
@dataclass
class VarPattern:
    """Variable pattern: x"""
    name: str

@dataclass
class ConstructorPattern:
    """Constructor: C p₁ ... pₙ"""
    constructor: str
    sub_patterns: list['Pattern']

@dataclass
class PatternHole:
    """Pattern hole: _"""
    expected_type: 'Type'

    def __repr__(self):
        return f"_ : {self.expected_type}"

Pattern = Union[VarPattern, ConstructorPattern, PatternHole]

# Match expression with holes
@dataclass
class Match:
    """match e with | p₁ → e₁ | ... | ?p → ?e"""
    scrutinee: 'Expr'
    branches: list[tuple[Pattern, 'Expr']]

# Typing rule for pattern holes
def type_pattern_match_with_holes(match_expr: Match, gamma: dict, expected: 'Type'):
    """
    Pattern holes contribute to hole context

    match (x, y) with
    | (0, _) → 1       -- _ : Int (inferred from (x,y) : Int × Int)
    | _     → ?e      -- ?e : Int (result type), _ : Int × Int

    Gradual type theory + contextual modal type theory
    """
    scrutinee_type = synth(match_expr.scrutinee, gamma)

    for (pattern, branch_expr) in match_expr.branches:
        # Pattern typing: Γ ⊢ p ◁ τ ⊣ Γ'
        # Produces new context Γ' with pattern variables
        new_gamma = type_pattern(pattern, scrutinee_type, gamma)

        # Check branch expression
        check(branch_expr, new_gamma, expected)

def type_pattern(pattern: Pattern, scrutinee_type: 'Type', gamma: dict) -> dict:
    """
    Type pattern against scrutinee type

    Returns extended context with pattern variables
    """
    match pattern:
        case VarPattern(x):
            # x : scrutinee_type
            return gamma | {x: scrutinee_type}

        case PatternHole(expected):
            # Hole must be consistent with scrutinee type
            if not consistent(expected, scrutinee_type):
                raise TypeError(f"Pattern hole {expected} !~ {scrutinee_type}")
            # No new bindings from hole
            return gamma

        case ConstructorPattern(ctor, sub_patterns):
            # Decompose scrutinee type, type sub-patterns
            # ...
            pass

print("Pattern holes: incomplete patterns with typing")
```

### Type Error Localization with Holes (POPL 2024)

**Marked lambda calculus**: Systematic error localization via holes

```python
@dataclass
class Marked:
    """Marked expression: expression with blame label"""
    expr: 'Expr'
    mark: str  # Blame label

    def __repr__(self):
        return f"{self.expr}^{self.mark}"

# Error localization strategy
class ErrorLocalizer:
    """
    Total Type Error Localization (POPL 2024)

    Key idea: Use holes + blame to pinpoint errors
    """

    @staticmethod
    def localize_error(program: 'Expr', gamma: dict) -> tuple['Expr', list[str]]:
        """
        Transform program to mark error locations

        Returns: (marked program, error locations)

        Example:
          (λx:Int. x) true

        Localized:
          (λx:Int. x) ⦇true⦈^m1    -- m1 marks type error

        Blame: m1 at position "argument of application"
        """
        try:
            check(program, gamma, synth(program, gamma))
            return (program, [])  # No errors
        except TypeError:
            # Insert holes at inconsistencies
            marked_program = insert_holes_at_errors(program, gamma)
            blame_labels = extract_blame_labels(marked_program)
            return (marked_program, blame_labels)

    @staticmethod
    def constraint_solving_with_holes(program: 'Expr'):
        """
        Gradual bidirectional typing with hole filling

        Generate constraints:
          τ₁ ~ τ₂  (consistency)
          τ₁ = τ₂  (equality where possible)

        Solve constraints:
          Replace ? with concrete types where possible
          Keep ? where underspecified
        """
        constraints = generate_constraints(program)
        solution = solve_constraints(constraints)
        return apply_solution(program, solution)

print("Error localization: holes mark exactly where type errors occur")
```

### Polymorphism with Typed Holes (TFP 2024)

**Polymorphic holes**: Holes in polymorphic contexts

```python
# System F-style polymorphism with holes
@dataclass
class TForall:
    """∀α. τ - polymorphic type"""
    type_var: str
    body: 'Type'

    def __repr__(self):
        return f"∀{self.type_var}.{self.body}"

@dataclass
class TyAbs:
    """Λα. e - type abstraction"""
    type_var: str
    expr: 'Expr'

@dataclass
class TyApp:
    """e [τ] - type application"""
    expr: 'Expr'
    type_arg: 'Type'

# Polymorphic hole
@dataclass
class PolyHole:
    """Hole with polymorphic expected type"""
    name: str
    type_scheme: TForall  # ∀α. τ

    def __repr__(self):
        return f"?{self.name} : {self.type_scheme}"

# Typing rule for polymorphic holes
def type_poly_hole(hole: PolyHole, instantiation: dict) -> 'Type':
    """
    Instantiate polymorphic hole

    ?h : ∀α. α → α

    Can be filled with:
    - λx. x           (id : ∀α. α → α)
    - λx. ?body       (?body : α with α free)
    """
    # Instantiate type variables in scheme
    return instantiate_type_scheme(hole.type_scheme, instantiation)

# Constraint generation
def generate_polymorphic_constraints(program: 'Expr'):
    """
    Generate constraints for polymorphic program with holes

    let id = Λα. λx:α. ?body in
      id [Int] 5

    Constraints:
    - ?body : α  (in context α, x:α)
    - When instantiated with Int: ?body : Int
    """
    pass

print("Polymorphic holes: holes in polymorphic contexts")
```

### Gradual Guarantees

**Static and dynamic gradual guarantees** for soundness

```python
class GradualGuarantees:
    """
    Gradual typing guarantees (Siek et al.)

    Applied to typed holes
    """

    @staticmethod
    def static_gradual_guarantee():
        """
        Static Gradual Guarantee:

        If Γ ⊢ e : τ, and e' is less precise than e
        (i.e., e' has more holes), then Γ ⊢ e' : τ'
        where τ' is consistent with τ

        Example:
          λx:Int. x + 1  :  Int → Int  ✓
          λx:Int. ?h + 1  :  Int → Int  ✓  (with ?h : Int)
          λx:Int. ?h      :  Int → ?    ✓  (with ?h : ?)

        Less precision → More programs accepted
        """
        pass

    @staticmethod
    def dynamic_gradual_guarantee():
        """
        Dynamic Gradual Guarantee:

        If e₁ evaluates to v₁, and e₂ is less precise than e₁,
        then e₂ evaluates to v₂ where:
        - v₂ is less precise than v₁, OR
        - v₂ is indeterminate (contains holes)

        Example:
          (λx. x + 1) 5  ⇓ 6
          (λx. x + ?h) 5  ⇓ ⊥h  (indeterminate)

        Adding holes → Same behavior or indeterminate
        """
        pass

    @staticmethod
    def precision_ordering():
        """
        Precision ordering: e₁ ⊑ e₂

        e₁ is less precise than e₂ if e₁ has more holes

        Examples:
        - ?h ⊑ 5
        - ?h + 1 ⊑ 5 + 1
        - λx. ?h ⊑ λx. x

        Reflexive, transitive ordering
        """
        pass

print("Gradual guarantees ensure soundness with holes")
```

### Blame Tracking

**Blame labels**: Track which hole caused error

```python
@dataclass
class BlameLabel:
    """Blame label for tracking hole provenance"""
    hole_id: str
    position: str  # Where in program
    expected: 'Type'
    actual: 'Type'

    def __repr__(self):
        return f"Blame({self.hole_id}): expected {self.expected}, got {self.actual}"

class BlameTracking:
    """Track blame through evaluation"""

    def __init__(self):
        self.blame_log = []

    def record_blame(self, label: BlameLabel):
        """Record when hole causes type error"""
        self.blame_log.append(label)

    def evaluate_with_blame(self, expr: 'Expr', env: dict):
        """
        Evaluate with blame tracking

        If hole causes cast failure: record blame
        """
        try:
            return self.eval(expr, env)
        except TypeError as e:
            # Find which hole caused error
            blame = self.find_responsible_hole(expr, e)
            self.record_blame(blame)
            raise

    def find_responsible_hole(self, expr: 'Expr', error: TypeError) -> BlameLabel:
        """
        Determine which hole is responsible for error

        Trace back through evaluation to find hole
        """
        # Walk expression tree, find hole that led to type mismatch
        pass

# Example usage
tracker = BlameTracking()

# Program with hole
program = """
(λx:Int → Int. x 5) ?f
"""

# ?f must have type Int → Int
# If we fill it with 42, we get blame:
# Blame(?f): expected Int → Int, got Int

print("Blame tracking: identify which hole caused problem")
```

### Constraint Generation and Solving

**Constraint-based typing** with holes

```python
@dataclass
class Constraint:
    """Type constraint"""
    pass

@dataclass
class EqualityConstraint(Constraint):
    """τ₁ = τ₂"""
    left: 'Type'
    right: 'Type'

    def __repr__(self):
        return f"{self.left} = {self.right}"

@dataclass
class ConsistencyConstraint(Constraint):
    """τ₁ ~ τ₂"""
    left: 'Type'
    right: 'Type'

    def __repr__(self):
        return f"{self.left} ~ {self.right}"

class ConstraintSolver:
    """Solve type constraints with holes"""

    def __init__(self):
        self.constraints = []
        self.substitution = {}  # Unification substitution

    def add_constraint(self, c: Constraint):
        """Add constraint to system"""
        self.constraints.append(c)

    def solve(self) -> dict:
        """
        Solve constraints

        Returns: Substitution mapping type variables to types

        Algorithm:
        1. Process equality constraints (unification)
        2. Process consistency constraints (check, don't fail on holes)
        3. Simplify: ? ~ τ always satisfies
        """
        for c in self.constraints:
            match c:
                case EqualityConstraint(left, right):
                    self.unify(left, right)
                case ConsistencyConstraint(left, right):
                    self.check_consistency(left, right)

        return self.substitution

    def unify(self, t1: 'Type', t2: 'Type'):
        """
        Unification with holes

        ? unifies with anything (most general)
        """
        if isinstance(t1, THole) or isinstance(t2, THole):
            return  # Success - holes unify with everything

        if isinstance(t1, TVar):
            self.substitution[t1.name] = t2
            return

        # ... standard unification

    def check_consistency(self, t1: 'Type', t2: 'Type'):
        """
        Check consistency (weaker than equality)

        Succeeds if types are compatible modulo holes
        """
        if not consistent(t1, t2):
            raise TypeError(f"Inconsistent types: {t1} !~ {t2}")

print("Constraint solving: systematic type inference with holes")
```

---

## Patterns

### Pattern 1: Gradual Type Migration

```python
def gradual_migration_pattern():
    """
    Migrate untyped code to typed using holes

    Step 1: Replace all types with holes
      f(x, y) → f(x: ?, y: ?) -> ?

    Step 2: Run type inference
      f(x: Int, y: ?) -> ?  (inferred x is Int)

    Step 3: Incrementally replace holes with concrete types
      f(x: Int, y: String) -> String

    Gradual guarantee: Always types at every step!
    """
    print("Gradual migration: untyped → holes → typed")
```

### Pattern 2: Error Recovery with Localization

```python
def error_recovery_with_localization(program: 'Expr'):
    """
    Localize type error, insert hole, continue

    Type error: (λx:Int. x) "hello"

    Step 1: Detect inconsistency
      Argument "hello" : String
      Expected: Int

    Step 2: Insert hole at error location
      (λx:Int. x) ⦇"hello"⦈

    Step 3: Continue type checking rest of program
      Other parts may be fine!

    Result: Partial type checking instead of total failure
    """
    try:
        typecheck(program)
    except TypeError as e:
        # Localize error
        error_loc = find_error_location(e)
        # Insert hole
        program_with_hole = insert_hole_at(program, error_loc)
        # Continue
        return typecheck_with_holes(program_with_hole)

print("Error recovery: localize → insert hole → continue")
```

### Pattern 3: Hole-Driven Refactoring

```python
def hole_driven_refactoring(old_function: 'Expr', new_signature: 'Type'):
    """
    Refactor by changing signature, filling holes

    Old: f : Int → Int
         f x = x + 1

    New signature: f : String → String

    Step 1: Replace body with hole
      f : String → String
      f x = ?body  -- ?body : String (x : String)

    Step 2: Type-directed filling
      Can't use x + 1 (Int operation)
      Must produce String
      → show x, x ++ x, etc.
    """
    # Create hole with new type
    hole = Hole("body", new_signature.result)

    # Get suggestions based on new context
    suggestions = type_driven_suggestions(hole, new_signature.param)

    print(f"Suggestions: {suggestions}")

print("Hole-driven refactoring: change type → fill holes")
```

---

## Quick Reference

### Advanced Concepts

| Concept | Notation | Meaning |
|---------|----------|---------|
| Hole closure | ⟨?h, Γ⟩ | Hole with captured environment |
| Pattern hole | _ | Incomplete pattern |
| Blame label | e^m | Expression with blame mark |
| Precision | e₁ ⊑ e₂ | e₁ less precise than e₂ |
| Consistency | τ ~ σ | Types consistent modulo holes |

### Gradual Guarantees

```
Static Gradual Guarantee:
  More holes → Still types (or more general type)

Dynamic Gradual Guarantee:
  More holes → Same behavior or indeterminate
```

### Constraint Forms

```
Equality: τ₁ = τ₂  (Unification)
Consistency: τ₁ ~ τ₂  (Gradual typing)
Subtyping: τ₁ <: τ₂  (With holes)
```

---

## Anti-Patterns

❌ **Failing on first type error**: Prevents finding other errors
✅ Insert holes, localize, continue checking

❌ **Losing hole provenance**: Can't track which hole caused issue
✅ Use blame tracking, maintain hole closures

❌ **Ignoring gradual guarantees**: Breaks soundness
✅ Verify static/dynamic gradual guarantees hold

❌ **Over-constraining holes**: Makes system rigid
✅ Use consistency (~) not equality (=)

---

## Related Skills

- `typed-holes-foundations.md` - Basic concepts and theory
- `hazelnut-calculus.md` - Structure editor implementation
- `type-systems.md` - Gradual typing, subtyping
- `dependent-types.md` - Holes in dependent contexts
- `program-verification.md` - Holes in proofs
- `typed-holes-interaction.md` - Practical IDE integration

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
