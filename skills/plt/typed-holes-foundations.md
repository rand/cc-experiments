---
name: typed-holes-foundations
description: Typed holes fundamentals - incomplete programs with static/dynamic meaning, connection to gradual typing, bidirectional type checking, and theoretical foundations
---

# Typed Holes: Foundations

**Scope**: Basic concepts, gradual typing connection, bidirectional typing, static/dynamic semantics, hole types
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding typed holes in any programming language
- Designing type systems that support incomplete programs
- Working with languages like Agda, Idris, Lean, Haskell (with holes)
- Building IDE features for incomplete code
- Understanding the connection between holes and gradual typing
- Implementing live programming environments

## Core Concepts

### What Are Typed Holes?

**Typed hole**: A placeholder in a program that has a type but no implementation yet

```python
from dataclasses import dataclass
from typing import Union, Optional

# Basic typed hole representation
@dataclass
class Hole:
    """Typed hole: unknown expression with expected type"""
    name: str
    expected_type: 'Type'
    context: dict  # Variables in scope

    def __repr__(self):
        return f"?{self.name} : {self.expected_type}"

# Example: incomplete function
def process_data(x: int) -> str:
    result = Hole("result", expected_type=str, context={'x': int})
    return result  # Type checks! But not complete

# In Haskell:
"""
process_data :: Int -> String
process_data x = _result  -- Typed hole, GHC tells us: _result :: String
"""

# In Agda:
"""
process-data : ℕ → String
process-data x = {! !}  -- Hole, Agda shows goal: String
"""

print("Typed holes allow programs to be incomplete but still meaningful")
```

### Static Semantics: Typing Holes

**Key insight**: Holes have types even though they lack implementations

```python
@dataclass
class TInt:
    def __repr__(self):
        return "Int"

@dataclass
class TBool:
    def __repr__(self):
        return "Bool"

@dataclass
class TFun:
    param: 'Type'
    result: 'Type'
    def __repr__(self):
        return f"({self.param} → {self.result})"

@dataclass
class THole:
    """Hole type: unknown type (gradual typing)"""
    def __repr__(self):
        return "?"

Type = Union[TInt, TBool, TFun, THole]

# Type checking with holes
def type_of_hole(hole: Hole, context: dict) -> Type:
    """
    Typing rule for holes:

    Γ ⊢ ?h : τ    (if hole expects type τ)

    The hole is assigned the expected type from context
    """
    return hole.expected_type

# Example: Function with hole
"""
λx:Int. ?body : Int → Bool

Type checking:
  x : Int ⊢ ?body : Bool   (hole must produce Bool)
  ∴ λx:Int. ?body : Int → Bool
"""

print("Holes are typed based on expected type from context")
```

### Dynamic Semantics: Evaluating Holes

**Indeterminate result**: Programs with holes can still evaluate

```python
@dataclass
class IndeterminateValue:
    """Result of evaluating a hole: we don't know what it should be"""
    hole_name: str
    expected_type: Type

    def __repr__(self):
        return f"⊥{self.hole_name}"

def evaluate_with_holes(expr):
    """
    Evaluation with holes produces indeterminate results

    Examples:
    - 2 + 3 ⇓ 5  (no holes, determinate)
    - 2 + ?h ⇓ ⊥h  (hole, indeterminate)
    - if true then 5 else ?h ⇓ 5  (hole not evaluated, determinate!)
    """
    if isinstance(expr, Hole):
        return IndeterminateValue(expr.name, expr.expected_type)
    # ... other cases

# Key property: Holes don't block ALL evaluation
def example_evaluation():
    """
    if true then 1 else ?h
    ⇓ 1   (determinate! We never evaluate the hole)

    if ?cond then 1 else 2
    ⇓ ⊥cond  (indeterminate - we need to evaluate the hole)
    """
    pass

print("Evaluation with holes: some programs still produce determinate results")
```

### Connection to Gradual Typing

**Key insight**: Hole type (?) is like the unknown type (★) in gradual typing

```python
# Gradual typing perspective
@dataclass
class TUnknown:
    """Unknown type ★ from gradual typing"""
    def __repr__(self):
        return "★"

# Type consistency (~) instead of equality (=)
def consistent(t1: Type, t2: Type) -> bool:
    """
    Type consistency relation: t1 ~ t2

    Rules:
    - τ ~ τ  (reflexive)
    - ? ~ τ  (hole consistent with anything)
    - τ ~ ?  (symmetric)
    - (τ₁ → τ₂) ~ (σ₁ → σ₂) if τ₁ ~ σ₁ and τ₂ ~ σ₂
    """
    if isinstance(t1, THole) or isinstance(t2, THole):
        return True  # Holes consistent with everything
    if type(t1) != type(t2):
        return False
    if isinstance(t1, TFun) and isinstance(t2, TFun):
        return consistent(t1.param, t2.param) and consistent(t1.result, t2.result)
    return t1 == t2

# Example: Gradual guarantees
"""
Static Gradual Guarantee:
  Removing type annotations (replacing with ?) preserves type checking

Dynamic Gradual Guarantee:
  Adding types doesn't change behavior of programs that don't fail
"""

print("Typed holes are gradual types: ? is the unknown type")
print(f"Int ~ ? = {consistent(TInt(), THole())}")  # True
print(f"Int ~ Bool = {consistent(TInt(), TBool())}")  # False
```

