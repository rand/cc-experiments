---
name: topology-algebraic
description: Algebraic topology including fundamental groups, homology, homotopy theory, and computational topology
---

# Algebraic Topology

**Scope**: Fundamental groups, homology, homotopy, covering spaces, computational topology
**Lines**: ~420
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Computing topological invariants (fundamental group, homology groups)
- Understanding homotopy equivalence and homotopy groups
- Working with covering spaces and deck transformations
- Studying CW complexes and cell decomposition
- Applying topology to data analysis (TDA, persistent homology)
- Proving topological theorems using algebraic methods

## Core Concepts

### Homotopy and Fundamental Group

**Homotopy**: Continuous deformation between continuous maps
- f, g: X → Y are homotopic (f ≃ g) if ∃ continuous H: X × [0,1] → Y with H(x,0) = f(x), H(x,1) = g(x)

**Fundamental group**: π₁(X, x₀) = homotopy classes of loops based at x₀

```python
import numpy as np
from collections import defaultdict

class Loop:
    """Represent a loop in a topological space"""
    def __init__(self, path, basepoint):
        self.path = path  # Function [0,1] → X
        self.basepoint = basepoint

    def compose(self, other):
        """Loop composition: traverse self, then other"""
        def composed(t):
            if t <= 0.5:
                return self.path(2 * t)
            else:
                return other.path(2 * (t - 0.5))
        return Loop(composed, self.basepoint)

    def inverse(self):
        """Reverse the loop"""
        return Loop(lambda t: self.path(1 - t), self.basepoint)

def fundamental_group_circle():
    """
    π₁(S¹) ≅ ℤ
    Loops classified by winding number
    """
    class S1Loop:
        def __init__(self, winding_number):
            self.n = winding_number  # How many times around

        def compose(self, other):
            return S1Loop(self.n + other.n)

        def inverse(self):
            return S1Loop(-self.n)

        def __eq__(self, other):
            return self.n == other.n

        def __repr__(self):
            return f"[loop with winding {self.n}]"

    # Identity element
    trivial_loop = S1Loop(0)

    # Generator (loop once around)
    generator = S1Loop(1)

    return {
        'identity': trivial_loop,
        'generator': generator,
        'group_structure': 'ℤ (integers under addition)'
    }

# Example
pi1_circle = fundamental_group_circle()
print(f"π₁(S¹) ≅ {pi1_circle['group_structure']}")
```

**Van Kampen's Theorem**: For path-connected spaces X = A ∪ B with A ∩ B path-connected:
π₁(X) ≅ π₁(A) *_{π₁(A∩B)} π₁(B) (amalgamated free product)

```python
def van_kampen_example():
    """
    Figure-eight space (two circles joined at a point)
    X = S¹ ∨ S¹ = two circles joined at basepoint
    """
    # π₁(S¹) ≅ ℤ for each circle
    # A ∩ B = {basepoint}, π₁({pt}) = 0 (trivial)
    # By Van Kampen: π₁(S¹ ∨ S¹) ≅ ℤ * ℤ (free group on 2 generators)

    class FreeGroupElement:
        def __init__(self, word):
            """word: list of ('a', n) or ('b', m) for generators"""
            self.word = word

        def compose(self, other):
            return FreeGroupElement(self.word + other.word)

        def reduce(self):
            """Cancel inverse pairs like a¹a⁻¹"""
            reduced = []
            for gen, power in self.word:
                if reduced and reduced[-1][0] == gen:
                    reduced[-1] = (gen, reduced[-1][1] + power)
                    if reduced[-1][1] == 0:
                        reduced.pop()
                else:
                    if power != 0:
                        reduced.append((gen, power))
            return FreeGroupElement(reduced)

    # Generators: a (first circle), b (second circle)
    a = FreeGroupElement([('a', 1)])
    b = FreeGroupElement([('b', 1)])

    # Example element: aba⁻¹b²
    element = FreeGroupElement([('a', 1), ('b', 1), ('a', -1), ('b', 2)])

    return {'generators': ['a', 'b'], 'structure': 'F₂ (free group on 2 generators)'}
```

### Homology Groups

**Simplicial homology**: Algebraic invariant computed from simplicial complex

**Chain complex**: C_n → C_{n-1} → ... → C_0
- C_n = free abelian group on n-simplices
- Boundary map ∂_n: C_n → C_{n-1}
- ∂_{n-1} ∘ ∂_n = 0

**Homology**: H_n = ker(∂_n) / im(∂_{n+1})

