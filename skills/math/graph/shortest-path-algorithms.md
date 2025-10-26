---
name: Shortest Path Algorithms
description: Dijkstra, Bellman-Ford, Floyd-Warshall, and A* algorithms for finding shortest paths in weighted graphs with various constraints
---

# Shortest Path Algorithms

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Finding shortest paths in weighted graphs
- Route planning and navigation
- Network routing protocols
- Optimizing delivery routes
- Handling negative edge weights
- Computing all-pairs shortest paths
- Using heuristics for faster pathfinding (A*)

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`, `graph-traversal-algorithms.md`

**Related Skills**: `minimum-spanning-tree.md`, `network-flow-algorithms.md`, `graph-applications.md`

---

## Core Algorithms

### 1. Dijkstra's Algorithm

**Concept**: Greedy algorithm for single-source shortest paths with non-negative weights

**Properties**:
- **Time**: O((V + E) log V) with binary heap, O(V²) with array
- **Space**: O(V) for distances and priority queue
- **Constraint**: Requires non-negative edge weights
- **Finds**: Shortest paths from source to all vertices

```python
import heapq
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

@dataclass
class DijkstraResult:
    """Results from Dijkstra's algorithm"""
    distances: Dict[int, float]
    parents: Dict[int, Optional[int]]

    def get_path(self, target: int) -> Optional[List[int]]:
        """Reconstruct shortest path to target"""
        if target not in self.parents:
            return None

        path = []
        current = target

        while current is not None:
            path.append(current)
            current = self.parents[current]

        return list(reversed(path))

def dijkstra(graph: 'WeightedGraph', source: int) -> DijkstraResult:
    """
    Dijkstra's shortest path algorithm

    Args:
        graph: Weighted graph (adjacency list with weights)
        source: Starting vertex

    Returns:
        DijkstraResult with distances and parent pointers
    """
    # Initialize distances to infinity
    distances = {v: math.inf for v in range(graph.num_vertices)}
    distances[source] = 0

    # Parent pointers for path reconstruction
    parents = {source: None}

    # Priority queue: (distance, vertex)
    pq = [(0, source)]
    visited = set()

    while pq:
        dist_u, u = heapq.heappop(pq)

        if u in visited:
            continue

        visited.add(u)

        # Relaxation: Update distances to neighbors
        for edge in graph.adj[u]:
            v = edge.dest
            weight = edge.weight

            if v in visited:
                continue

            new_dist = distances[u] + weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                parents[v] = u
                heapq.heappush(pq, (new_dist, v))

    return DijkstraResult(distances, parents)

# Example usage
from graph_data_structures import WeightedGraph

graph = WeightedGraph(5, directed=False)
graph.add_edge(0, 1, 4)
graph.add_edge(0, 2, 1)
graph.add_edge(2, 1, 2)
graph.add_edge(1, 3, 1)
graph.add_edge(2, 3, 5)
graph.add_edge(3, 4, 3)

result = dijkstra(graph, source=0)
path = result.get_path(4)
print(f"Shortest path 0→4: {path}")        # [0, 2, 1, 3, 4]
print(f"Distance: {result.distances[4]}")  # 7.0
```

**Optimized Dijkstra with Early Termination**:
```python
def dijkstra_single_target(graph: 'WeightedGraph',
                          source: int,
                          target: int) -> Tuple[float, List[int]]:
    """
    Dijkstra with early termination when target is reached

    More efficient when only one shortest path is needed
    """
    distances = {v: math.inf for v in range(graph.num_vertices)}
    distances[source] = 0
    parents = {source: None}

    pq = [(0, source)]
    visited = set()

    while pq:
        dist_u, u = heapq.heappop(pq)

        # Early termination
        if u == target:
            path = []
            current = target
            while current is not None:
                path.append(current)
                current = parents[current]
            return dist_u, list(reversed(path))

        if u in visited:
            continue

        visited.add(u)

        for edge in graph.adj[u]:
            v = edge.dest
            new_dist = distances[u] + edge.weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                parents[v] = u
                heapq.heappush(pq, (new_dist, v))

    return math.inf, []  # Target not reachable
```

### 2. Bellman-Ford Algorithm

**Concept**: Dynamic programming approach that handles negative weights

**Properties**:
- **Time**: O(V × E)
- **Space**: O(V) for distances
- **Constraint**: Detects negative cycles
- **Finds**: Shortest paths even with negative weights

```python
@dataclass
class BellmanFordResult:
    """Results from Bellman-Ford algorithm"""
    distances: Dict[int, float]
    parents: Dict[int, Optional[int]]
    has_negative_cycle: bool

    def get_path(self, target: int) -> Optional[List[int]]:
        """Reconstruct path if no negative cycle"""
        if self.has_negative_cycle:
            return None

        if target not in self.parents:
            return None

        path = []
        current = target

        while current is not None:
            path.append(current)
            current = self.parents[current]

        return list(reversed(path))

