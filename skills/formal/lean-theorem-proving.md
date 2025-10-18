---
name: formal-lean-theorem-proving
description: Formalizing complex mathematics
---


# Lean 4 Theorem Proving

## Overview
Advanced formalization strategies, proof patterns, and architectural techniques for complex mathematical theorem proving and formal verification in Lean 4.

## Scope
**Included:**
- Inductive type design
- Well-founded recursion and termination
- Quotient types and setoids
- Proof by reflection
- Automation strategies
- Proof refactoring patterns
- Large-scale formalization architecture
- Abstraction and generalization techniques
- Computational reflection
- Tactic programming basics

**Excluded:**
- Basic proof tactics (see `lean-proof-basics.md`)
- Standard tactic library (see `lean-tactics.md`)
- mathlib4 library usage (see `lean-mathlib4.md`)
- Full metaprogramming (separate advanced skill)

## When to Use This Skill
**Primary use cases:**
- Formalizing complex mathematics
- Designing custom inductive types
- Proving termination of recursive functions
- Building proof automation for domain
- Refactoring large proof developments
- Research-level formalization
- Verified software development

**Indicators you need this:**
- "How do I formalize this mathematical concept?"
- "How do I prove termination of this recursion?"
- "How do I automate these repetitive proofs?"
- "How do I structure a large formalization?"
- "How do I use quotient types?"

**When to use other skills instead:**
- Learning basics → `lean-proof-basics.md`
- Standard tactics → `lean-tactics.md`
- Library search → `lean-mathlib4.md`

## Prerequisites
**Required knowledge:**
- Lean 4 fundamentals (`lean-proof-basics.md`)
- Advanced tactics (`lean-tactics.md`)
- Type theory basics (dependent types, universe levels)
- Mathematical maturity

**Required setup:**
```bash
# Lean 4 with mathlib4
lake +leanprover/lean4:nightly-2024-01-15 new my_formalization math
cd my_formalization
lake exe cache get
lake build
```

## Core Concepts

### 1. Inductive Types
Foundation of Lean's logic and data structures.

```lean
-- Simple inductive type
inductive MyNat where
  | zero : MyNat
  | succ : MyNat → MyNat

-- Indexed inductive type (dependent)
inductive Vec (α : Type u) : Nat → Type u where
  | nil : Vec α 0
  | cons : α → Vec α n → Vec α (n + 1)

-- Mutually inductive types
mutual
  inductive Even : Nat → Prop where
    | zero : Even 0
    | succ_odd : Odd n → Even (n + 1)

  inductive Odd : Nat → Prop where
    | succ_even : Even n → Odd (n + 1)
end

-- Inductive predicates
inductive Le : Nat → Nat → Prop where
  | refl : Le n n
  | step : Le n m → Le n (m + 1)
```

### 2. Well-Founded Recursion
Proving termination for complex recursive functions.

```lean
-- Well-founded relation
def sizeOf_list {α : Type} : List α → Nat
  | [] => 0
  | _::xs => 1 + sizeOf_list xs

-- Structural recursion (automatic termination)
def length {α : Type} : List α → Nat
  | [] => 0
  | _::xs => 1 + length xs

-- Well-founded recursion with custom measure
def ackermann (m n : Nat) : Nat :=
  match m, n with
  | 0, n => n + 1
  | m+1, 0 => ackermann m 1
  | m+1, n+1 => ackermann m (ackermann (m+1) n)
termination_by (m, n)  -- Lexicographic ordering

-- Custom well-founded relation
def div2 (n : Nat) : Nat :=
  if h : n < 2 then 0
  else 1 + div2 (n - 2)
termination_by n
decreasing_by simp_wf; omega
```

### 3. Quotient Types
Formal quotients by equivalence relations.

