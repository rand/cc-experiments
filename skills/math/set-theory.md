---
name: math-set-theory
description: Set theory including ZFC axioms, ordinals, cardinals, axiom of choice, and forcing
---

# Set Theory

**Scope**: ZFC axioms, ordinal and cardinal arithmetic, axiom of choice, transfinite induction, forcing
**Lines**: ~380
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding foundations of mathematics
- Working with infinite sets and cardinalities
- Proving results using transfinite induction
- Studying independence results (CH, AC)
- Formalizing mathematics in set-theoretic foundations
- Constructing mathematical objects via ordinals

## Core Concepts

### ZFC Axioms

**Zermelo-Fraenkel Set Theory with Choice**:

```python
# Conceptual representation of ZFC axioms

class ZFC:
    """
    ZFC Axioms (informal Python representation):
    1. Extensionality: Sets equal iff same elements
    2. Empty Set: ∃ set with no elements
    3. Pairing: {a, b} exists for any a, b
    4. Union: ⋃ S exists for any set S
    5. Power Set: 𝒫(S) exists for any S
    6. Infinity: ∃ infinite set (ℕ)
    7. Replacement: Image of set under function is set
    8. Foundation: ∈-minimal element exists (no infinite ∈-descent)
    9. Choice: ∃ choice function for any family of non-empty sets
    """
    
    @staticmethod
    def extensionality(A: set, B: set) -> bool:
        """A = B iff ∀x: x ∈ A ↔ x ∈ B"""
        return A == B
    
    @staticmethod
    def empty_set() -> set:
        """∃ ∅: ∀x: x ∉ ∅"""
        return set()
    
    @staticmethod
    def pairing(a, b) -> set:
        """{a, b} exists"""
        return {a, b}
    
    @staticmethod
    def union(S: set) -> set:
        """⋃ S = {x : ∃A ∈ S: x ∈ A}"""
        result = set()
        for subset in S:
            if isinstance(subset, (set, frozenset)):
                result |= set(subset)
        return result
    
    @staticmethod
    def power_set(S: set) -> set:
        """𝒫(S) = {A : A ⊆ S}"""
        from itertools import chain, combinations
        s_list = list(S)
        return set(
            frozenset(combo) 
            for combo in chain.from_iterable(
                combinations(s_list, r) for r in range(len(s_list) + 1)
            )
        )
    
    @staticmethod
    def natural_numbers() -> set:
        """
        Infinity axiom: ∃ inductive set
        ℕ = {∅, {∅}, {∅, {∅}}, ...}
        In practice, finite representation
        """
        # von Neumann ordinals: 0={}, 1={0}, 2={0,1}, etc.
        omega = set()
        current = frozenset()
        for _ in range(10):  # Finite approximation
            omega.add(current)
            current = frozenset(omega)
        return omega

# Example usage
zfc = ZFC()
empty = zfc.empty_set()
pair = zfc.pairing(1, 2)
union_result = zfc.union({frozenset({1, 2}), frozenset({2, 3})})
print(f"∪ {{{{1,2}}, {{2,3}}}} = {union_result}")  # {1, 2, 3}

power = zfc.power_set({1, 2})
print(f"𝒫({{1,2}}) = {power}")  # {∅, {1}, {2}, {1,2}}
```

### Ordinals

**Definition**: Well-ordered set where every element equals set of predecessors

**von Neumann ordinals**: α = {β : β < α}
- 0 = ∅
- 1 = {0} = {∅}
- 2 = {0, 1} = {∅, {∅}}
- ω = {0, 1, 2, ...} (first infinite ordinal)

