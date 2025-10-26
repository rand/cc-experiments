---
name: Graph Data Structures
description: Efficient graph representations including adjacency matrices, adjacency lists, edge lists, and specialized structures with space-time tradeoffs
---

# Graph Data Structures

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Implementing graph algorithms efficiently
- Choosing optimal representation for space/time constraints
- Working with dense vs sparse graphs
- Needing fast edge queries vs iteration
- Building graph libraries or frameworks
- Optimizing graph storage for large networks

**Prerequisites**: `graph-theory-fundamentals.md`, basic data structures (arrays, lists, hash tables)

**Related Skills**: `graph-traversal-algorithms.md`, `shortest-path-algorithms.md`, `network-flow-algorithms.md`

---

## Core Representations

### 1. Adjacency Matrix

**Definition**: 2D array where `A[i][j] = 1` if edge exists from `i` to `j`

**Characteristics**:
- **Space**: O(V²) - dense storage
- **Edge query**: O(1) - direct array access
- **Edge iteration**: O(V²) - must check all entries
- **Add vertex**: O(V²) - resize matrix
- **Add edge**: O(1) - set array entry

**Best for**: Dense graphs, frequent edge queries, matrix operations

```python
from typing import Optional
import numpy as np

class AdjacencyMatrix:
    """Graph representation as 2D matrix"""

    def __init__(self, num_vertices: int, directed: bool = False):
        self.num_vertices = num_vertices
        self.directed = directed
        # Initialize V×V matrix with zeros
        self.matrix = np.zeros((num_vertices, num_vertices), dtype=int)

    def add_edge(self, u: int, v: int, weight: float = 1.0):
        """Add edge from u to v with optional weight"""
        if not (0 <= u < self.num_vertices and 0 <= v < self.num_vertices):
            raise ValueError(f"Vertex out of range: ({u}, {v})")

        self.matrix[u][v] = weight

        if not self.directed:
            self.matrix[v][u] = weight

    def remove_edge(self, u: int, v: int):
        """Remove edge from u to v"""
        self.matrix[u][v] = 0
        if not self.directed:
            self.matrix[v][u] = 0

    def has_edge(self, u: int, v: int) -> bool:
        """Check if edge exists - O(1)"""
        return self.matrix[u][v] != 0

    def get_weight(self, u: int, v: int) -> Optional[float]:
        """Get edge weight or None"""
        weight = self.matrix[u][v]
        return weight if weight != 0 else None

    def neighbors(self, u: int) -> list[int]:
        """Get neighbors of u - O(V)"""
        return [v for v in range(self.num_vertices)
                if self.matrix[u][v] != 0]

    def degree(self, u: int) -> int:
        """Degree of vertex u - O(V)"""
        if self.directed:
            in_deg = np.count_nonzero(self.matrix[:, u])
            out_deg = np.count_nonzero(self.matrix[u, :])
            return in_deg + out_deg
        else:
            return np.count_nonzero(self.matrix[u, :])

    def edge_count(self) -> int:
        """Total number of edges - O(V²)"""
        count = np.count_nonzero(self.matrix)
        return count if self.directed else count // 2

    def to_adjacency_list(self) -> 'AdjacencyList':
        """Convert to adjacency list representation"""
        adj_list = AdjacencyList(self.num_vertices, self.directed)

        for u in range(self.num_vertices):
            for v in range(self.num_vertices):
                if self.matrix[u][v] != 0:
                    weight = self.matrix[u][v]
                    adj_list.add_edge(u, v, weight)

        return adj_list

# Example usage
graph = AdjacencyMatrix(4, directed=False)
graph.add_edge(0, 1, weight=5)
graph.add_edge(1, 2, weight=3)
graph.add_edge(2, 3, weight=7)

print(f"Has edge (0,1): {graph.has_edge(0, 1)}")  # True
print(f"Neighbors of 1: {graph.neighbors(1)}")    # [0, 2]
print(f"Degree of 1: {graph.degree(1)}")          # 2
```

