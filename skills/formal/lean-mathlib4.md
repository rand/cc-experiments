---
name: formal-lean-mathlib4
description: Formalizing mathematics using existing results
---


# Lean 4 mathlib4 Library

## Overview
Comprehensive guide to using, navigating, and contributing to mathlib4, Lean 4's extensive mathematics library covering algebra, analysis, topology, category theory, and more.

## Scope
**Included:**
- mathlib4 structure and organization
- Library search strategies
- Import management
- Type class system and instance synthesis
- Naming conventions
- Common mathematical domains (algebra, analysis, topology)
- Contributing to mathlib4
- Performance and compilation best practices

**Excluded:**
- Basic proof tactics (see `lean-proof-basics.md`)
- Advanced tactic development (see `lean-tactics.md`)
- Formalization architecture (see `lean-theorem-proving.md`)
- Lean 3 mathlib (outdated)

## When to Use This Skill
**Primary use cases:**
- Formalizing mathematics using existing results
- Finding theorems and definitions in mathlib4
- Understanding type class hierarchies
- Setting up mathlib4 projects
- Contributing definitions and theorems
- Resolving import and instance issues

**Indicators you need this:**
- "How do I find theorem X in mathlib4?"
- "What's the right import for this?"
- "How do I get this instance to synthesize?"
- "What's the mathlib naming convention?"
- "How do I contribute to mathlib4?"

**When to use other skills instead:**
- Learning basic proofs → `lean-proof-basics.md`
- Advanced tactics → `lean-tactics.md`
- Formalization strategy → `lean-theorem-proving.md`

## Prerequisites
**Required knowledge:**
- Lean 4 basics (see `lean-proof-basics.md`)
- Basic mathematics (domain-dependent)
- Type classes and instance resolution

**Required setup:**
```bash
# Create project with mathlib4
lake +leanprover/lean4:nightly-2024-01-15 new my_project math
cd my_project

# Get mathlib4 cache (fast!)
lake exe cache get

# Build project
lake build

# Update mathlib4
lake update mathlib
lake exe cache get
lake build
```

**Key files:**
- `lakefile.lean`: Project configuration
- `lean-toolchain`: Lean version
- `lake-manifest.json`: Dependency lock file

## Core Concepts

### 1. Library Organization
mathlib4 is organized by mathematical domain.

```
Mathlib/
├── Algebra/           # Algebraic structures
│   ├── Group/         # Groups, subgroups
│   ├── Ring/          # Rings, ideals
│   └── Field/         # Fields
├── Analysis/          # Real/complex analysis
│   ├── Calculus/      # Differentiation, integration
│   └── Topology/      # Topological spaces
├── Data/              # Data structures
│   ├── List/          # List operations
│   ├── Finset/        # Finite sets
│   └── Set/           # Set theory
├── Logic/             # Logic and foundations
├── NumberTheory/      # Number theory
├── Topology/          # General topology
└── CategoryTheory/    # Category theory
```

### 2. Naming Conventions
mathlib4 follows strict naming conventions.

**Structure:**
```
[namespace.]subject_description[_variant]
```

**Examples:**
```lean
-- Theorems about operations
Nat.add_comm : ∀ n m, n + m = m + n
Nat.add_assoc : ∀ n m k, (n + m) + k = n + (m + k)
Nat.mul_comm : ∀ n m, n * m = m * n

-- Type class instances
instAddNat : Add Nat
instMulNat : Mul Nat

-- Lemmas with variants
List.append_nil : xs ++ [] = xs
List.nil_append : [] ++ xs = xs
```

**Patterns:**
- `_comm`: Commutativity
- `_assoc`: Associativity
- `_left`/`_right`: Left/right versions
- `_iff`: Equivalence
- `_of_`: Implication (← direction)
- `_inv`: Inverse operation
- `_neg`: Negation

### 3. Type Classes
mathlib4 uses type classes extensively.

```lean
-- Algebraic hierarchy
class Add (α : Type u) where
  add : α → α → α

class Semigroup (α : Type u) extends Mul α where
  mul_assoc : ∀ a b c : α, (a * b) * c = a * (b * c)

class Monoid (α : Type u) extends Semigroup α, One α where
  one_mul : ∀ a : α, 1 * a = a
  mul_one : ∀ a : α, a * 1 = a

class Group (α : Type u) extends Monoid α, Inv α where
  inv_mul_cancel : ∀ a : α, a⁻¹ * a = 1
```

