---
name: Graph Traversal Algorithms
description: Breadth-first search, depth-first search, topological sort, strongly connected components, and traversal-based graph analysis
---

# Graph Traversal Algorithms

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Finding paths between vertices
- Exploring graph structure systematically
- Detecting cycles in directed/undirected graphs
- Computing connected components
- Performing topological sort on DAGs
- Finding strongly connected components
- Analyzing reachability and connectivity

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`

**Related Skills**: `shortest-path-algorithms.md`, `minimum-spanning-tree.md`, `network-flow-algorithms.md`

---

## Core Algorithms

### 1. Breadth-First Search (BFS)

**Concept**: Explore graph level by level from source vertex

**Properties**:
- **Time**: O(V + E) with adjacency list
- **Space**: O(V) for queue and visited set
- **Finds**: Shortest paths in unweighted graphs
- **Order**: Visits vertices by distance from source

```python
from collections import deque
from typing import List, Set, Dict, Optional

def bfs(graph: 'AdjacencyList', start: int) -> Dict[int, int]:
    """
    Breadth-first search from start vertex

    Returns:
        distances: dict mapping vertex to distance from start
    """
    visited = {start}
    distances = {start: 0}
    queue = deque([start])

    while queue:
        u = queue.popleft()

        for v in graph.neighbors(u):
            if v not in visited:
                visited.add(v)
                distances[v] = distances[u] + 1
                queue.append(v)

    return distances

def bfs_with_parents(graph: 'AdjacencyList', start: int
                    ) -> tuple[Dict[int, int], Dict[int, Optional[int]]]:
    """
    BFS with parent tracking for path reconstruction

    Returns:
        (distances, parents) where parents[v] is parent of v in BFS tree
    """
    visited = {start}
    distances = {start: 0}
    parents = {start: None}
    queue = deque([start])

    while queue:
        u = queue.popleft()

        for v in graph.neighbors(u):
            if v not in visited:
                visited.add(v)
                distances[v] = distances[u] + 1
                parents[v] = u
                queue.append(v)

    return distances, parents

def reconstruct_path(parents: Dict[int, Optional[int]],
                    target: int) -> Optional[List[int]]:
    """Reconstruct path from source to target using parent pointers"""
    if target not in parents:
        return None  # Target not reachable

    path = []
    current = target

    while current is not None:
        path.append(current)
        current = parents[current]

    return list(reversed(path))

# Example usage
from graph_data_structures import AdjacencyList

graph = AdjacencyList(6, directed=False)
graph.add_edge(0, 1)
graph.add_edge(0, 2)
graph.add_edge(1, 3)
graph.add_edge(2, 3)
graph.add_edge(3, 4)
graph.add_edge(4, 5)

distances, parents = bfs_with_parents(graph, start=0)
path_to_5 = reconstruct_path(parents, 5)
print(f"Shortest path 0→5: {path_to_5}")  # [0, 1, 3, 4, 5]
print(f"Distance: {distances[5]}")         # 4
```

**BFS Applications**:
```python
class BFSApplications:
    """Common BFS-based algorithms"""

    @staticmethod
    def shortest_path_unweighted(graph: 'AdjacencyList',
                                 start: int, end: int) -> Optional[List[int]]:
        """Find shortest path in unweighted graph"""
        distances, parents = bfs_with_parents(graph, start)
        return reconstruct_path(parents, end)

    @staticmethod
    def is_bipartite(graph: 'AdjacencyList') -> tuple[bool, Optional[Dict]]:
        """
        Check if graph is bipartite using 2-coloring

        Returns: (is_bipartite, coloring) where coloring[v] ∈ {0, 1}
        """
        if graph.num_vertices == 0:
            return True, {}

        coloring = {}

        for start in range(graph.num_vertices):
            if start in coloring:
                continue  # Already processed this component

            coloring[start] = 0
            queue = deque([start])

            while queue:
                u = queue.popleft()

                for v in graph.neighbors(u):
                    if v not in coloring:
                        # Color with opposite color
                        coloring[v] = 1 - coloring[u]
                        queue.append(v)
                    elif coloring[v] == coloring[u]:
                        # Odd cycle detected - not bipartite
                        return False, None

        return True, coloring

    @staticmethod
    def connected_components(graph: 'AdjacencyList') -> List[Set[int]]:
        """Find all connected components using BFS"""
        components = []
        visited = set()

        for start in range(graph.num_vertices):
            if start in visited:
                continue

            # BFS to find component
            component = {start}
            queue = deque([start])
            visited.add(start)

            while queue:
                u = queue.popleft()

                for v in graph.neighbors(u):
                    if v not in visited:
                        visited.add(v)
                        component.add(v)
                        queue.append(v)

            components.append(component)

        return components