```python
class Ordinal:
    """Ordinal number implementation"""
    
    def __init__(self, value):
        """
        For finite ordinals: integer value
        For ω and beyond: special representation
        """
        self.value = value
    
    def __lt__(self, other):
        if isinstance(other.value, int) and isinstance(self.value, int):
            return self.value < other.value
        elif self.value == 'omega':
            return isinstance(other.value, int)  # ω > all finite ordinals
        else:
            # General ordinal comparison
            return self._compare(other) < 0
    
    def __eq__(self, other):
        return self.value == other.value
    
    def successor(self):
        """S(α) = α ∪ {α}"""
        if isinstance(self.value, int):
            return Ordinal(self.value + 1)
        else:
            return Ordinal(f"{self.value}+1")
    
    def __repr__(self):
        return f"Ordinal({self.value})"

# Ordinal arithmetic
def ordinal_addition(alpha: Ordinal, beta: Ordinal):
    """
    α + β defined by transfinite recursion:
    - α + 0 = α
    - α + S(β) = S(α + β)
    - α + λ = sup{α + β : β < λ} for limit λ
    """
    if beta.value == 0:
        return alpha
    elif isinstance(beta.value, int) and beta.value > 0:
        # Finite case
        return Ordinal(alpha.value + beta.value) if isinstance(alpha.value, int) else alpha
    else:
        # Limit case (simplified)
        return Ordinal(f"{alpha.value}+{beta.value}")

def ordinal_multiplication(alpha: Ordinal, beta: Ordinal):
    """
    α · β defined by transfinite recursion:
    - α · 0 = 0
    - α · S(β) = (α · β) + α
    - α · λ = sup{α · β : β < λ} for limit λ
    """
    if beta.value == 0:
        return Ordinal(0)
    elif isinstance(alpha.value, int) and isinstance(beta.value, int):
        return Ordinal(alpha.value * beta.value)
    else:
        return Ordinal(f"{alpha.value}·{beta.value}")

# Examples
omega = Ordinal('omega')
one = Ordinal(1)
print(f"1 + ω = {ordinal_addition(one, omega)}")  # ω (NOT ω+1!)
print(f"ω + 1 = {ordinal_addition(omega, one)}")  # ω+1
print(f"2 · ω = {ordinal_multiplication(Ordinal(2), omega)}")  # ω
print(f"ω · 2 = {ordinal_multiplication(omega, Ordinal(2))}")  # ω+ω = ω·2
```

### Cardinals

**Definition**: Cardinality |A| measures "size" of set A

**Finite cardinals**: |A| = n for some n ∈ ℕ

**Infinite cardinals**:
- ℵ₀ = |ℕ| (countable)
- ℵ₁ = next infinite cardinal
- 2^ℵ₀ = |ℝ| (continuum)

```python
class Cardinal:
    """Cardinal number representation"""
    
    def __init__(self, name, value=None):
        self.name = name
        self.value = value  # Ordinal representation
    
    def __lt__(self, other):
        """κ < λ if ∃ injection but no bijection"""
        # Simplified for demonstration
        cardinal_order = {'aleph_0': 0, '2^aleph_0': 1, 'aleph_1': 2}
        return cardinal_order.get(self.name, float('inf')) < cardinal_order.get(other.name, float('inf'))
    
    def __eq__(self, other):
        return self.name == other.name
    
    def __repr__(self):
        return f"Cardinal({self.name})"

# Cardinal arithmetic
def cardinal_addition(kappa: Cardinal, lambda_: Cardinal):
    """
    κ + λ = max(κ, λ) for infinite cardinals
    """
    if kappa.name == 'aleph_0' and lambda_.name == 'aleph_0':
        return Cardinal('aleph_0')
    else:
        return max(kappa, lambda_, key=lambda c: (c < kappa, c < lambda_))

def cardinal_multiplication(kappa: Cardinal, lambda_: Cardinal):
    """
    κ · λ = max(κ, λ) for infinite cardinals (assuming AC)
    """
    return cardinal_addition(kappa, lambda_)

def cardinal_exponentiation(kappa: Cardinal, lambda_: Cardinal):
    """
    κ^λ = |{f : λ → κ}|
    Special case: 2^ℵ₀ = continuum
    """
    if kappa.name == '2' and lambda_.name == 'aleph_0':
        return Cardinal('2^aleph_0')
    else:
        return Cardinal(f"{kappa.name}^{lambda_.name}")

# Examples
aleph_0 = Cardinal('aleph_0')
continuum = Cardinal('2^aleph_0')
print(f"ℵ₀ + ℵ₀ = {cardinal_addition(aleph_0, aleph_0)}")  # ℵ₀
print(f"ℵ₀ · ℵ₀ = {cardinal_multiplication(aleph_0, aleph_0)}")  # ℵ₀
print(f"2^ℵ₀ = {cardinal_exponentiation(Cardinal('2'), aleph_0)}")  # continuum
```

