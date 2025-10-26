---
name: abstract-algebra
description: Abstract algebra including groups, rings, fields, Galois theory, and algebraic structures
---

# Abstract Algebra

**Scope**: Groups, rings, fields, homomorphisms, quotient structures, Galois theory
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Studying symmetry and group actions
- Working with polynomial rings and field extensions
- Understanding quotient structures and homomorphisms
- Applying Galois theory to polynomial equations
- Implementing algebraic algorithms (GCD, factorization)
- Formalizing algebraic proofs in theorem provers

## Core Concepts

### Groups

**Definition**: A group (G, ·) is a set G with binary operation · satisfying:
- Closure: a, b ∈ G ⟹ a · b ∈ G
- Associativity: (a · b) · c = a · (b · c)
- Identity: ∃e ∈ G: e · a = a · e = a
- Inverse: ∀a ∈ G, ∃a⁻¹: a · a⁻¹ = a⁻¹ · a = e

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')

class Group(ABC, Generic[T]):
    """Abstract base class for groups"""
    
    @abstractmethod
    def op(self, a: T, b: T) -> T:
        """Group operation"""
        pass
    
    @abstractmethod
    def identity(self) -> T:
        """Identity element"""
        pass
    
    @abstractmethod
    def inverse(self, a: T) -> T:
        """Inverse of element"""
        pass
    
    def associative_check(self, a: T, b: T, c: T) -> bool:
        """Verify associativity"""
        return self.op(self.op(a, b), c) == self.op(a, self.op(b, c))

# Example: Integers mod n under addition
class ZnAdditive(Group[int]):
    def __init__(self, n: int):
        self.n = n
    
    def op(self, a: int, b: int) -> int:
        return (a + b) % self.n
    
    def identity(self) -> int:
        return 0
    
    def inverse(self, a: int) -> int:
        return (self.n - a) % self.n

# Example: Symmetric group S_n
class SymmetricGroup(Group[tuple]):
    def __init__(self, n: int):
        self.n = n
    
    def op(self, sigma: tuple, tau: tuple) -> tuple:
        """Compose permutations: (σ ∘ τ)(i) = σ(τ(i))"""
        return tuple(sigma[tau[i]] for i in range(self.n))
    
    def identity(self) -> tuple:
        return tuple(range(self.n))
    
    def inverse(self, sigma: tuple) -> tuple:
        """Find inverse permutation"""
        inv = [0] * self.n
        for i, s in enumerate(sigma):
            inv[s] = i
        return tuple(inv)

# Usage
Z5 = ZnAdditive(5)
print(f"3 + 4 mod 5 = {Z5.op(3, 4)}")  # 2
print(f"Inverse of 3 mod 5 = {Z5.inverse(3)}")  # 2

S3 = SymmetricGroup(3)
sigma = (1, 2, 0)  # Permutation (0→1, 1→2, 2→0)
tau = (0, 2, 1)    # Permutation (0→0, 1→2, 2→1)
print(f"σ ∘ τ = {S3.op(sigma, tau)}")
```

**Subgroups**: H ⊆ G is a subgroup if H is itself a group under the same operation

**Lagrange's Theorem**: If H ⊆ G is a subgroup, then |H| divides |G|

```python
def is_subgroup(G: Group, H: set) -> bool:
    """Check if H is a subgroup of G"""
    if not H:
        return False
    
    # Check closure
    for a in H:
        for b in H:
            if G.op(a, b) not in H:
                return False
    
    # Check identity
    if G.identity() not in H:
        return False
    
    # Check inverses
    for a in H:
        if G.inverse(a) not in H:
            return False
    
    return True
```

### Rings

**Definition**: A ring (R, +, ·) is a set R with two operations satisfying:
- (R, +) is an abelian group
- · is associative with identity (for rings with unity)
- Distributive laws: a·(b+c) = a·b + a·c, (a+b)·c = a·c + b·c

```python
class Ring(ABC, Generic[T]):
    """Abstract base class for rings"""
    
    @abstractmethod
    def add(self, a: T, b: T) -> T:
        pass
    
    @abstractmethod
    def multiply(self, a: T, b: T) -> T:
        pass
    
    @abstractmethod
    def zero(self) -> T:
        """Additive identity"""
        pass
    
    @abstractmethod
    def one(self) -> T:
        """Multiplicative identity"""
        pass
    
    @abstractmethod
    def negate(self, a: T) -> T:
        """Additive inverse"""
        pass

