---
name: Network Flow Algorithms
description: Maximum flow, minimum cut, Ford-Fulkerson, Edmonds-Karp, and flow-based algorithms for capacity-constrained network optimization
---

# Network Flow Algorithms

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Maximizing throughput in networks (data, traffic, pipelines)
- Finding bottlenecks in systems
- Solving bipartite matching problems
- Computing minimum cuts in graphs
- Optimizing resource allocation with capacities
- Solving circulation and transportation problems

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`, `graph-traversal-algorithms.md`

**Related Skills**: `shortest-path-algorithms.md`, `minimum-spanning-tree.md`, `advanced-graph-algorithms.md`

---

## Core Concepts

### Flow Network

**Definition**: Directed graph G = (V, E) with:
- **Source** s ∈ V: Flow originates here
- **Sink** t ∈ V: Flow terminates here
- **Capacity** c: E → ℝ⁺: Maximum flow on each edge
- **Flow** f: E → ℝ: Actual flow on each edge

**Flow Properties**:
```
1. Capacity constraint: 0 ≤ f(u,v) ≤ c(u,v) for all (u,v) ∈ E
2. Flow conservation: ∑f(u,v) = ∑f(v,w) for all v ∈ V \ {s,t}
                      (in)      (out)
   (Flow in = flow out for non-source/sink vertices)
3. Value of flow: |f| = ∑f(s,v) - ∑f(u,s)
                        (out of s)  (into s)
```

**Maximum Flow Problem**: Find flow f with maximum value |f|

---

## Core Algorithms

### 1. Ford-Fulkerson Method

**Concept**: Iteratively find augmenting paths and increase flow

**Key Ideas**:
- **Residual graph** Gf: Shows remaining capacity
- **Augmenting path**: Path from s to t in residual graph
- **Max-flow min-cut theorem**: Max flow value = min cut capacity

```python
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque
import math

class FlowNetwork:
    """Flow network representation"""

    def __init__(self, num_vertices: int):
        self.num_vertices = num_vertices
        # capacity[u][v] = capacity from u to v
        self.capacity: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        # flow[u][v] = current flow from u to v
        self.flow: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))

    def add_edge(self, u: int, v: int, capacity: float):
        """Add directed edge with capacity"""
        self.capacity[u][v] += capacity

    def get_residual_capacity(self, u: int, v: int) -> float:
        """Get residual capacity: capacity - flow"""
        return self.capacity[u][v] - self.flow[u][v]

    def get_neighbors(self, u: int) -> List[int]:
        """Get all neighbors (forward and backward edges) in residual graph"""
        neighbors = set()

        # Forward edges with residual capacity
        for v in self.capacity[u]:
            if self.get_residual_capacity(u, v) > 0:
                neighbors.add(v)

        # Backward edges with flow (can push back)
        for v in self.capacity:
            if self.flow[v][u] > 0:
                neighbors.add(v)

        return list(neighbors)

def ford_fulkerson_dfs(network: FlowNetwork, source: int, sink: int
                      ) -> Tuple[float, Dict[int, Dict[int, float]]]:
    """
    Ford-Fulkerson with DFS for finding augmenting paths

    Time: O(E × |f*|) where |f*| is max flow value
    Not polynomial - can be slow if capacities are large

    Returns: (max_flow_value, flow_dict)
    """
    max_flow = 0.0

    def dfs_augment(u: int, min_capacity: float, visited: set) -> float:
        """DFS to find augmenting path, returns bottleneck capacity"""
        if u == sink:
            return min_capacity

        visited.add(u)

        for v in network.get_neighbors(u):
            if v in visited:
                continue

            residual = network.get_residual_capacity(u, v)

            if residual > 0:
                # Augment along this edge
                bottleneck = dfs_augment(v, min(min_capacity, residual), visited)

                if bottleneck > 0:
                    # Update flow
                    network.flow[u][v] += bottleneck
                    network.flow[v][u] -= bottleneck  # Reverse flow
                    return bottleneck

        return 0.0

    # Find augmenting paths until none exist
    while True:
        visited = set()
        augment = dfs_augment(source, math.inf, visited)

        if augment == 0:
            break  # No more augmenting paths

        max_flow += augment

    return max_flow, dict(network.flow)

# Example usage
network = FlowNetwork(6)
network.add_edge(0, 1, 16)
network.add_edge(0, 2, 13)
network.add_edge(1, 2, 10)
network.add_edge(1, 3, 12)
network.add_edge(2, 1, 4)
network.add_edge(2, 4, 14)
network.add_edge(3, 2, 9)
network.add_edge(3, 5, 20)
network.add_edge(4, 3, 7)
network.add_edge(4, 5, 4)