```python
import numpy as np
from scipy.sparse import lil_matrix

class SimplicialComplex:
    """Represent simplicial complex for homology computation"""
    def __init__(self):
        self.simplices = {0: set(), 1: set(), 2: set()}  # dim → simplices

    def add_vertex(self, v):
        self.simplices[0].add((v,))

    def add_edge(self, v1, v2):
        # Ensure vertices exist
        self.add_vertex(v1)
        self.add_vertex(v2)
        edge = tuple(sorted([v1, v2]))
        self.simplices[1].add(edge)

    def add_triangle(self, v1, v2, v3):
        # Ensure edges exist
        self.add_edge(v1, v2)
        self.add_edge(v2, v3)
        self.add_edge(v3, v1)
        triangle = tuple(sorted([v1, v2, v3]))
        self.simplices[2].add(triangle)

    def boundary_matrix(self, dim):
        """
        Compute boundary matrix ∂_dim: C_dim → C_{dim-1}
        Rows: (dim-1)-simplices, Cols: dim-simplices
        """
        if dim == 0:
            return None

        simplices_n = sorted(self.simplices[dim])
        simplices_n_minus_1 = sorted(self.simplices[dim-1])

        # Create index maps
        idx_n = {s: i for i, s in enumerate(simplices_n)}
        idx_n_minus_1 = {s: i for i, s in enumerate(simplices_n_minus_1)}

        # Build boundary matrix
        rows, cols = len(simplices_n_minus_1), len(simplices_n)
        boundary = lil_matrix((rows, cols), dtype=int)

        for col_idx, simplex in enumerate(simplices_n):
            # Compute boundary of simplex
            for i, vertex in enumerate(simplex):
                # Remove i-th vertex
                face = tuple(v for j, v in enumerate(simplex) if j != i)
                row_idx = idx_n_minus_1[face]
                # Sign: (-1)^i
                boundary[row_idx, col_idx] = (-1) ** i

        return boundary.tocsr()

    def compute_homology(self, dim):
        """Compute H_dim using boundary matrices"""
        import numpy as np
        from numpy.linalg import matrix_rank

        ∂_n_plus_1 = self.boundary_matrix(dim + 1)
        ∂_n = self.boundary_matrix(dim)

        if ∂_n is None:
            # H_0
            Z_n = len(self.simplices[0])  # All vertices
        else:
            # ker(∂_n) dimension
            Z_n = len(self.simplices[dim]) - matrix_rank(∂_n.toarray())

        if ∂_n_plus_1 is None:
            B_n = 0
        else:
            # im(∂_{n+1}) dimension
            B_n = matrix_rank(∂_n_plus_1.toarray())

        # Betti number: dim(H_n) = dim(ker) - dim(im)
        betti_n = Z_n - B_n

        return {'betti_number': betti_n, 'rank': betti_n}

# Example: Compute H_* of a circle (triangulated as hexagon)
circle = SimplicialComplex()
for i in range(6):
    circle.add_edge(i, (i+1) % 6)

h0 = circle.compute_homology(0)
h1 = circle.compute_homology(1)

print(f"H_0(S¹) has Betti number {h0['betti_number']}")  # 1 (connected)
print(f"H_1(S¹) has Betti number {h1['betti_number']}")  # 1 (one hole)
```

### Euler Characteristic

**Definition**: χ(X) = Σ (-1)^i · rank(H_i(X)) = Σ (-1)^i · b_i

For finite simplicial complex: χ = V - E + F (vertices - edges + faces)

```python
def euler_characteristic(complex):
    """χ = Σ(-1)^i · #(i-simplices)"""
    chi = 0
    for dim, simplices in complex.simplices.items():
        chi += (-1) ** dim * len(simplices)
    return chi

# Examples
# Sphere: χ(S²) = 2
# Torus: χ(T²) = 0
# Genus-g surface: χ = 2 - 2g
```

### Persistent Homology (TDA)

**Idea**: Track homology as parameter varies (e.g., scale in point cloud)

```python
# Using gudhi library for computational topology
try:
    import gudhi
except ImportError:
    print("Install: pip install gudhi")

def compute_persistent_homology(points, max_dim=2):
    """
    Compute persistence diagram from point cloud
    """
    # Build Vietoris-Rips complex
    rips_complex = gudhi.RipsComplex(points=points, max_edge_length=2.0)
    simplex_tree = rips_complex.create_simplex_tree(max_dimension=max_dim)

    # Compute persistence
    persistence = simplex_tree.persistence()

    # Extract diagrams by dimension
    diagrams = {}
    for dim in range(max_dim + 1):
        diagrams[dim] = simplex_tree.persistence_intervals_in_dimension(dim)

    return diagrams

# Example: Point cloud sampled from circle
theta = np.linspace(0, 2*np.pi, 50, endpoint=False)
points_circle = np.column_stack([np.cos(theta), np.sin(theta)])

# Persistence detects circular structure
# diagrams = compute_persistent_homology(points_circle, max_dim=1)
# H_1 has persistent feature (the circle)
```

---

## Patterns

### Pattern 1: Computing Fundamental Groups

**Deformation retracts**: X deformation retracts to A ⟹ π₁(X) ≅ π₁(A)