# Example: Polynomial ring ℤ[x]
class PolynomialRing(Ring[list]):
    """Polynomials with integer coefficients"""
    
    def add(self, p: list, q: list) -> list:
        """Add polynomials (coefficients lists)"""
        n = max(len(p), len(q))
        result = [0] * n
        for i in range(len(p)):
            result[i] += p[i]
        for i in range(len(q)):
            result[i] += q[i]
        # Remove leading zeros
        while len(result) > 1 and result[-1] == 0:
            result.pop()
        return result
    
    def multiply(self, p: list, q: list) -> list:
        """Multiply polynomials"""
        if not p or not q:
            return [0]
        result = [0] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            for j, b in enumerate(q):
                result[i + j] += a * b
        return result
    
    def zero(self) -> list:
        return [0]
    
    def one(self) -> list:
        return [1]
    
    def negate(self, p: list) -> list:
        return [-c for c in p]

# Usage
Z_poly = PolynomialRing()
p = [1, 2, 1]  # x² + 2x + 1 = (x+1)²
q = [1, -1]    # x - 1
product = Z_poly.multiply(p, q)
print(f"(x²+2x+1)(x-1) = {product}")  # [1, 1, -1, -1] = x³ + x² - x - 1
```

**Ideals**: Subset I ⊆ R where:
- I is a subgroup under addition
- For all r ∈ R, a ∈ I: r·a ∈ I and a·r ∈ I

**Quotient Rings**: R/I = {a + I : a ∈ R}

```python
def gcd_polynomials(p: list, q: list) -> list:
    """Euclidean algorithm for polynomial GCD"""
    poly_ring = PolynomialRing()
    
    def degree(poly):
        return len(poly) - 1 if poly != [0] else -float('inf')
    
    def divide(dividend, divisor):
        """Polynomial division, returns (quotient, remainder)"""
        if degree(divisor) > degree(dividend):
            return [0], dividend
        
        quotient = []
        remainder = dividend[:]
        
        while degree(remainder) >= degree(divisor):
            # Leading coefficient
            coeff = remainder[-1] // divisor[-1]
            deg_diff = degree(remainder) - degree(divisor)
            
            # Subtract divisor * (coeff * x^deg_diff)
            term = [0] * deg_diff + [coeff]
            subtrahend = poly_ring.multiply(divisor, term)
            
            quotient = poly_ring.add(quotient, term)
            remainder = poly_ring.add(remainder, poly_ring.negate(subtrahend))
        
        return quotient, remainder
    
    # Euclidean algorithm
    a, b = p, q
    while b != [0]:
        _, r = divide(a, b)
        a, b = b, r
    
    return a

# Example: gcd(x² - 1, x³ - 1)
p1 = [-1, 0, 1]   # x² - 1
p2 = [-1, 0, 0, 1]  # x³ - 1
gcd = gcd_polynomials(p1, p2)
print(f"gcd(x²-1, x³-1) = {gcd}")  # [1, -1] = x - 1
```

### Fields

**Definition**: A field (F, +, ·) is a commutative ring where every non-zero element has a multiplicative inverse

**Examples**: ℚ, ℝ, ℂ, ℤ/pℤ (p prime), finite fields 𝔽_q

```python
class FiniteField:
    """Finite field ℤ/pℤ for prime p"""
    
    def __init__(self, p: int):
        if not self._is_prime(p):
            raise ValueError(f"{p} is not prime")
        self.p = p
    
    @staticmethod
    def _is_prime(n: int) -> bool:
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True
    
    def add(self, a: int, b: int) -> int:
        return (a + b) % self.p
    
    def multiply(self, a: int, b: int) -> int:
        return (a * b) % self.p
    
    def inverse(self, a: int) -> int:
        """Multiplicative inverse via extended Euclidean algorithm"""
        if a % self.p == 0:
            raise ValueError("Zero has no inverse")
        
        # Extended Euclidean algorithm
        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1
            return gcd, x, y
        
        _, x, _ = extended_gcd(a % self.p, self.p)
        return x % self.p
    
    def divide(self, a: int, b: int) -> int:
        """a / b = a · b⁻¹"""
        return self.multiply(a, self.inverse(b))