max_flow, flow = ford_fulkerson_dfs(network, source=0, sink=5)
print(f"Maximum flow: {max_flow}")  # 23.0
```

### 2. Edmonds-Karp Algorithm

**Concept**: Ford-Fulkerson using BFS to find shortest augmenting paths

**Properties**:
- **Time**: O(V × E²) - polynomial, independent of capacities
- **Space**: O(V + E)
- **Guarantees**: Finds max flow in polynomial time

```python
def edmonds_karp(network: FlowNetwork, source: int, sink: int
                ) -> Tuple[float, Dict[int, Dict[int, float]]]:
    """
    Edmonds-Karp maximum flow algorithm

    Uses BFS to find shortest augmenting path in each iteration

    Time: O(V × E²)
    """
    max_flow = 0.0

    def bfs_augment() -> Tuple[Optional[List[int]], float]:
        """
        BFS to find shortest augmenting path

        Returns: (path, bottleneck_capacity) or (None, 0)
        """
        queue = deque([source])
        parents = {source: None}

        while queue:
            u = queue.popleft()

            if u == sink:
                # Reconstruct path and find bottleneck
                path = []
                node = sink
                bottleneck = math.inf

                while node != source:
                    parent = parents[node]
                    path.append(node)

                    # Update bottleneck
                    residual = network.get_residual_capacity(parent, node)
                    bottleneck = min(bottleneck, residual)

                    node = parent

                path.append(source)
                path.reverse()

                return path, bottleneck

            # Explore neighbors in residual graph
            for v in network.get_neighbors(u):
                if v not in parents and network.get_residual_capacity(u, v) > 0:
                    parents[v] = u
                    queue.append(v)

        return None, 0.0

    # Find augmenting paths until none exist
    while True:
        path, bottleneck = bfs_augment()

        if path is None:
            break

        # Augment flow along path
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            network.flow[u][v] += bottleneck
            network.flow[v][u] -= bottleneck

        max_flow += bottleneck

    return max_flow, dict(network.flow)

# Example usage (same network as above)
network2 = FlowNetwork(6)
network2.add_edge(0, 1, 16)
network2.add_edge(0, 2, 13)
network2.add_edge(1, 2, 10)
network2.add_edge(1, 3, 12)
network2.add_edge(2, 1, 4)
network2.add_edge(2, 4, 14)
network2.add_edge(3, 2, 9)
network2.add_edge(3, 5, 20)
network2.add_edge(4, 3, 7)
network2.add_edge(4, 5, 4)

max_flow, flow = edmonds_karp(network2, source=0, sink=5)
print(f"Maximum flow (Edmonds-Karp): {max_flow}")  # 23.0
```

### 3. Minimum Cut

**Concept**: Partition vertices into sets S and T such that s ∈ S, t ∈ T, minimizing capacity of edges crossing cut

**Max-Flow Min-Cut Theorem**: Maximum flow value = minimum cut capacity

```python
def find_min_cut(network: FlowNetwork, source: int, sink: int
                ) -> Tuple[set, set, List[Tuple[int, int]], float]:
    """
    Find minimum cut after computing maximum flow

    Must run max flow algorithm first!

    Returns: (S, T, cut_edges, cut_capacity)
    where S = reachable from source in residual graph
          T = unreachable from source
          cut_edges = edges crossing from S to T
    """
    # BFS from source in residual graph
    reachable = {source}
    queue = deque([source])

    while queue:
        u = queue.popleft()

        for v in network.get_neighbors(u):
            if v not in reachable and network.get_residual_capacity(u, v) > 0:
                reachable.add(v)
                queue.append(v)

    # Partition: S = reachable, T = unreachable
    S = reachable
    T = set(range(network.num_vertices)) - S

    # Find cut edges and compute capacity
    cut_edges = []
    cut_capacity = 0.0

    for u in S:
        for v in network.capacity[u]:
            if v in T:
                cut_edges.append((u, v))
                cut_capacity += network.capacity[u][v]

    return S, T, cut_edges, cut_capacity

# Example usage
network3 = FlowNetwork(6)
network3.add_edge(0, 1, 16)
network3.add_edge(0, 2, 13)
network3.add_edge(1, 2, 10)
network3.add_edge(1, 3, 12)
network3.add_edge(2, 1, 4)
network3.add_edge(2, 4, 14)
network3.add_edge(3, 2, 9)
network3.add_edge(3, 5, 20)
network3.add_edge(4, 3, 7)
network3.add_edge(4, 5, 4)

# First compute max flow
max_flow, _ = edmonds_karp(network3, source=0, sink=5)

# Then find min cut
S, T, cut_edges, cut_capacity = find_min_cut(network3, source=0, sink=5)

