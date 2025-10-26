---
name: dependent-types
description: Dependent types including Π-types, Σ-types, indexed families, and proof assistants
---

# Dependent Types

**Scope**: Π-types, Σ-types, indexed families, equality types, proof assistants (Lean, Coq, Agda)
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Implementing proof assistants or verified compilers
- Working with Lean 4, Coq, Agda, or Idris
- Encoding invariants in types (length-indexed vectors)
- Proving program correctness via dependent types
- Understanding Curry-Howard correspondence at type level
- Designing expressive type systems for DSLs

## Core Concepts

### Dependent Function Types (Π-types)

**Π-type**: Π(x:A). B(x) - function type where result type depends on argument value

**Examples**:
- Vector of length n: `Vec A n`
- `replicate : Π(n:Nat). A → Vec A n`

```python
from dataclasses import dataclass
from typing import Union, Callable

# Dependent types representation (simplified)
@dataclass
class Pi:
    """Π(x:A). B(x) - dependent function type"""
    param_name: str
    param_type: 'Type'
    result_type: Callable  # Function from value to type
    
    def __repr__(self):
        return f"Π({self.param_name}:{self.param_type}). ..."

@dataclass
class Nat:
    """Natural number type"""
    def __repr__(self):
        return "Nat"

@dataclass
class Vec:
    """Length-indexed vector: Vec A n"""
    elem_type: 'Type'
    length: int
    
    def __repr__(self):
        return f"Vec {self.elem_type} {self.length}"

Type = Union[Nat, Vec, Pi]

# Example: replicate : Π(n:Nat). A → Vec A n
def replicate_type(A):
    """Type of replicate function"""
    return Pi('n', Nat(), lambda n: FunctionType(A, Vec(A, n)))

# In Lean 4:
"""
def replicate {α : Type} (n : Nat) (x : α) : Vector α n :=
  match n with
  | 0 => []
  | n+1 => x :: replicate n x
"""

print("replicate : Π(n:Nat). A → Vec A n")
```

### Dependent Pair Types (Σ-types)

**Σ-type**: Σ(x:A). B(x) - pair where second component's type depends on first

**Examples**:
- Existential types: ∃(n:Nat). Vec A n (vector with unknown length)
- Refinement types: {x:Int | x > 0} ≅ Σ(x:Int). (x > 0)

```python
@dataclass
class Sigma:
    """Σ(x:A). B(x) - dependent pair type"""
    param_name: str
    param_type: Type
    result_type: Callable  # Function from value to type
    
    def __repr__(self):
        return f"Σ({self.param_name}:{self.param_type}). ..."

@dataclass
class Pair:
    """Dependent pair value: (a, b) : Σ(x:A). B(x)"""
    fst: any
    snd: any

# Example: existential vector (vector with hidden length)
def existential_vector(A):
    """Σ(n:Nat). Vec A n"""
    return Sigma('n', Nat(), lambda n: Vec(A, n))

# In Lean 4:
"""
structure ExVec (α : Type) where
  length : Nat
  data : Vector α length

-- Example
def myVec : ExVec Int := ⟨3, [1, 2, 3]⟩
"""

print("ExVec A ≅ Σ(n:Nat). Vec A n")
```

### Indexed Families

**Indexed family**: Family of types indexed by values

```python
# Length-indexed vectors in Python (conceptual)
class Vector:
    """Vec A n - vector of length n"""
    def __init__(self, elem_type, length, elements):
        self.elem_type = elem_type
        self.length = length
        self.elements = elements
        assert len(elements) == length
    
    def __repr__(self):
        return f"Vec {self.elem_type} {self.length} {self.elements}"

# Operations preserving length
def vmap(f, vec):
    """map : (A → B) → Vec A n → Vec B n"""
    return Vector(
        elem_type='B',
        length=vec.length,
        elements=[f(x) for x in vec.elements]
    )

def vappend(vec1, vec2):
    """append : Vec A m → Vec A n → Vec A (m+n)"""
    return Vector(
        elem_type=vec1.elem_type,
        length=vec1.length + vec2.length,
        elements=vec1.elements + vec2.elements
    )

# Example
v1 = Vector('Int', 3, [1, 2, 3])
v2 = Vector('Int', 2, [4, 5])
v3 = vappend(v1, v2)
print(f"{v1} ++ {v2} = {v3}")  # Vec Int 5 [1,2,3,4,5]

# In Lean 4:
"""
def Vector.append {α : Type} {m n : Nat} : Vector α m → Vector α n → Vector α (m + n)
  | [], ys => ys
  | x :: xs, ys => x :: xs.append ys
"""
```

### Equality Types

**Identity type**: a =_A b (proof that a equals b in type A)

```python
@dataclass
class Eq:
    """Equality type: a =_A b"""
    type_: Type
    lhs: any
    rhs: any
    
    def __repr__(self):
        return f"{self.lhs} =_{self.type_} {self.rhs}"

@dataclass
class Refl:
    """Reflexivity: refl : a =_A a"""
    value: any
    
    def __repr__(self):
        return f"refl {self.value}"

# Leibniz's law: if a = b, then P(a) → P(b)
def leibniz_subst(eq_proof, P, pa):
    """
    subst : a =_A b → P(a) → P(b)
    Transport along equality
    """
    match eq_proof:
        case Refl(a):
            # a = a, so P(a) = P(a)
            return pa
        # In practice, need full pattern matching on equality proofs

# In Lean 4:
"""
theorem leibniz_subst {α : Type} {a b : α} (h : a = b) (P : α → Prop) : P a → P b := by
  rw [h]
"""

print("Equality allows transporting proofs along equalities")
```