def bellman_ford(graph: 'WeightedGraph', source: int) -> BellmanFordResult:
    """
    Bellman-Ford shortest path algorithm

    Handles negative edge weights and detects negative cycles
    """
    # Initialize
    distances = {v: math.inf for v in range(graph.num_vertices)}
    distances[source] = 0
    parents = {source: None}

    # Relax all edges V-1 times
    for _ in range(graph.num_vertices - 1):
        for u in range(graph.num_vertices):
            if distances[u] == math.inf:
                continue

            for edge in graph.adj[u]:
                v = edge.dest
                new_dist = distances[u] + edge.weight

                if new_dist < distances[v]:
                    distances[v] = new_dist
                    parents[v] = u

    # Check for negative cycles
    has_negative_cycle = False

    for u in range(graph.num_vertices):
        if distances[u] == math.inf:
            continue

        for edge in graph.adj[u]:
            v = edge.dest
            if distances[u] + edge.weight < distances[v]:
                has_negative_cycle = True
                break

        if has_negative_cycle:
            break

    return BellmanFordResult(distances, parents, has_negative_cycle)

# Example with negative weights
graph_neg = WeightedGraph(4, directed=True)
graph_neg.add_edge(0, 1, 1)
graph_neg.add_edge(1, 2, -2)
graph_neg.add_edge(2, 3, 3)
graph_neg.add_edge(0, 3, 5)

result = bellman_ford(graph_neg, source=0)
print(f"Has negative cycle: {result.has_negative_cycle}")  # False
print(f"Distance to 3: {result.distances[3]}")              # 2.0
```

**SPFA (Shortest Path Faster Algorithm)**:
```python
from collections import deque

def spfa(graph: 'WeightedGraph', source: int) -> BellmanFordResult:
    """
    SPFA: Queue-based optimization of Bellman-Ford

    Average case: O(E), worst case: O(V × E)
    Often faster in practice than standard Bellman-Ford
    """
    distances = {v: math.inf for v in range(graph.num_vertices)}
    distances[source] = 0
    parents = {source: None}

    queue = deque([source])
    in_queue = {source}
    relax_count = {v: 0 for v in range(graph.num_vertices)}

    while queue:
        u = queue.popleft()
        in_queue.discard(u)

        for edge in graph.adj[u]:
            v = edge.dest
            new_dist = distances[u] + edge.weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                parents[v] = u

                if v not in in_queue:
                    queue.append(v)
                    in_queue.add(v)

                    relax_count[v] += 1

                    # Negative cycle detection
                    if relax_count[v] >= graph.num_vertices:
                        return BellmanFordResult({}, {}, True)

    return BellmanFordResult(distances, parents, False)
```

### 3. Floyd-Warshall Algorithm

**Concept**: Dynamic programming for all-pairs shortest paths

**Properties**:
- **Time**: O(V³)
- **Space**: O(V²) for distance matrix
- **Constraint**: Can detect negative cycles
- **Finds**: Shortest paths between all pairs of vertices

```python
def floyd_warshall(graph: 'WeightedGraph') -> Tuple[List[List[float]],
                                                     List[List[Optional[int]]]]:
    """
    Floyd-Warshall all-pairs shortest paths

    Returns:
        (dist, next) where:
        - dist[i][j] = shortest distance from i to j
        - next[i][j] = next vertex on shortest path from i to j
    """
    n = graph.num_vertices

    # Initialize distance matrix
    dist = [[math.inf] * n for _ in range(n)]
    next_vertex = [[None] * n for _ in range(n)]

    # Distance from vertex to itself is 0
    for i in range(n):
        dist[i][i] = 0

    # Initialize with direct edges
    for u in range(n):
        for edge in graph.adj[u]:
            v = edge.dest
            dist[u][v] = edge.weight
            next_vertex[u][v] = v

    # Floyd-Warshall: Try each intermediate vertex k
    for k in range(n):
        for i in range(n):
            for j in range(n):
                new_dist = dist[i][k] + dist[k][j]

                if new_dist < dist[i][j]:
                    dist[i][j] = new_dist
                    next_vertex[i][j] = next_vertex[i][k]

    # Check for negative cycles
    for i in range(n):
        if dist[i][i] < 0:
            raise ValueError("Graph contains negative cycle")

    return dist, next_vertex

def reconstruct_path_fw(next_vertex: List[List[Optional[int]]],
                       u: int, v: int) -> Optional[List[int]]:
    """Reconstruct path from u to v using Floyd-Warshall next pointers"""
    if next_vertex[u][v] is None:
        return None

    path = [u]
    current = u

    while current != v:
        current = next_vertex[current][v]
        path.append(current)

    return path

