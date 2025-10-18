---
name: formal-lean-tactics
description: Optimizing proof efficiency
---


# Lean 4 Tactics

## Overview
Advanced tactics, tactic combinators, automation strategies, and custom tactic development for efficient proof construction in Lean 4.

## Scope
**Included:**
- Core tactic repertoire (rw, simp, ring, linarith, omega)
- Tactic combinators and control flow
- Simplification and normalization
- Automation tactics (aesop, tauto, decide)
- Conversion mode (conv)
- Structured proofs (calc, have, show)
- Tactic debugging and inspection
- Custom tactic basics

**Excluded:**
- Basic proof structure (see `lean-proof-basics.md`)
- mathlib4 library search (see `lean-mathlib4.md`)
- Advanced metaprogramming (separate skill)
- Complex formalization strategies (see `lean-theorem-proving.md`)

## When to Use This Skill
**Primary use cases:**
- Optimizing proof efficiency
- Automating repetitive reasoning
- Complex equational reasoning
- Arithmetic and algebraic proofs
- Debugging stuck proofs
- Developing domain-specific tactics

**Indicators you need this:**
- "How do I simplify this expression?"
- "What tactic should I use for arithmetic?"
- "How do I automate this proof pattern?"
- "My proof is too verbose"
- "How do I use conv mode?"

**When to use other skills instead:**
- Learning basic proofs → `lean-proof-basics.md`
- Finding mathlib theorems → `lean-mathlib4.md`
- Formalization architecture → `lean-theorem-proving.md`

## Prerequisites
**Required knowledge:**
- Lean 4 basics (see `lean-proof-basics.md`)
- Tactic mode fundamentals
- Basic mathematical reasoning

**Required setup:**
```bash
# Lean 4 with mathlib4 (for advanced tactics)
lake new my_project math
cd my_project
lake update
lake build
```

**Key dependencies:**
- Lean 4.0.0+
- mathlib4 (for tactics like ring, linarith, omega)

## Core Concepts

### 1. Tactic Monad and Goal State
Tactics operate in a monadic context, transforming goal states.

```lean
-- Goal state structure
-- ⊢ goal
-- Context:
--   h1 : assumption1
-- h2 : assumption2
-- Goal: conclusion

-- Tactics transform this state
example (h : p) : p ∨ q := by
  -- State: h : p ⊢ p ∨ q
  left
  -- State: h : p ⊢ p
  exact h
  -- State: (no goals)
```

### 2. Rewriting and Simplification
The workhorse of equational reasoning.

```lean
-- rw: Directed rewriting
example (h : a = b) : f a = f b := by
  rw [h]

-- simp: Simplification with simp set
example : 0 + n = n := by
  simp

-- simp with arguments
example : xs.reverse.reverse = xs := by
  simp [List.reverse_reverse]
```

### 3. Unification and Pattern Matching
Tactics use unification to match patterns and apply theorems.

```lean
-- apply unifies with goal
example (h : p → q) : p → q := by
  apply h  -- Unifies goal with conclusion of h

-- refine for partial terms with holes
example : ∃ n, n + 0 = n := by
  refine ⟨?_, ?_⟩
  · exact 5
  · simp
```

### 4. Simp Lemmas and Normal Forms
The `simp` tactic uses lemmas marked with `@[simp]`.

```lean
-- Declaring simp lemmas
@[simp]
theorem zero_add (n : Nat) : 0 + n = n := by
  induction n <;> simp [*, Nat.add_succ]

-- Using simp
example (n : Nat) : 0 + (0 + n) = n := by
  simp  -- Applies zero_add twice
```

## Advanced Tactics

### Tactic 1: rw (Rewrite)
Directed equational reasoning.

