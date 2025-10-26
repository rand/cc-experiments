---
name: Graph Theory Fundamentals
description: Core concepts, terminology, and mathematical foundations of graph theory including graph types, properties, and fundamental theorems
---

# Graph Theory Fundamentals

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Modeling relationships, networks, or dependencies
- Analyzing social networks, web graphs, or citation networks
- Solving connectivity, path, or reachability problems
- Designing routing, scheduling, or resource allocation systems
- Working with trees, DAGs, or hierarchical structures
- Implementing graph-based algorithms or data structures

**Prerequisites**: Basic set theory, discrete mathematics

**Related Skills**: `graph-data-structures.md`, `graph-traversal-algorithms.md`, `linear-algebra-computation.md`, `category-theory-foundations.md`

---

## Core Concepts

### 1. Graph Definition

**Formal Definition**:
```
Graph G = (V, E) where:
- V = finite set of vertices (nodes)
- E ⊆ V × V = set of edges (connections)

For undirected graphs: E is set of unordered pairs {u,v}
For directed graphs: E is set of ordered pairs (u,v)
```

**Python Representation**:
```python
from dataclasses import dataclass
from typing import Set, Tuple, Optional

@dataclass
class Graph:
    """Abstract graph representation"""
    vertices: Set[int]
    edges: Set[Tuple[int, int]]
    directed: bool = False

    def __post_init__(self):
        """Validate graph structure"""
        for u, v in self.edges:
            if u not in self.vertices or v not in self.vertices:
                raise ValueError(f"Edge ({u},{v}) references non-existent vertex")

    def order(self) -> int:
        """Number of vertices |V|"""
        return len(self.vertices)

    def size(self) -> int:
        """Number of edges |E|"""
        return len(self.edges)

    def degree(self, v: int) -> int:
        """Degree of vertex v"""
        if v not in self.vertices:
            raise ValueError(f"Vertex {v} not in graph")

        if self.directed:
            # In-degree + out-degree for directed graphs
            in_deg = sum(1 for _, target in self.edges if target == v)
            out_deg = sum(1 for source, _ in self.edges if source == v)
            return in_deg + out_deg
        else:
            # Number of incident edges for undirected
            return sum(1 for u, w in self.edges if u == v or w == v)

# Example usage
undirected = Graph(
    vertices={1, 2, 3, 4},
    edges={(1,2), (2,3), (3,4), (4,1)},
    directed=False
)

directed = Graph(
    vertices={1, 2, 3},
    edges={(1,2), (2,3), (3,1)},
    directed=True
)
```

### 2. Graph Types

**Classification by Edge Direction**:
```python
class GraphType:
    """Common graph classifications"""

    @staticmethod
    def is_undirected(graph: Graph) -> bool:
        """Edges have no direction: {u,v} = {v,u}"""
        return not graph.directed

    @staticmethod
    def is_directed(graph: Graph) -> bool:
        """Edges have direction: (u,v) ≠ (v,u)"""
        return graph.directed

    @staticmethod
    def is_mixed(edges: Set) -> bool:
        """Contains both directed and undirected edges"""
        # Requires custom edge representation
        pass

# Undirected: Social networks (friendship is mutual)
# Directed: Web graphs (link A→B doesn't imply B→A)
# Mixed: Road networks (some one-way, some two-way)
```

**Classification by Edge Weights**:
```python
@dataclass
class WeightedGraph(Graph):
    """Graph with weighted edges"""
    weights: dict[Tuple[int, int], float] = None

    def __post_init__(self):
        super().__post_init__()
        if self.weights is None:
            self.weights = {}

        # Validate weights match edges
        for edge in self.weights:
            if edge not in self.edges:
                raise ValueError(f"Weight for non-existent edge {edge}")

    def weight(self, u: int, v: int) -> Optional[float]:
        """Get edge weight, None if edge doesn't exist"""
        edge = (u, v) if self.directed else tuple(sorted([u, v]))
        return self.weights.get(edge)

# Weighted: Road networks (distances), social networks (strength)
# Unweighted: Simple connectivity (edge exists or doesn't)
```