### Bidirectional Type Checking

**Key idea**: Two modes of typing to handle holes effectively

```python
from enum import Enum

class Mode(Enum):
    SYNTHESIS = "synth"  # Figure out type from expression
    CHECKING = "check"   # Check expression against expected type

def bidirectional_type(expr, context, mode, expected_type=None):
    """
    Bidirectional typing with holes

    Synthesis mode (⇒): Γ ⊢ e ⇒ τ   (what type does e have?)
    Checking mode (⇐): Γ ⊢ e ⇐ τ   (does e have type τ?)

    Holes work best in checking mode!
    """
    match mode:
        case Mode.SYNTHESIS:
            # Synthesize type from expression
            if isinstance(expr, Hole):
                # Can't synthesize from hole - we need expected type!
                raise TypeError(f"Cannot synthesize type for hole {expr.name}")
            # ... other synthesis cases

        case Mode.CHECKING:
            # Check expression against expected type
            if isinstance(expr, Hole):
                # Holes always check! Assign expected type to hole
                expr.expected_type = expected_type
                return True
            # ... other checking cases

# Pattern: Switch between modes strategically
"""
Application: (f e)

Mode switching:
  Γ ⊢ f ⇒ τ₁ → τ₂    (synthesize function type)
  Γ ⊢ e ⇐ τ₁         (check argument against param type)
  ────────────────
  Γ ⊢ (f e) ⇒ τ₂     (synthesize result type)

This allows: f ?arg
  - Synthesize f's type: Int → Bool
  - Check ?arg against Int (assigns ?arg : Int)
  - Result: Bool
"""

print("Bidirectional typing: synthesis (⇒) and checking (⇐)")
```

### Hole Contexts and Closures

**Hole context**: Variables in scope when hole was created

```python
@dataclass
class HoleWithContext:
    """Hole with captured environment"""
    name: str
    expected_type: Type
    environment: dict  # Captured variables

    def available_variables(self):
        """What can the hole use?"""
        return self.environment.keys()

# Example: Nested scopes
def example_hole_context():
    """
    λx:Int. λy:Bool. ?body : Int → Bool → String

    At hole ?body:
    - Available: x : Int, y : Bool
    - Expected type: String
    - Hole context: {x: Int, y: Bool}
    """
    x_type = TInt()
    y_type = TBool()
    hole_context = {'x': x_type, 'y': y_type}

    body_hole = HoleWithContext(
        name="body",
        expected_type=TString(),
        environment=hole_context
    )

    return body_hole

# IDE integration: Show available variables
hole = example_hole_context()
print(f"Hole {hole.name} can use: {list(hole.available_variables())}")
print(f"Hole must produce: {hole.expected_type}")
```

### Type Holes vs Expression Holes

**Two kinds of holes**: In types and in expressions

```python
# Expression hole: ?e
expression_hole = Hole("e", expected_type=TInt(), context={})

# Type hole: unknown type
@dataclass
class TypeHole:
    """Hole in type position: we don't know the type"""
    name: str

    def __repr__(self):
        return f"?{self.name}"

# Example: Polymorphic function with type hole
"""
In Haskell:
  id :: a -> a
  id x = x

With type hole:
  id :: _t -> _t    -- GHC infers: _t :: Type
  id x = x

Type hole tells us what type should be!
"""

# In Agda:
"""
id : {A : Set} → A → A   -- Explicit polymorphism
id x = x

id : {! !} → {! !}        -- Type holes, Agda will suggest: Set → Set
id x = {! !}              -- Expression hole, Agda shows goal: A
"""

print("Expression holes: missing terms. Type holes: missing types")
```

### Metatheoretic Properties

**Key properties** that well-designed hole systems should satisfy

```python
class HoleSystemProperties:
    """Properties of sound typed hole systems"""

    @staticmethod
    def progress_with_holes():
        """
        Modified Progress:
        If Γ ⊢ e : τ, then either:
        1. e is a value
        2. e is indeterminate (contains holes)
        3. e → e' (can step)

        Holes don't get stuck!
        """
        pass

    @staticmethod
    def preservation_with_holes():
        """
        Preservation:
        If Γ ⊢ e : τ and e → e', then Γ ⊢ e' : τ

        Even with holes, types are preserved during evaluation
        """
        pass

    @staticmethod
    def gradual_guarantee():
        """
        Static Gradual Guarantee:
        If Γ ⊢ e : τ, and e' differs from e only by replacing
        terms with holes, then Γ ⊢ e' : τ

        Less information ⇒ more programs accepted
        """
        pass

print("Well-designed hole systems preserve type safety")
```