### Axiom of Choice

**Axiom of Choice (AC)**: For any family {A_i}_{i∈I} of non-empty sets, ∃ choice function f: I → ⋃A_i with f(i) ∈ A_i

**Equivalent formulations**:
- Zorn's Lemma: Every chain in poset has maximal element
- Well-Ordering Theorem: Every set can be well-ordered

```python
def choice_function(family: dict) -> dict:
    """
    Given family {A_i : i ∈ I}, construct choice function
    f: I → ⋃ A_i with f(i) ∈ A_i
    
    In constructive math, may not exist without AC
    """
    choice = {}
    for index, set_i in family.items():
        if not set_i:
            raise ValueError(f"Set A_{index} is empty")
        # Choose arbitrary element (requires AC in general)
        choice[index] = next(iter(set_i))
    return choice

# Example: Product of non-empty sets is non-empty
def cartesian_product_nonempty(sets: list[set]) -> bool:
    """
    ∏ A_i ≠ ∅ iff ∀i: A_i ≠ ∅
    Requires AC for infinite products
    """
    if not sets:
        return True
    
    # Use choice function
    family = {i: s for i, s in enumerate(sets)}
    try:
        choice = choice_function(family)
        return True
    except ValueError:
        return False
```

### Transfinite Induction

**Principle**: To prove P(α) for all ordinals α:
1. Base case: P(0)
2. Successor: P(α) ⟹ P(α+1)
3. Limit: (∀β < λ: P(β)) ⟹ P(λ) for limit ordinal λ

```python
def transfinite_induction(property_P, ordinal_limit):
    """
    Verify property P for all ordinals up to limit
    
    property_P: function taking ordinal, returning bool
    ordinal_limit: maximum ordinal to check
    """
    
    # Base case
    if not property_P(Ordinal(0)):
        return False
    
    # Successor case (check finite ordinals)
    for alpha in range(ordinal_limit):
        if not property_P(Ordinal(alpha)):
            return False
        # Verify successor step
        if not property_P(Ordinal(alpha + 1)):
            return False
    
    # Limit case would check supremum property
    # (simplified for finite case)
    
    return True

# Example: Prove every ordinal is well-ordered
def is_well_ordered(alpha: Ordinal) -> bool:
    """Check if α is well-ordered"""
    # Every ordinal is well-ordered by construction
    return True

# Verify by transfinite induction
result = transfinite_induction(is_well_ordered, ordinal_limit=100)
print(f"All ordinals up to 100 are well-ordered: {result}")
```

---

## Patterns

### Pattern 1: Cantor's Diagonal Argument

**Theorem**: ℕ and ℝ have different cardinalities (|ℕ| < |ℝ|)

```python
def cantors_diagonal():
    """
    Prove no bijection ℕ → (0,1)
    Given any sequence of reals, construct real not in sequence
    """
    # Suppose f: ℕ → (0,1) is surjective
    # Represent reals as infinite decimals
    sequence = [
        "0.1234567890...",
        "0.9876543210...",
        "0.5555555555...",
        # ... infinite sequence
    ]
    
    # Construct diagonal real differing at each position
    diagonal = "0."
    for i, real_str in enumerate(sequence[:10]):  # Finite approximation
        digit = real_str[2 + i]  # i-th digit after decimal
        # Choose different digit
        new_digit = '5' if digit != '5' else '7'
        diagonal += new_digit
    
    print(f"Diagonal real: {diagonal}")
    print("This real differs from every real in sequence")
    print("Therefore, no surjection ℕ → (0,1) exists")
    
    return diagonal
```