print(f"Max flow: {max_flow}")              # 23.0
print(f"Min cut capacity: {cut_capacity}")  # 23.0 (equal!)
print(f"Cut edges: {cut_edges}")
print(f"S = {S}, T = {T}")
```

### 4. Bipartite Matching via Flow

**Concept**: Maximum bipartite matching reduces to maximum flow problem

**Reduction**:
1. Create source s connected to all left vertices (capacity 1)
2. Create sink t connected to all right vertices (capacity 1)
3. Direct edges from left to right (capacity 1)
4. Max flow = maximum matching size

```python
def maximum_bipartite_matching(left_vertices: set,
                               right_vertices: set,
                               edges: List[Tuple[int, int]]
                              ) -> List[Tuple[int, int]]:
    """
    Find maximum matching in bipartite graph using max flow

    Args:
        left_vertices: Vertices in left partition
        right_vertices: Vertices in right partition
        edges: Edges between left and right

    Returns: List of matched pairs
    """
    # Create flow network
    num_vertices = len(left_vertices) + len(right_vertices) + 2
    source = num_vertices - 2
    sink = num_vertices - 1

    network = FlowNetwork(num_vertices)

    # Source to left vertices (capacity 1)
    for u in left_vertices:
        network.add_edge(source, u, 1)

    # Right vertices to sink (capacity 1)
    for v in right_vertices:
        network.add_edge(v, sink, 1)

    # Left to right edges (capacity 1)
    for u, v in edges:
        network.add_edge(u, v, 1)

    # Compute max flow
    max_flow, flow_dict = edmonds_karp(network, source, sink)

    # Extract matching from flow
    matching = []
    for u in left_vertices:
        for v in right_vertices:
            if flow_dict[u][v] == 1:  # Flow of 1 means matched
                matching.append((u, v))

    return matching

# Example: Job assignment
jobs = {0, 1, 2}       # Left: workers
tasks = {3, 4, 5}      # Right: tasks
edges = [
    (0, 3), (0, 4),    # Worker 0 can do tasks 3, 4
    (1, 3), (1, 5),    # Worker 1 can do tasks 3, 5
    (2, 4), (2, 5)     # Worker 2 can do tasks 4, 5
]

matching = maximum_bipartite_matching(jobs, tasks, edges)
print(f"Maximum matching: {matching}")  # 3 workers matched
```

---

## Advanced Algorithms

### Push-Relabel Algorithm

**Concept**: Maintain preflow (local excess allowed), push flow forward, relabel vertices

**Properties**:
- **Time**: O(V² × E) with simple implementation, O(V³) with optimizations
- **Space**: O(V + E)
- **Advantage**: Faster on dense graphs, parallelizable

```python
class PushRelabel:
    """Push-relabel maximum flow algorithm"""

    def __init__(self, network: FlowNetwork, source: int, sink: int):
        self.network = network
        self.source = source
        self.sink = sink

        # Height function: source at V, others at 0
        self.height = [0] * network.num_vertices
        self.height[source] = network.num_vertices

        # Excess flow at each vertex
        self.excess = [0.0] * network.num_vertices

        # Initialize: push max flow from source
        for v in network.capacity[source]:
            capacity = network.capacity[source][v]
            network.flow[source][v] = capacity
            network.flow[v][source] = -capacity
            self.excess[v] = capacity
            self.excess[source] -= capacity

    def push(self, u: int, v: int):
        """Push flow from u to v"""
        # Push minimum of excess and residual capacity
        residual = self.network.get_residual_capacity(u, v)
        push_amount = min(self.excess[u], residual)

        self.network.flow[u][v] += push_amount
        self.network.flow[v][u] -= push_amount

        self.excess[u] -= push_amount
        self.excess[v] += push_amount

    def relabel(self, u: int):
        """Increase height of vertex u"""
        min_height = math.inf

        for v in self.network.get_neighbors(u):
            if self.network.get_residual_capacity(u, v) > 0:
                min_height = min(min_height, self.height[v])

        if min_height < math.inf:
            self.height[u] = min_height + 1

    def discharge(self, u: int):
        """Push all excess flow from u"""
        while self.excess[u] > 0:
            # Try to push to neighbors with lower height
            pushed = False

            for v in self.network.get_neighbors(u):
                if self.excess[u] == 0:
                    break

                residual = self.network.get_residual_capacity(u, v)

                if residual > 0 and self.height[u] == self.height[v] + 1:
                    self.push(u, v)
                    pushed = True

            if not pushed:
                # No valid push - relabel
                self.relabel(u)

    def max_flow(self) -> float:
        """Compute maximum flow using push-relabel"""
        # Process all vertices with excess (except source/sink)
        work_list = [v for v in range(self.network.num_vertices)
                    if v != self.source and v != self.sink
                    and self.excess[v] > 0]

        while work_list:
            u = work_list.pop()

            if self.excess[u] > 0:
                self.discharge(u)

                # Re-add neighbors if they now have excess
                for v in self.network.get_neighbors(u):
                    if v != self.source and v != self.sink and self.excess[v] > 0:
                        if v not in work_list:
                            work_list.append(v)

        # Max flow = excess at sink
        return self.excess[self.sink]