```lean
-- Define equivalence relation
def IntEqv : (Nat × Nat) → (Nat × Nat) → Prop :=
  fun (a, b) (c, d) => a + d = b + c

-- Prove it's an equivalence
instance : Setoid (Nat × Nat) where
  r := IntEqv
  iseqv := {
    refl := fun (a, b) => rfl
    symm := fun h => h.symm
    trans := fun h1 h2 => by
      simp [IntEqv] at *
      omega
  }

-- Define quotient
def MyInt : Type := Quotient (inferInstanceAs (Setoid (Nat × Nat)))

-- Lift operations
def MyInt.add : MyInt → MyInt → MyInt :=
  Quotient.lift₂
    (fun (a, b) (c, d) => Quotient.mk _ (a + c, b + d))
    (by
      intro (a, b) (a', b') (c, d) (c', d') hab hcd
      apply Quotient.sound
      simp [IntEqv] at *
      omega)
```

### 4. Proof by Reflection
Prove properties by computation.

```lean
-- Decidable propositions via computation
def isEven (n : Nat) : Bool :=
  n % 2 == 0

-- Reflect to proposition
theorem even_4 : isEven 4 = true := rfl

-- General reflection pattern
theorem even_iff_mod_eq_zero (n : Nat) :
    isEven n = true ↔ n % 2 = 0 := by
  simp [isEven]
  cases Nat.decEq (n % 2) 0 <;> simp [*]

-- Use reflection for automation
theorem even_100 : 100 % 2 = 0 := by
  have : isEven 100 = true := rfl
  exact (even_iff_mod_eq_zero 100).mp this
```

## Advanced Patterns

### Pattern 1: Custom Inductive Predicates
```lean
-- Define accessibility predicate
inductive Acc {α : Type} (r : α → α → Prop) : α → Prop where
  | intro : (∀ y, r y x → Acc r y) → Acc r x

-- Prove well-foundedness
theorem natLt_wf : WellFounded (· < · : Nat → Nat → Prop) :=
  ⟨fun n => by
    induction n with
    | zero =>
      constructor
      intro y h
      omega
    | succ n ih =>
      constructor
      intro y h
      cases Nat.lt_or_eq_of_le (Nat.le_of_lt_succ h) with
      | inl h' => exact ih.inv y h'
      | inr h' => rw [←h']; exact ih
  ⟩
```

### Pattern 2: Sized Types
```lean
-- Size-indexed vector operations
def Vec.append {α : Type} : Vec α m → Vec α n → Vec α (m + n)
  | .nil, ys => ys
  | .cons x xs, ys => .cons x (xs.append ys)

-- Type-safe head
def Vec.head {α : Type} : Vec α (n + 1) → α
  | .cons x _ => x

-- Dependent pattern matching
def Vec.tail {α : Type} : Vec α (n + 1) → Vec α n
  | .cons _ xs => xs
```

### Pattern 3: Propositional Truncation
```lean
-- Existential without data
structure Nonempty (α : Type u) : Prop where
  intro :: (val : α)

-- Use for proof irrelevance
theorem exists_of_nonempty {α : Type} {p : α → Prop}
    (h : Nonempty α) : (∃ x, True) :=
  ⟨h.val, trivial⟩

-- Squash for propositions
def TruncatedExists (p : α → Prop) : Prop :=
  ∃ x, p x  -- Already in Prop, so truncated
```

### Pattern 4: Proof Automation with Macros
```lean
-- Simple tactic macro
macro "solve_nat_eq" : tactic =>
  `(tactic| omega)

example (n : Nat) : n + 0 = n := by solve_nat_eq

-- Macro with arguments
macro "rw_all" t:term : tactic =>
  `(tactic| rw [$t] at *)

-- Custom notation
notation:65 lhs:65 " ≈ " rhs:66 => Equivalence lhs rhs
```

### Pattern 5: Well-Founded Induction Principles
```lean
-- Define custom induction principle
theorem nat_strong_induction {p : Nat → Prop}
    (h : ∀ n, (∀ m, m < n → p m) → p n) :
    ∀ n, p n := by
  intro n
  suffices ∀ m, m < n → p m from h n this
  intro m hm
  apply nat_strong_induction h

-- Use for complex recursion
def fastFib (n : Nat) : Nat :=
  match n with
  | 0 => 0
  | 1 => 1
  | n+2 => fastFib (n+1) + fastFib n
termination_by n
```