**Special Graph Classes**:
```python
class SpecialGraphs:
    """Factory for common graph types"""

    @staticmethod
    def complete_graph(n: int) -> Graph:
        """Kₙ: Every vertex connected to every other
        |V| = n, |E| = n(n-1)/2"""
        vertices = set(range(n))
        edges = {(i, j) for i in range(n) for j in range(i+1, n)}
        return Graph(vertices, edges, directed=False)

    @staticmethod
    def cycle_graph(n: int) -> Graph:
        """Cₙ: Vertices in circular arrangement
        |V| = n, |E| = n"""
        vertices = set(range(n))
        edges = {(i, (i+1) % n) for i in range(n)}
        return Graph(vertices, edges, directed=False)

    @staticmethod
    def path_graph(n: int) -> Graph:
        """Pₙ: Linear chain of vertices
        |V| = n, |E| = n-1"""
        vertices = set(range(n))
        edges = {(i, i+1) for i in range(n-1)}
        return Graph(vertices, edges, directed=False)

    @staticmethod
    def bipartite_graph(left: Set[int], right: Set[int],
                       edges: Set[Tuple[int, int]]) -> Graph:
        """G = (L ∪ R, E) where edges only between L and R"""
        if left & right:
            raise ValueError("Partitions must be disjoint")

        vertices = left | right
        # Validate edges only cross partitions
        for u, v in edges:
            if (u in left and v in left) or (u in right and v in right):
                raise ValueError(f"Edge {(u,v)} within partition")

        return Graph(vertices, edges, directed=False)

    @staticmethod
    def tree(n: int, edges: Set[Tuple[int, int]]) -> Graph:
        """Connected acyclic graph with n vertices, n-1 edges"""
        vertices = set(range(n))
        if len(edges) != n - 1:
            raise ValueError(f"Tree must have {n-1} edges, got {len(edges)}")

        graph = Graph(vertices, edges, directed=False)
        # Would need connectivity/acyclicity check
        return graph

# Examples
K5 = SpecialGraphs.complete_graph(5)  # 5 vertices, 10 edges
C6 = SpecialGraphs.cycle_graph(6)     # Hexagon
P10 = SpecialGraphs.path_graph(10)    # Linear chain
```

### 3. Graph Properties

**Degree Properties**:
```python
class GraphProperties:
    """Compute graph-theoretic properties"""

    @staticmethod
    def degree_sequence(graph: Graph) -> list[int]:
        """Sorted list of vertex degrees"""
        degrees = [graph.degree(v) for v in graph.vertices]
        return sorted(degrees, reverse=True)

    @staticmethod
    def is_regular(graph: Graph, k: Optional[int] = None) -> bool:
        """All vertices have same degree k"""
        degrees = [graph.degree(v) for v in graph.vertices]
        if len(set(degrees)) != 1:
            return False
        if k is not None:
            return degrees[0] == k
        return True

    @staticmethod
    def max_degree(graph: Graph) -> int:
        """Δ(G) = maximum vertex degree"""
        return max(graph.degree(v) for v in graph.vertices)

    @staticmethod
    def min_degree(graph: Graph) -> int:
        """δ(G) = minimum vertex degree"""
        return min(graph.degree(v) for v in graph.vertices)

    @staticmethod
    def avg_degree(graph: Graph) -> float:
        """Average vertex degree"""
        total = sum(graph.degree(v) for v in graph.vertices)
        return total / graph.order()

# Handshaking Lemma: Sum of degrees = 2|E|
def verify_handshaking_lemma(graph: Graph) -> bool:
    """∑deg(v) = 2|E| for undirected graphs"""
    if graph.directed:
        return True  # Different formula for directed

    degree_sum = sum(graph.degree(v) for v in graph.vertices)
    return degree_sum == 2 * graph.size()
```

**Connectivity**:
```python
class ConnectivityProperties:
    """Graph connectivity analysis"""

    @staticmethod
    def is_connected(graph: Graph) -> bool:
        """Path exists between every pair of vertices (undirected)"""
        if not graph.vertices:
            return True

        # BFS from arbitrary vertex
        start = next(iter(graph.vertices))
        visited = {start}
        queue = [start]

        while queue:
            v = queue.pop(0)
            for u, w in graph.edges:
                neighbor = w if u == v else (u if w == v else None)
                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == graph.order()

    @staticmethod
    def is_strongly_connected(graph: Graph) -> bool:
        """Directed path exists between every pair (directed)"""
        if not graph.directed:
            raise ValueError("Strong connectivity only for directed graphs")

        # Would need DFS from each vertex
        # (Simplified - full implementation in graph-traversal-algorithms.md)
        pass

    @staticmethod
    def connected_components(graph: Graph) -> list[Set[int]]:
        """Maximal connected subgraphs"""
        components = []
        unvisited = set(graph.vertices)

        while unvisited:
            start = unvisited.pop()
            component = {start}
            queue = [start]

            while queue:
                v = queue.pop(0)
                for u, w in graph.edges:
                    neighbor = w if u == v else (u if w == v else None)
                    if neighbor and neighbor in unvisited:
                        component.add(neighbor)
                        unvisited.remove(neighbor)
                        queue.append(neighbor)

            components.append(component)

        return components
```