**Using type classes:**
```lean
-- Generic theorem using type classes
theorem mul_left_cancel [Group α] {a b c : α} (h : a * b = a * c) : b = c := by
  have : a⁻¹ * (a * b) = a⁻¹ * (a * c) := by rw [h]
  simp [mul_assoc, inv_mul_cancel] at this
  exact this

-- Instance synthesis
#check (1 + 1 : Nat)  -- Uses instAddNat
#check (1 * 1 : Int)  -- Uses instMulInt
```

### 4. Import Management
Organize imports for fast compilation.

```lean
-- Import specific modules
import Mathlib.Algebra.Group.Defs
import Mathlib.Data.List.Basic

-- Import whole directories (slower)
import Mathlib.Algebra.Group

-- Import everything (very slow, avoid!)
import Mathlib
```

## Library Search Strategies

### Strategy 1: Exact Name Search
Use VS Code autocomplete and `#check`.

```lean
-- Autocomplete: type partial name
#check Nat.add_  -- Shows: add_comm, add_assoc, add_zero, ...

-- Check full name
#check List.append_nil
#check Ring.mul_comm
```

### Strategy 2: Docstring Search
Use Lean 4 web docs.

```
1. Visit: https://leanprover-community.github.io/mathlib4_docs/
2. Search: "continuous" → finds continuity definitions
3. Browse: Mathlib.Topology.Constructions
```

### Strategy 3: Type-Based Search
Use `exact?` tactic (formerly `library_search`).

```lean
example (a b : Nat) : a + b = b + a := by
  exact?
  -- Try this: exact Nat.add_comm a b

example [Group G] (a : G) : a * a⁻¹ = 1 := by
  exact?
  -- Try this: exact mul_inv_cancel a
```

### Strategy 4: Pattern Matching Search
Use `apply?` for applicable theorems.

```lean
example (xs ys : List α) : (xs ++ ys).length = xs.length + ys.length := by
  apply?
  -- Try this: exact List.length_append xs ys
```

### Strategy 5: Local Context Search
Use `assumption` and `simp`.

```lean
example (h : p) : p := by
  assumption  -- Searches local context

example : 0 + n = n := by
  simp  -- Searches simp lemmas
```

## Common Mathematical Domains

### Domain 1: Algebra
```lean
import Mathlib.Algebra.Group.Defs
import Mathlib.Algebra.Ring.Defs

-- Groups
example [Group G] (a b : G) : (a * b)⁻¹ = b⁻¹ * a⁻¹ := by
  exact mul_inv_rev a b

-- Rings
example [Ring R] (a b : R) : (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2 := by
  ring

-- Fields
example [Field F] (a b : F) (h : b ≠ 0) : a / b * b = a := by
  field_simp
```

### Domain 2: Analysis
```lean
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic

-- Continuity
example : Continuous (fun x : ℝ => x ^ 2) := by
  exact continuous_pow 2

-- Derivatives
example : deriv (fun x : ℝ => x ^ 2) = (fun x => 2 * x) := by
  ext x
  simp [deriv_pow]
```

### Domain 3: Topology
```lean
import Mathlib.Topology.Basic
import Mathlib.Topology.MetricSpace.Basic

-- Open sets
example [TopologicalSpace X] (s : Set X) (hs : IsOpen s) :
    IsOpen sᶜ ↔ IsClosed s := by
  exact isOpen_compl_iff

-- Metric spaces
example [MetricSpace X] (x y : X) : dist x y = 0 ↔ x = y := by
  exact dist_eq_zero
```

### Domain 4: Data Structures
```lean
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Set.Basic

-- Lists
example (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse := by
  exact List.reverse_append xs ys

-- Finite sets
example (s t : Finset α) : s ∪ t = t ∪ s := by
  exact Finset.union_comm

-- Sets
example (s t : Set α) : s ∩ t = t ∩ s := by
  exact Set.inter_comm s t
```

### Domain 5: Number Theory
```lean
import Mathlib.NumberTheory.Divisors
import Mathlib.Data.Nat.Prime.Basic

-- Primes
example : Nat.Prime 7 := by
  norm_num

-- Divisibility
example (a b c : Nat) (h1 : a ∣ b) (h2 : b ∣ c) : a ∣ c := by
  exact Nat.dvd_trans h1 h2
```

## Type Class Patterns

### Pattern 1: Instance Synthesis
Let Lean infer type class instances.

```lean
-- Automatic instance synthesis
example [Add α] (a b : α) : α := a + b  -- Uses [Add α]

-- Manual instance specification (rare)
example : Nat := @Add.add Nat instAddNat 1 2

-- Check instance
#check (inferInstance : Add Nat)
```

