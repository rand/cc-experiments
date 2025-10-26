---
name: curry-howard
description: Curry-Howard correspondence relating proofs and programs, propositions and types
---

# Curry-Howard Correspondence

**Scope**: Propositions as types, proofs as programs, logical connectives as type constructors
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding connection between logic and programming
- Working with proof assistants (Lean, Coq, Agda)
- Extracting programs from constructive proofs
- Designing type systems with logical foundations
- Proving program properties via types
- Studying intuitionistic logic and type theory

## Core Concepts

### The Correspondence

**Curry-Howard Isomorphism**: Deep connection between:
- Propositions ↔ Types
- Proofs ↔ Programs
- Proof normalization ↔ Program evaluation

| Logic | Type Theory | Programming |
|-------|-------------|-------------|
| Proposition P | Type P | Type P |
| Proof of P | Term of type P | Value of type P |
| P → Q | Function type P → Q | Function from P to Q |
| P ∧ Q | Product type P × Q | Pair (p, q) |
| P ∨ Q | Sum type P + Q | Either left(p) or right(q) |
| ⊤ (true) | Unit type 1 | () |
| ⊥ (false) | Empty type 0 | No values |
| ¬P | P → ⊥ | Function from P to absurdity |
| ∀x. P(x) | Π(x:A). P(x) | Dependent function |
| ∃x. P(x) | Σ(x:A). P(x) | Dependent pair |

```python
from dataclasses import dataclass
from typing import Union

# Propositions as types
@dataclass
class Implies:
    """P → Q"""
    premise: 'Prop'
    conclusion: 'Prop'
    
    def __repr__(self):
        return f"({self.premise} → {self.conclusion})"

@dataclass
class And:
    """P ∧ Q"""
    left: 'Prop'
    right: 'Prop'
    
    def __repr__(self):
        return f"({self.left} ∧ {self.right})"

@dataclass
class Or:
    """P ∨ Q"""
    left: 'Prop'
    right: 'Prop'
    
    def __repr__(self):
        return f"({self.left} ∨ {self.right})"

@dataclass
class Not:
    """¬P ≡ P → ⊥"""
    prop: 'Prop'
    
    def __repr__(self):
        return f"¬{self.prop}"

@dataclass
class True_:
    """⊤"""
    def __repr__(self):
        return "⊤"

@dataclass
class False_:
    """⊥"""
    def __repr__(self):
        return "⊥"

Prop = Union[Implies, And, Or, Not, True_, False_]

# Proofs as programs
@dataclass
class Lambda:
    """λx. M - proof of P → Q"""
    var: str
    body: 'Proof'

@dataclass
class Pair:
    """(M, N) - proof of P ∧ Q"""
    fst: 'Proof'
    snd: 'Proof'

@dataclass
class Inl:
    """inl(M) - proof of P ∨ Q (left)"""
    proof: 'Proof'

@dataclass
class Inr:
    """inr(N) - proof of P ∨ Q (right)"""
    proof: 'Proof'

@dataclass
class Unit:
    """() - proof of ⊤"""
    pass

Proof = Union[Lambda, Pair, Inl, Inr, Unit]

print("Proposition P → Q corresponds to function type P → Q")
print("Proof of P → Q is a function taking proof of P to proof of Q")
```

### Logical Connectives as Types

**Implication (→)**:

```python
# P → Q corresponds to function type P → Q
# Proof: λx:P. M : Q (function taking P to Q)

# Example: Prove A → A (identity)
# Proof: λx. x

# In Lean 4:
"""
theorem id (A : Prop) : A → A := fun x => x

-- Or with tactics:
theorem id' (A : Prop) : A → A := by
  intro x
  exact x
"""

def prove_implication_id():
    """A → A: identity function"""
    return Lambda('x', Variable('x'))

print("Proof of A → A is the identity function: λx. x")
```

**Conjunction (∧)**:

```python
# P ∧ Q corresponds to product type P × Q
# Proof: (M, N) where M : P, N : Q

# Example: Prove (A ∧ B) → (B ∧ A) (commutativity)
# Proof: λp. (snd p, fst p)

# In Lean 4:
"""
theorem and_comm (A B : Prop) : A ∧ B → B ∧ A := by
  intro ⟨a, b⟩
  exact ⟨b, a⟩

-- Equivalent:
theorem and_comm' (A B : Prop) : A ∧ B → B ∧ A :=
  fun ⟨a, b⟩ => ⟨b, a⟩
"""

def prove_and_comm():
    """(A ∧ B) → (B ∧ A)"""
    return Lambda('p', Pair(Project2(Variable('p')), Project1(Variable('p'))))

print("Proof of (A ∧ B) → (B ∧ A) swaps pair components")
```

**Disjunction (∨)**:

```python
# P ∨ Q corresponds to sum type P + Q
# Proof: inl(M) : P ∨ Q or inr(N) : P ∨ Q

# Example: Prove A → (A ∨ B)
# Proof: λx. inl(x)

# In Lean 4:
"""
theorem or_intro_left (A B : Prop) : A → A ∨ B := by
  intro a
  left
  exact a

-- Equivalent:
theorem or_intro_left' (A B : Prop) : A → A ∨ B :=
  fun a => Or.inl a
"""

def prove_or_intro_left():
    """A → (A ∨ B)"""
    return Lambda('x', Inl(Variable('x')))

print("Proof of A → (A ∨ B) injects A into left side")
```

**Negation (¬)**:

```python
# ¬P ≡ P → ⊥
# Proof of ¬P is a function from P to absurdity

# Example: Prove ¬(A ∧ ¬A) (non-contradiction)
# Proof: λp. (snd p) (fst p)

# In Lean 4:
"""
theorem not_and_not (A : Prop) : ¬(A ∧ ¬A) := by
  intro ⟨a, na⟩
  exact na a

-- Equivalent:
theorem not_and_not' (A : Prop) : ¬(A ∧ ¬A) :=
  fun ⟨a, na⟩ => na a
"""

def prove_non_contradiction():
    """¬(A ∧ ¬A)"""
    # (A ∧ ¬A) → ⊥
    # λp. (snd p) (fst p)  [where snd p : A → ⊥, fst p : A]
    return Lambda('p', Apply(Project2(Variable('p')), Project1(Variable('p'))))

print("Proof of ¬(A ∧ ¬A): apply ¬A to A to get ⊥")
```

### Proof Extraction

**Extracting programs from proofs**:

```python
# Lean 4 example: Extracting program from constructive proof
"""
-- Prove: ∃(x:Nat). x > 0
theorem exists_positive : ∃(x:Nat), x > 0 := by
  use 1
  norm_num

-- Extract witness:
#eval (exists_positive.choose : Nat)  -- 1

-- Extracting a sorting function from proof of sorting correctness:
def sort (xs : List Nat) : {ys : List Nat // Sorted ys ∧ Permutation xs ys} := ...

-- Type ensures:
-- 1. Result is sorted
-- 2. Result is permutation of input
-- Program AND proof in one!
"""

print("Proofs in constructive logic contain computational content")
print("Can extract programs from proofs")
```

### Classical vs Intuitionistic Logic

**Law of Excluded Middle (LEM)**: P ∨ ¬P

```python
# LEM is NOT provable in intuitionistic logic
# Cannot construct P ∨ ¬P without knowing which one holds

# In classical logic (Lean with Classical axiom):
"""
open Classical

theorem lem (P : Prop) : P ∨ ¬P := em P

-- Non-constructive proof by contradiction:
theorem sqrt_2_irrational : Irrational (√2) := by
  by_contra h
  -- Assume √2 is rational, derive contradiction
  ...
"""

# In intuitionistic logic:
"""
-- Can only prove double negation of LEM:
theorem not_not_lem (P : Prop) : ¬¬(P ∨ ¬P) := by
  intro h
  apply h
  right
  intro p
  apply h
  left
  exact p
"""

print("Classical logic: P ∨ ¬P always holds")
print("Intuitionistic logic: Need explicit construction of P or ¬P")
```

