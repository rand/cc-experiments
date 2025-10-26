---
name: category-theory-foundations
description: Category theory foundations including categories, functors, natural transformations, limits, and adjunctions
---

# Category Theory Foundations

**Scope**: Categories, functors, natural transformations, limits/colimits, adjunctions, Yoneda lemma
**Lines**: ~450
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding abstract mathematical structures uniformly
- Working with functors between categories (homology, fundamental group)
- Designing composable abstractions in functional programming
- Studying universal properties (products, coproducts, limits)
- Understanding monads, functors, natural transformations in Haskell/Scala
- Formalizing mathematical concepts categorically

## Core Concepts

### Categories

**Definition**: A category C consists of:
- Objects: ob(C)
- Morphisms: For objects A, B, a set hom(A, B) of morphisms f: A → B
- Composition: For f: A → B and g: B → C, composition g ∘ f: A → C
- Identity: For each object A, identity morphism id_A: A → A

**Axioms**:
- Associativity: h ∘ (g ∘ f) = (h ∘ g) ∘ f
- Identity: f ∘ id_A = f = id_B ∘ f

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')

class Category(ABC):
    """Abstract base for category"""

    @abstractmethod
    def objects(self):
        """Return collection of objects"""
        pass

    @abstractmethod
    def morphisms(self, source, target):
        """Return morphisms from source to target"""
        pass

    @abstractmethod
    def compose(self, f, g):
        """Compose g ∘ f"""
        pass

    @abstractmethod
    def identity(self, obj):
        """Return identity morphism for object"""
        pass

# Example: Category of Sets
class Set_Category(Category):
    """Category Set: objects are sets, morphisms are functions"""

    def objects(self):
        # Conceptual: all sets (can't enumerate)
        return "All sets"

    def morphisms(self, source, target):
        # All functions from source to target
        return f"Functions: {source} → {target}"

    def compose(self, f, g):
        """g ∘ f"""
        return lambda x: g(f(x))

    def identity(self, obj):
        """id(x) = x"""
        return lambda x: x

# Example usage
Set = Set_Category()
f = lambda x: x + 1  # ℕ → ℕ
g = lambda x: x * 2  # ℕ → ℕ
h = Set.compose(f, g)  # h(x) = g(f(x)) = 2(x+1)
print(h(3))  # 8
```

**Common categories**:
```python
def category_examples():
    """Common mathematical categories"""
    return {
        'Set': 'Sets and functions',
        'Grp': 'Groups and group homomorphisms',
        'Ring': 'Rings and ring homomorphisms',
        'Vect_k': 'Vector spaces over field k, linear maps',
        'Top': 'Topological spaces and continuous maps',
        'Poset': 'Partially ordered sets, monotone functions',
        'Cat': 'Small categories and functors',
        'Hask': 'Haskell types and functions (idealized)'
    }
```

### Functors

**Definition**: Functor F: C → D maps:
- Objects: F(A) ∈ ob(D) for A ∈ ob(C)
- Morphisms: F(f: A → B) = F(f): F(A) → F(B)

**Axioms**:
- F(id_A) = id_{F(A)}
- F(g ∘ f) = F(g) ∘ F(f)

```python
class Functor(ABC):
    """Abstract functor between categories"""

    def __init__(self, source_category, target_category):
        self.source = source_category
        self.target = target_category

    @abstractmethod
    def map_object(self, obj):
        """F(A)"""
        pass

    @abstractmethod
    def map_morphism(self, f):
        """F(f: A → B): F(A) → F(B)"""
        pass

# Example: List functor in programming
class ListFunctor(Functor):
    """F(A) = List[A] in Hask"""

    def map_object(self, type_a):
        """F(A) = List[A]"""
        return f"List[{type_a}]"

    def map_morphism(self, f):
        """
        F(f: A → B) = map(f): List[A] → List[B]
        """
        return lambda xs: [f(x) for x in xs]

# Usage
list_functor = ListFunctor(None, None)
f = lambda x: x * 2  # Int → Int
F_f = list_functor.map_morphism(f)  # List[Int] → List[Int]
print(F_f([1, 2, 3]))  # [2, 4, 6]
```

**Contravariant functors**: Reverse arrow direction
```python
class ContravariantFunctor(Functor):
    """F: C^op → D (reverses arrows)"""

    @abstractmethod
    def map_morphism(self, f):
        """F(f: A → B): F(B) → F(A) (reversed!)"""
        pass

# Example: Hom functor hom(-, B): C^op → Set
def hom_functor(B):
    """hom(-, B) sends A ↦ hom(A, B)"""
    return lambda A: f"Functions from {A} to {B}"