### Pattern 2: Instance Diamonds
mathlib4 uses careful design to avoid instance diamonds.

```lean
-- Safe: single path to instance
class A (α : Type)
class B (α : Type) extends A α
class C (α : Type) extends A α
-- No D extending both B and C (would create diamond)

-- If diamonds exist, use priority
instance [A α] : B α := sorry
instance (priority := 100) [A α] : C α := sorry
```

### Pattern 3: Outparam and Infer Instance
```lean
-- Outparam: output parameter (determined by other args)
class HMul (α : Type u) (β : Type v) (γ : outParam (Type w)) where
  hMul : α → β → γ

-- Example: Nat * Nat = Nat
instance : HMul Nat Nat Nat where
  hMul := Nat.mul

-- Infer instance in structures
structure Point (α : Type) [Add α] where
  x : α
  y : α

  add (other : Point α) : Point α :=
    ⟨x + other.x, y + other.y⟩  -- Uses [Add α]
```

## Import Best Practices

### Strategy 1: Minimal Imports
Only import what you need.

```lean
-- BAD: Import everything (slow!)
import Mathlib

-- GOOD: Import specific modules
import Mathlib.Algebra.Group.Defs
import Mathlib.Data.List.Basic
```

### Strategy 2: Import Organization
Group related imports.

```lean
-- Core Lean 4
import Lean
import Std

-- mathlib4: Data structures
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Basic

-- mathlib4: Algebra
import Mathlib.Algebra.Group.Defs
import Mathlib.Algebra.Ring.Defs

-- mathlib4: Topology
import Mathlib.Topology.Basic
```

### Strategy 3: Precompiled Imports
Use precompiled modules for speed.

```lean
-- Create precompiled import file
-- In MyProject/Imports.lean:
import Mathlib.Algebra.Group.Defs
import Mathlib.Algebra.Ring.Defs
import Mathlib.Data.List.Basic

-- In other files:
import MyProject.Imports
```

## Contributing to mathlib4

### Contribution Workflow
```bash
# 1. Fork mathlib4 on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/mathlib4.git
cd mathlib4

# 3. Create branch
git checkout -b my-contribution

# 4. Make changes
# Edit files, add theorems

# 5. Build and test
lake exe cache get
lake build

# 6. Lint
./scripts/lint-style.sh

# 7. Commit and push
git add .
git commit -m "feat: add theorem about groups"
git push origin my-contribution

# 8. Create PR on GitHub
```

### Style Guidelines
```lean
-- Use snake_case for theorems
theorem nat_add_comm (n m : Nat) : n + m = m + n := Nat.add_comm n m

-- Document with docstrings
/-- The sum of two natural numbers is commutative. -/
theorem add_comm (n m : Nat) : n + m = m + n := Nat.add_comm n m

-- Use type classes
theorem mul_comm [CommMagma α] (a b : α) : a * b = b * a := CommMagma.mul_comm a b

-- Prefer term mode for simple proofs
theorem zero_add (n : Nat) : 0 + n = n := Nat.zero_add n

-- Use tactic mode for complex proofs
theorem complex_theorem : P := by
  intro h
  cases h
  · sorry
  · sorry
```

### Naming Conventions
```lean
-- Operations
add, mul, neg, inv, sub, div

-- Properties
comm, assoc, left_distrib, right_distrib
zero, one, inv_mul_cancel

-- Implications
of (← direction), iff (↔)

-- Variants
left, right, neg, inv
```

## Quick Reference

### Common Imports
```lean
-- Algebra
import Mathlib.Algebra.Group.Defs
import Mathlib.Algebra.Ring.Defs
import Mathlib.Algebra.Field.Defs

-- Data structures
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Set.Basic

-- Topology
import Mathlib.Topology.Basic
import Mathlib.Topology.MetricSpace.Basic

-- Analysis
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.Calculus.FDeriv.Basic

-- Number theory
import Mathlib.NumberTheory.Divisors
import Mathlib.Data.Nat.Prime.Basic
```

### Instance Resolution
```lean
#check (inferInstance : Add Nat)  -- Find instance
#synth Add Nat                     -- Synthesize instance
set_option trace.Meta.synthInstance true  -- Debug synthesis
```

### Library Search
```lean
exact?        -- Find exact proof in library
apply?        -- Find applicable theorem
simp?         -- Show which simp lemmas used
#check_failure expr  -- Why doesn't expr typecheck?
```

## Anti-Patterns

### Anti-Pattern 1: Reinventing Wheels
```lean
-- BAD: Define your own addition commutativity
theorem my_add_comm (n m : Nat) : n + m = m + n := by
  induction n <;> simp [Nat.add_succ, *]

-- GOOD: Use mathlib
#check Nat.add_comm  -- Already exists!
```