### Pattern 6: Coinductive Types
```lean
-- Infinite streams (coinductive)
coinductive Stream (α : Type u) : Type u where
  | cons : α → Stream α → Stream α

-- Operations on streams
def Stream.head : Stream α → α
  | .cons x _ => x

def Stream.tail : Stream α → Stream α
  | .cons _ xs => xs

-- Bisimulation for equality
def Stream.bisim (R : Stream α → Stream α → Prop) : Prop :=
  ∀ s1 s2, R s1 s2 →
    s1.head = s2.head ∧ R s1.tail s2.tail
```

### Pattern 7: Proof Irrelevance Patterns
```lean
-- Use Subtype for computationally relevant data
def Pos : Type := { n : Nat // n > 0 }

def Pos.toNat (p : Pos) : Nat := p.val

-- Proofs are irrelevant
theorem pos_eq_of_val_eq (p q : Pos) (h : p.val = q.val) : p = q := by
  cases p; cases q
  simp at h
  subst h
  rfl

-- Use for predicate subtypes
def Even : Type := { n : Nat // n % 2 = 0 }
```

### Pattern 8: Recursion-Recursion
```lean
-- Mutually recursive functions
mutual
  def even : Nat → Bool
    | 0 => true
    | n+1 => odd n

  def odd : Nat → Bool
    | 0 => false
    | n+1 => even n
end

-- Prove properties mutually
mutual
  theorem even_iff : even n = true ↔ n % 2 = 0 := by
    cases n <;> simp [even, odd_iff, *]

  theorem odd_iff : odd n = true ↔ n % 2 = 1 := by
    cases n <;> simp [even, odd, even_iff, *]
end
```

### Pattern 9: Abstract Nonsense (Category Theory Style)
```lean
-- Abstract interface
class Functor (F : Type u → Type v) where
  map : (α → β) → F α → F β
  map_id : map (id : α → α) = id
  map_comp : map (g ∘ f) = map g ∘ map f

-- Concrete instances
instance : Functor List where
  map := List.map
  map_id := List.map_id
  map_comp := fun f g => (List.map_comp_map f g).symm

-- Generic theorems
theorem functor_preserves_const {F : Type → Type} [Functor F]
    (x : α) (c : β) :
    Functor.map (fun _ => c) (Functor.map (fun _ => x) fa) =
    Functor.map (fun _ => c) fa := by
  rw [←Functor.map_comp]
  rfl
```

### Pattern 10: Proof Combinators
```lean
-- Compose proofs
def proof_comp {p q r : Prop} (h1 : p → q) (h2 : q → r) : p → r :=
  fun hp => h2 (h1 hp)

-- Proof lifting
def lift_iff {p q : Prop} (h : p ↔ q) : (p → r) ↔ (q → r) :=
  ⟨fun hpr hq => hpr (h.mpr hq), fun hqr hp => hqr (h.mp hp)⟩

-- Proof functoriality
theorem map_proof {p q r s : Prop}
    (hpq : p → q) (hrs : r → s)
    (hqr : q → r) : p → s :=
  fun hp => hrs (hqr (hpq hp))
```

## Formalization Architecture

### Large-Scale Organization
```lean
-- File: MyProject/Basic.lean
-- Foundational definitions

-- File: MyProject/Properties.lean
import MyProject.Basic
-- Basic properties and lemmas

-- File: MyProject/Advanced.lean
import MyProject.Properties
-- Advanced theorems

-- File: MyProject/Automation.lean
import MyProject.Properties
-- Custom tactics and automation
```

### Abstraction Levels
```lean
-- Level 1: Raw definition
def raw_gcd (a b : Nat) : Nat := sorry

-- Level 2: Specification
theorem gcd_spec (a b : Nat) :
    (raw_gcd a b ∣ a) ∧
    (raw_gcd a b ∣ b) ∧
    (∀ d, d ∣ a → d ∣ b → d ∣ raw_gcd a b) := sorry

-- Level 3: Interface
class GCD (α : Type) [Dvd α] where
  gcd : α → α → α
  gcd_dvd_left : ∀ a b, gcd a b ∣ a
  gcd_dvd_right : ∀ a b, gcd a b ∣ b
  dvd_gcd : ∀ a b d, d ∣ a → d ∣ b → d ∣ gcd a b
```