**Planarity**:
```python
class PlanarityProperties:
    """Planar graph properties"""

    @staticmethod
    def eulers_formula(vertices: int, edges: int, faces: int) -> bool:
        """V - E + F = 2 for connected planar graphs"""
        return vertices - edges + faces == 2

    @staticmethod
    def satisfies_planar_bound(graph: Graph) -> bool:
        """Necessary condition: |E| ≤ 3|V| - 6 for V ≥ 3"""
        v = graph.order()
        e = graph.size()

        if v < 3:
            return True

        return e <= 3 * v - 6

    @staticmethod
    def satisfies_bipartite_planar_bound(graph: Graph) -> bool:
        """For bipartite planar: |E| ≤ 2|V| - 4"""
        v = graph.order()
        e = graph.size()

        if v < 3:
            return True

        return e <= 2 * v - 4

# Note: These are necessary but not sufficient conditions
# Full planarity testing requires Kuratowski's theorem
```

### 4. Fundamental Theorems

**Handshaking Lemma**:
```python
def handshaking_lemma(graph: Graph) -> dict:
    """
    Theorem: ∑deg(v) = 2|E|

    Corollary: Number of odd-degree vertices is even
    """
    degree_sum = sum(graph.degree(v) for v in graph.vertices)
    odd_degree_vertices = [v for v in graph.vertices
                          if graph.degree(v) % 2 == 1]

    return {
        "degree_sum": degree_sum,
        "twice_edges": 2 * graph.size(),
        "verified": degree_sum == 2 * graph.size(),
        "odd_degree_count": len(odd_degree_vertices),
        "odd_count_even": len(odd_degree_vertices) % 2 == 0
    }
```

**Euler's Theorem (Planar Graphs)**:
```python
def eulers_planar_formula(v: int, e: int, f: int) -> dict:
    """
    Theorem: For connected planar graph, V - E + F = 2

    Applications:
    - Bounds on edges: E ≤ 3V - 6 (V ≥ 3)
    - Bounds on faces: F ≤ 2V - 4
    """
    euler_char = v - e + f

    return {
        "vertices": v,
        "edges": e,
        "faces": f,
        "euler_characteristic": euler_char,
        "is_planar": euler_char == 2,
        "edge_bound": e <= 3*v - 6 if v >= 3 else True
    }
```

**Kuratowski's Theorem**:
```python
def is_kuratowski_subgraph(graph: Graph) -> bool:
    """
    Theorem: Graph is planar ⟺ contains no K₅ or K₃,₃ subdivision

    K₅ = complete graph on 5 vertices
    K₃,₃ = complete bipartite graph with 3+3 vertices

    This is a necessary and sufficient condition for planarity
    """
    # Full implementation requires subgraph isomorphism
    # See advanced graph algorithms
    pass
```

---

## Patterns

### Pattern 1: Graph Modeling
```python
class GraphModeling:
    """Convert real-world problems to graphs"""

    @staticmethod
    def social_network(users: list[str],
                      friendships: list[Tuple[str, str]]) -> Graph:
        """Model social network as undirected graph"""
        user_ids = {user: i for i, user in enumerate(users)}
        vertices = set(range(len(users)))
        edges = {(user_ids[u], user_ids[v]) for u, v in friendships}
        return Graph(vertices, edges, directed=False)

    @staticmethod
    def web_graph(pages: list[str],
                  links: list[Tuple[str, str]]) -> Graph:
        """Model web as directed graph (links)"""
        page_ids = {page: i for i, page in enumerate(pages)}
        vertices = set(range(len(pages)))
        edges = {(page_ids[src], page_ids[dst]) for src, dst in links}
        return Graph(vertices, edges, directed=True)

    @staticmethod
    def dependency_graph(tasks: list[str],
                        dependencies: list[Tuple[str, str]]) -> Graph:
        """Model task dependencies as DAG"""
        task_ids = {task: i for i, task in enumerate(tasks)}
        vertices = set(range(len(tasks)))
        # (u, v) means u must complete before v
        edges = {(task_ids[dep], task_ids[task])
                for task, dep in dependencies}
        return Graph(vertices, edges, directed=True)
```

