---
name: Minimum Spanning Tree Algorithms
description: Kruskal and Prim algorithms for finding minimum spanning trees in weighted undirected graphs with union-find and priority queue optimizations
---

# Minimum Spanning Tree Algorithms

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Designing network infrastructure (roads, cables, pipelines)
- Minimizing connection costs in networks
- Clustering and hierarchical data analysis
- Approximating NP-hard problems (TSP, Steiner tree)
- Building network backbones
- Finding minimum cost spanning subgraphs

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`, `graph-traversal-algorithms.md`

**Related Skills**: `shortest-path-algorithms.md`, `network-flow-algorithms.md`, `graph-applications.md`

---

## Core Concepts

### Minimum Spanning Tree (MST)

**Definition**: For connected undirected weighted graph G = (V, E):
- **Spanning tree**: Subgraph T = (V, E') that is:
  - **Connected**: Path exists between all vertex pairs
  - **Acyclic**: No cycles
  - **Spanning**: Includes all vertices
  - Has exactly |V| - 1 edges

- **Minimum spanning tree**: Spanning tree with minimum total edge weight

**Properties**:
```
1. MST exists ⟺ graph is connected
2. MST has |V| - 1 edges
3. MST may not be unique (if edge weights not distinct)
4. Removing any MST edge disconnects tree
5. Adding any non-MST edge creates cycle
```

---

## Core Algorithms

### 1. Kruskal's Algorithm

**Concept**: Greedy algorithm that builds MST by adding edges in ascending weight order

**Strategy**: Sort edges by weight, add edge if it doesn't create cycle

**Properties**:
- **Time**: O(E log E) for sorting + O(E α(V)) for union-find ≈ O(E log V)
- **Space**: O(V) for union-find structure
- **Best for**: Sparse graphs, edge-centric processing

```python
from typing import List, Set, Tuple
from dataclasses import dataclass

@dataclass
class Edge:
    """Weighted edge for MST algorithms"""
    u: int
    v: int
    weight: float

    def __lt__(self, other):
        return self.weight < other.weight

class UnionFind:
    """
    Disjoint set union (union-find) data structure

    Operations:
    - find(x): Find representative of x's set - O(α(n)) amortized
    - union(x, y): Merge sets containing x and y - O(α(n)) amortized

    α(n) = inverse Ackermann function, effectively constant
    """

    def __init__(self, n: int):
        self.parent = list(range(n))  # parent[i] = parent of i
        self.rank = [0] * n           # rank[i] = tree height (approx)
        self.num_sets = n             # Number of disjoint sets

    def find(self, x: int) -> int:
        """Find representative with path compression"""
        if self.parent[x] != x:
            # Path compression: point directly to root
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """
        Union by rank: attach smaller tree to larger

        Returns: True if sets were merged, False if already in same set
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False  # Already in same set

        # Union by rank: attach smaller to larger
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        self.num_sets -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """Check if x and y in same set"""
        return self.find(x) == self.find(y)

def kruskal(num_vertices: int, edges: List[Edge]) -> Tuple[List[Edge], float]:
    """
    Kruskal's MST algorithm

    Args:
        num_vertices: Number of vertices
        edges: List of weighted edges

    Returns:
        (mst_edges, total_weight) where mst_edges is list of edges in MST
    """
    # Sort edges by weight
    sorted_edges = sorted(edges)

    # Initialize union-find
    uf = UnionFind(num_vertices)

    mst_edges = []
    total_weight = 0.0

    for edge in sorted_edges:
        # Add edge if it doesn't create cycle
        if uf.union(edge.u, edge.v):
            mst_edges.append(edge)
            total_weight += edge.weight

            # Stop when MST is complete
            if len(mst_edges) == num_vertices - 1:
                break

    # Check if graph was connected
    if len(mst_edges) != num_vertices - 1:
        raise ValueError("Graph is not connected - no spanning tree exists")

    return mst_edges, total_weight

# Example usage
edges = [
    Edge(0, 1, 4),
    Edge(0, 2, 1),
    Edge(1, 2, 2),
    Edge(1, 3, 5),
    Edge(2, 3, 8),
    Edge(2, 4, 10),
    Edge(3, 4, 2),
    Edge(3, 5, 6),
    Edge(4, 5, 3)
]

mst_edges, total_weight = kruskal(6, edges)
print(f"MST total weight: {total_weight}")  # 16.0
print("MST edges:")
for edge in mst_edges:
    print(f"  ({edge.u}, {edge.v}): {edge.weight}")
```

**Kruskal with Edge Filtering**:
```python
def kruskal_with_constraints(num_vertices: int,
                             edges: List[Edge],
                             required_edges: Set[Tuple[int, int]] = None,
                             forbidden_edges: Set[Tuple[int, int]] = None
                            ) -> Tuple[List[Edge], float]:
    """
    Kruskal's algorithm with edge constraints

    Args:
        required_edges: Edges that MUST be in MST
        forbidden_edges: Edges that CANNOT be in MST
    """
    if required_edges is None:
        required_edges = set()
    if forbidden_edges is None:
        forbidden_edges = set()

    # Add required edges first
    uf = UnionFind(num_vertices)
    mst_edges = []
    total_weight = 0.0

    for edge in edges:
        edge_tuple = tuple(sorted([edge.u, edge.v]))

        if edge_tuple in required_edges:
            if not uf.union(edge.u, edge.v):
                raise ValueError(f"Required edges create cycle: {edge_tuple}")
            mst_edges.append(edge)
            total_weight += edge.weight

    # Filter and sort remaining edges
    remaining = [e for e in edges
                if tuple(sorted([e.u, e.v])) not in required_edges
                and tuple(sorted([e.u, e.v])) not in forbidden_edges]
    remaining.sort()

    # Standard Kruskal on remaining edges
    for edge in remaining:
        if uf.union(edge.u, edge.v):
            mst_edges.append(edge)
            total_weight += edge.weight

            if len(mst_edges) == num_vertices - 1:
                break

    return mst_edges, total_weight
```

### 2. Prim's Algorithm

**Concept**: Greedy algorithm that grows MST from single vertex

**Strategy**: Start from arbitrary vertex, repeatedly add minimum-weight edge connecting tree to non-tree vertex

**Properties**:
- **Time**: O(E log V) with binary heap, O(V²) with array
- **Space**: O(V) for priority queue and visited set
- **Best for**: Dense graphs, vertex-centric processing

```python
import heapq
from typing import Optional
import math

@dataclass
class MSTResult:
    """Results from Prim's algorithm"""
    edges: List[Edge]
    total_weight: float
    parents: dict[int, Optional[int]]

