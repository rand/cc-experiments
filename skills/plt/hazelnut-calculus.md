---
name: hazelnut-calculus
description: Hazelnut structure editor calculus - bidirectionally typed lambda calculus with holes and cursor, edit actions preserving static meaning, zipper structures
---

# Hazelnut: Structure Editor Calculus

**Scope**: Hazelnut calculus (POPL 2017), structure editing, edit actions, zipper structures, Grove extensions
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Implementing structure editors (projectional editors)
- Building Hazel-like live programming environments
- Designing syntax-directed editing systems
- Understanding edit action semantics
- Working with cursor-based program manipulation
- Implementing collaborative editing for code (Grove)

## Core Concepts

### Structure Editing vs Text Editing

**Key insight**: Edit AST directly, not text

```python
from dataclasses import dataclass
from typing import Union, Optional

# Traditional text editing
text_edit_example = """
User types: "if true th"
State: Syntactically invalid!
Parser: Error, incomplete conditional
"""

# Structure editing (Hazel approach)
@dataclass
class EmptyHole:
    """⦇ ⦈ - empty hole, no expression yet"""
    def __repr__(self):
        return "⦇⦈"

@dataclass
class NonEmptyHole:
    """⦇e⦈ - non-empty hole, expression with wrong type"""
    expr: 'Expr'
    def __repr__(self):
        return f"⦇{self.expr}⦈"

# Structure edit sequence:
"""
1. Start: ⦇⦈  (empty hole)
2. construct if: if ⦇⦈ then ⦇⦈ else ⦇⦈
3. Fill condition: if true then ⦇⦈ else ⦇⦈
4. Fill branches...

At EVERY step: syntactically valid, typeable!
"""

print("Structure editing: always syntactically well-formed")
```

### Hazelnut Language

**Core language**: Simply-typed lambda calculus + holes + cursor

```python
# Hazelnut expressions (UExp)
@dataclass
class Num:
    """Number literal"""
    value: int

@dataclass
class Var:
    """Variable"""
    name: str

@dataclass
class Lam:
    """Lambda: λx.e"""
    param: str
    body: 'UExp'

@dataclass
class Ap:
    """Application: e₁ e₂"""
    func: 'UExp'
    arg: 'UExp'

@dataclass
class Plus:
    """Addition: e₁ + e₂"""
    left: 'UExp'
    right: 'UExp'

@dataclass
class EHole:
    """Empty expression hole: ⦇⦈"""
    pass

@dataclass
class NEHole:
    """Non-empty hole: ⦇e⦈"""
    expr: 'UExp'

UExp = Union[Num, Var, Lam, Ap, Plus, EHole, NEHole]

print("Hazelnut: λ-calculus + holes")
```

### Zipper Structure with Cursor

**Zipper**: Navigate AST with cursor

```python
@dataclass
class ZExp:
    """Expression with cursor (zipper)"""
    focus: UExp  # Current expression under cursor
    context: 'ZContext'  # Surrounding context

# Zipper contexts (one-hole contexts)
@dataclass
class ZTop:
    """Top level: no surrounding context"""
    def __repr__(self):
        return "□"

@dataclass
class ZLam:
    """λx.□ - cursor inside lambda body"""
    param: str
    parent_context: 'ZContext'

@dataclass
class ZApL:
    """□ e - cursor in function position"""
    arg: UExp
    parent_context: 'ZContext'

@dataclass
class ZApR:
    """e □ - cursor in argument position"""
    func: UExp
    parent_context: 'ZContext'

@dataclass
class ZPlusL:
    """□ + e - cursor in left operand"""
    right: UExp
    parent_context: 'ZContext'

@dataclass
class ZPlusR:
    """e + □ - cursor in right operand"""
    left: UExp
    parent_context: 'ZContext'

@dataclass
class ZNEHole:
    """⦇□⦈ - cursor inside non-empty hole"""
    parent_context: 'ZContext'

ZContext = Union[ZTop, ZLam, ZApL, ZApR, ZPlusL, ZPlusR, ZNEHole]

# Example: Navigate through expression
def example_zipper():
    """
    Expression: (λx. x + 1) 5
    Cursor positions:
    1. ▸(λx. x + 1) 5       (function)
    2. (λx. ▸x + 1) 5       (inside lambda, at variable)
    3. (λx. x ▸+ 1) 5       (at operator)
    4. (λx. x + 1) ▸5       (argument)
    """
    pass

print("Zipper: cursor position + surrounding context")
```