```

### 2. Depth-First Search (DFS)

**Concept**: Explore graph by going as deep as possible before backtracking

**Properties**:
- **Time**: O(V + E) with adjacency list
- **Space**: O(V) for recursion stack/visited set
- **Finds**: Cycles, topological ordering, components
- **Order**: Visits vertices depth-first

```python
from typing import Callable

def dfs_recursive(graph: 'AdjacencyList', start: int,
                 visited: Optional[Set[int]] = None,
                 preorder: Optional[List[int]] = None,
                 postorder: Optional[List[int]] = None):
    """
    Recursive depth-first search

    Args:
        preorder: List to record vertices in preorder (optional)
        postorder: List to record vertices in postorder (optional)
    """
    if visited is None:
        visited = set()
    if preorder is None:
        preorder = []
    if postorder is None:
        postorder = []

    visited.add(start)
    preorder.append(start)  # Record on entry

    for neighbor in graph.neighbors(start):
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited, preorder, postorder)

    postorder.append(start)  # Record on exit

def dfs_iterative(graph: 'AdjacencyList', start: int) -> List[int]:
    """
    Iterative DFS using explicit stack

    Returns: Vertices in DFS order
    """
    visited = {start}
    stack = [start]
    order = []

    while stack:
        u = stack.pop()
        order.append(u)

        # Add neighbors in reverse order to match recursive DFS
        for v in reversed(graph.neighbors(u)):
            if v not in visited:
                visited.add(v)
                stack.append(v)

    return order

def dfs_with_timestamps(graph: 'AdjacencyList'
                       ) -> Dict[int, tuple[int, int]]:
    """
    DFS with discovery/finish timestamps

    Returns: dict mapping vertex to (discovery_time, finish_time)
    """
    timestamps = {}
    visited = set()
    time = [0]  # Mutable counter

    def dfs_visit(u: int):
        time[0] += 1
        discovery = time[0]
        visited.add(u)

        for v in graph.neighbors(u):
            if v not in visited:
                dfs_visit(v)

        time[0] += 1
        finish = time[0]
        timestamps[u] = (discovery, finish)

    for u in range(graph.num_vertices):
        if u not in visited:
            dfs_visit(u)

    return timestamps
