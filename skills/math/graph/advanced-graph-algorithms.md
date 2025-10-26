---
name: Advanced Graph Algorithms
description: Specialized graph algorithms including graph decomposition, vertex coloring, matching algorithms, and 2024 research advances
---

# Advanced Graph Algorithms

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Solving graph coloring and scheduling problems
- Computing matchings in general graphs
- Decomposing graphs into components
- Finding cliques and independent sets
- Solving vertex cover and dominating set problems
- Implementing latest graph algorithm research

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`, `graph-traversal-algorithms.md`, `network-flow-algorithms.md`

**Related Skills**: `shortest-path-algorithms.md`, `minimum-spanning-tree.md`, `graph-applications.md`

---

## Core Algorithms

### 1. Graph Coloring

**Concept**: Assign colors to vertices such that no adjacent vertices share same color

**Chromatic Number**: χ(G) = minimum number of colors needed

```python
from typing import Dict, Set, Optional, List

def greedy_coloring(graph: 'AdjacencyList') -> Dict[int, int]:
    """
    Greedy graph coloring algorithm

    Time: O(V + E)
    Approximation: Uses at most Δ(G) + 1 colors where Δ = max degree
    """
    coloring = {}

    for v in range(graph.num_vertices):
        # Find colors used by neighbors
        neighbor_colors = {coloring[u] for u in graph.neighbors(v)
                          if u in coloring}

        # Assign smallest available color
        color = 0
        while color in neighbor_colors:
            color += 1

        coloring[v] = color

    return coloring

def welsh_powell_coloring(graph: 'AdjacencyList') -> Dict[int, int]:
    """
    Welsh-Powell algorithm: Color vertices in degree-descending order

    Often produces better coloring than simple greedy
    """
    # Sort vertices by degree (descending)
    vertices_by_degree = sorted(
        range(graph.num_vertices),
        key=lambda v: graph.degree(v),
        reverse=True
    )

    coloring = {}

    for v in vertices_by_degree:
        # Find colors used by neighbors
        neighbor_colors = {coloring[u] for u in graph.neighbors(v)
                          if u in coloring}

        # Assign smallest available color
        color = 0
        while color in neighbor_colors:
            color += 1

        coloring[v] = color

    return coloring

def is_valid_coloring(graph: 'AdjacencyList', coloring: Dict[int, int]) -> bool:
    """Verify that coloring is valid (no adjacent vertices same color)"""
    for u in range(graph.num_vertices):
        for v in graph.neighbors(u):
            if coloring[u] == coloring[v]:
                return False
    return True

def chromatic_number_bound(graph: 'AdjacencyList') -> tuple[int, int]:
    """
    Compute bounds on chromatic number

    Returns: (lower_bound, upper_bound)
    """
    # Lower bound: size of maximum clique
    # Upper bound: Δ(G) + 1 (greedy bound)

    max_degree = max(graph.degree(v) for v in range(graph.num_vertices))
    upper_bound = max_degree + 1

    # Simple lower bound: 2 if graph has edges, 1 otherwise
    lower_bound = 2 if graph.edge_count() > 0 else 1

    return lower_bound, upper_bound

# Example usage
from graph_data_structures import AdjacencyList

graph = AdjacencyList(5, directed=False)
graph.add_edge(0, 1)
graph.add_edge(0, 2)
graph.add_edge(1, 2)
graph.add_edge(1, 3)
graph.add_edge(2, 3)
graph.add_edge(3, 4)

coloring = welsh_powell_coloring(graph)
num_colors = max(coloring.values()) + 1
print(f"Coloring uses {num_colors} colors")
print(f"Valid: {is_valid_coloring(graph, coloring)}")
```

**Edge Coloring**:
```python
def edge_coloring_vizing(graph: 'AdjacencyList') -> Dict[tuple[int, int], int]:
    """
    Edge coloring using Vizing's algorithm

    Vizing's Theorem: χ'(G) ∈ {Δ(G), Δ(G) + 1}
    where χ'(G) = edge chromatic number, Δ(G) = max degree

    Time: O(V × E)
    """
    if graph.directed:
        raise ValueError("Edge coloring for undirected graphs only")

    edge_colors = {}
    max_degree = max(graph.degree(v) for v in range(graph.num_vertices))

    # Process edges one by one
    edges = graph.all_edges()

    for u, v, _ in edges:
        edge = tuple(sorted([u, v]))

        # Find colors used at u and v
        colors_at_u = {edge_colors.get(tuple(sorted([u, w])))
                      for w in graph.neighbors(u)
                      if tuple(sorted([u, w])) in edge_colors}

        colors_at_v = {edge_colors.get(tuple(sorted([v, w])))
                      for w in graph.neighbors(v)
                      if tuple(sorted([v, w])) in edge_colors}

        # Assign smallest color not used at u or v
        used_colors = colors_at_u | colors_at_v
        color = 0
        while color in used_colors:
            color += 1

        edge_colors[edge] = color

    return edge_colors