```lean
-- Basic rewrite
example (h : a = b) : a + c = b + c := by
  rw [h]

-- Multiple rewrites
example (h1 : a = b) (h2 : b = c) : a = c := by
  rw [h1, h2]

-- Rewrite backwards
example (h : a = b) : b = a := by
  rw [←h]

-- Rewrite in hypothesis
example (h1 : a = b) (h2 : f a = g a) : f b = g a := by
  rw [h1] at h2
  exact h2

-- Rewrite everywhere
example (h : a = b) (h1 : f a = c) (h2 : g a = d) : f b = c ∧ g b = d := by
  rw [h] at *
  exact ⟨h1, h2⟩
```

### Tactic 2: simp (Simplification)
Normalize expressions using simp lemmas.

```lean
-- Basic simplification
example : [1, 2] ++ [] = [1, 2] := by simp

-- With specific lemmas
example : xs.reverse.reverse = xs := by
  simp only [List.reverse_reverse]

-- With hypotheses
example (h : x = 0) : x + y = y := by
  simp [h]

-- Simplify everywhere
example (h : x = 0) : x + y = y ∧ y + x = y := by
  simp [h] at *
  exact ⟨h, h⟩

-- Simplify with arithmetic
example : (n + 1) * 2 = n * 2 + 2 := by
  simp [Nat.add_mul, Nat.mul_comm]
```

**Key simp variants:**
```lean
simp           -- Use full simp set
simp only [...]  -- Use only specified lemmas
simp [h1, h2]  -- Add hypotheses to simp set
simp at h      -- Simplify hypothesis
simp at *      -- Simplify all
simp?          -- Show which lemmas were used (debugging)
```

### Tactic 3: ring (Ring Arithmetic)
Decide equality in commutative (semi)rings.

```lean
-- Polynomial equality
example (a b : Nat) : (a + b) * (a + b) = a * a + 2 * a * b + b * b := by
  ring

-- Complex expressions
example (x y z : Int) :
    (x + y) * z - x * z = y * z := by
  ring

-- Works with variables and constants
example (n : Nat) : (n + 1) ^ 2 = n ^ 2 + 2 * n + 1 := by
  ring
```

### Tactic 4: linarith (Linear Arithmetic)
Solve linear arithmetic goals.

```lean
-- From linear inequalities
example (h1 : a ≤ b) (h2 : b < c) : a < c := by
  linarith

-- With arithmetic
example (h : x ≤ 3) : 2 * x + 1 ≤ 7 := by
  linarith

-- Complex linear reasoning
example (h1 : x + y ≤ 10) (h2 : x ≥ 3) (h3 : y ≥ 4) : x + y ≤ 10 := by
  linarith
```

### Tactic 5: omega (Integer/Natural Arithmetic)
Decision procedure for Presburger arithmetic (linear integer arithmetic).

```lean
-- Natural number arithmetic
example (n m : Nat) (h : n + m = 5) (h2 : n ≥ 3) : m ≤ 2 := by
  omega

-- Integer arithmetic
example (x y : Int) (h1 : x + y = 10) (h2 : x - y = 2) : x = 6 := by
  omega

-- With modular arithmetic
example (n : Nat) : n % 2 = 0 ∨ n % 2 = 1 := by
  omega
```

### Tactic 6: conv (Conversion Mode)
Fine-grained rewriting control.

```lean
-- Rewrite specific subterm
example : (1 + 2) + 3 = 3 + 3 := by
  conv_lhs =>
    arg 1  -- Select first argument
    rw [Nat.add_comm]
  rfl

-- Navigate expression tree
example : f (g (h a)) = f (g (h b)) := by
  conv_lhs =>
    arg 1    -- Enter f's argument
    arg 1    -- Enter g's argument
    arg 1    -- Enter h's argument
    rw [hab]

-- Using for: target specific occurrences
example : a + (a + b) = (a + a) + b := by
  conv =>
    lhs
    arg 2  -- Second argument of outer +
    rw [Nat.add_comm]
```

### Tactic 7: calc (Calculational Proofs)
Chain equalities and inequalities.