### Anti-Pattern 2: Ignoring Naming Conventions
```lean
-- BAD: Non-standard names
theorem addComm (n m : Nat) : n + m = m + n := Nat.add_comm n m
theorem AdditionCommutative : ∀ n m, n + m = m + n := Nat.add_comm

-- GOOD: Follow conventions
theorem add_comm (n m : Nat) : n + m = m + n := Nat.add_comm n m
```

### Anti-Pattern 3: Poor Import Organization
```lean
-- BAD: Single massive import
import Mathlib

-- BAD: Disorganized imports
import Mathlib.Topology.Basic
import Mathlib.Data.List.Basic
import Mathlib.Algebra.Group.Defs
import Mathlib.Data.Finset.Basic

-- GOOD: Organized by domain
-- Data structures
import Mathlib.Data.List.Basic
import Mathlib.Data.Finset.Basic

-- Algebra
import Mathlib.Algebra.Group.Defs

-- Topology
import Mathlib.Topology.Basic
```

### Anti-Pattern 4: Over-Specified Instances
```lean
-- BAD: Manually specify instances
example : Nat := @Add.add Nat instAddNat 1 2

-- GOOD: Let Lean infer
example : Nat := 1 + 2
```

### Anti-Pattern 5: Not Using Library Search
```lean
-- BAD: Implement proof from scratch
theorem list_append_nil (xs : List α) : xs ++ [] = xs := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [List.append, ih]

-- GOOD: Search first
theorem list_append_nil (xs : List α) : xs ++ [] = xs := by
  exact?
  -- Try this: exact List.append_nil xs
```

### Anti-Pattern 6: Ignoring Type Class Hierarchy
```lean
-- BAD: Duplicate type class constraints
theorem bad [Add α] [Monoid α] (a b : α) : a + b = b + a := by
  sorry  -- Monoid doesn't imply commutativity anyway!

-- GOOD: Use correct type class
theorem good [AddCommMonoid α] (a b : α) : a + b = b + a :=
  add_comm a b
```

## Related Skills
- **lean-proof-basics.md**: Fundamental proof techniques
- **lean-tactics.md**: Advanced tactics and automation
- **lean-theorem-proving.md**: Formalization strategies
- **lean-metaprogramming.md**: Custom tactics and elaborators

## References
- [mathlib4 Documentation](https://leanprover-community.github.io/mathlib4_docs/)
- [mathlib4 GitHub](https://github.com/leanprover-community/mathlib4)
- [Contributing Guide](https://leanprover-community.github.io/contribute/index.html)
- [mathlib4 Naming Conventions](https://leanprover-community.github.io/contribute/naming.html)
- [Undergrad Math in Lean](https://leanprover-community.github.io/undergrad.html)

## Examples

### Example 1: Using Algebraic Hierarchy
```lean
import Mathlib.Algebra.Group.Defs
import Mathlib.Algebra.Ring.Defs

-- Generic group theorem
theorem inv_unique [Group G] (a b : G) (h : a * b = 1) : b = a⁻¹ := by
  have : a⁻¹ * (a * b) = a⁻¹ * 1 := by rw [h]
  rw [mul_assoc, inv_mul_cancel, one_mul, mul_one] at this
  exact this.symm

-- Ring theorem using type classes
theorem ring_square [Ring R] (a b : R) :
    (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2 := by
  ring
```

### Example 2: List Theorems
```lean
import Mathlib.Data.List.Basic

-- Using existing theorems
theorem list_reverse_append (xs ys : List α) :
    (xs ++ ys).reverse = ys.reverse ++ xs.reverse :=
  List.reverse_append xs ys

-- Building on mathlib
theorem list_reverse_involutive (xs : List α) :
    xs.reverse.reverse = xs :=
  List.reverse_reverse xs
```

### Example 3: Type Class Instance Synthesis
```lean
import Mathlib.Algebra.Group.Defs

-- Let Lean find instances
example : 1 + 1 = 2 := rfl  -- Uses instAddNat

-- Check what instance is used
#check (1 + 1 : Nat)  -- Uses Add.add via instAddNat

-- Synthesize instance explicitly
#synth Add Nat  -- instAddNat
#synth Monoid Nat  -- instMonoidNat
```

---

**Skill Metadata:**
- Scope: mathlib4 library usage and contribution
- Complexity: Intermediate
- Prerequisites: lean-proof-basics.md
- Related: lean-tactics.md, lean-theorem-proving.md