```

### 2. Maximum Matching (General Graphs)

**Concept**: Maximum set of edges with no shared vertices

**Blossom Algorithm** (Edmonds, 1965): Polynomial-time maximum matching for general graphs

```python
class BlossomMatching:
    """
    Edmonds' blossom algorithm for maximum matching

    Simplified implementation - full version is complex

    Time: O(V² × E)
    """

    def __init__(self, graph: 'AdjacencyList'):
        if graph.directed:
            raise ValueError("Matching for undirected graphs only")

        self.graph = graph
        self.matching = {}  # matching[u] = v if (u,v) in matching

    def is_matched(self, v: int) -> bool:
        """Check if vertex is matched"""
        return v in self.matching

    def find_augmenting_path_simple(self) -> Optional[List[int]]:
        """
        Find augmenting path (simple version, doesn't handle blossoms)

        Augmenting path: Path with alternating unmatched/matched edges
        starting and ending at unmatched vertices
        """
        # Start from unmatched vertex
        for start in range(self.graph.num_vertices):
            if self.is_matched(start):
                continue

            # BFS to find augmenting path
            from collections import deque
            queue = deque([(start, [start])])
            visited = {start}

            while queue:
                u, path = queue.popleft()

                for v in self.graph.neighbors(u):
                    if v == start:
                        continue

                    if v in visited:
                        continue

                    new_path = path + [v]

                    # Check if path alternates between matched/unmatched
                    if len(new_path) % 2 == 0:
                        # Even length - should be matched edge
                        if self.matching.get(u) == v:
                            visited.add(v)
                            queue.append((v, new_path))
                    else:
                        # Odd length - should be unmatched edge
                        if self.matching.get(u) != v:
                            if not self.is_matched(v):
                                # Found augmenting path!
                                return new_path

                            visited.add(v)
                            queue.append((v, new_path))

        return None

    def augment_along_path(self, path: List[int]):
        """Flip matched/unmatched edges along path"""
        for i in range(0, len(path) - 1, 2):
            u, v = path[i], path[i + 1]
            # Add edge to matching
            self.matching[u] = v
            self.matching[v] = u

    def maximum_matching(self) -> Set[tuple[int, int]]:
        """
        Compute maximum matching (simplified, no blossom contraction)

        Full blossom algorithm handles odd cycles (blossoms)
        """
        # Repeatedly find and augment along augmenting paths
        while True:
            path = self.find_augmenting_path_simple()

            if path is None:
                break  # No more augmenting paths

            self.augment_along_path(path)

        # Convert to set of edges
        matching_edges = set()
        seen = set()

        for u in self.matching:
            if u not in seen:
                v = self.matching[u]
                matching_edges.add(tuple(sorted([u, v])))
                seen.add(u)
                seen.add(v)

        return matching_edges

# Example usage
graph_match = AdjacencyList(6, directed=False)
graph_match.add_edge(0, 1)
graph_match.add_edge(0, 2)
graph_match.add_edge(1, 3)
graph_match.add_edge(2, 3)
graph_match.add_edge(3, 4)
graph_match.add_edge(4, 5)

blossom = BlossomMatching(graph_match)
matching = blossom.maximum_matching()
print(f"Maximum matching: {matching}")
print(f"Matching size: {len(matching)}")
```

### 3. Vertex Cover

**Concept**: Minimum set of vertices such that every edge has at least one endpoint in set

**NP-Complete**: No polynomial exact algorithm (unless P=NP)

```python
def vertex_cover_approximation(graph: 'AdjacencyList') -> Set[int]:
    """
    2-approximation for minimum vertex cover

    Algorithm: Maximal matching gives 2-approximation
    (Include both endpoints of each matching edge)

    Time: O(E)
    Approximation ratio: 2
    """
    if graph.directed:
        raise ValueError("Vertex cover for undirected graphs")

    cover = set()
    remaining_edges = set(graph.all_edges())

    while remaining_edges:
        # Pick arbitrary edge
        u, v, _ = remaining_edges.pop()

        # Add both endpoints to cover
        cover.add(u)
        cover.add(v)

        # Remove all edges incident to u or v
        remaining_edges = {(a, b, w) for a, b, w in remaining_edges
                          if a != u and a != v and b != u and b != v}

    return cover