```lean
-- Chain equalities
example (h1 : a = b) (h2 : b = c) : a = c := by
  calc a = b := h1
       _ = c := h2

-- Chain inequalities
example (h1 : a ≤ b) (h2 : b < c) : a < c := by
  calc a ≤ b := h1
       _ < c := h2

-- Mixed operations
example (n : Nat) : (n + 1) ^ 2 = n ^ 2 + 2 * n + 1 := by
  calc (n + 1) ^ 2 = (n + 1) * (n + 1) := by rfl
    _ = n * n + n * 1 + 1 * n + 1 * 1 := by ring
    _ = n ^ 2 + 2 * n + 1 := by ring
```

### Tactic 8: aesop (Automated Search)
Automated proof search using a tactic library.

```lean
-- Solves goals by searching
example (h : p ∧ q) : q ∧ p := by
  aesop

-- With custom rule sets
example : ∀ x, x ∈ xs → x ∈ xs ++ ys := by
  aesop (add norm simp List.mem_append)
```

### Tactic 9: tauto (Tautology)
Decide propositional tautologies.

```lean
-- Propositional logic
example : p ∧ q → q ∧ p := by
  tauto

-- Complex tautologies
example : (p → q) → (q → r) → (p → r) := by
  tauto
```

### Tactic 10: decide (Decision Procedures)
Decide decidable propositions by evaluation.

```lean
-- Decidable equality
example : (5 : Nat) ≠ 3 := by
  decide

-- Boolean conditions
example : (10 < 20) = true := by
  decide

-- List membership
example : 3 ∈ [1, 2, 3, 4] := by
  decide
```

## Tactic Combinators

### Sequential and Parallel
```lean
-- Sequential (;)
example : p → p ∧ p := by
  intro h; constructor; exact h; exact h

-- All goals (<;>)
example : p → p ∧ p := by
  intro h
  constructor <;> exact h  -- Apply to both goals

-- Focus first goal (·)
example : p ∧ q → q ∧ p := by
  intro ⟨hp, hq⟩
  constructor
  · exact hq  -- First goal
  · exact hp  -- Second goal
```

### Control Flow
```lean
-- Alternative (first success)
example : p ∨ q := by
  first | left; assumption | right; assumption

-- Try (don't fail)
example : p → p := by
  try rw [some_lemma]  -- Continue even if rw fails
  intro h
  exact h

-- Repeat
example : 0 + (0 + n) = n := by
  repeat rw [Nat.zero_add]
  -- Applies until no longer applicable
```

### Conditional
```lean
-- By cases
example : p ∨ ¬p → q → q := by
  intro h hq
  cases h <;> exact hq

-- If-then-else pattern
by
  if h : condition then
    -- Proof with h : condition
    sorry
  else
    -- Proof with h : ¬condition
    sorry
```

## Structured Proof Patterns

### Pattern 1: have (Intermediate Results)
```lean
-- Name intermediate facts
example (h1 : a = b) (h2 : b = c) : f a = f c := by
  have hab : a = b := h1
  have hbc : b = c := h2
  have hac : a = c := by rw [hab, hbc]
  rw [hac]

-- Anonymous have
example (h : a = b) : f a = f b := by
  have : a = b := h
  rw [this]
```

### Pattern 2: show (Make Goal Explicit)
```lean
-- Explicitly show what you're proving
example : p → q → p ∧ q := by
  intro hp hq
  show p ∧ q
  exact ⟨hp, hq⟩

-- Useful for type-directed proof
example : (fun x => x + 0) = (fun x => x) := by
  show (fun x => x + 0) = (fun x => x)
  funext x
  simp
```

### Pattern 3: suffices (Backwards Reasoning)
```lean
-- Prove it suffices to show something simpler
example (h : p) : p ∧ p := by
  suffices hp : p from ⟨hp, hp⟩
  exact h

-- Chain backwards
example : a = d := by
  suffices a = c by rw [this, hcd]
  suffices a = b by rw [this, hbc]
  exact hab
```