def prim(graph: 'WeightedGraph', start: int = 0) -> MSTResult:
    """
    Prim's MST algorithm

    Args:
        graph: Weighted undirected graph (adjacency list)
        start: Starting vertex (arbitrary)

    Returns:
        MSTResult with edges, total weight, and parent pointers
    """
    visited = set()
    parents = {start: None}
    min_weight = {v: math.inf for v in range(graph.num_vertices)}
    min_weight[start] = 0

    # Priority queue: (weight, vertex, parent)
    pq = [(0, start, None)]

    mst_edges = []
    total_weight = 0.0

    while pq and len(visited) < graph.num_vertices:
        weight, u, parent = heapq.heappop(pq)

        if u in visited:
            continue

        visited.add(u)

        # Add edge to MST (except for start vertex)
        if parent is not None:
            mst_edges.append(Edge(parent, u, weight))
            total_weight += weight

        # Explore neighbors
        for edge in graph.adj[u]:
            v = edge.dest
            edge_weight = edge.weight

            if v not in visited and edge_weight < min_weight[v]:
                min_weight[v] = edge_weight
                parents[v] = u
                heapq.heappush(pq, (edge_weight, v, u))

    if len(visited) != graph.num_vertices:
        raise ValueError("Graph is not connected")

    return MSTResult(mst_edges, total_weight, parents)

# Example usage
from graph_data_structures import WeightedGraph

graph = WeightedGraph(6, directed=False)
graph.add_edge(0, 1, 4)
graph.add_edge(0, 2, 1)
graph.add_edge(1, 2, 2)
graph.add_edge(1, 3, 5)
graph.add_edge(2, 3, 8)
graph.add_edge(2, 4, 10)
graph.add_edge(3, 4, 2)
graph.add_edge(3, 5, 6)
graph.add_edge(4, 5, 3)

result = prim(graph, start=0)
print(f"MST total weight: {result.total_weight}")  # 16.0
print("MST edges:")
for edge in result.edges:
    print(f"  ({edge.u}, {edge.v}): {edge.weight}")