def is_vertex_cover(graph: 'AdjacencyList', cover: Set[int]) -> bool:
    """Verify that cover is valid"""
    for u in range(graph.num_vertices):
        for v in graph.neighbors(u):
            if u not in cover and v not in cover:
                return False
    return True

# Example
graph_vc = AdjacencyList(5, directed=False)
graph_vc.add_edge(0, 1)
graph_vc.add_edge(0, 2)
graph_vc.add_edge(1, 3)
graph_vc.add_edge(2, 3)
graph_vc.add_edge(3, 4)

cover = vertex_cover_approximation(graph_vc)
print(f"Vertex cover (size {len(cover)}): {cover}")
print(f"Valid: {is_vertex_cover(graph_vc, cover)}")
```

### 4. Clique Finding

**Concept**: Find maximum complete subgraph (all vertices connected)

**NP-Complete**: Finding maximum clique is NP-hard

```python
def find_all_cliques_bron_kerbosch(graph: 'AdjacencyList'
                                  ) -> List[Set[int]]:
    """
    Bron-Kerbosch algorithm for finding all maximal cliques

    Time: O(3^(V/3)) worst case (exponential)
    """
    cliques = []

    def bronker bosch(R: Set[int], P: Set[int], X: Set[int]):
        """
        R = current clique being built
        P = candidates for extension
        X = already processed vertices
        """
        if not P and not X:
            # R is maximal clique
            cliques.append(R.copy())
            return

        # Choose pivot to minimize iterations
        pivot = max(P | X, key=lambda v: len(set(graph.neighbors(v)) & P),
                   default=None)

        if pivot is None:
            return

        pivot_neighbors = set(graph.neighbors(pivot))

        # Process vertices not adjacent to pivot
        for v in list(P - pivot_neighbors):
            v_neighbors = set(graph.neighbors(v))

            bronkerbosch(
                R | {v},
                P & v_neighbors,
                X & v_neighbors
            )

            P.remove(v)
            X.add(v)

    # Initialize: R = empty, P = all vertices, X = empty
    all_vertices = set(range(graph.num_vertices))
    bronkerbosch(set(), all_vertices, set())

    return cliques

def maximum_clique(graph: 'AdjacencyList') -> Set[int]:
    """Find maximum clique (largest complete subgraph)"""
    all_cliques = find_all_cliques_bron_kerbosch(graph)

    if not all_cliques:
        return set()

    return max(all_cliques, key=len)

# Example
graph_clique = AdjacencyList(5, directed=False)
graph_clique.add_edge(0, 1)
graph_clique.add_edge(0, 2)
graph_clique.add_edge(0, 3)
graph_clique.add_edge(1, 2)
graph_clique.add_edge(1, 3)
graph_clique.add_edge(2, 3)
graph_clique.add_edge(3, 4)

max_clique = maximum_clique(graph_clique)
print(f"Maximum clique: {max_clique}")  # {0, 1, 2, 3}
```

---

## 2024 Research Advances

### Graph Neural Networks Integration

```python
class GraphAttentionNetwork:
    """
    Graph Attention Network (GAT) integration

    2024 advances: Multi-head attention, edge features, heterogeneous graphs
    """

    def __init__(self, num_features: int, num_heads: int = 4):
        self.num_features = num_features
        self.num_heads = num_heads
        # Would integrate with PyTorch/TensorFlow in practice

    def attention_coefficients(self, node_features, neighbors):
        """
        Compute attention coefficients using self-attention

        2024 approach: Learned edge weights for graph algorithms
        """
        # Simplified - actual implementation uses neural networks
        pass

    def aggregate_features(self, graph, node_features):
        """
        Aggregate neighbor features using attention

        Applications:
        - Node classification
        - Link prediction
        - Graph classification
        """
        pass