# Example: Field ℤ/7ℤ
F7 = FiniteField(7)
print(f"3 + 5 mod 7 = {F7.add(3, 5)}")  # 1
print(f"3 * 5 mod 7 = {F7.multiply(3, 5)}")  # 1
print(f"3⁻¹ mod 7 = {F7.inverse(3)}")  # 5
print(f"2 / 3 mod 7 = {F7.divide(2, 3)}")  # 3 (since 2/3 = 2·5 = 10 = 3 mod 7)
```

### Homomorphisms

**Definition**: φ: G → H is a group homomorphism if φ(a · b) = φ(a) · φ(b)

**Kernel**: ker(φ) = {g ∈ G : φ(g) = e_H}
**Image**: im(φ) = {φ(g) : g ∈ G}

**First Isomorphism Theorem**: G/ker(φ) ≅ im(φ)

```python
class GroupHomomorphism:
    def __init__(self, domain: Group, codomain: Group, mapping: callable):
        self.domain = domain
        self.codomain = codomain
        self.phi = mapping
    
    def preserves_operation(self, a, b) -> bool:
        """Check φ(a·b) = φ(a)·φ(b)"""
        lhs = self.phi(self.domain.op(a, b))
        rhs = self.codomain.op(self.phi(a), self.phi(b))
        return lhs == rhs
    
    def kernel(self, elements: set) -> set:
        """ker(φ) = {g ∈ G : φ(g) = e_H}"""
        e_H = self.codomain.identity()
        return {g for g in elements if self.phi(g) == e_H}
    
    def image(self, elements: set) -> set:
        """im(φ) = {φ(g) : g ∈ G}"""
        return {self.phi(g) for g in elements}

# Example: Sign homomorphism S_n → {±1}
def sign_permutation(sigma: tuple) -> int:
    """Compute sign of permutation (1 for even, -1 for odd)"""
    n = len(sigma)
    inversions = 0
    for i in range(n):
        for j in range(i + 1, n):
            if sigma[i] > sigma[j]:
                inversions += 1
    return 1 if inversions % 2 == 0 else -1
```

### Galois Theory

**Field Extension**: K/F where F ⊆ K are fields

**Galois Group**: Gal(K/F) = {automorphisms σ: K → K fixing F}

**Fundamental Theorem**: Correspondence between intermediate fields and subgroups

```python
class FieldExtension:
    """Represent field extension K/F"""
    
    def __init__(self, base_field, extension_field, minimal_polynomial):
        self.F = base_field
        self.K = extension_field
        self.min_poly = minimal_polynomial
    
    def degree(self) -> int:
        """[K:F] = degree of extension"""
        return len(self.min_poly) - 1
    
    def is_galois(self) -> bool:
        """Check if extension is Galois (normal + separable)"""
        # Simplified check: polynomial splits completely
        # In practice, need to verify all roots are in K
        return self._splits_completely()
    
    def _splits_completely(self) -> bool:
        """Check if minimal polynomial splits into linear factors"""
        # Placeholder: would need to factor polynomial over K
        pass

# Example: ℚ(√2) / ℚ
# Minimal polynomial: x² - 2
# Galois group: {id, σ} where σ(√2) = -√2
# Gal(ℚ(√2)/ℚ) ≅ ℤ/2ℤ

def galois_group_quadratic():
    """
    For ℚ(√d)/ℚ where d is square-free:
    Galois group is {id, σ} where σ(√d) = -√d
    Isomorphic to ℤ/2ℤ
    """
    return {
        'elements': ['id', 'sigma'],
        'operation': {
            ('id', 'id'): 'id',
            ('id', 'sigma'): 'sigma',
            ('sigma', 'id'): 'sigma',
            ('sigma', 'sigma'): 'id'
        },
        'isomorphic_to': 'Z/2Z'
    }
```

---

## Patterns

### Pattern 1: Quotient Structures

**Quotient Group**: G/N where N is normal subgroup

```python
def quotient_group(G: Group, N: set, elements: set):
    """
    Construct quotient group G/N
    Elements are cosets {gN : g ∈ G}
    """
    cosets = {}
    
    for g in elements:
        # Compute left coset gN = {g·n : n ∈ N}
        coset = frozenset(G.op(g, n) for n in N)
        
        # Representative is minimal element (for canonical form)
        rep = min(coset)
        cosets[rep] = coset
    
    # Quotient operation: (g₁N)(g₂N) = (g₁g₂)N
    def quotient_op(coset1_rep, coset2_rep):
        product = G.op(coset1_rep, coset2_rep)
        # Find canonical representative
        product_coset = frozenset(G.op(product, n) for n in N)
        return min(product_coset)
    
    return {
        'cosets': cosets,
        'operation': quotient_op,
        'identity': min(N)  # eN = N
    }