```

**DFS Applications**:
```python
class DFSApplications:
    """Common DFS-based algorithms"""

    @staticmethod
    def has_cycle_undirected(graph: 'AdjacencyList') -> bool:
        """
        Detect cycle in undirected graph

        Approach: If we visit a vertex that's already visited
        and it's not our parent, there's a cycle
        """
        visited = set()

        def dfs(u: int, parent: Optional[int]) -> bool:
            visited.add(u)

            for v in graph.neighbors(u):
                if v not in visited:
                    if dfs(v, u):
                        return True
                elif v != parent:
                    # Back edge to non-parent = cycle
                    return True

            return False

        for start in range(graph.num_vertices):
            if start not in visited:
                if dfs(start, None):
                    return True

        return False

    @staticmethod
    def has_cycle_directed(graph: 'AdjacencyList') -> bool:
        """
        Detect cycle in directed graph using color marking

        Colors: WHITE (unvisited), GRAY (in progress), BLACK (finished)
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {v: WHITE for v in range(graph.num_vertices)}

        def dfs(u: int) -> bool:
            color[u] = GRAY

            for v in graph.neighbors(u):
                if color[v] == GRAY:
                    # Back edge to ancestor = cycle
                    return True
                if color[v] == WHITE:
                    if dfs(v):
                        return True

            color[u] = BLACK
            return False

        for start in range(graph.num_vertices):
            if color[start] == WHITE:
                if dfs(start):
                    return True

        return False

    @staticmethod
    def find_bridges(graph: 'AdjacencyList') -> List[tuple[int, int]]:
        """
        Find bridges (edges whose removal disconnects graph)

        Uses: Tarjan's algorithm with discovery times and low values
        """
        if graph.directed:
            raise ValueError("Bridges only defined for undirected graphs")

        discovery = {}
        low = {}  # Lowest discovery time reachable
        parent = {}
        bridges = []
        time = [0]

        def dfs(u: int):
            time[0] += 1
            discovery[u] = low[u] = time[0]

            for v in graph.neighbors(u):
                if v not in discovery:
                    parent[v] = u
                    dfs(v)

                    # Update low value
                    low[u] = min(low[u], low[v])

                    # Check if u-v is a bridge
                    if low[v] > discovery[u]:
                        bridges.append((u, v))

                elif v != parent.get(u):
                    # Back edge (not to parent)
                    low[u] = min(low[u], discovery[v])

        for start in range(graph.num_vertices):
            if start not in discovery:
                parent[start] = None
                dfs(start)

        return bridges

    @staticmethod
    def find_articulation_points(graph: 'AdjacencyList') -> Set[int]:
        """
        Find articulation points (vertices whose removal disconnects graph)

        Uses: Similar to bridges algorithm
        """
        if graph.directed:
            raise ValueError("Articulation points for undirected graphs")

        discovery = {}
        low = {}
        parent = {}
        articulation_points = set()
        time = [0]

        def dfs(u: int):
            children = 0
            time[0] += 1
            discovery[u] = low[u] = time[0]

            for v in graph.neighbors(u):
                if v not in discovery:
                    children += 1
                    parent[v] = u
                    dfs(v)

                    low[u] = min(low[u], low[v])

                    # Check if u is articulation point
                    if parent[u] is None and children > 1:
                        # Root with 2+ children
                        articulation_points.add(u)
                    elif parent[u] is not None and low[v] >= discovery[u]:
                        # Non-root with child not reaching above
                        articulation_points.add(u)

                elif v != parent.get(u):
                    low[u] = min(low[u], discovery[v])

        for start in range(graph.num_vertices):
            if start not in discovery:
                parent[start] = None
                dfs(start)

        return articulation_points
```

### 3. Topological Sort

**Concept**: Linear ordering of vertices such that for every edge u→v, u appears before v

**Precondition**: Graph must be a DAG (Directed Acyclic Graph)

```python
def topological_sort_dfs(graph: 'AdjacencyList') -> Optional[List[int]]:
    """
    Topological sort using DFS postorder

    Returns: Topologically sorted vertices, or None if cycle exists
    """
    if not graph.directed:
        raise ValueError("Topological sort only for directed graphs")

    # First check for cycles
    if DFSApplications.has_cycle_directed(graph):
        return None  # No topological ordering exists

    visited = set()
    postorder = []

    def dfs(u: int):
        visited.add(u)

        for v in graph.neighbors(u):
            if v not in visited:
                dfs(v)

        postorder.append(u)  # Add after visiting all descendants

    for start in range(graph.num_vertices):
        if start not in visited:
            dfs(start)

    # Reverse postorder = topological order
    return list(reversed(postorder))

def topological_sort_kahn(graph: 'AdjacencyList') -> Optional[List[int]]:
    """
    Topological sort using Kahn's algorithm (in-degree based)

    Repeatedly remove vertices with in-degree 0
    """
    if not graph.directed:
        raise ValueError("Topological sort only for directed graphs")

    # Compute in-degrees
    in_degree = {v: 0 for v in range(graph.num_vertices)}
    for u in range(graph.num_vertices):
        for v in graph.neighbors(u):
            in_degree[v] += 1

    # Queue of vertices with in-degree 0
    queue = deque([v for v in range(graph.num_vertices)
                   if in_degree[v] == 0])
    result = []

    while queue:
        u = queue.popleft()
        result.append(u)

        # Remove u from graph (decrease in-degrees)
        for v in graph.neighbors(u):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(result) != graph.num_vertices:
        return None  # Cycle exists

    return result
```

### 4. Strongly Connected Components (SCCs)

**Concept**: Maximal subgraphs where every vertex reaches every other vertex

**Algorithm**: Kosaraju's algorithm using two DFS passes

```python
def strongly_connected_components(graph: 'AdjacencyList') -> List[Set[int]]:
    """
    Find strongly connected components using Kosaraju's algorithm

    Steps:
    1. DFS on original graph to get finish times
    2. Transpose graph
    3. DFS on transpose in decreasing finish time order
    """
    if not graph.directed:
        raise ValueError("SCCs only for directed graphs")

    # Step 1: First DFS to get finish times
    visited = set()
    finish_order = []

    def dfs1(u: int):
        visited.add(u)
        for v in graph.neighbors(u):
            if v not in visited:
                dfs1(v)
        finish_order.append(u)

    for u in range(graph.num_vertices):
        if u not in visited:
            dfs1(u)

    # Step 2: Transpose graph
    transpose = AdjacencyList(graph.num_vertices, directed=True)
    for u in range(graph.num_vertices):
        for v in graph.neighbors(u):
            transpose.add_edge(v, u)  # Reverse edge

    # Step 3: Second DFS on transpose in reverse finish order
    visited = set()
    sccs = []

    def dfs2(u: int, component: Set[int]):
        visited.add(u)
        component.add(u)
        for v in transpose.neighbors(u):
            if v not in visited:
                dfs2(v, component)

    for u in reversed(finish_order):
        if u not in visited:
            component = set()
            dfs2(u, component)
            sccs.append(component)

    return sccs
```

---

## Patterns

### Pattern 1: Traversal with Custom Actions
```python
def dfs_with_actions(graph: 'AdjacencyList',
                     start: int,
                     pre_action: Callable[[int], None],
                     post_action: Callable[[int], None]):
    """Generic DFS with custom pre/post actions"""
    visited = set()

    def dfs(u: int):
        visited.add(u)
        pre_action(u)  # Execute on entry

        for v in graph.neighbors(u):
            if v not in visited:
                dfs(v)

        post_action(u)  # Execute on exit

    dfs(start)

# Example: Print entering/leaving messages
dfs_with_actions(
    graph, start=0,
    pre_action=lambda u: print(f"Entering {u}"),
    post_action=lambda u: print(f"Leaving {u}")
)
```

### Pattern 2: Early Termination
```python
def dfs_find(graph: 'AdjacencyList', start: int,
             predicate: Callable[[int], bool]) -> Optional[int]:
    """DFS that terminates early when predicate is satisfied"""
    visited = set()

    def dfs(u: int) -> Optional[int]:
        visited.add(u)

        if predicate(u):
            return u

        for v in graph.neighbors(u):
            if v not in visited:
                result = dfs(v)
                if result is not None:
                    return result

        return None

    return dfs(start)

# Example: Find vertex with degree > 5
target = dfs_find(graph, start=0, predicate=lambda v: graph.degree(v) > 5)
```

---

## Quick Reference

### Algorithm Comparison
| Algorithm | Time | Space | Use Case |
|-----------|------|-------|----------|
| BFS | O(V+E) | O(V) | Shortest paths (unweighted) |
| DFS | O(V+E) | O(V) | Cycles, topological sort, SCCs |
| Topological (DFS) | O(V+E) | O(V) | DAG ordering |
| Topological (Kahn) | O(V+E) | O(V) | DAG ordering, cycle detection |
| Kosaraju SCC | O(V+E) | O(V) | Strongly connected components |
| Tarjan Bridges | O(V+E) | O(V) | Critical edges |

### When to Use Which
- **BFS**: Level-order traversal, shortest paths, bipartiteness
- **DFS**: Cycle detection, topological sort, components, backtracking
- **Topological Sort**: Task scheduling, dependency resolution
- **SCCs**: Web crawling, social network analysis

---

## Anti-Patterns

### ❌ Not Handling Disconnected Graphs
```python
# WRONG: Only traverses from vertex 0
visited = bfs(graph, start=0)
# Misses disconnected components

# CORRECT: Traverse all components
all_visited = set()
for start in range(graph.num_vertices):
    if start not in all_visited:
        visited = bfs(graph, start)
        all_visited.update(visited)
```

### ❌ Modifying Graph During Traversal
```python
# WRONG: Remove edges during DFS
def dfs(u):
    for v in graph.neighbors(u):
        graph.remove_edge(u, v)  # Modifies during iteration!
        dfs(v)

# CORRECT: Collect then modify
def dfs(u, to_remove):
    for v in graph.neighbors(u):
        to_remove.append((u, v))
        dfs(v, to_remove)
```

### ❌ Assuming DAG Without Checking
```python
# WRONG: Topological sort without cycle check
result = topological_sort_dfs(graph)
process(result)  # Crashes if result is None

# CORRECT: Check for cycles first
result = topological_sort_dfs(graph)
if result is None:
    print("Graph has cycle - no topological ordering")
else:
    process(result)
```

---

## Related Skills

**Next Steps**:
- `shortest-path-algorithms.md` → Weighted shortest paths (Dijkstra, Bellman-Ford)
- `minimum-spanning-tree.md` → MST algorithms (Kruskal, Prim)
- `network-flow-algorithms.md` → Max flow, min cut

**Foundations**:
- `graph-theory-fundamentals.md` → Graph concepts
- `graph-data-structures.md` → Representation choices

---

## Summary

Graph traversal algorithms provide systematic exploration of graph structure:
- **BFS**: Level-by-level, finds shortest paths in unweighted graphs
- **DFS**: Depth-first, detects cycles, computes topological order
- **Topological Sort**: Orders DAG vertices respecting dependencies
- **SCCs**: Finds maximal mutually reachable subgraphs in directed graphs

**Key takeaways**:
1. BFS and DFS both run in O(V+E) time with adjacency lists
2. BFS uses queue (FIFO), DFS uses stack/recursion (LIFO)
3. DFS postorder enables topological sort and SCC algorithms
4. Always handle disconnected graphs by iterating over all vertices
5. Check for cycles before topological sort on directed graphs

**Next**: Move to `shortest-path-algorithms.md` for weighted path algorithms.