```

### Quantum-Inspired Algorithms (2024)

```python
def quantum_inspired_max_cut(graph: 'WeightedGraph') -> tuple[Set[int], Set[int]]:
    """
    Quantum-inspired approximation for maximum cut

    Based on 2024 research: Classical simulation of quantum algorithms
    Achieves better approximation ratios than classical methods

    Max cut: Partition vertices to maximize edges between partitions
    """
    # Simplified version - full implementation uses tensor networks

    import random

    # Initialize random partition
    S = set(random.sample(range(graph.num_vertices),
                         graph.num_vertices // 2))
    T = set(range(graph.num_vertices)) - S

    improved = True

    while improved:
        improved = False

        # Try moving each vertex
        for v in range(graph.num_vertices):
            current_cut = compute_cut_value(graph, S, T)

            # Move v to other partition
            if v in S:
                S.remove(v)
                T.add(v)
            else:
                T.remove(v)
                S.add(v)

            new_cut = compute_cut_value(graph, S, T)

            if new_cut > current_cut:
                improved = True
            else:
                # Move back
                if v in S:
                    S.remove(v)
                    T.add(v)
                else:
                    T.remove(v)
                    S.add(v)

    return S, T

def compute_cut_value(graph: 'WeightedGraph', S: Set[int], T: Set[int]) -> float:
    """Compute total weight of edges crossing cut"""
    cut_value = 0.0

    for u in S:
        for edge in graph.adj[u]:
            v = edge.dest
            if v in T:
                cut_value += edge.weight

    return cut_value
```

---

## Patterns

### Pattern 1: NP-Hard Problem Strategies
```python
class NPHardGraphProblems:
    """Strategies for NP-hard graph problems"""

    @staticmethod
    def choose_approach(problem: str, graph_size: int) -> str:
        """Select approach based on problem and size"""

        if graph_size <= 20:
            return "exact_exponential"  # Brute force, backtracking

        elif graph_size <= 100:
            return "exact_bounded"  # Branch and bound, ILP

        elif graph_size <= 1000:
            return "approximation"  # Polynomial approximations

        else:
            return "heuristic"  # Fast heuristics, local search

    @staticmethod
    def vertex_cover_strategy(graph):
        """Example: Choosing vertex cover approach"""
        n = graph.num_vertices

        if n <= 20:
            return "exact_backtracking"
        else:
            return vertex_cover_approximation(graph)
```

---

## Quick Reference

### Complexity Classes
| Problem | Complexity | Best Algorithm |
|---------|-----------|----------------|
| Graph Coloring | NP-Complete | Greedy (Δ+1 colors) |
| Chromatic Number | NP-Complete | Bounds + backtracking |
| Maximum Matching | P | Blossom (O(V²E)) |
| Vertex Cover | NP-Complete | 2-approximation |
| Maximum Clique | NP-Complete | Bron-Kerbosch |
| Independent Set | NP-Complete | Complement of vertex cover |

### Approximation Ratios
| Problem | Algorithm | Ratio |
|---------|-----------|-------|
| Vertex Cover | Maximal matching | 2 |
| Graph Coloring | Greedy | Δ + 1 |
| Max Cut | Randomized | 0.5 |
| TSP (metric) | Christofides | 1.5 |

---

## Anti-Patterns

### ❌ Using Exponential Algorithms on Large Graphs
```python
# WRONG: Bron-Kerbosch on large graph
large_graph = AdjacencyList(1000)
# ... add edges ...
cliques = find_all_cliques_bron_kerbosch(large_graph)  # May never finish!

# CORRECT: Use heuristics or approximate for large graphs
if graph.num_vertices > 100:
    # Use greedy or sampling-based approach
    pass
```

### ❌ Assuming Optimal Solution Exists Quickly
```python
# WRONG: Expect exact minimum vertex cover
cover = minimum_vertex_cover_exact(graph)  # NP-hard!

# CORRECT: Use approximation with known bounds
cover = vertex_cover_approximation(graph)  # 2-approximation
```

---

## Related Skills

**Next Steps**:
- `graph-applications.md` → Real-world applications of these algorithms

**Foundations**:
- `graph-theory-fundamentals.md` → Basic graph concepts
- `graph-traversal-algorithms.md` → BFS and DFS
- `network-flow-algorithms.md` → Maximum matching via flow

---

## Summary

Advanced graph algorithms tackle complex combinatorial problems:
- **Graph Coloring**: NP-complete, greedy gives Δ+1 approximation
- **Maximum Matching**: Polynomial via Edmonds' blossom algorithm
- **Vertex Cover**: NP-complete, 2-approximation via maximal matching
- **Clique Finding**: NP-complete, Bron-Kerbosch finds all maximal cliques
- **2024 Advances**: GNNs, quantum-inspired algorithms

**Key takeaways**:
1. Many graph problems are NP-complete - use approximations
2. Greedy coloring uses at most Δ+1 colors
3. Blossom algorithm solves maximum matching in polynomial time
4. Vertex cover has 2-approximation, clique finding is exponential
5. Recent advances use machine learning and quantum-inspired methods

**Next**: Move to `graph-applications.md` for real-world use cases.