### Modular Proofs
```lean
-- Separate concerns
namespace IntegerProps
  theorem add_comm : ∀ a b : Int, a + b = b + a := sorry
  theorem mul_comm : ∀ a b : Int, a * b = b * a := sorry
end IntegerProps

namespace RingProps
  variable [Ring R]
  theorem distrib : ∀ a b c : R, a * (b + c) = a * b + a * c := sorry
end RingProps
```

## Quick Reference

### Inductive Type Checklist
```lean
-- 1. Define constructors
inductive MyType where
  | constructor1 : ...
  | constructor2 : ...

-- 2. Define recursion principle (if needed)
def MyType.rec ...

-- 3. Prove induction principle
theorem MyType.induction ...

-- 4. Define operations
def MyType.operation ...

-- 5. Prove properties
theorem MyType.property ...
```

### Well-Founded Recursion Template
```lean
def recursiveFunction (x : α) : β :=
  match ... with
  | base_case => ...
  | recursive_case => ... recursiveFunction ...
termination_by measure_function x
decreasing_by
  -- Prove recursive calls decrease measure
  simp_wf
  -- Additional tactics (omega, etc.)
```

### Quotient Type Template
```lean
-- 1. Define relation
def myRel : α → α → Prop := ...

-- 2. Prove equivalence
instance : Setoid α where
  r := myRel
  iseqv := ⟨refl_proof, symm_proof, trans_proof⟩

-- 3. Define quotient
def MyQuotient := Quotient (inferInstanceAs (Setoid α))

-- 4. Lift operations
def MyQuotient.op := Quotient.lift (raw_op) (congruence_proof)
```

## Anti-Patterns

### Anti-Pattern 1: Poor Abstraction
```lean
-- BAD: Over-concrete definition
def list_sum_nat : List Nat → Nat
  | [] => 0
  | x::xs => x + list_sum_nat xs

-- GOOD: Generic with type classes
def list_sum {α : Type} [Add α] [Zero α] : List α → α
  | [] => 0
  | x::xs => x + list_sum xs
```

### Anti-Pattern 2: Ignoring Automation
```lean
-- BAD: Manual proof
theorem add_assoc (a b c : Nat) : (a + b) + c = a + (b + c) := by
  induction a with
  | zero => rfl
  | succ a ih =>
    simp [Nat.add_succ]
    rw [ih]

-- GOOD: Use automation
theorem add_assoc (a b c : Nat) : (a + b) + c = a + (b + c) := by
  omega
```

### Anti-Pattern 3: Verbose Proofs
```lean
-- BAD: Overly detailed
theorem my_theorem : p ∧ q → q ∧ p := by
  intro h
  have hp := h.left
  have hq := h.right
  have hq_again := hq
  have hp_again := hp
  exact ⟨hq_again, hp_again⟩

-- GOOD: Concise
theorem my_theorem : p ∧ q → q ∧ p := by
  intro ⟨hp, hq⟩
  exact ⟨hq, hp⟩

-- BEST: Term mode
theorem my_theorem : p ∧ q → q ∧ p :=
  fun ⟨hp, hq⟩ => ⟨hq, hp⟩
```

### Anti-Pattern 4: Not Using calc
```lean
-- BAD: Manual chaining
theorem transitivity (h1 : a = b) (h2 : b = c) (h3 : c = d) : a = d := by
  rw [h1, h2, h3]

-- GOOD: calc for clarity
theorem transitivity (h1 : a = b) (h2 : b = c) (h3 : c = d) : a = d :=
  calc a = b := h1
       _ = c := h2
       _ = d := h3
```

### Anti-Pattern 5: Monolithic Proofs
```lean
-- BAD: 100-line proof
theorem huge_theorem : complicated_statement := by
  -- 100 lines of tactics
  sorry

-- GOOD: Modular with lemmas
theorem helper_lemma1 : ... := by ...
theorem helper_lemma2 : ... := by ...
theorem huge_theorem : complicated_statement := by
  have h1 := helper_lemma1
  have h2 := helper_lemma2
  -- Short proof using h1, h2
```

### Anti-Pattern 6: Ignoring Type Universe Issues
```lean
-- BAD: Type errors due to universe levels
def bad_list_of_types : List Type := [Nat, String]
-- Error: Type : Type 1, not Type 0

-- GOOD: Explicit universe polymorphism
def good_wrapper {α : Type u} (x : α) : { β : Type u // β = α } :=
  ⟨α, rfl⟩
```