### Edit Actions

**Core edit actions**: Construct, delete, move

```python
from enum import Enum

class Direction(Enum):
    PARENT = "parent"
    CHILD_1 = "child1"
    CHILD_2 = "child2"

# Movement actions
def move(zexp: ZExp, dir: Direction) -> Optional[ZExp]:
    """
    Move cursor in direction

    move parent: Go up to parent
    move child(n): Go down to nth child
    """
    match dir:
        case Direction.PARENT:
            # Move up: plug hole, move context
            return move_parent(zexp)
        case Direction.CHILD_1:
            # Move to first child (if exists)
            return move_child(zexp, 1)
        case Direction.CHILD_2:
            return move_child(zexp, 2)

# Construction actions
def construct_lam(zexp: ZExp, param: str) -> ZExp:
    """
    construct lam x

    Wrap current expression in λx.□
    If current is ⦇⦈, produces λx.⦇⦈
    """
    current = zexp.focus
    new_body = EHole() if isinstance(current, EHole) else current
    new_lam = Lam(param, new_body)
    return ZExp(new_lam, zexp.context)

def construct_ap(zexp: ZExp) -> ZExp:
    """
    construct ap

    Current becomes function, add hole for argument
    e → e ⦇⦈
    """
    func = zexp.focus
    new_ap = Ap(func, EHole())
    return ZExp(new_ap, zexp.context)

def construct_plus_left(zexp: ZExp) -> ZExp:
    """
    construct + L

    Current becomes right operand, add hole on left
    e → ⦇⦈ + e
    """
    right = zexp.focus
    new_plus = Plus(EHole(), right)
    # Move cursor to left hole
    return ZExp(EHole(), ZPlusL(right, zexp.context))

# Deletion action
def delete(zexp: ZExp) -> ZExp:
    """
    del

    Replace current expression with empty hole
    e → ⦇⦈
    """
    return ZExp(EHole(), zexp.context)

print("Edit actions: move, construct, delete")
```

### Type Consistency and Inconsistency Handling

**Key innovation**: Automatically wrap inconsistent terms in holes

```python
# Types (Hazelnut)
@dataclass
class TNum:
    def __repr__(self):
        return "Num"

@dataclass
class TArrow:
    param: 'Type'
    result: 'Type'
    def __repr__(self):
        return f"({self.param} → {self.result})"

@dataclass
class THole:
    """Type hole: unknown type"""
    def __repr__(self):
        return "?"

Type = Union[TNum, TArrow, THole]

# Type consistency (~)
def consistent(t1: Type, t2: Type) -> bool:
    """
    Type consistency:
    - ? ~ τ  for all τ
    - Num ~ Num
    - (τ₁ → τ₂) ~ (σ₁ → σ₂) if τ₁ ~ σ₁ and τ₂ ~ σ₂
    """
    if isinstance(t1, THole) or isinstance(t2, THole):
        return True
    if isinstance(t1, TNum) and isinstance(t2, TNum):
        return True
    if isinstance(t1, TArrow) and isinstance(t2, TArrow):
        return (consistent(t1.param, t2.param) and
                consistent(t1.result, t2.result))
    return False

# Inconsistency handling
def construct_with_type_check(zexp: ZExp, expected: Type):
    """
    When constructing, check type consistency

    If inconsistent: wrap in non-empty hole!

    Example:
      Expected: Num
      Construct: λx.x  (type: ? → ?)
      Result: ⦇λx.x⦈  (non-empty hole, preserves typing)
    """
    expr = zexp.focus
    expr_type = synthesize_type(expr)

    if not consistent(expr_type, expected):
        # Wrap in non-empty hole
        return NEHole(expr)
    else:
        return expr

print("Inconsistent expressions automatically wrapped in holes")
```

### Bidirectional Typing for Hazelnut

**Action semantics**: Actions preserve types