```

### Natural Transformations

**Definition**: Natural transformation η: F ⇒ G between functors F, G: C → D
- Components: η_A: F(A) → G(A) for each object A
- Naturality: For f: A → B, the square commutes:
  ```
  F(A) --η_A--> G(A)
   |             |
  F(f)          G(f)
   |             |
   v             v
  F(B) --η_B--> G(B)
  ```
  i.e., G(f) ∘ η_A = η_B ∘ F(f)

```python
class NaturalTransformation:
    """Natural transformation η: F ⇒ G"""

    def __init__(self, source_functor, target_functor):
        self.F = source_functor
        self.G = target_functor
        self.components = {}

    def component(self, obj):
        """η_A: F(A) → G(A)"""
        return self.components.get(obj)

    def set_component(self, obj, morphism):
        """Define component at object"""
        self.components[obj] = morphism

    def verify_naturality(self, f, source_obj, target_obj):
        """Check: G(f) ∘ η_A = η_B ∘ F(f)"""
        η_A = self.component(source_obj)
        η_B = self.component(target_obj)
        Ff = self.F.map_morphism(f)
        Gf = self.G.map_morphism(f)

        # Would need to check equality of composed morphisms
        return "Naturality condition (conceptual check)"

# Example: List to Maybe natural transformation
# length: List[A] → Maybe[Int]
def list_to_maybe_length():
    """η: List ⇒ Maybe where η_A(xs) = Just(len(xs)) if xs non-empty"""
    def component(type_a):
        def eta(xs):
            if xs:
                return ('Just', len(xs))
            else:
                return ('Nothing', None)
        return eta
    return component
```

### Universal Properties and Limits

**Product**: A × B with projections π₁: A × B → A, π₂: A × B → B
Universal property: For any Z with f: Z → A, g: Z → B,
∃! h: Z → A × B such that π₁ ∘ h = f and π₂ ∘ h = g

```python
class Product:
    """Categorical product A × B"""

    def __init__(self, A, B):
        self.A = A
        self.B = B
        self.product = (A, B)  # Conceptual tuple

    def projection1(self):
        """π₁: A × B → A"""
        return lambda pair: pair[0]

    def projection2(self):
        """π₂: A × B → B"""
        return lambda pair: pair[1]

    def universal_morphism(self, f, g):
        """
        Given f: Z → A, g: Z → B
        Return h: Z → A × B (unique)
        """
        return lambda z: (f(z), g(z))

# Example in Set
A, B = "A", "B"
prod = Product(A, B)

# Universal property: pairing
f = lambda z: f"f({z})"  # Z → A
g = lambda z: f"g({z})"  # Z → B
h = prod.universal_morphism(f, g)  # Z → A × B

z0 = "z0"
print(h(z0))  # ('f(z0)', 'g(z0)')
print(prod.projection1()(h(z0)))  # 'f(z0)' = f(z0) ✓
```

**Coproduct (sum)**: A + B with injections ι₁: A → A + B, ι₂: B → A + B
Universal property: Dual to product

```python
class Coproduct:
    """Categorical coproduct A + B (disjoint union)"""

    def __init__(self, A, B):
        self.A = A
        self.B = B

    def injection1(self):
        """ι₁: A → A + B"""
        return lambda a: ('Left', a)

    def injection2(self):
        """ι₂: B → A + B"""
        return lambda b: ('Right', b)

    def universal_morphism(self, f, g):
        """
        Given f: A → Z, g: B → Z
        Return h: A + B → Z (unique)
        """
        def h(coproduct_elem):
            tag, value = coproduct_elem
            if tag == 'Left':
                return f(value)
            else:  # 'Right'
                return g(value)
        return h

# Example: Either a b in Haskell
# Either a b = Left a | Right b (coproduct)
```

### Adjunctions

**Definition**: Functor F: C → D is left adjoint to G: D → C (F ⊣ G) if:
hom_D(F(A), B) ≅ hom_C(A, G(B)) naturally in A and B

**Unit and counit**:
- Unit: η: 1_C ⇒ G ∘ F
- Counit: ε: F ∘ G ⇒ 1_D

```python
class Adjunction:
    """F ⊣ G: Adjunction between functors"""

    def __init__(self, left_adjoint, right_adjoint):
        self.F = left_adjoint  # F: C → D
        self.G = right_adjoint  # G: D → C

    def unit(self):
        """η: Id ⇒ G ∘ F"""
        # For each A in C, η_A: A → G(F(A))
        pass

    def counit(self):
        """ε: F ∘ G ⇒ Id"""
        # For each B in D, ε_B: F(G(B)) → B
        pass

# Example: Free-Forgetful adjunction
# Free: Set → Grp (free group functor)
# Forgetful: Grp → Set (forget group structure)
# Free ⊣ Forgetful
```

### Monads

**Definition**: Monad on category C is a triple (M, η, μ) where:
- M: C → C is endofunctor
- η: 1_C ⇒ M (unit)
- μ: M ∘ M ⇒ M (multiplication)

**Axioms**:
- μ ∘ M(μ) = μ ∘ μ(M) (associativity)
- μ ∘ η(M) = μ ∘ M(η) = id_M (unit laws)

```python
class Monad:
    """Monad (M, η, μ)"""

    def __init__(self, functor_m):
        self.M = functor_m

    def unit(self, x):
        """η: a → M(a) (return/pure)"""
        raise NotImplementedError

    def join(self, mmx):
        """μ: M(M(a)) → M(a) (flatten)"""
        raise NotImplementedError

    def bind(self, mx, f):
        """
        (>>=): M(a) → (a → M(b)) → M(b)
        bind(mx, f) = μ(M(f)(mx))
        """
        # Apply f to get M(M(b)), then join
        mmx = self.M.map_morphism(f)(mx)
        return self.join(mmx)