# Example usage
graph = WeightedGraph(4, directed=True)
graph.add_edge(0, 1, 3)
graph.add_edge(0, 2, 8)
graph.add_edge(1, 3, 1)
graph.add_edge(2, 1, 4)
graph.add_edge(3, 0, 2)
graph.add_edge(3, 2, -5)

dist, next_v = floyd_warshall(graph)
path = reconstruct_path_fw(next_v, 0, 2)
print(f"Shortest path 0→2: {path}")     # [0, 1, 3, 2]
print(f"Distance: {dist[0][2]}")         # -1.0
```

### 4. A* Algorithm

**Concept**: Informed search using heuristic to guide exploration

**Properties**:
- **Time**: Depends on heuristic quality, often much better than Dijkstra
- **Space**: O(V) for open/closed sets
- **Constraint**: Requires admissible heuristic (never overestimates)
- **Finds**: Optimal path if heuristic is consistent

```python
from typing import Callable

def a_star(graph: 'WeightedGraph',
          source: int,
          target: int,
          heuristic: Callable[[int, int], float]) -> Tuple[float, List[int]]:
    """
    A* shortest path algorithm with heuristic

    Args:
        graph: Weighted graph
        source: Start vertex
        target: Goal vertex
        heuristic: h(v, target) estimates distance from v to target

    Returns:
        (distance, path) from source to target

    Heuristic must be admissible: h(v, target) ≤ true distance
    """
    # g[v] = cost from source to v
    g_score = {v: math.inf for v in range(graph.num_vertices)}
    g_score[source] = 0

    # f[v] = g[v] + h(v, target) = estimated total cost
    f_score = {source: heuristic(source, target)}

    parents = {source: None}

    # Priority queue: (f_score, vertex)
    open_set = [(f_score[source], source)]
    closed_set = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        # Found target
        if current == target:
            path = []
            node = current
            while node is not None:
                path.append(node)
                node = parents[node]
            return g_score[target], list(reversed(path))

        if current in closed_set:
            continue

        closed_set.add(current)

        # Explore neighbors
        for edge in graph.adj[current]:
            neighbor = edge.dest

            if neighbor in closed_set:
                continue

            tentative_g = g_score[current] + edge.weight

            if tentative_g < g_score[neighbor]:
                parents[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, target)

                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return math.inf, []  # No path found

