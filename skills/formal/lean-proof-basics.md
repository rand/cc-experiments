---
name: formal-lean-proof-basics
description: Learning Lean 4 from scratch
---


# Lean 4 Proof Basics

## Overview
Fundamental concepts and patterns for writing proofs in Lean 4, covering propositions as types, proof terms, basic tactics, and simple proof structures.

## Scope
**Included:**
- Propositions as types (Curry-Howard correspondence)
- Proof terms vs tactic mode
- Basic tactics (intro, exact, apply, rw)
- Function and implication proofs
- Conjunction, disjunction, negation
- Universal and existential quantifiers
- Simple induction proofs
- Lean 4 syntax and conventions

**Excluded:**
- Advanced tactics (see `lean-tactics.md`)
- mathlib4 library usage (see `lean-mathlib4.md`)
- Complex formalization strategies (see `lean-theorem-proving.md`)
- Type class mechanics
- Metaprogramming and custom tactics

## When to Use This Skill
**Primary use cases:**
- Learning Lean 4 from scratch
- Writing simple mathematical proofs
- Understanding proof term representation
- Teaching formal verification basics
- Converting paper proofs to Lean

**Indicators you need this:**
- "How do I prove X in Lean 4?"
- "What's the difference between term mode and tactic mode?"
- "How do I use intro/exact/apply?"
- "How do I prove basic logical statements?"

**When to use other skills instead:**
- Complex tactic automation → `lean-tactics.md`
- Using mathlib4 theorems → `lean-mathlib4.md`
- Advanced formalization → `lean-theorem-proving.md`

## Prerequisites
**Required knowledge:**
- Basic functional programming (types, functions)
- Propositional logic (and, or, implies, not)
- First-order logic (forall, exists)

**Required setup:**
```bash
# Install Lean 4 (via elan)
⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
```bash
# Download script first
curl -O https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh
# Verify checksum
sha256sum elan-init.sh
# Review content
less elan-init.sh
# Then execute
bash elan-init.sh
```
For development/learning only:
```bash
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Create new project
lake new my_project
cd my_project

# Build project
lake build

# Open in VS Code (with Lean 4 extension)
code .
```

**Dependencies:**
- Lean 4.0.0+ (preferably latest stable)
- VS Code with Lean 4 extension
- mathlib4 (optional, for library access)

## Core Concepts

### 1. Propositions as Types (Curry-Howard)
In Lean, propositions are types, and proofs are terms of those types.

```lean
-- Proposition: 2 + 2 = 4
#check (2 + 2 = 4 : Prop)

-- Proof: a term of type "2 + 2 = 4"
example : 2 + 2 = 4 := rfl

-- Type of a proof
#check (rfl : 2 + 2 = 4)
```

**Key principle:** To prove proposition P, construct a term of type P.

### 2. Term Mode vs Tactic Mode

**Term mode** (direct proof construction):
```lean
-- Prove implication directly
example : p → q → p := fun hp hq => hp

-- Prove conjunction
example : p ∧ q → q ∧ p := fun ⟨hp, hq⟩ => ⟨hq, hp⟩
```

**Tactic mode** (interactive proof construction):
```lean
example : p → q → p := by
  intro hp hq
  exact hp

example : p ∧ q → q ∧ p := by
  intro ⟨hp, hq⟩
  exact ⟨hq, hp⟩
```

**When to use each:**
- Term mode: Simple proofs, direct constructions, obvious terms
- Tactic mode: Complex proofs, exploratory proving, step-by-step reasoning

### 3. Basic Proof Structure

**Anatomy of a proof:**
```lean
-- Theorem statement
theorem my_theorem (assumptions : Type) : conclusion := by
  -- Tactic 1
  -- Tactic 2
  -- ...
  -- Tactic N (closes goal)
```

**Example:**
```lean
theorem and_comm (p q : Prop) : p ∧ q → q ∧ p := by
  intro ⟨hp, hq⟩  -- Introduce hypothesis, destructure
  exact ⟨hq, hp⟩  -- Provide exact proof term