# Example: List monad
class ListMonad(Monad):
    """List monad in Python"""

    def unit(self, x):
        """η(x) = [x]"""
        return [x]

    def join(self, lists):
        """μ([[x]]) = [x] (flatten)"""
        result = []
        for lst in lists:
            result.extend(lst)
        return result

    def bind(self, xs, f):
        """xs >>= f = concat(map(f, xs))"""
        return self.join([f(x) for x in xs])

# Usage
list_monad = ListMonad(None)
xs = [1, 2, 3]
f = lambda x: [x, -x]  # a → [a]
result = list_monad.bind(xs, f)  # [1, -1, 2, -2, 3, -3]
print(result)
```

---

## Patterns

### Pattern 1: Yoneda Lemma

**Statement**: Natural transformations η: hom(A, -) ⇒ F correspond bijectively to elements of F(A)
- Given η, get x ∈ F(A) by x = η_A(id_A)
- Given x ∈ F(A), define η_B(f: A → B) = F(f)(x)

```python
def yoneda_embedding():
    """
    Yoneda: C → Set^(C^op)
    A ↦ hom(-, A)
    Fully faithful embedding
    """
    def embed(obj):
        # Returns functor hom(-, obj)
        return lambda x: f"hom({x}, {obj})"

    return embed
```

### Pattern 2: Functoriality of Homology

**Homology as functor**: H_n: Top → Grp
- Sends spaces to abelian groups
- Sends continuous maps to group homomorphisms
- H_n(g ∘ f) = H_n(g) ∘ H_n(f)

```python
# Conceptual: H_n functor
class HomologyFunctor(Functor):
    def __init__(self, n):
        self.degree = n

    def map_object(self, space):
        """H_n(X) = n-th homology group"""
        return f"H_{self.degree}({space})"

    def map_morphism(self, f):
        """f: X → Y induces f_*: H_n(X) → H_n(Y)"""
        return f"induced_homomorphism({f})"
```

### Pattern 3: Curry-Howard-Lambek Correspondence

**Correspondence**:
- Logic ↔ Type Theory ↔ Category Theory
- Proposition ↔ Type ↔ Object
- Proof ↔ Program ↔ Morphism
- Implication (A → B) ↔ Function type ↔ Exponential B^A

```python
def curry_howard_lambek():
    """Three-way correspondence"""
    return {
        'Conjunction (A ∧ B)': 'Product type (A, B) | A × B',
        'Disjunction (A ∨ B)': 'Sum type Either A B | A + B',
        'Implication (A → B)': 'Function type A → B | B^A',
        'True': 'Unit type () | Terminal object 1',
        'False': 'Empty type Void | Initial object 0',
    }
```

---

## Quick Reference

### Category Theory Hierarchy

```
Objects and Morphisms (Category)
    ↓
Functors (between categories)
    ↓
Natural Transformations (between functors)
    ↓
Modifications (between natural transformations)
```

### Universal Constructions

| Construction | Universal Property | Example |
|--------------|-------------------|---------|
| Product | ∀ f, g ∃! h | Cartesian product |
| Coproduct | ∀ f, g ∃! h | Disjoint union |
| Equalizer | Limit | Kernel |
| Coequalizer | Colimit | Cokernel |
| Pullback | Limit | Fiber product |
| Pushout | Colimit | Gluing |

### Adjunctions in Programming

| Left Adjoint | Right Adjoint | Example |
|--------------|---------------|---------|
| Free | Forgetful | Free monoid ⊣ Underlying set |
| Curry | Uncurry | (A → B → C) ≅ (A × B → C) |
| Σ (Sum) | → (Function) | Dependent sum ⊣ Function |

---

## Anti-Patterns

❌ **Ignoring universal properties**: Defining product as just a tuple
✅ Product defined by universal property (unique mediating morphism)

❌ **Confusing objects and morphisms**: Category theory is about morphisms
✅ "Objects are completely determined by morphisms to/from them"

❌ **Forgetting naturality**: Just defining components of transformation
✅ Natural transformation requires commuting squares for all morphisms

❌ **Treating functors as just "type constructors"**: Missing preservation of structure
✅ Functor preserves composition: F(g ∘ f) = F(g) ∘ F(f)

---

## Related Skills

- `curry-howard.md` - Propositions as types, category-theoretic view
- `topology-algebraic.md` - Functorial nature of π₁, H_*
- `abstract-algebra.md` - Categories of groups, rings, modules
- `type-systems.md` - Categories in programming languages
- `formal/lean-mathlib4.md` - Category theory in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