# Example: Grid graph with Manhattan distance heuristic
class GridGraph:
    """2D grid represented as graph"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.graph = WeightedGraph(width * height, directed=False)

        # Connect adjacent cells
        for y in range(height):
            for x in range(width):
                u = y * width + x

                # Right neighbor
                if x + 1 < width:
                    v = y * width + (x + 1)
                    self.graph.add_edge(u, v, 1)

                # Down neighbor
                if y + 1 < height:
                    v = (y + 1) * width + x
                    self.graph.add_edge(u, v, 1)

    def manhattan_heuristic(self, v: int, target: int) -> float:
        """Manhattan distance on grid"""
        v_x, v_y = v % self.width, v // self.width
        t_x, t_y = target % self.width, target // self.width
        return abs(v_x - t_x) + abs(v_y - t_y)

# Find path in 10×10 grid
grid = GridGraph(10, 10)
source = 0  # Top-left
target = 99  # Bottom-right

dist, path = a_star(
    grid.graph,
    source,
    target,
    lambda v, t: grid.manhattan_heuristic(v, t)
)

print(f"A* path length: {len(path)}")  # 19 (Manhattan distance = 18 + 1)
print(f"Distance: {dist}")              # 18.0
```

---

## Patterns

### Pattern 1: Algorithm Selection
```python
def choose_shortest_path_algorithm(graph_info: dict) -> str:
    """
    Select optimal shortest path algorithm based on graph properties
    """
    has_negative_weights = graph_info.get("has_negative_weights", False)
    all_pairs = graph_info.get("all_pairs_needed", False)
    has_heuristic = graph_info.get("has_heuristic", False)
    num_vertices = graph_info["num_vertices"]
    num_edges = graph_info["num_edges"]

    if all_pairs:
        if num_vertices <= 400:
            return "Floyd-Warshall"  # O(V³) acceptable
        else:
            return "Multiple Dijkstra"  # V × O(E log V)

    if has_negative_weights:
        if num_edges < num_vertices * 10:
            return "SPFA"  # Often faster for sparse graphs
        else:
            return "Bellman-Ford"

    if has_heuristic:
        return "A*"  # Best for single-target with good heuristic

    return "Dijkstra"  # Default for non-negative weights
```

### Pattern 2: Path Reconstruction Helper
```python
class ShortestPathSolver:
    """Unified interface for shortest path algorithms"""

    @staticmethod
    def solve(graph: 'WeightedGraph',
             source: int,
             target: Optional[int] = None,
             algorithm: str = "auto") -> Dict:
        """
        Solve shortest path problem with automatic algorithm selection
        """
        has_negative = any(
            edge.weight < 0
            for u in range(graph.num_vertices)
            for edge in graph.adj[u]
        )

        if algorithm == "auto":
            if has_negative:
                algorithm = "bellman-ford"
            elif target is not None:
                algorithm = "dijkstra-single"
            else:
                algorithm = "dijkstra"

        if algorithm == "dijkstra":
            result = dijkstra(graph, source)
            return {
                "algorithm": "Dijkstra",
                "distances": result.distances,
                "get_path": result.get_path
            }

        elif algorithm == "dijkstra-single":
            dist, path = dijkstra_single_target(graph, source, target)
            return {
                "algorithm": "Dijkstra (single-target)",
                "distance": dist,
                "path": path
            }

        elif algorithm == "bellman-ford":
            result = bellman_ford(graph, source)
            return {
                "algorithm": "Bellman-Ford",
                "distances": result.distances,
                "has_negative_cycle": result.has_negative_cycle,
                "get_path": result.get_path
            }

        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
```

---

## Quick Reference

### Algorithm Comparison
| Algorithm | Time | Space | Negative Weights | All Pairs | Best Use Case |
|-----------|------|-------|------------------|-----------|---------------|
| Dijkstra | O((V+E) log V) | O(V) | ❌ | ❌ | Non-negative, single-source |
| Bellman-Ford | O(VE) | O(V) | ✅ | ❌ | Negative weights, cycle detection |
| SPFA | O(E) avg | O(V) | ✅ | ❌ | Sparse graphs, negative weights |
| Floyd-Warshall | O(V³) | O(V²) | ✅ | ✅ | Small graphs, all pairs |
| A* | Heuristic-dependent | O(V) | ❌ | ❌ | Single target with heuristic |

### When to Use Which
- **Dijkstra**: Default for non-negative weights, best performance
- **Bellman-Ford**: Negative weights, need cycle detection
- **SPFA**: Optimization of Bellman-Ford for sparse graphs
- **Floyd-Warshall**: All-pairs distances, small graphs (V ≤ 400)
- **A***: Single target, good heuristic available (games, robotics)

---

## Anti-Patterns

### ❌ Using Dijkstra with Negative Weights
```python
# WRONG: Dijkstra fails with negative weights
graph.add_edge(0, 1, -5)
result = dijkstra(graph, 0)  # Incorrect results!

# CORRECT: Use Bellman-Ford or SPFA
result = bellman_ford(graph, 0)
```

### ❌ Not Checking for Negative Cycles
```python
# WRONG: Assume result is valid
result = bellman_ford(graph, 0)
print(result.distances[target])  # May be incorrect!

# CORRECT: Check for negative cycle
result = bellman_ford(graph, 0)
if result.has_negative_cycle:
    print("No shortest path exists (negative cycle)")
else:
    print(result.distances[target])
```

### ❌ Using Floyd-Warshall for Large Graphs
```python
# WRONG: O(V³) for 10,000 vertices = 10¹² operations
large_graph = WeightedGraph(10000)
dist, next_v = floyd_warshall(large_graph)  # Too slow!

# CORRECT: Run Dijkstra from each vertex
for source in range(large_graph.num_vertices):
    result = dijkstra(large_graph, source)
    # Process result
```

---

## Related Skills

**Next Steps**:
- `minimum-spanning-tree.md` → Kruskal and Prim algorithms
- `network-flow-algorithms.md` → Max flow, min cost flow
- `graph-applications.md` → Real-world routing and navigation

**Foundations**:
- `graph-theory-fundamentals.md` → Basic graph concepts
- `graph-data-structures.md` → Efficient graph representations
- `graph-traversal-algorithms.md` → BFS and DFS basics

---

## Summary

Shortest path algorithms find optimal routes in weighted graphs:
- **Dijkstra**: Greedy algorithm for non-negative weights, O((V+E) log V)
- **Bellman-Ford**: DP for negative weights with cycle detection, O(VE)
- **Floyd-Warshall**: DP for all-pairs shortest paths, O(V³)
- **A***: Informed search with heuristic guidance

**Key takeaways**:
1. Dijkstra is fastest for non-negative weights
2. Bellman-Ford handles negative weights and detects negative cycles
3. Floyd-Warshall computes all-pairs distances but scales O(V³)
4. A* outperforms Dijkstra when good heuristic is available
5. Always validate graph properties before algorithm selection

**Next**: Move to `minimum-spanning-tree.md` for MST algorithms.