**Matrix Operations**:
```python
class MatrixOperations:
    """Advanced operations on adjacency matrices"""

    @staticmethod
    def transpose(matrix: np.ndarray) -> np.ndarray:
        """Transpose for directed graph reversal"""
        return matrix.T

    @staticmethod
    def power(matrix: np.ndarray, k: int) -> np.ndarray:
        """
        A^k[i][j] = number of walks of length k from i to j

        Applications:
        - Path counting
        - Reachability in k steps
        - Graph diameter computation
        """
        result = np.linalg.matrix_power(matrix, k)
        return result

    @staticmethod
    def laplacian(adj_matrix: np.ndarray) -> np.ndarray:
        """
        L = D - A where D is degree matrix, A is adjacency

        Applications:
        - Spectral graph theory
        - Graph clustering
        - Random walks
        """
        n = adj_matrix.shape[0]
        degree_matrix = np.diag([np.sum(adj_matrix[i, :])
                                for i in range(n)])
        return degree_matrix - adj_matrix

    @staticmethod
    def normalized_laplacian(adj_matrix: np.ndarray) -> np.ndarray:
        """L_norm = I - D^(-1/2) A D^(-1/2)"""
        n = adj_matrix.shape[0]
        degrees = np.array([np.sum(adj_matrix[i, :]) for i in range(n)])

        # Avoid division by zero for isolated vertices
        deg_inv_sqrt = np.zeros(n)
        for i in range(n):
            deg_inv_sqrt[i] = 1.0 / np.sqrt(degrees[i]) if degrees[i] > 0 else 0

        D_inv_sqrt = np.diag(deg_inv_sqrt)
        L_norm = np.eye(n) - D_inv_sqrt @ adj_matrix @ D_inv_sqrt

        return L_norm
```

### 2. Adjacency List

**Definition**: Array of lists where `adj[u]` contains neighbors of `u`

**Characteristics**:
- **Space**: O(V + E) - sparse storage
- **Edge query**: O(degree(u)) - linear search in list
- **Edge iteration**: O(V + E) - visit each edge once
- **Add vertex**: O(1) - append new list
- **Add edge**: O(1) - append to list

**Best for**: Sparse graphs, edge iteration, most graph algorithms

```python
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Tuple, Dict, Set

@dataclass
class WeightedEdge:
    """Edge with destination and weight"""
    dest: int
    weight: float = 1.0

class AdjacencyList:
    """Graph representation as array of lists"""

    def __init__(self, num_vertices: int = 0, directed: bool = False):
        self.num_vertices = num_vertices
        self.directed = directed
        # List of lists of weighted edges
        self.adj: List[List[WeightedEdge]] = [[] for _ in range(num_vertices)]

    def add_vertex(self) -> int:
        """Add new vertex, return its ID - O(1)"""
        self.adj.append([])
        self.num_vertices += 1
        return self.num_vertices - 1

    def add_edge(self, u: int, v: int, weight: float = 1.0):
        """Add edge from u to v - O(1)"""
        if u >= self.num_vertices or v >= self.num_vertices:
            raise ValueError(f"Vertex out of range: ({u}, {v})")

        self.adj[u].append(WeightedEdge(v, weight))

        if not self.directed:
            self.adj[v].append(WeightedEdge(u, weight))

    def remove_edge(self, u: int, v: int):
        """Remove edge from u to v - O(degree(u))"""
        self.adj[u] = [e for e in self.adj[u] if e.dest != v]

        if not self.directed:
            self.adj[v] = [e for e in self.adj[v] if e.dest != u]

    def has_edge(self, u: int, v: int) -> bool:
        """Check if edge exists - O(degree(u))"""
        return any(e.dest == v for e in self.adj[u])

    def get_weight(self, u: int, v: int) -> Optional[float]:
        """Get edge weight - O(degree(u))"""
        for edge in self.adj[u]:
            if edge.dest == v:
                return edge.weight
        return None

    def neighbors(self, u: int) -> List[int]:
        """Get neighbors of u - O(1) to start iteration"""
        return [edge.dest for edge in self.adj[u]]

    def degree(self, u: int) -> int:
        """Degree of vertex u - O(1)"""
        if self.directed:
            out_deg = len(self.adj[u])
            in_deg = sum(1 for v in range(self.num_vertices)
                        for edge in self.adj[v] if edge.dest == u)
            return in_deg + out_deg
        else:
            return len(self.adj[u])

    def out_degree(self, u: int) -> int:
        """Out-degree for directed graphs - O(1)"""
        return len(self.adj[u])

    def edge_count(self) -> int:
        """Total number of edges - O(V)"""
        count = sum(len(edges) for edges in self.adj)
        return count if self.directed else count // 2

    def all_edges(self) -> List[Tuple[int, int, float]]:
        """Get all edges as list - O(V + E)"""
        edges = []
        seen = set() if not self.directed else None

        for u in range(self.num_vertices):
            for edge in self.adj[u]:
                v, w = edge.dest, edge.weight

                if self.directed:
                    edges.append((u, v, w))
                else:
                    # Avoid duplicates in undirected
                    edge_key = tuple(sorted([u, v]))
                    if edge_key not in seen:
                        edges.append((u, v, w))
                        seen.add(edge_key)

        return edges

# Example usage
graph = AdjacencyList(5, directed=False)
graph.add_edge(0, 1, weight=4)
graph.add_edge(0, 2, weight=1)
graph.add_edge(1, 3, weight=2)
graph.add_edge(2, 3, weight=5)
graph.add_edge(3, 4, weight=3)

print(f"Neighbors of 0: {graph.neighbors(0)}")   # [1, 2]
print(f"Out-degree of 0: {graph.out_degree(0)}") # 2
print(f"Total edges: {graph.edge_count()}")       # 5
```