```

### 4. Function Types and Implication
Functions and implications are the same (Π-types).

```lean
-- These are equivalent
example : ∀ (n : Nat), n + 0 = n := fun n => Nat.add_zero n
example : ∀ (n : Nat), n + 0 = n := by intro n; exact Nat.add_zero n

-- Implication is a function
example : p → q := fun hp => _  -- hp : p, goal: q
```

## Common Patterns

### Pattern 1: Proving Implications
```lean
-- Template
theorem impl_proof : P → Q := by
  intro hP    -- Assume P (hypothesis hP)
  -- Now prove Q using hP
  sorry

-- Example
theorem modus_ponens : p → (p → q) → q := by
  intro hp hpq
  apply hpq
  exact hp
```

### Pattern 2: Proving Conjunctions
```lean
-- Template
theorem conj_proof : P ∧ Q := by
  constructor
  · -- Prove P
    sorry
  · -- Prove Q
    sorry

-- Example
theorem and_intro : p → q → p ∧ q := by
  intro hp hq
  constructor
  · exact hp
  · exact hq
```

### Pattern 3: Using Conjunctions
```lean
-- Destructuring in intro
theorem and_left : p ∧ q → p := by
  intro ⟨hp, hq⟩
  exact hp

-- Using cases
theorem and_right : p ∧ q → q := by
  intro h
  cases h with
  | intro hp hq => exact hq
```

### Pattern 4: Proving Disjunctions
```lean
-- Template: prove one side
theorem disj_left : P → P ∨ Q := by
  intro hP
  left
  exact hP

theorem disj_right : Q → P ∨ Q := by
  intro hQ
  right
  exact hQ
```

### Pattern 5: Case Analysis on Disjunctions
```lean
-- Template
theorem disj_elim : P ∨ Q → (P → R) → (Q → R) → R := by
  intro hPQ hPR hQR
  cases hPQ with
  | inl hP => exact hPR hP
  | inr hQ => exact hQR hQ

-- Example
theorem or_comm : p ∨ q → q ∨ p := by
  intro h
  cases h with
  | inl hp => right; exact hp
  | inr hq => left; exact hq
```

### Pattern 6: Negation and Contradiction
```lean
-- Negation is implication to False
#check (¬p : Prop)  -- p → False

-- Proof by contradiction
theorem not_not_intro : p → ¬¬p := by
  intro hp hnp
  exact hnp hp

-- Using contradiction
theorem contradiction : p → ¬p → q := by
  intro hp hnp
  exfalso
  exact hnp hp
```

### Pattern 7: Universal Quantification
```lean
-- Template
theorem forall_intro : ∀ (x : α), P x := by
  intro x
  -- Prove P x for arbitrary x
  sorry

-- Example
theorem forall_impl : (∀ x, P x → Q x) → (∀ x, P x) → (∀ x, Q x) := by
  intro hPQ hP x
  apply hPQ
  exact hP x
```

### Pattern 8: Existential Quantification
```lean
-- Proving existence
theorem exists_intro : P a → ∃ x, P x := by
  intro hPa
  use a
  exact hPa

-- Using existential hypothesis
theorem exists_elim : (∃ x, P x) → (∀ x, P x → Q) → Q := by
  intro ⟨x, hPx⟩ hPQ
  exact hPQ x hPx
```

### Pattern 9: Equality and Rewriting
```lean
-- Reflexivity
example : a = a := rfl

-- Symmetry
example (h : a = b) : b = a := h.symm

-- Transitivity
example (h1 : a = b) (h2 : b = c) : a = c := by
  rw [h1, h2]

-- Rewriting in goal
example (h : a = b) : f a = f b := by
  rw [h]

-- Rewriting in hypothesis
example (h1 : a = b) (h2 : f a = c) : f b = c := by
  rw [h1] at h2
  exact h2
```

### Pattern 10: Simple Induction
```lean
-- Template
theorem nat_induction (P : Nat → Prop)
    (base : P 0)
    (step : ∀ n, P n → P (n + 1)) :
    ∀ n, P n := by
  intro n
  induction n with
  | zero => exact base
  | succ n ih => exact step n ih