### Pattern 4: obtain (Destructure Existentials)
```lean
-- Clean existential elimination
example (h : ∃ x, P x ∧ Q x) : ∃ x, P x := by
  obtain ⟨x, hPx, hQx⟩ := h
  exact ⟨x, hPx⟩

-- With pattern matching
example (h : ∃ x y, x + y = 10) : ∃ z, z ≤ 10 := by
  obtain ⟨x, y, hsum⟩ := h
  use x
  omega
```

## Debugging Tactics

### Inspection
```lean
-- Show current goal state
example : p → p := by
  intro h
  trace "{h}"  -- Print hypothesis
  exact h

-- Show term
#check (rfl : a = a)
#print Nat.add  -- Print definition

-- simp? shows which lemmas were used
example : xs.reverse.reverse = xs := by
  simp?
  -- Try this: simp only [List.reverse_reverse]
```

### Common Issues
```lean
-- Tactic failed: goal doesn't match
example : p := by
  exact q  -- Error: type mismatch

-- Fix: check types
example : p := by
  have hq : q := sorry
  -- Can't use hq to prove p directly

-- Unknown identifier
example : p := by
  exact h  -- Error: h not found

-- Fix: intro first
example : p → p := by
  intro h
  exact h
```

## Quick Reference

### Essential Tactics
```lean
-- Equality/Rewriting
rfl            -- Reflexivity
rw [h]         -- Rewrite with h
simp           -- Simplify

-- Arithmetic
ring           -- Ring equality
linarith       -- Linear arithmetic
omega          -- Presburger arithmetic

-- Structure
constructor    -- Build constructor
cases h        -- Case analysis
induction n    -- Induction

-- Automation
aesop          -- Automated search
tauto          -- Propositional tautology
decide         -- Decision procedure

-- Control
exact t        -- Provide exact term
apply t        -- Apply theorem
refine t       -- Partial term with holes
```

### Tactic Combinators
```lean
t1; t2         -- Sequential
t1 <;> t2      -- All goals
· t            -- Focus first
first | t1 | t2 -- Alternative
try t          -- Don't fail
repeat t       -- Repeat until failure
all_goals t    -- Apply to all goals
```

### Conversion Mode
```lean
conv =>
  lhs          -- Left-hand side
  rhs          -- Right-hand side
  arg n        -- nth argument
  args         -- All arguments
  enter [1, 2] -- Navigate path
  rw [h]       -- Rewrite
  simp         -- Simplify
```

## Anti-Patterns

### Anti-Pattern 1: Tactic Soup
```lean
-- BAD: Long sequence of low-level tactics
example : complicated_goal := by
  intro h1
  intro h2
  intro h3
  have x := h1
  have y := h2
  rw [x]
  rw [y]
  simp
  ring
  sorry

-- GOOD: Structure and automation
example : complicated_goal := by
  intro h1 h2 h3
  simp [h1, h2]
  ring
```

### Anti-Pattern 2: Ignoring calc
```lean
-- BAD: Manual chaining
example (h1 : a = b) (h2 : b = c) (h3 : c = d) : a = d := by
  have hab := h1
  rw [hab]
  have hbc := h2
  rw [hbc]
  exact h3

-- GOOD: Use calc
example (h1 : a = b) (h2 : b = c) (h3 : c = d) : a = d := by
  calc a = b := h1
       _ = c := h2
       _ = d := h3
```

### Anti-Pattern 3: Over-Reliance on sorry
```lean
-- BAD: Sorry as crutch
theorem main_result : important_property := by
  have lemma1 := sorry
  have lemma2 := sorry
  sorry

-- GOOD: Explicit admits with tracking
-- In separate file or section
axiom lemma1 : auxiliary_fact_1  -- TODO: issue #123
axiom lemma2 : auxiliary_fact_2  -- TODO: issue #124

theorem main_result : important_property := by
  have h1 := lemma1
  have h2 := lemma2
  -- Actual proof using h1, h2
  sorry  -- Requires h1 and h2, tracked in #125
```