### Universe Levels

**Type hierarchy**: Type₀ : Type₁ : Type₂ : ...

```python
@dataclass
class Universe:
    """Type_i - universe at level i"""
    level: int
    
    def __repr__(self):
        return f"Type_{self.level}"

# Examples:
# Nat : Type₀
# Type₀ : Type₁
# Vec : Type₀ → Nat → Type₀
# List : Type₀ → Type₀

# In Lean 4:
"""
#check Nat        -- Nat : Type
#check Type       -- Type : Type 1
#check Type 1     -- Type 1 : Type 2

universe u v
def MyVec (α : Type u) (n : Nat) : Type u := ...
"""

print("Universes prevent Russell's paradox: Type : Type is inconsistent")
```

### Dependent Pattern Matching

**Match with dependent types**: Result type depends on matched value

```python
# Example: head function for non-empty vectors
def vec_head(vec):
    """
    head : Π{n:Nat}. Vec A (n+1) → A
    Only defined for non-empty vectors (n ≥ 1)
    """
    if vec.length == 0:
        raise ValueError("Cannot take head of empty vector")
    return vec.elements[0]

# In Lean 4:
"""
def Vector.head {α : Type} {n : Nat} : Vector α (n+1) → α
  | x :: _ => x

-- Pattern matching refines type:
-- Matching on `n+1` in index tells Lean vector is non-empty
"""

# Example: safe division (result type depends on divisor ≠ 0)
def safe_div(a, b):
    """
    div : (a : Int) → (b : Int) → {b ≠ 0} → Int
    Requires proof that b ≠ 0
    """
    if b == 0:
        raise ValueError("Division by zero")
    return a // b

# In Lean 4:
"""
def safeDiv (a b : Int) (h : b ≠ 0) : Int := a / b

-- Usage requires proof:
example : Int := safeDiv 10 2 (by norm_num)  -- OK
example : Int := safeDiv 10 0 ?_             -- Error: need proof 0 ≠ 0
"""

print("Dependent pattern matching enables type-safe operations")
```

---

## Patterns

### Pattern 1: Vectors with Length

```lean
-- Lean 4
inductive Vector (α : Type u) : Nat → Type u where
  | nil : Vector α 0
  | cons (x : α) {n : Nat} (xs : Vector α n) : Vector α (n+1)

def Vector.append {α : Type} {m n : Nat} : Vector α m → Vector α n → Vector α (m+n)
  | nil, ys => ys
  | cons x xs, ys => cons x (xs.append ys)

-- Type ensures length correctness at compile time
```

### Pattern 2: Dependent Records

```lean
-- Lean 4
structure Matrix (α : Type) (rows cols : Nat) where
  data : Vector (Vector α cols) rows

def Matrix.multiply {α : Type} [Mul α] [Add α] [Zero α] 
    {m n p : Nat} : Matrix α m n → Matrix α n p → Matrix α m p := ...

-- Matrix multiplication type: (m×n) · (n×p) = (m×p)
-- Dimension checking at type level!
```

### Pattern 3: Proofs as Indices

```lean
-- Lean 4
def lookup {α : Type} (vec : Vector α n) (i : Nat) (h : i < n) : α := ...

-- h : i < n is a proof that i is valid index
-- Eliminates runtime bounds checks!

example : Nat := lookup ⟨3, [1, 2, 3]⟩ 1 (by norm_num)  -- OK: 1 < 3
example : Nat := lookup ⟨3, [1, 2, 3]⟩ 5 (by norm_num)  -- Error: can't prove 5 < 3
```

---

## Quick Reference

### Dependent Types Hierarchy

```
Π-type (dependent function):
  Simple function: A → B
  Dependent function: Π(x:A). B(x)
  Polymorphic: ∀(A:Type). ...

Σ-type (dependent pair):
  Simple pair: A × B
  Dependent pair: Σ(x:A). B(x)
  Existential: ∃(x:A). P(x)
```

### Lean 4 Syntax

```lean
-- Π-type
def foo (n : Nat) : Vector Bool n := ...
-- Equivalent to: foo : Π(n:Nat). Vector Bool n

-- Σ-type
structure Sigma (α : Type u) (β : α → Type v) where
  fst : α
  snd : β fst

-- Equality type
example (a b : Nat) (h : a = b) : b = a := h.symm
```

### Common Indexed Families

| Family | Index | Example |
|--------|-------|---------|
| Vector | Nat (length) | Vector α n |
| Matrix | Nat × Nat (dimensions) | Matrix α m n |
| Fin | Nat (bound) | Fin n (numbers < n) |
| Eq | Values | a = b |

---

## Anti-Patterns

❌ **Overusing dependent types**: Not every function needs dependent types
✅ Use when invariants are critical (safety) or improve ergonomics

❌ **Confusing Π and ∀**: Π is dependent function, ∀ is logical quantifier (though related)
✅ In Lean: `∀(x:A). P(x)` is `Π(x:A). P(x)` where P(x) : Prop

❌ **Ignoring universe levels**: Can cause inconsistency
✅ Use universe polymorphism: `def foo {α : Type u} ...`

❌ **Fighting the type checker**: Complex dependent types can be hard to work with
✅ Use tactics and automation (Lean's `simp`, `omega`, etc.)

---

## Related Skills

- `lambda-calculus.md` - Foundation for dependent λ-calculus
- `type-systems.md` - Simpler type systems (System F, HM)
- `curry-howard.md` - Proofs as programs via dependent types
- `formal/lean-proof-basics.md` - Practical dependent type proving in Lean
- `program-verification.md` - Using dependent types for verification

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