### Quantifiers

**Universal quantification (∀)**:

```python
# ∀(x:A). P(x) corresponds to Π(x:A). P(x)
# Proof: function from x to proof of P(x)

# Example: Prove ∀(n:Nat). n = n
# Proof: λn. refl

# In Lean 4:
"""
theorem forall_eq (n : Nat) : n = n := rfl

-- Explicitly as ∀:
theorem forall_eq' : ∀(n : Nat), n = n := fun n => rfl
"""

print("Proof of ∀(n:Nat). P(n) is a function λn. proof of P(n)")
```

**Existential quantification (∃)**:

```python
# ∃(x:A). P(x) corresponds to Σ(x:A). P(x)
# Proof: pair (witness, proof that witness satisfies P)

# Example: Prove ∃(n:Nat). n > 5
# Proof: (6, proof that 6 > 5)

# In Lean 4:
"""
theorem exists_gt_5 : ∃(n : Nat), n > 5 := by
  use 6
  norm_num

-- Equivalent:
theorem exists_gt_5' : ∃(n : Nat), n > 5 :=
  ⟨6, by norm_num⟩
"""

print("Proof of ∃(n:Nat). P(n) is a pair: (witness, proof P(witness))")
```

---

## Patterns

### Pattern 1: Modus Ponens

```lean
-- Lean 4
theorem modus_ponens (P Q : Prop) : (P → Q) → P → Q :=
  fun f p => f p

-- Program: function application!
```

### Pattern 2: Curry/Uncurry

```lean
-- Lean 4
theorem curry (A B C : Prop) : ((A ∧ B) → C) → (A → B → C) :=
  fun f a b => f ⟨a, b⟩

theorem uncurry (A B C : Prop) : (A → B → C) → ((A ∧ B) → C) :=
  fun f ⟨a, b⟩ => f a b
```

### Pattern 3: De Morgan's Laws

```lean
-- Lean 4
-- Intuitionistically valid:
theorem de_morgan_1 (A B : Prop) : ¬(A ∨ B) → ¬A ∧ ¬B := by
  intro h
  constructor
  · intro a; apply h; left; exact a
  · intro b; apply h; right; exact b

-- Requires classical logic:
theorem de_morgan_2 (A B : Prop) : ¬A ∧ ¬B → ¬(A ∨ B) := by
  intro ⟨na, nb⟩ h
  cases h with
  | inl a => exact na a
  | inr b => exact nb b
```

---

## Quick Reference

### Correspondence Table

| Logic | Type | Proof Term |
|-------|------|------------|
| P → Q | P → Q | λx:P. M |
| P ∧ Q | P × Q | (M, N) |
| P ∨ Q | P + Q | inl(M) \| inr(N) |
| ⊤ | Unit | () |
| ⊥ | Empty | (no terms) |
| ¬P | P → ⊥ | λx:P. absurd |
| ∀x. P(x) | Π(x:A). P(x) | λx. M |
| ∃x. P(x) | Σ(x:A). P(x) | (a, M) |

### Proof Tactics (Lean 4)

```lean
intro      -- Introduce hypothesis (λ)
exact      -- Provide exact proof
constructor -- Build ∧ or ∃
left/right -- Build ∨
cases      -- Case split on ∨ or ∃
apply      -- Function application
```

---

## Anti-Patterns

❌ **Using classical logic unnecessarily**: LEM makes proofs non-constructive
✅ Prefer constructive proofs when possible (extract programs)

❌ **Confusing provability and truth**: ¬¬P doesn't imply P intuitionistically
✅ Understand difference between classical and intuitionistic logic

❌ **Ignoring computational content**: Proofs are programs!
✅ Exploit Curry-Howard to extract verified programs

---

## Related Skills

- `lambda-calculus.md` - Untyped foundation
- `type-systems.md` - Typed λ-calculus
- `dependent-types.md` - Dependent functions (∀) and pairs (∃)
- `formal/lean-proof-basics.md` - Practical proof development
- `program-verification.md` - Using proofs to verify programs

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