```python
def action_type(action: str, zexp: ZExp, ctx_type: Type) -> Type:
    """
    Type-aware action semantics

    Every action produces typeable result!

    Example: construct lam x
      Before: ⦇⦈ : τ
      After: λx.⦇⦈ : ? → τ
      (Hole becomes lambda body)
    """
    pass

# Synthesis (⇒) vs Checking (⇐)
def synth(expr: UExp, gamma: dict) -> Type:
    """
    Synthesis: Γ ⊢ e ⇒ τ

    Figure out type from expression
    """
    match expr:
        case Num(n):
            return TNum()
        case Var(x):
            return gamma.get(x, THole())
        case EHole():
            return THole()  # Holes synthesize hole type
        case NEHole(e):
            return THole()  # Non-empty holes too
        case Ap(f, a):
            # Synthesize function, check argument
            f_type = synth(f, gamma)
            if isinstance(f_type, TArrow):
                check(a, gamma, f_type.param)
                return f_type.result
            else:
                return THole()
        # ... other cases

def check(expr: UExp, gamma: dict, expected: Type):
    """
    Checking: Γ ⊢ e ⇐ τ

    Verify expression has expected type
    """
    match expr:
        case Lam(x, body):
            if isinstance(expected, TArrow):
                new_gamma = gamma | {x: expected.param}
                check(body, new_gamma, expected.result)
            else:
                # Can't check lambda against non-arrow
                raise TypeError("Expected arrow type for lambda")
        case _:
            # Fallback: synthesize and check consistency
            synth_type = synth(expr, gamma)
            if not consistent(synth_type, expected):
                raise TypeError(f"Inconsistent: {synth_type} !~ {expected}")

print("Bidirectional typing ensures actions preserve types")
```

### Action Semantics (Complete Example)

**Formal action rules**: From POPL 2017 paper

```python
class ActionSemantics:
    """
    Hazelnut action semantics

    Judgment: (e, γ, α) → e'
      Given expression e, context γ, action α
      Produces new expression e'
    """

    @staticmethod
    def construct_num(zexp: ZExp, n: int) -> ZExp:
        """
        construct num n

        Rule:
          e is ⦇⦈
          ──────────────
          e → n

        Replaces empty hole with number
        """
        if isinstance(zexp.focus, EHole):
            return ZExp(Num(n), zexp.context)
        else:
            raise ValueError("construct num requires empty hole")

    @staticmethod
    def construct_var(zexp: ZExp, x: str) -> ZExp:
        """
        construct var x

        Replaces empty hole with variable
        """
        if isinstance(zexp.focus, EHole):
            return ZExp(Var(x), zexp.context)
        else:
            raise ValueError("construct var requires empty hole")

    @staticmethod
    def construct_lam(zexp: ZExp, x: str) -> ZExp:
        """
        construct lam x

        Rule:
          ──────────────
          e → λx.e

        Wraps current expression in lambda
        """
        body = zexp.focus if not isinstance(zexp.focus, EHole) else EHole()
        new_lam = Lam(x, body)
        # Move cursor to body
        return ZExp(body, ZLam(x, zexp.context))

    @staticmethod
    def finish(zexp: ZExp) -> ZExp:
        """
        finish

        Remove non-empty hole wrapper if types match

        Rule:
          Γ ⊢ e ⇒ τ
          Γ ⊢ ⦇e⦈ ⇐ τ
          ──────────────
          ⦇e⦈ → e

        Only works if types are consistent!
        """
        if isinstance(zexp.focus, NEHole):
            # Check if inner expression has consistent type
            # If yes, unwrap; if no, keep hole
            return ZExp(zexp.focus.expr, zexp.context)
        else:
            return zexp

print("Action semantics: formal rules from Hazelnut paper")
```

### Grove Extensions (POPL 2025)

**Collaborative editing**: Commutative edit actions