## Related Skills
- **lean-proof-basics.md**: Foundational proof techniques
- **lean-tactics.md**: Tactic library and automation
- **lean-mathlib4.md**: Using mathlib4 library
- **lean-metaprogramming.md**: Advanced custom tactics (advanced skill)
- **smt-theory-applications.md**: Automated reasoning with SMT

## References
- [Theorem Proving in Lean 4](https://lean-lang.org/theorem_proving_in_lean4/)
- [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/)
- [The Lean 4 Reference Manual](https://lean-lang.org/lean4/doc/reference.html)
- [mathlib4 Archive](https://github.com/leanprover-community/mathlib4/tree/master/Archive)
- [Lean Zulip (for questions)](https://leanprover.zulipchat.com/)

## Examples

### Example 1: Binary Trees with Proofs
```lean
-- Define binary tree
inductive Tree (α : Type) where
  | leaf : Tree α
  | node : α → Tree α → Tree α → Tree α

-- Size function
def Tree.size {α : Type} : Tree α → Nat
  | .leaf => 0
  | .node _ l r => 1 + l.size + r.size

-- Mirror function
def Tree.mirror {α : Type} : Tree α → Tree α
  | .leaf => .leaf
  | .node x l r => .node x r.mirror l.mirror

-- Prove involution
theorem Tree.mirror_involutive {α : Type} (t : Tree α) :
    t.mirror.mirror = t := by
  induction t with
  | leaf => rfl
  | node x l r ihl ihr =>
    simp [mirror, ihl, ihr]

-- Prove size preservation
theorem Tree.size_mirror {α : Type} (t : Tree α) :
    t.mirror.size = t.size := by
  induction t with
  | leaf => rfl
  | node x l r ihl ihr =>
    simp [mirror, size, ihl, ihr]
    omega
```

### Example 2: Ackermann Function with Termination
```lean
-- Ackermann function (classic well-founded recursion)
def ackermann : Nat → Nat → Nat
  | 0, n => n + 1
  | m + 1, 0 => ackermann m 1
  | m + 1, n + 1 => ackermann m (ackermann (m + 1) n)
termination_by m n => (m, n)

-- Properties
theorem ackermann_pos (m n : Nat) : 0 < ackermann m n := by
  match m, n with
  | 0, n => omega
  | m + 1, 0 =>
    have : 0 < ackermann m 1 := ackermann_pos m 1
    exact this
  | m + 1, n + 1 =>
    have : 0 < ackermann m (ackermann (m + 1) n) :=
      ackermann_pos m (ackermann (m + 1) n)
    exact this
termination_by m n => (m, n)
```

### Example 3: Quotient for Rational Numbers
```lean
-- Rational numbers as quotient
def RatEqv : (Int × Int) → (Int × Int) → Prop :=
  fun (a, b) (c, d) => a * d = b * c

instance : Setoid (Int × Int) where
  r := RatEqv
  iseqv := {
    refl := fun (a, b) => rfl
    symm := fun h => h.symm
    trans := fun {x y z} h1 h2 => by
      obtain ⟨a, b⟩ := x
      obtain ⟨c, d⟩ := y
      obtain ⟨e, f⟩ := z
      simp [RatEqv] at *
      -- Proof by ring manipulation
      have : a * f * (c * d) = b * e * (c * d) := by
        calc a * f * (c * d) = (a * d) * (c * f) := by ring
             _ = (b * c) * (c * f) := by rw [h1]
             _ = b * (c * c * f) := by ring
             _ = b * (c * e * d) := by rw [h2]; ring
             _ = b * e * (c * d) := by ring
      sorry -- Need non-zero denominators
  }

def Rat : Type := Quotient (inferInstanceAs (Setoid (Int × Int)))
```

---

**Skill Metadata:**
- Scope: Advanced Lean 4 theorem proving and formalization
- Complexity: Advanced
- Prerequisites: lean-proof-basics.md, lean-tactics.md, lean-mathlib4.md
- Related: lean-metaprogramming.md, smt-theory-applications.md