### 3. Edge List

**Definition**: Simple list of edges, optionally with weights

**Characteristics**:
- **Space**: O(E) - minimal storage
- **Edge query**: O(E) - linear search
- **Edge iteration**: O(E) - direct iteration
- **Add edge**: O(1) - append to list
- **Sort edges**: O(E log E) - useful for MST algorithms

**Best for**: Kruskal's algorithm, edge-centric operations, simple storage

```python
@dataclass
class Edge:
    """Single edge with source, destination, weight"""
    src: int
    dest: int
    weight: float = 1.0

    def __lt__(self, other):
        """Compare by weight for sorting"""
        return self.weight < other.weight

    def reverse(self) -> 'Edge':
        """Reverse direction"""
        return Edge(self.dest, self.src, self.weight)

class EdgeList:
    """Graph representation as list of edges"""

    def __init__(self, num_vertices: int, directed: bool = False):
        self.num_vertices = num_vertices
        self.directed = directed
        self.edges: List[Edge] = []

    def add_edge(self, u: int, v: int, weight: float = 1.0):
        """Add edge - O(1)"""
        self.edges.append(Edge(u, v, weight))

    def sort_by_weight(self):
        """Sort edges by weight - O(E log E)"""
        self.edges.sort()

    def neighbors(self, u: int) -> List[int]:
        """Get neighbors - O(E)"""
        neighbors = []
        for edge in self.edges:
            if edge.src == u:
                neighbors.append(edge.dest)
            elif not self.directed and edge.dest == u:
                neighbors.append(edge.src)
        return neighbors

    def to_adjacency_list(self) -> AdjacencyList:
        """Convert to adjacency list - O(V + E)"""
        adj_list = AdjacencyList(self.num_vertices, self.directed)

        for edge in self.edges:
            adj_list.add_edge(edge.src, edge.dest, edge.weight)

        return adj_list

    def filter_by_weight(self, min_weight: float,
                        max_weight: float) -> 'EdgeList':
        """Create subgraph with edge weights in range"""
        filtered = EdgeList(self.num_vertices, self.directed)
        filtered.edges = [e for e in self.edges
                         if min_weight <= e.weight <= max_weight]
        return filtered

# Example: Kruskal's MST preparation
edges = EdgeList(5, directed=False)
edges.add_edge(0, 1, 4)
edges.add_edge(0, 2, 1)
edges.add_edge(1, 3, 2)
edges.add_edge(2, 3, 5)
edges.add_edge(3, 4, 3)

edges.sort_by_weight()  # Prepare for Kruskal's algorithm
print([f"({e.src},{e.dest}):{e.weight}" for e in edges.edges])
```

### 4. Specialized Structures