-- Example
theorem zero_add (n : Nat) : 0 + n = n := by
  induction n with
  | zero => rfl
  | succ n ih =>
    rw [Nat.add_succ, ih]
```

## Basic Tactics Reference

### Core Tactics
```lean
-- intro: Introduce hypothesis or variable
intro h        -- Name hypothesis h
intro          -- Auto-generate name
intro ⟨h1, h2⟩ -- Destructure simultaneously

-- exact: Provide exact proof term
exact h        -- Use hypothesis h
exact rfl      -- Reflexivity for equality

-- apply: Apply function/theorem (backward reasoning)
apply f        -- If goal is Q and f : P → Q, new goal is P

-- constructor: Build constructors (and, exists, etc.)
constructor    -- For ∧, split into two goals

-- left/right: Choose disjunction branch
left           -- Prove P for goal P ∨ Q
right          -- Prove Q for goal P ∨ Q

-- cases: Case analysis
cases h        -- Split on hypothesis h

-- exfalso: Proof by contradiction
exfalso        -- Change goal to False

-- rfl: Reflexivity
rfl            -- Prove a = a

-- rw: Rewrite using equality
rw [h]         -- Rewrite goal using h : a = b
rw [h] at h2   -- Rewrite in hypothesis h2
rw [←h]        -- Rewrite backwards (b to a)
```

### Tactic Combinators
```lean
-- Sequential execution
tac1; tac2     -- Do tac1 then tac2

-- All goals
all_goals tac  -- Apply tac to all goals

-- Focus on goals
· tac          -- Focus on first goal
next => tac    -- Focus on next goal

-- Repetition
repeat tac     -- Repeat until failure
```

## Quick Reference

### Logical Connectives
```lean
-- Implication
P → Q         -- Function type
fun h => ...  -- Proof (term mode)
intro h       -- Proof (tactic mode)

-- Conjunction
P ∧ Q         -- And.intro : P → Q → P ∧ Q
⟨hp, hq⟩      -- Construct (term mode)
constructor   -- Construct (tactic mode)

-- Disjunction
P ∨ Q         -- Or.inl : P → P ∨ Q, Or.inr : Q → P ∨ Q
Or.inl hp     -- Construct left (term mode)
left; exact hp -- Construct left (tactic mode)

-- Negation
¬P            -- P → False
fun h => ...  -- Prove negation

-- Universal
∀ x, P x      -- (x : α) → P x
fun x => ...  -- Proof (term mode)
intro x       -- Proof (tactic mode)

-- Existential
∃ x, P x      -- Exists.intro : ∀ (a : α), P a → ∃ x, P x
⟨a, ha⟩       -- Construct (term mode)
use a; exact ha -- Construct (tactic mode)
```

### Equality
```lean
rfl           -- a = a
h.symm        -- a = b → b = a
rw [h]        -- Rewrite using h : a = b
rw [←h]       -- Rewrite backwards
calc          -- Chain equalities
  a = b := h1
  _ = c := h2
```

### Common Proof Structures
```lean
-- By cases
cases h with
| case1 => ...
| case2 => ...

-- By induction
induction n with
| zero => ...
| succ n ih => ...

-- Let binding
let x := value
show goal
```

## Anti-Patterns

### Anti-Pattern 1: Over-Complicating Simple Proofs
```lean
-- BAD: Verbose tactic proof
example : p → p := by
  intro h
  have h2 : p := h
  exact h2

-- GOOD: Direct term
example : p → p := fun h => h

-- GOOD: Minimal tactics
example : p → p := by intro h; exact h
```

### Anti-Pattern 2: Ignoring Type Inference
```lean
-- BAD: Explicit types everywhere
example : (fun (x : Nat) => (x : Nat) + (0 : Nat)) = (fun (x : Nat) => x) := by
  funext (x : Nat)
  simp

-- GOOD: Let Lean infer
example : (fun x => x + 0) = (fun x => x) := by
  funext x
  simp