```

**Optimized Prim with Fibonacci Heap**:
```python
def prim_dense(graph: 'WeightedGraph') -> MSTResult:
    """
    Prim's algorithm optimized for dense graphs using simple array

    Time: O(V²) - better than O(E log V) when E ≈ V²
    """
    visited = [False] * graph.num_vertices
    min_weight = [math.inf] * graph.num_vertices
    parents = [None] * graph.num_vertices

    min_weight[0] = 0
    mst_edges = []
    total_weight = 0.0

    for _ in range(graph.num_vertices):
        # Find minimum unvisited vertex - O(V)
        u = -1
        for v in range(graph.num_vertices):
            if not visited[v] and (u == -1 or min_weight[v] < min_weight[u]):
                u = v

        if min_weight[u] == math.inf:
            raise ValueError("Graph is not connected")

        visited[u] = True

        # Add edge to MST
        if parents[u] is not None:
            mst_edges.append(Edge(parents[u], u, min_weight[u]))
            total_weight += min_weight[u]

        # Update neighbors - O(V) for adjacency matrix
        for edge in graph.adj[u]:
            v = edge.dest
            if not visited[v] and edge.weight < min_weight[v]:
                min_weight[v] = edge.weight
                parents[v] = u

    return MSTResult(mst_edges, total_weight, dict(enumerate(parents)))
```

---

## Algorithm Comparison

### Kruskal vs Prim

| Aspect | Kruskal | Prim |
|--------|---------|------|
| **Strategy** | Edge-centric (sort edges) | Vertex-centric (grow tree) |
| **Time (sparse)** | O(E log E) | O(E log V) |
| **Time (dense)** | O(E log E) | O(V²) with array |
| **Data structure** | Union-Find | Priority Queue |
| **Best for** | Sparse graphs, edge list | Dense graphs, adj matrix |
| **Parallelizable** | Easier (independent edges) | Harder (sequential growth) |
| **Memory** | O(V) for UF | O(V) for PQ |

### Selection Guide
```python
def choose_mst_algorithm(graph_info: dict) -> str:
    """Select optimal MST algorithm based on graph properties"""
    num_vertices = graph_info["num_vertices"]
    num_edges = graph_info["num_edges"]
    density = num_edges / (num_vertices * (num_vertices - 1) / 2)

    has_edge_list = graph_info.get("has_edge_list", False)
    has_adj_matrix = graph_info.get("has_adj_matrix", False)

    if has_edge_list or density < 0.3:
        return "Kruskal"  # Sparse graph or edge list available

    if has_adj_matrix or density > 0.7:
        if num_vertices <= 1000:
            return "Prim (dense)"  # O(V²) better for dense
        else:
            return "Prim (heap)"

    return "Prim (heap)"  # Default
```

---

## Patterns

### Pattern 1: MST Variants
```python
class MSTVariants:
    """Common MST-related problems"""

    @staticmethod
    def second_best_mst(num_vertices: int, edges: List[Edge]
                       ) -> Tuple[List[Edge], float]:
        """
        Find second-best minimum spanning tree

        Approach: For each MST edge, find best MST without it
        """
        # Find primary MST
        mst_edges, min_weight = kruskal(num_vertices, edges)
        mst_edge_set = {tuple(sorted([e.u, e.v])) for e in mst_edges}

        second_best_weight = math.inf
        second_best_edges = None

        # Try removing each MST edge
        for excluded_edge in mst_edges:
            forbidden = {tuple(sorted([excluded_edge.u, excluded_edge.v]))}

            try:
                alt_edges, alt_weight = kruskal_with_constraints(
                    num_vertices, edges, forbidden_edges=forbidden
                )

                if alt_weight < second_best_weight:
                    second_best_weight = alt_weight
                    second_best_edges = alt_edges

            except ValueError:
                # Graph becomes disconnected
                continue

        return second_best_edges, second_best_weight

    @staticmethod
    def mst_with_degree_bound(num_vertices: int,
                             edges: List[Edge],
                             max_degree: int) -> Optional[Tuple[List[Edge], float]]:
        """
        Find MST where no vertex has degree > max_degree

        This is NP-hard in general; uses greedy heuristic
        """
        sorted_edges = sorted(edges)
        uf = UnionFind(num_vertices)
        degree = [0] * num_vertices

        mst_edges = []
        total_weight = 0.0

        for edge in sorted_edges:
            # Check degree constraints
            if degree[edge.u] >= max_degree or degree[edge.v] >= max_degree:
                continue

            if uf.union(edge.u, edge.v):
                mst_edges.append(edge)
                total_weight += edge.weight
                degree[edge.u] += 1
                degree[edge.v] += 1

                if len(mst_edges) == num_vertices - 1:
                    return mst_edges, total_weight

        return None  # No solution found
