---
name: topology-point-set
description: Point-set topology, metric spaces, open/closed sets, continuity, compactness, separation axioms
---

# Point-Set Topology

**Scope**: General topology, metric spaces, topological properties, continuity
**Lines**: ~400
**Last Updated**: 2025-10-25

## When to Use This Skill

Activate this skill when:
- Understanding continuity and convergence in abstract spaces
- Working with metric spaces and generalizations
- Studying compactness and connectedness properties
- Proving topological theorems (separation axioms, Urysohn's lemma)
- Preparing for algebraic topology or differential geometry
- Analyzing properties invariant under homeomorphisms

## Core Concepts

### Topological Spaces

**Definition**: A topological space (X, τ) consists of a set X and a collection τ of subsets (open sets) satisfying:
- ∅ and X are in τ
- Arbitrary unions of sets in τ are in τ
- Finite intersections of sets in τ are in τ

**Open and closed sets**:
```python
# Conceptual Python representation
class TopologicalSpace:
    def __init__(self, points, open_sets):
        self.X = set(points)
        self.tau = set(frozenset(s) for s in open_sets)

        # Verify topology axioms
        assert frozenset() in self.tau  # Empty set
        assert frozenset(self.X) in self.tau  # Whole space

    def is_open(self, subset):
        return frozenset(subset) in self.tau

    def is_closed(self, subset):
        # Closed if complement is open
        complement = self.X - set(subset)
        return frozenset(complement) in self.tau

    def interior(self, subset):
        # Largest open set contained in subset
        interior_pts = set()
        for pt in subset:
            # Check if pt has open neighborhood in subset
            for open_set in self.tau:
                if pt in open_set and open_set.issubset(subset):
                    interior_pts.add(pt)
                    break
        return interior_pts

    def closure(self, subset):
        # Smallest closed set containing subset
        # Intersection of all closed sets containing subset
        closed_sets = []
        for candidate in self._all_subsets():
            if self.is_closed(candidate) and set(subset).issubset(candidate):
                closed_sets.append(candidate)
        return set.intersection(*closed_sets) if closed_sets else set()
```

### Metric Spaces

**Definition**: A metric space (X, d) with distance function d: X × X → ℝ satisfying:
- d(x, y) ≥ 0, d(x, y) = 0 iff x = y
- d(x, y) = d(y, x)
- d(x, z) ≤ d(x, y) + d(y, z) (triangle inequality)

**Metric induces topology**:
```python
import numpy as np

class MetricSpace:
    def __init__(self, points, metric):
        """
        points: collection of points
        metric: function (x, y) -> distance
        """
        self.X = points
        self.metric = metric

    def open_ball(self, center, radius):
        """B_r(x) = {y ∈ X : d(x,y) < r}"""
        return {y for y in self.X if self.metric(center, y) < radius}

    def closed_ball(self, center, radius):
        """B̄_r(x) = {y ∈ X : d(x,y) ≤ r}"""
        return {y for y in self.X if self.metric(center, y) <= radius}

    def is_open(self, subset):
        """
        Subset is open if for each point, there exists an open ball
        centered at that point contained in the subset
        """
        for pt in subset:
            # Find if there's an epsilon ball around pt in subset
            epsilon = 0.01  # Simplified check
            ball = self.open_ball(pt, epsilon)
            if not ball.issubset(subset):
                # Try smaller balls...
                found = False
                for eps in [0.1, 0.01, 0.001]:
                    if self.open_ball(pt, eps).issubset(subset):
                        found = True
                        break
                if not found:
                    return False
        return True

# Example: Euclidean metric on ℝ²
def euclidean_metric(p1, p2):
    return np.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))

points_2d = [(x, y) for x in range(-5, 6) for y in range(-5, 6)]
R2 = MetricSpace(points_2d, euclidean_metric)

# Open ball around origin with radius 2
ball = R2.open_ball((0, 0), 2)
print(f"Open ball B_2(0): {len(ball)} points")
```

### Continuity

**Definition**: Function f: X → Y between topological spaces is continuous if:
- For every open set V in Y, the preimage f⁻¹(V) is open in X

**Equivalent characterizations**:
```python
class ContinuousMap:
    def __init__(self, domain, codomain, func):
        self.X = domain  # TopologicalSpace
        self.Y = codomain  # TopologicalSpace
        self.f = func

    def preimage(self, subset_Y):
        """f⁻¹(V) = {x ∈ X : f(x) ∈ V}"""
        return {x for x in self.X.X if self.f(x) in subset_Y}

    def is_continuous(self):
        """Check if preimage of every open set is open"""
        for open_Y in self.Y.tau:
            preim = self.preimage(open_Y)
            if not self.X.is_open(preim):
                return False
        return True

    def is_continuous_at_point(self, x0, epsilon=0.01):
        """
        For metric spaces: continuous at x0 if
        ∀ε>0 ∃δ>0: d_X(x,x0)<δ ⟹ d_Y(f(x),f(x0))<ε
        """
        # Simplified epsilon-delta check
        for delta in [0.1, 0.01, 0.001]:
            neighborhood_x = self.X.open_ball(x0, delta)
            images = {self.f(x) for x in neighborhood_x}
            # Check if all images are within epsilon of f(x0)
            if all(self.Y.metric(self.f(x0), y) < epsilon for y in images):
                return True
        return False

# Example: f(x) = x² on ℝ
def square(x):
    return x * x

R = MetricSpace(range(-10, 11), lambda x, y: abs(x - y))
f = ContinuousMap(R, R, square)
print(f"f(x)=x² continuous at 0: {f.is_continuous_at_point(0)}")
```

### Compactness

**Definitions**:
- **Cover**: Collection of sets whose union contains the space
- **Compact**: Every open cover has a finite subcover
- **Sequentially compact**: Every sequence has a convergent subsequence

**Heine-Borel Theorem**: In ℝⁿ, compact ⟺ closed and bounded

```python
def is_compact_finite(space, subset):
    """
    Check compactness for finite spaces (finite open covers)
    Compact: every open cover has finite subcover
    """
    # Generate all possible open covers
    from itertools import combinations, chain

    subset_frozen = frozenset(subset)

    # All open sets that intersect subset
    relevant_opens = [s for s in space.tau if s & subset_frozen]

    # Check if any finite subcollection covers subset
    for size in range(1, len(relevant_opens) + 1):
        for cover_attempt in combinations(relevant_opens, size):
            union = set().union(*cover_attempt)
            if subset_frozen.issubset(union):
                # Found finite subcover!
                return True, cover_attempt

    return False, None

# Example: [0, 1] is compact, (0, 1) is not
# Simplified discrete approximation
interval_closed = set(i/10 for i in range(0, 11))  # [0, 1]
interval_open = set(i/10 for i in range(1, 10))  # (0, 1) approximation
```

### Connectedness

**Definition**: Space X is connected if it cannot be written as union of two disjoint non-empty open sets

**Path-connected**: Any two points can be joined by a continuous path

```python
def is_connected(space):
    """
    Space is connected if only clopen (closed and open) sets are ∅ and X
    Equivalently: no separation into two disjoint non-empty open sets
    """
    X = space.X

    # Try to find separation
    for A_candidate in space._all_subsets():
        if not A_candidate or A_candidate == X:
            continue

        B_candidate = X - A_candidate

        # Check if A and B are both open (separation)
        if space.is_open(A_candidate) and space.is_open(B_candidate):
            return False  # Found separation, not connected

    return True  # No separation found

def is_path_connected(metric_space, path_finder):
    """
    Check if any two points can be connected by continuous path
    path_finder: function(p1, p2) -> path or None
    """
    points_list = list(metric_space.X)

    # Sample pairs of points
    for i, p1 in enumerate(points_list[:5]):  # Sample for efficiency
        for p2 in points_list[i+1:i+6]:
            path = path_finder(p1, p2)
            if path is None:
                return False
    return True
```

---

## Patterns

### Pattern 1: Separation Axioms

**T0 (Kolmogorov)**: For distinct points x, y, ∃ open set containing one but not other
**T1 (Fréchet)**: For distinct points x, y, ∃ open sets separating each
**T2 (Hausdorff)**: For distinct points x, y, ∃ disjoint open neighborhoods
**T3 (Regular)**: T0 + point and closed set can be separated
**T4 (Normal)**: T1 + disjoint closed sets can be separated

```python
def is_hausdorff(space):
    """T2: Distinct points have disjoint neighborhoods"""
    for x in space.X:
        for y in space.X:
            if x == y:
                continue

            # Find disjoint open neighborhoods
            found_separation = False
            for U in space.tau:
                if x not in U:
                    continue
                for V in space.tau:
                    if y not in V:
                        continue
                    if U.isdisjoint(V):
                        found_separation = True
                        break
                if found_separation:
                    break

            if not found_separation:
                return False
    return True
```

### Pattern 2: Bases and Subbases

**Base**: Collection β where every open set is union of sets in β

```python
def generates_topology(space, base):
    """Check if base generates the topology"""
    # Every open set should be union of base elements
    for open_set in space.tau:
        if not open_set:  # Empty set
            continue

        # Try to write open_set as union of base elements
        union = set()
        for B in base:
            if B.issubset(open_set):
                union |= B

        if union != open_set:
            return False
    return True

# Standard base for ℝ: open intervals (a, b)
```

### Pattern 3: Product Topology

**Product**: If (X, τ_X) and (Y, τ_Y) are topological spaces,
product topology on X × Y has base {U × V : U ∈ τ_X, V ∈ τ_Y}

```python
def product_topology(space1, space2):
    """Construct product topology X × Y"""
    # Cartesian product of underlying sets
    product_points = {(x, y) for x in space1.X for y in space2.X}

    # Base: products of open sets
    base = set()
    for U in space1.tau:
        for V in space2.tau:
            product_set = frozenset((x, y) for x in U for y in V)
            base.add(product_set)

    # Generate topology from base (all unions)
    topology = set(base)
    # Add arbitrary unions...

    return TopologicalSpace(product_points, topology)
```

---

## Quick Reference

### Key Definitions

| Concept | Definition | Example |
|---------|------------|---------|
| Open set | Member of topology τ | (a, b) in ℝ |
| Closed set | Complement is open | [a, b] in ℝ |
| Interior | Largest open subset | int([0,1]) = (0,1) |
| Closure | Smallest closed superset | cl((0,1)) = [0,1] |
| Continuous | Preimage of open is open | f: ℝ → ℝ, f(x)=x² |
| Compact | Every open cover has finite subcover | [0,1], S¹ |
| Connected | No separation into disjoint opens | ℝ, intervals |
| Hausdorff | Distinct points have disjoint nbhds | Metric spaces |

### Metric Space Properties

```python
# Common metrics
euclidean = lambda p, q: np.sqrt(sum((a-b)**2 for a,b in zip(p,q)))
manhattan = lambda p, q: sum(abs(a-b) for a,b in zip(p,q))
discrete = lambda p, q: 0 if p == q else 1
```

### Topological Invariants

Properties preserved by homeomorphisms:
- Compactness
- Connectedness
- Path-connectedness
- Separation axioms
- Fundamental group (algebraic topology)

---

## Anti-Patterns

❌ **Confusing open/closed**: Sets can be both (clopen), neither, or just one
✅ In ℝ: (0,1) is open; [0,1] is closed; [0,1) is neither; ℝ is clopen

❌ **Assuming metric space properties**: Not all topological spaces have metrics
✅ Indiscrete topology: τ = {∅, X} has no non-trivial metric

❌ **Conflating compact and closed**: In ℝⁿ compact ⟺ closed + bounded
✅ General spaces: (0,1) is bounded and not compact; ℝ is closed but not compact

❌ **Ignoring sequential vs topological definitions**: Not equivalent in general
✅ Sequential compactness ⟹ compactness in metric spaces only

---

## Related Skills

- `topology-algebraic.md` - Fundamental groups, homology, homotopy theory
- `category-theory-foundations.md` - Topological spaces as category objects
- `linear-algebra-computation.md` - Metric spaces, norms on vector spaces
- `numerical-methods.md` - Convergence in topological spaces
- `formal/lean-mathlib4.md` - Formalizing topology in Lean

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