### Anti-Pattern 4: Not Using Automation
```lean
-- BAD: Manual propositional reasoning
example : (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  intro ⟨⟨hp, hq⟩, hr⟩
  constructor
  · exact hr
  · constructor
    · exact hq
    · exact hp

-- GOOD: Let automation handle it
example : (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  tauto
```

### Anti-Pattern 5: Verbose Rewrites
```lean
-- BAD: Rewrite one at a time
example (h1 : a = b) (h2 : b = c) (h3 : c = d) : f a = f d := by
  rw [h1]
  rw [h2]
  rw [h3]

-- GOOD: Batch rewrites
example (h1 : a = b) (h2 : b = c) (h3 : c = d) : f a = f d := by
  rw [h1, h2, h3]
```

### Anti-Pattern 6: Ignoring conv
```lean
-- BAD: Rewrite everything (may fail)
example : f (g a + h a) = f (h a + g a) := by
  rw [add_comm]  -- Might rewrite wrong occurrence

-- GOOD: Target specific subterm
example : f (g a + h a) = f (h a + g a) := by
  conv_lhs =>
    arg 1
    rw [add_comm]
```

## Related Skills
- **lean-proof-basics.md**: Foundational proof techniques
- **lean-mathlib4.md**: Using mathlib4 library and theorems
- **lean-theorem-proving.md**: Advanced formalization strategies
- **lean-metaprogramming.md**: Custom tactic development (advanced)

## References
- [Lean 4 Tactics Index](https://lean-lang.org/theorem_proving_in_lean4/tactics.html)
- [Mathlib4 Tactics Documentation](https://leanprover-community.github.io/mathlib4_docs/tactics.html)
- [Aesop Documentation](https://github.com/leanprover-community/aesop)
- [Batteries Tactics](https://github.com/leanprover-community/batteries)

## Examples

### Example 1: Algebraic Manipulation
```lean
-- Expanding and simplifying
example (a b : Nat) : (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2 := by
  ring

-- Using calc for clarity
example (x y : Int) : (x + y) * (x - y) = x ^ 2 - y ^ 2 := by
  calc (x + y) * (x - y)
      = x * x - x * y + y * x - y * y := by ring
    _ = x ^ 2 - y ^ 2 := by ring
```

### Example 2: Linear Arithmetic
```lean
-- Combining linarith with other tactics
example (x y z : Nat) (h1 : x ≤ y) (h2 : y < z) : x < z := by
  linarith

-- Complex linear reasoning
example (a b c : Int)
    (h1 : 2 * a + b ≤ 10)
    (h2 : a + 2 * b ≤ 11)
    (h3 : a ≥ 0)
    (h4 : b ≥ 0) :
    3 * a + 3 * b ≤ 21 := by
  linarith
```

### Example 3: Simplification Strategies
```lean
-- Controlled simplification
example (xs ys : List α) :
    (xs ++ ys).reverse = ys.reverse ++ xs.reverse := by
  simp only [List.reverse_append]

-- Simplification with arithmetic
example (n m : Nat) : (n + m) + 0 = n + m := by
  simp

-- Using simp to normalize before other tactics
example (n : Nat) : (n + 1) * 2 = n * 2 + 2 := by
  simp [Nat.add_mul]
  ring
```

### Example 4: Conversion Mode for Precise Rewriting
```lean
-- Target specific subexpression
example (h : a = b) : f (g a + c) + d = f (g b + c) + d := by
  conv_lhs =>
    arg 1  -- Enter first argument of +
    arg 1  -- Enter first argument of f
    arg 1  -- Enter first argument of +
    arg 1  -- Enter argument of g
    rw [h]

-- Multiple targeted rewrites
example : (a + b) + (c + d) = (b + a) + (d + c) := by
  conv =>
    lhs
    arg 1
    rw [add_comm]
  conv =>
    lhs
    arg 2
    rw [add_comm]
```

---

**Skill Metadata:**
- Scope: Advanced Lean 4 tactics and automation
- Complexity: Intermediate to advanced
- Prerequisites: lean-proof-basics.md
- Related: lean-mathlib4.md, lean-theorem-proving.md