```

### Pattern 2: MST-Based Clustering
```python
def hierarchical_clustering(num_vertices: int,
                           edges: List[Edge],
                           num_clusters: int) -> List[Set[int]]:
    """
    Perform hierarchical clustering by removing largest MST edges

    Strategy: Build MST, remove k-1 largest edges to get k clusters
    """
    if num_clusters >= num_vertices:
        return [{i} for i in range(num_vertices)]

    # Build MST
    mst_edges, _ = kruskal(num_vertices, edges)

    # Sort MST edges by weight (descending)
    mst_edges.sort(key=lambda e: e.weight, reverse=True)

    # Remove k-1 largest edges
    keep_edges = mst_edges[num_clusters - 1:]

    # Build clusters using union-find on remaining edges
    uf = UnionFind(num_vertices)

    for edge in keep_edges:
        uf.union(edge.u, edge.v)

    # Group vertices by component
    clusters_map = {}
    for v in range(num_vertices):
        root = uf.find(v)
        if root not in clusters_map:
            clusters_map[root] = set()
        clusters_map[root].add(v)

    return list(clusters_map.values())
```

---

## Quick Reference

### MST Properties
| Property | Value |
|----------|-------|
| Number of edges | \|V\| - 1 |
| Exists ⟺ | Graph is connected |
| Uniqueness | Not guaranteed (unless all weights distinct) |
| Cycle property | Max weight edge in cycle not in MST |
| Cut property | Min weight edge crossing cut is in some MST |

### Algorithm Complexity
| Algorithm | Time (sparse) | Time (dense) | Space |
|-----------|---------------|--------------|-------|
| Kruskal | O(E log E) | O(V² log V²) | O(V) |
| Prim (heap) | O(E log V) | O(V² log V) | O(V) |
| Prim (array) | O(V²) | O(V²) | O(V) |

---

## Anti-Patterns

### ❌ Using MST on Directed Graphs
```python
# WRONG: MST only defined for undirected graphs
directed_graph = WeightedGraph(5, directed=True)
result = prim(directed_graph)  # Incorrect!

# CORRECT: Use minimum spanning arborescence for directed
# (Different algorithm - not covered here)
```

### ❌ Not Checking Connectivity
```python
# WRONG: Assume graph is connected
mst_edges, weight = kruskal(num_vertices, edges)
print(f"MST weight: {weight}")  # May be incomplete!

# CORRECT: Check edge count or catch exception
try:
    mst_edges, weight = kruskal(num_vertices, edges)
    if len(mst_edges) != num_vertices - 1:
        print("Graph is not connected")
except ValueError as e:
    print(f"Error: {e}")
```

### ❌ Inefficient Algorithm Choice
```python
# WRONG: Kruskal on dense graph with adjacency matrix
dense_graph = WeightedGraph(1000, directed=False)
# ... add ~500,000 edges ...
edges = dense_graph.all_edges()  # Expensive conversion!
mst = kruskal(1000, edges)        # O(E log E) ≈ O(V² log V²)

# CORRECT: Use Prim with array for dense graphs
mst = prim_dense(dense_graph)     # O(V²) better for dense
```

---

## Related Skills

**Next Steps**:
- `network-flow-algorithms.md` → Max flow, min cut algorithms
- `advanced-graph-algorithms.md` → Steiner tree, matching algorithms
- `graph-applications.md` → Real-world MST applications

**Foundations**:
- `graph-theory-fundamentals.md` → Basic graph concepts
- `graph-data-structures.md` → Graph representations
- `graph-traversal-algorithms.md` → DFS and BFS

---

## Summary

Minimum spanning tree algorithms find minimum-weight connected acyclic subgraphs:
- **Kruskal**: Edge-centric, O(E log E), best for sparse graphs
- **Prim**: Vertex-centric, O(E log V) or O(V²), best for dense graphs
- **Union-Find**: Key data structure for efficient cycle detection in Kruskal
- **Applications**: Network design, clustering, approximation algorithms

**Key takeaways**:
1. MST has exactly |V| - 1 edges for connected graph
2. Both algorithms produce optimal MST (greedy choice property)
3. Kruskal better for sparse graphs and edge lists
4. Prim better for dense graphs and adjacency matrices
5. Union-find with path compression and union by rank achieves near-constant time

**Next**: Move to `network-flow-algorithms.md` for maximum flow algorithms.