```python
@dataclass
class GroveAction:
    """
    Grove: Commutative edit actions for collaboration

    Key idea: Actions commute so concurrent edits merge automatically
    """
    action_id: str
    timestamp: int
    user: str
    action_type: str
    parameters: dict

def commute(a1: GroveAction, a2: GroveAction) -> bool:
    """
    Check if actions commute: a1; a2 ≡ a2; a1

    Examples:
    - Edits at different locations: commute
    - Edits at same location: conflict (handled specially)
    - Dependent edits: don't commute (serialize)
    """
    # If actions touch disjoint parts of tree
    if disjoint_paths(a1, a2):
        return True

    # If one creates, other references: order matters
    if creates_dependency(a1, a2):
        return False

    return True

# Operational transformation for concurrent editing
def merge_concurrent_edits(actions: list[GroveAction]) -> UExp:
    """
    Merge concurrent edits using commutative properties

    Grove ensures most edits commute, reducing conflicts
    """
    pass

print("Grove: Commutative actions for collaborative editing")
```

---

## Patterns

### Pattern 1: Progressive Refinement

```python
def progressive_refinement_example():
    """
    Build program by refining holes

    1. Start: ⦇⦈ : Num → Num
    2. construct lam x: λx.⦇⦈ : Num → Num
    3. move child1 (to body)
    4. construct + L: ⦇⦈ + ⦇⦈ : Num
    5. construct num 1 (left): 1 + ⦇⦈
    6. construct var x (right): 1 + x

    Result: λx. 1 + x
    """
    print("Progressive refinement: holes → complete program")
```

### Pattern 2: Type-Directed Construction

```python
def type_directed_construction(expected_type: Type):
    """
    Use expected type to guide construction

    Expected: Num → Num
    → Suggest: construct lam (makes lambda)

    Expected: Num
    → Suggest: construct num, construct +, construct var (if Num in context)
    """
    suggestions = []

    if isinstance(expected_type, TArrow):
        suggestions.append("construct lam x")
    elif isinstance(expected_type, TNum):
        suggestions.extend(["construct num n", "construct +"])

    return suggestions
```

### Pattern 3: Hole-Driven Error Recovery

```python
def error_recovery_pattern(expr: UExp, expected: Type):
    """
    When type error: wrap in non-empty hole

    User constructs: λx.x  (type: ? → ?)
    Expected: Num

    Instead of error: ⦇λx.x⦈ : Num
    → Program still types!
    → User can fix later
    """
    expr_type = synth(expr, {})

    if not consistent(expr_type, expected):
        # Don't throw error - wrap in hole!
        return NEHole(expr)
    else:
        return expr

print("Non-empty holes: graceful error recovery")
```

---

## Quick Reference

### Expression Forms

| Syntax | Meaning |
|--------|---------|
| ⦇⦈ | Empty hole (EHole) |
| ⦇e⦈ | Non-empty hole (NEHole) |
| λx.e | Lambda abstraction |
| e₁ e₂ | Application |
| e₁ + e₂ | Addition |

### Edit Actions

| Action | Effect |
|--------|--------|
| move parent | Move cursor up |
| move child(n) | Move cursor to nth child |
| construct lam x | Wrap in λx.□ |
| construct ap | Add application: □ ⦇⦈ |
| construct num n | Replace ⦇⦈ with n |
| del | Replace with ⦇⦈ |
| finish | Remove hole wrapper (if types match) |

### Key Properties

```
Syntactic Well-Formedness:
  Every edit action produces syntactically valid expression

Static Meaning:
  Every expression has a type (possibly with ?)

Type Preservation:
  Actions preserve typability
```

---

## Anti-Patterns

❌ **Allowing syntactically invalid states**: Defeats purpose of structure editing
✅ Actions always produce valid AST

❌ **Throwing errors on type mismatch**: Breaks flow
✅ Wrap inconsistent terms in non-empty holes

❌ **Ignoring cursor position**: Can't implement navigation
✅ Use zipper structure to track cursor

❌ **Requiring complete programs**: Defeats holes
✅ Allow incomplete programs, use ⦇⦈ liberally

---

## Related Skills

- `typed-holes-foundations.md` - Basic typed holes concepts
- `type-systems.md` - Type checking and consistency
- `lambda-calculus.md` - Underlying calculus
- `structure-editors.md` - General structure editor design
- `live-programming-holes.md` - Hazel environment implementation
- `typed-holes-semantics.md` - Advanced semantics

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