```

---

## Patterns

### Pattern 1: Algorithm Selection
```python
def choose_flow_algorithm(graph_info: dict) -> str:
    """Select optimal max flow algorithm"""
    num_vertices = graph_info["num_vertices"]
    num_edges = graph_info["num_edges"]
    max_capacity = graph_info.get("max_capacity", math.inf)

    if max_capacity < 100 and num_vertices < 1000:
        return "Ford-Fulkerson (DFS)"  # Simple, works for small capacities

    if num_edges < num_vertices ** 1.5:
        return "Edmonds-Karp"  # Good for sparse graphs

    return "Push-Relabel"  # Best for dense graphs
```

### Pattern 2: Flow Decomposition
```python
def decompose_flow(network: FlowNetwork, source: int, sink: int, flow_dict: dict
                  ) -> List[Tuple[List[int], float]]:
    """
    Decompose flow into paths and cycles

    Returns: List of (path, flow_amount) pairs
    """
    paths = []

    # Create residual graph from flow
    residual = defaultdict(lambda: defaultdict(float))

    for u in flow_dict:
        for v in flow_dict[u]:
            if flow_dict[u][v] > 0:
                residual[u][v] = flow_dict[u][v]

    # Extract paths using DFS
    while residual[source]:
        path = [source]
        current = source
        min_flow = math.inf

        # Find path from source to sink
        while current != sink:
            for next_v in residual[current]:
                if residual[current][next_v] > 0:
                    path.append(next_v)
                    min_flow = min(min_flow, residual[current][next_v])
                    current = next_v
                    break

        # Subtract flow along path
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            residual[u][v] -= min_flow

            if residual[u][v] == 0:
                del residual[u][v]

        paths.append((path, min_flow))

    return paths
```

---

## Quick Reference

### Algorithm Comparison
| Algorithm | Time | Space | Best Use Case |
|-----------|------|-------|---------------|
| Ford-Fulkerson (DFS) | O(E × \|f*\|) | O(V) | Small integer capacities |
| Edmonds-Karp (BFS) | O(V × E²) | O(V) | General purpose, polynomial |
| Push-Relabel | O(V² × E) | O(V) | Dense graphs |
| Dinic | O(V² × E) | O(V) | Better average case |

### Max-Flow Min-Cut Theorem
```
max_flow(s, t) = min_cut(S, T)

where S = vertices reachable from s in residual graph
      T = vertices not reachable from s
```

---

## Anti-Patterns

### ❌ Not Checking Undirected Graphs
```python
# WRONG: Flow algorithms for directed graphs only
undirected_graph = ...
max_flow = edmonds_karp(undirected_graph, s, t)  # Incorrect!

# CORRECT: Convert undirected to directed (both directions)
for u, v in undirected_edges:
    network.add_edge(u, v, capacity)
    network.add_edge(v, u, capacity)  # Reverse edge
```

### ❌ Forgetting Integer Capacities for Ford-Fulkerson
```python
# WRONG: Ford-Fulkerson with large/fractional capacities
network.add_edge(0, 1, 1e9)  # May take 10⁹ iterations!

# CORRECT: Use Edmonds-Karp for large capacities
max_flow = edmonds_karp(network, s, t)  # Polynomial time
```

---

## Related Skills

**Next Steps**:
- `advanced-graph-algorithms.md` → Matching, vertex cover, edge coloring
- `graph-applications.md` → Real-world network optimization

**Foundations**:
- `graph-theory-fundamentals.md` → Basic graph concepts
- `graph-traversal-algorithms.md` → BFS and DFS
- `shortest-path-algorithms.md` → Path finding algorithms

---

## Summary

Network flow algorithms solve capacity-constrained optimization problems:
- **Ford-Fulkerson**: Augmenting path method, O(E × |f*|)
- **Edmonds-Karp**: BFS-based augmenting paths, O(V × E²)
- **Min Cut**: Partition with minimum capacity, equals max flow
- **Bipartite Matching**: Reduces to max flow problem

**Key takeaways**:
1. Max-flow min-cut theorem: Maximum flow = minimum cut capacity
2. Edmonds-Karp guarantees polynomial time via BFS shortest paths
3. Bipartite matching, edge-disjoint paths reduce to max flow
4. Residual graph guides augmenting path search
5. Push-relabel often faster on dense graphs

**Next**: Move to `advanced-graph-algorithms.md` for specialized algorithms.