### Pattern 2: Property Checking
```python
def analyze_graph_structure(graph: Graph) -> dict:
    """Comprehensive graph analysis"""
    props = GraphProperties()
    conn = ConnectivityProperties()

    analysis = {
        "order": graph.order(),
        "size": graph.size(),
        "directed": graph.directed,
        "degree_sequence": props.degree_sequence(graph),
        "max_degree": props.max_degree(graph),
        "min_degree": props.min_degree(graph),
        "avg_degree": props.avg_degree(graph),
        "is_regular": props.is_regular(graph),
        "is_connected": conn.is_connected(graph) if not graph.directed else None,
        "num_components": len(conn.connected_components(graph)),
        "handshaking_verified": verify_handshaking_lemma(graph)
    }

    return analysis
```

---

## Quick Reference

### Graph Types
| Type | Definition | Example |
|------|------------|---------|
| Simple | No loops, no multi-edges | Social network |
| Multigraph | Multiple edges between vertices | Road network |
| Directed | Edges have direction | Web graph |
| Weighted | Edges have weights | Distance map |
| Complete | Every vertex connected | Kₙ |
| Bipartite | Two independent sets | Job assignments |
| Tree | Connected, acyclic | File system |
| DAG | Directed, acyclic | Dependencies |

### Key Theorems
| Theorem | Statement | Application |
|---------|-----------|-------------|
| Handshaking | ∑deg(v) = 2\|E\| | Degree counting |
| Euler Planar | V - E + F = 2 | Planarity testing |
| Kuratowski | No K₅/K₃,₃ ⟺ planar | Planarity characterization |
| Planar bound | \|E\| ≤ 3\|V\| - 6 | Edge limit for planarity |

### Complexity Bounds
| Graph Type | Vertices | Max Edges |
|------------|----------|-----------|
| Simple undirected | n | n(n-1)/2 |
| Simple directed | n | n(n-1) |
| Tree | n | n-1 |
| Planar | n | 3n-6 |

---

## Anti-Patterns

### ❌ Confusing Directed and Undirected
```python
# WRONG: Treating directed as undirected
def degree(graph, v):
    return sum(1 for u, w in graph.edges if u == v or w == v)
    # Fails for directed graphs

# CORRECT: Check graph type
def degree(graph: Graph, v: int) -> int:
    if graph.directed:
        in_deg = sum(1 for _, target in graph.edges if target == v)
        out_deg = sum(1 for source, _ in graph.edges if source == v)
        return in_deg + out_deg
    else:
        return sum(1 for u, w in graph.edges if u == v or w == v)
```

### ❌ Ignoring Edge Cases
```python
# WRONG: Assume graph is non-empty
def analyze(graph):
    max_deg = max(graph.degree(v) for v in graph.vertices)
    # Crashes on empty graph

# CORRECT: Handle empty graphs
def analyze(graph: Graph) -> dict:
    if not graph.vertices:
        return {"order": 0, "size": 0, "max_degree": None}

    return {
        "order": graph.order(),
        "size": graph.size(),
        "max_degree": max(graph.degree(v) for v in graph.vertices)
    }
```

### ❌ Inefficient Degree Calculation
```python
# WRONG: Recalculate degrees repeatedly
for v in vertices:
    if graph.degree(v) > threshold:  # O(|E|) each call
        process(v)

# CORRECT: Cache degrees
degrees = {v: graph.degree(v) for v in graph.vertices}  # O(|E|) once
for v in vertices:
    if degrees[v] > threshold:  # O(1) lookup
        process(v)
```

---

## Related Skills

**Next Steps**:
- `graph-data-structures.md` → Efficient graph representations
- `graph-traversal-algorithms.md` → BFS, DFS, topological sort
- `shortest-path-algorithms.md` → Dijkstra, Bellman-Ford, Floyd-Warshall

**Mathematical Foundations**:
- `linear-algebra-computation.md` → Adjacency matrices, spectral graph theory
- `category-theory-foundations.md` → Graph categories, functors

**Applications**:
- `network-flow-algorithms.md` → Max flow, min cut
- `graph-applications.md` → Social networks, route planning

---

## Summary

Graph theory fundamentals provide the vocabulary and mathematical framework for:
- Modeling relationships and networks
- Analyzing connectivity and structure
- Applying classical theorems (Handshaking, Euler, Kuratowski)
- Classifying graphs by type and properties
- Building foundation for advanced algorithms

**Key takeaways**:
1. Graphs are pairs G = (V, E) with rich structural properties
2. Graph types (directed/undirected, weighted/unweighted, special classes) dictate algorithm choices
3. Fundamental theorems (Handshaking, Euler) provide bounds and characterizations
4. Proper representation choices affect algorithm efficiency

**Next**: Move to `graph-data-structures.md` to learn efficient implementations.