### Pattern 2: Continuum Hypothesis

**CH**: There is no cardinality strictly between ℵ₀ and 2^ℵ₀

**Statement**: 2^ℵ₀ = ℵ₁ (continuum equals first uncountable cardinal)

**Status**: Independent of ZFC (neither provable nor disprovable)

```python
def continuum_hypothesis():
    """
    CH: 2^ℵ₀ = ℵ₁
    
    Results:
    - Gödel (1940): CH consistent with ZFC (using L, constructible universe)
    - Cohen (1963): ¬CH consistent with ZFC (using forcing)
    - Therefore: CH independent of ZFC
    """
    return {
        'statement': '2^ℵ₀ = ℵ₁',
        'status': 'independent of ZFC',
        'models': {
            'L (constructible universe)': 'CH holds',
            'forcing extensions': '¬CH can hold (e.g., 2^ℵ₀ = ℵ₂)'
        }
    }
```

### Pattern 3: Borel Hierarchy

**Σ⁰_n, Π⁰_n**: Levels of definability for subsets of ℝ

```python
class BorelHierarchy:
    """
    Borel sets hierarchy:
    - Σ⁰₁ = open sets
    - Π⁰₁ = closed sets (complements of Σ⁰₁)
    - Σ⁰₂ = countable unions of Π⁰₁
    - Π⁰₂ = countable intersections of Σ⁰₁
    - ...
    """
    
    @staticmethod
    def is_sigma_0_1(description: str) -> bool:
        """Check if set is Σ⁰₁ (open)"""
        return 'union of open intervals' in description
    
    @staticmethod
    def is_pi_0_1(description: str) -> bool:
        """Check if set is Π⁰₁ (closed)"""
        return 'complement of open set' in description or 'closed' in description
    
    @staticmethod
    def is_sigma_0_2(description: str) -> bool:
        """Check if set is Σ⁰₂"""
        return 'countable union of closed sets' in description
```

---

## Quick Reference

### Cardinality Comparisons

| Set | Cardinality | Symbol |
|-----|------------|--------|
| ℕ | Countable | ℵ₀ |
| ℤ | Countable | ℵ₀ |
| ℚ | Countable | ℵ₀ |
| ℝ | Continuum | 2^ℵ₀ |
| 𝒫(ℕ) | Continuum | 2^ℵ₀ |
| ℝ^ℕ | Uncountable | 2^ℵ₀ |

### Ordinal Arithmetic

```
Addition (not commutative):
  1 + ω = ω
  ω + 1 = ω + 1 (≠ ω)

Multiplication (not commutative):
  2 · ω = ω
  ω · 2 = ω + ω (≠ ω)

Exponentiation:
  ω^2 = ω · ω
  2^ω = sup{2^n : n < ω} = ω
```

### ZFC Independence Results

| Statement | Status |
|-----------|--------|
| Continuum Hypothesis (CH) | Independent |
| Axiom of Choice (AC) | Independent of ZF |
| Generalized CH (GCH) | Independent |

---

## Anti-Patterns

❌ **Treating ordinals like cardinals**: ω + 1 ≠ 1 + ω as ordinals
✅ Ordinal arithmetic is not commutative

❌ **Assuming CH is provable**: CH independent of ZFC
✅ Some models satisfy CH, others don't

❌ **Confusing ∈ and ⊆**: For ordinals, α ∈ β iff α ⊂ β (proper subset)
✅ In von Neumann ordinals, ∈ and < coincide

❌ **Assuming all sets are countable**: ℝ is uncountable by Cantor's theorem
✅ Use diagonal argument to prove uncountability

---

## Related Skills

- `abstract-algebra.md` - Algebraic structures built on sets
- `number-theory.md` - Properties of specific sets (ℕ, ℤ, ℚ)
- `topology-point-set.md` - Topological spaces on sets
- `category-theory-foundations.md` - Category of sets
- `formal/lean-mathlib4.md` - Formalizing set theory in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