```

### Anti-Pattern 3: Manual Term Construction
```lean
-- BAD: Building complex terms manually
example : p ∧ q → q ∧ p :=
  fun h => And.intro (And.right h) (And.left h)

-- GOOD: Use tactics for clarity
example : p ∧ q → q ∧ p := by
  intro ⟨hp, hq⟩
  exact ⟨hq, hp⟩
```

### Anti-Pattern 4: Not Using Structured Proofs
```lean
-- BAD: All tactics at same level
example : p ∨ q → q ∨ p := by
  intro h
  cases h
  right
  assumption
  left
  assumption

-- GOOD: Use bullets for structure
example : p ∨ q → q ∨ p := by
  intro h
  cases h with
  | inl hp =>
    right
    exact hp
  | inr hq =>
    left
    exact hq
```

### Anti-Pattern 5: Overuse of sorry
```lean
-- BAD: Leaving sorries
theorem important_theorem : P := by
  sorry  -- TODO: prove this later

-- GOOD: Use admit only for exploration, remove before committing
-- GOOD: Break into lemmas with clear sorry locations
lemma helper_lemma : Q := by
  sorry  -- Needs complex proof, tracked in issue #123

theorem important_theorem : P := by
  have hq := helper_lemma
  -- ... rest of proof
```

## Related Skills
- **lean-tactics.md**: Advanced tactics, tactic combinators, automation
- **lean-mathlib4.md**: Using mathlib4 library, finding theorems
- **lean-theorem-proving.md**: Advanced formalization strategies
- **smt-theory-applications.md**: Automated theorem proving with SMT solvers

## References
- [Lean 4 Manual](https://lean-lang.org/lean4/doc/)
- [Theorem Proving in Lean 4](https://lean-lang.org/theorem_proving_in_lean4/)
- [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/)
- [Natural Number Game (Lean 4 version)](https://adam.math.hhu.de/#/g/leanprover-community/nng4)

## Examples

### Example 1: Classical Logic Theorems
```lean
-- Modus tollens
theorem modus_tollens : (p → q) → ¬q → ¬p := by
  intro hpq hnq hp
  exact hnq (hpq hp)

-- Hypothetical syllogism
theorem hyp_syllogism : (p → q) → (q → r) → (p → r) := by
  intro hpq hqr hp
  exact hqr (hpq hp)

-- De Morgan's laws (one direction)
theorem not_and_of_not_or_not : ¬p ∨ ¬q → ¬(p ∧ q) := by
  intro h ⟨hp, hq⟩
  cases h with
  | inl hnp => exact hnp hp
  | inr hnq => exact hnq hq
```

### Example 2: Quantifier Manipulation
```lean
-- Swap quantifiers
theorem forall_swap : (∀ x y, P x y) → (∀ y x, P x y) := by
  intro h y x
  exact h x y

-- Distribute quantifier over conjunction
theorem forall_and : (∀ x, P x ∧ Q x) → (∀ x, P x) ∧ (∀ x, Q x) := by
  intro h
  constructor
  · intro x; exact (h x).left
  · intro x; exact (h x).right
```

### Example 3: Simple Arithmetic
```lean
-- Addition is commutative (using built-in)
example (m n : Nat) : m + n = n + m := Nat.add_comm m n

-- Zero is right identity
theorem add_zero (n : Nat) : n + 0 = n := by
  induction n with
  | zero => rfl
  | succ n ih => rw [Nat.add_succ, ih]

-- Successor relationship
theorem succ_add (m n : Nat) : (m + 1) + n = (m + n) + 1 := by
  induction n with
  | zero => rfl
  | succ n ih => rw [Nat.add_succ, Nat.add_succ, ih, Nat.add_succ]
```

---

**Skill Metadata:**
- Scope: Lean 4 proof fundamentals
- Complexity: Beginner to intermediate
- Prerequisites: Basic logic and functional programming
- Related: lean-tactics.md, lean-mathlib4.md, lean-theorem-proving.md