**Compressed Sparse Row (CSR)**:
```python
class CSRGraph:
    """
    Compressed Sparse Row format for very large sparse graphs

    Space: O(V + E) with excellent cache locality
    Best for: Large graphs, read-heavy workloads, parallel processing
    """

    def __init__(self, num_vertices: int):
        self.num_vertices = num_vertices
        # Row pointers: offsets[i] = start of neighbors for vertex i
        self.offsets: List[int] = [0] * (num_vertices + 1)
        # Column indices: neighbors packed into single array
        self.neighbors: List[int] = []
        # Edge weights (optional)
        self.weights: List[float] = []

    @staticmethod
    def from_adjacency_list(adj_list: AdjacencyList) -> 'CSRGraph':
        """Convert adjacency list to CSR format"""
        csr = CSRGraph(adj_list.num_vertices)

        offset = 0
        for u in range(adj_list.num_vertices):
            csr.offsets[u] = offset

            for edge in adj_list.adj[u]:
                csr.neighbors.append(edge.dest)
                csr.weights.append(edge.weight)
                offset += 1

        csr.offsets[adj_list.num_vertices] = offset
        return csr

    def get_neighbors(self, u: int) -> List[Tuple[int, float]]:
        """Get neighbors with weights - O(degree(u))"""
        start = self.offsets[u]
        end = self.offsets[u + 1]

        return [(self.neighbors[i], self.weights[i])
                for i in range(start, end)]

    def out_degree(self, u: int) -> int:
        """Out-degree - O(1)"""
        return self.offsets[u + 1] - self.offsets[u]
```

---

## Representation Comparison

### Space Complexity
| Representation | Space | Best Case | Worst Case |
|----------------|-------|-----------|------------|
| Adjacency Matrix | O(V²) | O(V²) | O(V²) |
| Adjacency List | O(V+E) | O(V) | O(V²) |
| Edge List | O(E) | O(1) | O(V²) |
| CSR | O(V+E) | O(V) | O(V²) |

### Time Complexity
| Operation | Adj Matrix | Adj List | Edge List |
|-----------|------------|----------|-----------|
| Add vertex | O(V²) | O(1) | O(1) |
| Add edge | O(1) | O(1) | O(1) |
| Remove edge | O(1) | O(degree) | O(E) |
| Has edge? | O(1) | O(degree) | O(E) |
| Get neighbors | O(V) | O(degree) | O(E) |
| Iterate edges | O(V²) | O(V+E) | O(E) |

### Selection Guide
```python
def choose_representation(graph_info: dict) -> str:
    """
    Choose optimal representation based on graph characteristics

    Factors:
    - Density: |E| vs |V|²
    - Operations: queries vs iterations
    - Dynamism: static vs changing
    """
    num_vertices = graph_info["vertices"]
    num_edges = graph_info["edges"]
    density = num_edges / (num_vertices ** 2)

    if density > 0.5:
        return "AdjacencyMatrix"  # Dense graph, matrix operations
    elif graph_info.get("frequent_edge_queries"):
        return "AdjacencyMatrix"  # Need O(1) edge queries
    elif graph_info.get("edge_sorting_needed"):
        return "EdgeList"  # Kruskal's MST, edge processing
    elif graph_info.get("very_large_static"):
        return "CSR"  # Large read-only graph
    else:
        return "AdjacencyList"  # Default for most algorithms
```

---

## Patterns

### Pattern 1: Lazy Conversion
```python
class HybridGraph:
    """Support multiple representations with lazy conversion"""

    def __init__(self, num_vertices: int, directed: bool = False):
        self.num_vertices = num_vertices
        self.directed = directed

        # Primary representation
        self.adj_list = AdjacencyList(num_vertices, directed)

        # Cached representations (lazy)
        self._adj_matrix: Optional[AdjacencyMatrix] = None
        self._edge_list: Optional[EdgeList] = None

    @property
    def adj_matrix(self) -> AdjacencyMatrix:
        """Get adjacency matrix (build if needed)"""
        if self._adj_matrix is None:
            self._adj_matrix = self._build_matrix()
        return self._adj_matrix

    @property
    def edge_list(self) -> EdgeList:
        """Get edge list (build if needed)"""
        if self._edge_list is None:
            self._edge_list = self._build_edge_list()
        return self._edge_list

    def _build_matrix(self) -> AdjacencyMatrix:
        """Build adjacency matrix from list"""
        matrix = AdjacencyMatrix(self.num_vertices, self.directed)
        for u in range(self.num_vertices):
            for edge in self.adj_list.adj[u]:
                matrix.add_edge(u, edge.dest, edge.weight)
        return matrix

    def _build_edge_list(self) -> EdgeList:
        """Build edge list from adjacency list"""
        return EdgeList.from_adjacency_list(self.adj_list)
```