```python
def fundamental_group_examples():
    """Common fundamental groups"""
    examples = {
        'S¹ (circle)': 'ℤ',
        'S² (sphere)': '0 (trivial)',
        'Sⁿ (n≥2)': '0 (simply connected)',
        'T² (torus)': 'ℤ × ℤ',
        'ℝPⁿ (real projective, n≥2)': 'ℤ/2ℤ',
        'S¹ ∨ S¹ (figure-eight)': 'F₂ (free group, 2 generators)',
        'genus-g surface': 'generators: 2g, relations: [a₁,b₁]···[aₐ,bₐ]=1'
    }
    return examples
```

### Pattern 2: Mayer-Vietoris Sequence

**Long exact sequence** relating homology of X, A, B, A∩B when X = A ∪ B:

... → H_n(A∩B) → H_n(A) ⊕ H_n(B) → H_n(X) → H_{n-1}(A∩B) → ...

```python
def mayer_vietoris_torus():
    """
    Compute H_*(T²) using Mayer-Vietoris
    Decompose torus as T² = A ∪ B where A, B are cylinders
    """
    # A ∩ B ≃ S¹ ∨ S¹ (two circles)
    # A ≃ S¹, B ≃ S¹

    # H_0: all are ℤ, sequence gives H_0(T²) ≅ ℤ
    # H_1: from sequence, H_1(T²) ≅ ℤ ⊕ ℤ
    # H_2: H_2(T²) ≅ ℤ

    return {
        'H_0': 'ℤ',
        'H_1': 'ℤ ⊕ ℤ',
        'H_2': 'ℤ',
        'euler_char': 0  # 1 - 2 + 1 = 0
    }
```

### Pattern 3: CW Complexes

**Definition**: Build space by attaching cells
- 0-cells (points)
- 1-cells (attach intervals to 0-skeleton)
- 2-cells (attach disks to 1-skeleton)
- etc.

```python
class CWComplex:
    """Represent CW complex structure"""
    def __init__(self):
        self.cells = defaultdict(list)  # dim → list of cells
        self.attaching_maps = {}  # cell → (skeleton, attaching map)

    def add_cell(self, dim, cell_id, attaching_info=None):
        self.cells[dim].append(cell_id)
        if attaching_info:
            self.attaching_maps[cell_id] = attaching_info

    def euler_characteristic(self):
        """χ = Σ (-1)^i · c_i where c_i = number of i-cells"""
        chi = 0
        for dim, cells in self.cells.items():
            chi += (-1) ** dim * len(cells)
        return chi

# Example: S² as CW complex
sphere_cw = CWComplex()
sphere_cw.add_cell(0, 'v0')  # One 0-cell
sphere_cw.add_cell(2, 'e1')  # One 2-cell attached to point

chi_sphere = sphere_cw.euler_characteristic()  # χ = 1 - 0 + 1 = 2
```

---

## Quick Reference

### Fundamental Groups

| Space | π₁(X) | Note |
|-------|-------|------|
| S¹ | ℤ | Winding number |
| Sⁿ (n≥2) | 0 | Simply connected |
| T² | ℤ × ℤ | Torus |
| ℝPⁿ (n≥2) | ℤ/2ℤ | Projective space |
| S¹ ∨ S¹ | F₂ | Free on 2 generators |

### Homology Groups (ℤ coefficients)

| Space | H_0 | H_1 | H_2 | χ |
|-------|-----|-----|-----|---|
| S¹ | ℤ | ℤ | 0 | 0 |
| S² | ℤ | 0 | ℤ | 2 |
| T² | ℤ | ℤ² | ℤ | 0 |
| ℝP² | ℤ | ℤ/2ℤ | 0 | 1 |

### Betti Numbers

b_i = rank(H_i(X)) = dimension of i-th homology group
- b_0 = number of connected components
- b_1 = number of 1-dimensional holes (circles)
- b_2 = number of 2-dimensional voids (spheres)

---

## Anti-Patterns

❌ **Confusing homotopy and homeomorphism**: S² and ℝ² not homeomorphic but ℝ² ≃ {point}
✅ Homotopy equivalence weaker than homeomorphism

❌ **Assuming π₁ determines space**: Lens spaces have same π₁ but different H₂
✅ Need full homology/homotopy groups for classification

❌ **Computing homology by hand for large complexes**: Exponential complexity
✅ Use computational tools (gudhi, javaplex, PHAT) for practical problems

❌ **Ignoring coefficients**: H_*(ℝP²; ℤ) ≠ H_*(ℝP²; ℤ/2ℤ)
✅ Specify coefficient group for homology

---

## Related Skills

- `topology-point-set.md` - Foundation for algebraic topology
- `category-theory-foundations.md` - Functorial nature of π₁ and H_*
- `abstract-algebra.md` - Group theory for fundamental groups
- `linear-algebra-computation.md` - Matrix computations for homology
- `formal/lean-mathlib4.md` - Formalizing algebraic topology in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