```

### Pattern 2: Chinese Remainder Theorem

**For Rings**: If I, J are coprime ideals, R/(I ∩ J) ≅ R/I × R/J

```python
def chinese_remainder_theorem(moduli: list[int], remainders: list[int]) -> int:
    """
    Solve system: x ≡ a_i (mod n_i)
    Requires moduli to be pairwise coprime
    """
    from math import gcd
    
    # Verify coprimality
    for i in range(len(moduli)):
        for j in range(i + 1, len(moduli)):
            if gcd(moduli[i], moduli[j]) != 1:
                raise ValueError("Moduli must be coprime")
    
    # Compute solution
    N = 1
    for n in moduli:
        N *= n
    
    x = 0
    for i, (n_i, a_i) in enumerate(zip(moduli, remainders)):
        N_i = N // n_i
        # Find M_i such that N_i * M_i ≡ 1 (mod n_i)
        _, M_i, _ = extended_gcd(N_i, n_i)
        x += a_i * N_i * M_i
    
    return x % N

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

# Example
moduli = [3, 5, 7]
remainders = [2, 3, 2]  # x ≡ 2 (mod 3), x ≡ 3 (mod 5), x ≡ 2 (mod 7)
solution = chinese_remainder_theorem(moduli, remainders)
print(f"Solution: x ≡ {solution} (mod {3*5*7})")  # x = 23
```

### Pattern 3: Sylow Theorems

**Sylow's First Theorem**: If p^k divides |G|, ∃ subgroup of order p^k

```python
def sylow_p_subgroups(G: Group, elements: set, p: int) -> list:
    """
    Find Sylow p-subgroups (maximal p-subgroups)
    For group G with |G| = p^k · m where p ∤ m
    """
    n = len(elements)
    
    # Find k where p^k divides n
    k = 0
    temp = n
    while temp % p == 0:
        k += 1
        temp //= p
    
    p_k = p ** k
    
    # Find all subgroups of order p^k
    # (In practice, use more efficient algorithms)
    sylow_subgroups = []
    
    # Placeholder: would enumerate and check
    # Real implementation uses permutation group algorithms
    
    return sylow_subgroups
```

---

## Quick Reference

### Group Properties

| Property | Definition | Example |
|----------|-----------|---------|
| Abelian | a·b = b·a | (ℤ, +) |
| Cyclic | G = ⟨g⟩ for some g | ℤ/nℤ |
| Simple | No normal subgroups except {e}, G | A_n (n≥5) |
| Solvable | Subnormal series with abelian quotients | S_n (n≤4) |

### Ring Types

| Type | Definition | Example |
|------|-----------|---------|
| Integral Domain | No zero divisors | ℤ |
| Principal Ideal Domain (PID) | Every ideal is principal | ℤ, k[x] |
| Unique Factorization Domain (UFD) | Unique prime factorization | ℤ[x] |
| Euclidean Domain | Has Euclidean algorithm | ℤ, k[x] |

### Field Extensions

| Concept | Definition | Example |
|---------|-----------|---------|
| Degree | [K:F] = dimF(K) | [ℂ:ℝ] = 2 |
| Algebraic | α root of polynomial over F | √2 over ℚ |
| Transcendental | Not algebraic | π over ℚ |
| Splitting field | Smallest field where polynomial splits | ℚ(√2, √3) |

---

## Anti-Patterns

❌ **Confusing quotient with subset**: G/N is set of cosets, not subset of G
✅ Elements of G/N are equivalence classes gN

❌ **Assuming all rings are commutative**: Matrix rings are non-commutative
✅ Always check if ab = ba when needed

❌ **Ignoring characteristic**: Field of char p has p·1 = 0
✅ Verify characteristic when working with finite fields

❌ **Assuming field extensions are Galois**: Need normal + separable
✅ Check if minimal polynomial splits completely

---

## Related Skills

- `set-theory.md` - Set-theoretic foundations for algebra
- `number-theory.md` - Applications to integers and primes
- `linear-algebra-computation.md` - Vector spaces over fields
- `category-theory-foundations.md` - Categorical perspective on algebra
- `formal/lean-mathlib4.md` - Formalizing algebra in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