---

## Patterns

### Pattern 1: Goal-Directed Development

```python
# Start with types, fill in holes
def goal_directed_example():
    """
    1. Write type signature first
    2. Create hole for body
    3. Inspect hole's expected type
    4. Refine hole step by step
    """

    # Step 1: Type signature
    # factorial : Int → Int

    # Step 2: Hole for body
    # factorial n = ?body    -- ?body : Int

    # Step 3: Case analysis (refine)
    # factorial n = if (n == 0) then ?base else ?recursive
    # ?base : Int
    # ?recursive : Int

    # Step 4: Fill holes
    # factorial n = if (n == 0) then 1 else n * factorial (n-1)

    print("Goal-directed: type → holes → refinement → completion")
```

### Pattern 2: Type-Driven Completion

```python
def type_driven_completion(hole: HoleWithContext):
    """
    Use hole type to suggest completions

    Given: ?h : Bool  with  x : Int, y : Int in scope

    Suggest:
    - x == y  (uses available Ints, produces Bool)
    - x < y
    - true
    - false
    """
    suggestions = []

    # Check expected type
    if hole.expected_type == TBool():
        suggestions.extend(['true', 'false'])

        # Check for Int comparisons
        int_vars = [v for v, t in hole.environment.items() if t == TInt()]
        if len(int_vars) >= 2:
            suggestions.append(f"{int_vars[0]} == {int_vars[1]}")

    return suggestions

# Example
hole = HoleWithContext("h", TBool(), {'x': TInt(), 'y': TInt()})
print(f"Suggestions for {hole.name}: {type_driven_completion(hole)}")
```

### Pattern 3: Incremental Type Checking

```python
def incremental_type_check(program_with_holes):
    """
    Type check incomplete programs incrementally

    As user fills holes:
    1. Re-check only affected parts
    2. Update hole contexts
    3. Show new goals
    """
    # Initial: type check with holes
    initial_check = typecheck(program_with_holes)

    # User fills one hole
    def on_hole_filled(hole_name, new_expr):
        # Incremental: only re-check dependent parts
        affected = find_dependent_expressions(hole_name)
        for expr in affected:
            recheck(expr)

        # Update other holes' contexts if needed
        propagate_type_information(hole_name, new_expr)

    print("Incremental checking: fast feedback as holes are filled")
```

---

## Quick Reference

### Hole Types

| Concept | Notation | Meaning |
|---------|----------|---------|
| Expression hole | ?h | Unknown expression with expected type |
| Type hole | ?T | Unknown type (gradual typing) |
| Indeterminate | ⊥h | Result of evaluating hole |
| Hole context | Γ | Variables available to hole |

### Typing Rules

```
Hole (checking mode):
  Γ ⊢ ?h ⇐ τ

Hole (synthesis mode):
  Cannot synthesize type for bare hole
  (Need expected type from context)

Type consistency:
  ? ~ τ  for all τ
```

### Evaluation Rules

```
Hole evaluation:
  ?h ⇓ ⊥h  (indeterminate)

Indeterminate propagation:
  e₁ ⇓ ⊥h
  ──────────
  e₁ + e₂ ⇓ ⊥h
```

### Implementation Checklist

- [ ] Represent holes with names and expected types
- [ ] Track hole contexts (available variables)
- [ ] Implement type consistency (~) not just equality
- [ ] Support bidirectional typing (⇒ and ⇐ modes)
- [ ] Handle indeterminate results in evaluation
- [ ] Preserve type safety (progress + preservation)

---

## Anti-Patterns

❌ **Treating holes as runtime errors**: Holes should have static meaning
✅ Use indeterminate results, allow inspection

❌ **Requiring all holes to synthesize types**: Can't always infer
✅ Use bidirectional typing, switch to checking mode

❌ **Ignoring hole contexts**: Can't provide good suggestions
✅ Capture environment, show available variables

❌ **Confusing holes with null/undefined**: Holes are typed!
✅ Holes have expected types, null/undefined are values

---

## Related Skills

- `type-systems.md` - Type checking, gradual typing foundations
- `hazelnut-calculus.md` - Structure editor calculus with holes
- `typed-holes-semantics.md` - Advanced semantics, pattern matching with holes
- `typed-holes-interaction.md` - IDE integration, goal-directed programming
- `curry-howard.md` - Holes in proof contexts
- `dependent-types.md` - Holes in dependently typed languages

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