### Pattern 2: Iterator-Based Access
```python
class GraphIterators:
    """Efficient iteration over graph elements"""

    @staticmethod
    def vertices(graph: AdjacencyList):
        """Iterate over vertices"""
        for v in range(graph.num_vertices):
            yield v

    @staticmethod
    def edges(graph: AdjacencyList):
        """Iterate over edges once (handles undirected)"""
        seen = set() if not graph.directed else None

        for u in range(graph.num_vertices):
            for edge in graph.adj[u]:
                v = edge.dest

                if graph.directed:
                    yield (u, v, edge.weight)
                else:
                    edge_key = tuple(sorted([u, v]))
                    if edge_key not in seen:
                        seen.add(edge_key)
                        yield (u, v, edge.weight)

    @staticmethod
    def neighbors_with_weights(graph: AdjacencyList, u: int):
        """Iterate over neighbors with weights"""
        for edge in graph.adj[u]:
            yield (edge.dest, edge.weight)

# Usage
graph = AdjacencyList(5, directed=False)
graph.add_edge(0, 1, 2.5)
graph.add_edge(1, 2, 1.0)

for u, v, w in GraphIterators.edges(graph):
    print(f"Edge ({u}, {v}) weight {w}")
```

---

## Anti-Patterns

### ❌ Wrong Representation for Workload
```python
# WRONG: Matrix for sparse graph
sparse_graph = AdjacencyMatrix(10000, directed=False)
sparse_graph.add_edge(0, 1)
sparse_graph.add_edge(5, 99)
# Wastes 10000² = 100M entries for 2 edges!

# CORRECT: List for sparse graph
sparse_graph = AdjacencyList(10000, directed=False)
sparse_graph.add_edge(0, 1)
sparse_graph.add_edge(5, 99)
# Uses only ~10000 + 4 entries
```

### ❌ Inefficient Edge Queries on List
```python
# WRONG: Repeated edge queries on adjacency list
for u in vertices:
    for v in vertices:
        if adj_list.has_edge(u, v):  # O(degree(u)) each
            process(u, v)
# Total: O(V² × avg_degree)

# CORRECT: Iterate edges directly
for u, v, w in GraphIterators.edges(adj_list):  # O(E)
    process(u, v)
```

### ❌ Modifying During Iteration
```python
# WRONG: Remove edges while iterating
for edge in graph.adj[u]:
    if edge.weight < threshold:
        graph.remove_edge(u, edge.dest)  # Modifies list!

# CORRECT: Collect then remove
to_remove = [edge.dest for edge in graph.adj[u]
             if edge.weight < threshold]
for v in to_remove:
    graph.remove_edge(u, v)
```

---

## Related Skills

**Next Steps**:
- `graph-traversal-algorithms.md` → BFS, DFS using these structures
- `shortest-path-algorithms.md` → Dijkstra, Bellman-Ford implementations
- `minimum-spanning-tree.md` → Kruskal, Prim with optimal representations

**Foundations**:
- `graph-theory-fundamentals.md` → Concepts these structures represent
- `linear-algebra-computation.md` → Matrix operations for spectral methods

---

## Summary

Graph data structures provide the foundation for efficient graph algorithms:
- **Adjacency Matrix**: O(V²) space, O(1) edge queries, best for dense graphs
- **Adjacency List**: O(V+E) space, O(degree) edge queries, best for sparse graphs
- **Edge List**: O(E) space, best for edge-centric algorithms (Kruskal's MST)
- **CSR**: O(V+E) space with cache efficiency, best for large static graphs

**Key takeaways**:
1. Representation choice affects algorithm performance significantly
2. Sparse graphs (|E| << |V|²) prefer adjacency lists
3. Dense graphs or matrix operations prefer adjacency matrices
4. Edge-centric algorithms prefer edge lists
5. Support lazy conversion between representations when needed

**Next**: Move to `graph-traversal-algorithms.md` to implement BFS and DFS.
