---
name: Graph Theory Applications
description: Real-world applications of graph algorithms including social networks, routing, dependency resolution, recommendation systems, and network analysis
---

# Graph Theory Applications

**Last Updated**: 2025-10-25

## When to Use This Skill

**Activate when**:
- Building social network features
- Implementing routing and navigation systems
- Managing dependencies in build systems
- Designing recommendation engines
- Analyzing network topologies
- Detecting fraud or anomalies in networks
- Optimizing resource allocation

**Prerequisites**: `graph-theory-fundamentals.md`, `graph-data-structures.md`, `graph-traversal-algorithms.md`, `shortest-path-algorithms.md`

**Related Skills**: `network-flow-algorithms.md`, `minimum-spanning-tree.md`, `advanced-graph-algorithms.md`

---

## Application Domains

### 1. Social Networks

**Graph Modeling**:
- **Vertices**: Users
- **Edges**: Friendships, follows, connections
- **Weights**: Interaction strength, time, relationship type

```python
from typing import List, Set, Dict, Tuple
from collections import defaultdict, deque
import heapq

class SocialNetwork:
    """Social network graph with user relationships"""

    def __init__(self):
        # Directed graph: user_id -> [friend_ids]
        self.friends: Dict[int, Set[int]] = defaultdict(set)
        # Edge weights: interaction scores
        self.interaction_scores: Dict[Tuple[int, int], float] = {}

    def add_user(self, user_id: int):
        """Add user to network"""
        if user_id not in self.friends:
            self.friends[user_id] = set()

    def add_friendship(self, user1: int, user2: int,
                      bidirectional: bool = True):
        """Add friendship (optionally bidirectional for mutual friends)"""
        self.friends[user1].add(user2)

        if bidirectional:
            self.friends[user2].add(user1)

    def set_interaction_score(self, user1: int, user2: int, score: float):
        """Set interaction strength between users"""
        self.interaction_scores[(user1, user2)] = score

    def mutual_friends(self, user1: int, user2: int) -> Set[int]:
        """Find mutual friends between two users"""
        return self.friends[user1] & self.friends[user2]

    def friend_suggestions(self, user: int, limit: int = 10) -> List[int]:
        """
        Suggest friends based on mutual connections

        Algorithm: Friends-of-friends with mutual friend count
        """
        suggestions = defaultdict(int)

        # Count mutual friends for each friend-of-friend
        for friend in self.friends[user]:
            for fof in self.friends[friend]:
                if fof != user and fof not in self.friends[user]:
                    suggestions[fof] += 1

        # Sort by mutual friend count
        ranked = sorted(suggestions.items(),
                       key=lambda x: x[1],
                       reverse=True)

        return [user_id for user_id, _ in ranked[:limit]]

    def influence_score(self, user: int) -> float:
        """
        Calculate user influence using PageRank-like algorithm

        Influence = weighted sum of follower influences
        """
        # Simplified PageRank
        scores = {u: 1.0 for u in self.friends}
        damping = 0.85
        iterations = 10

        for _ in range(iterations):
            new_scores = {}

            for u in self.friends:
                # Base score
                score = (1 - damping)

                # Add contribution from followers
                for follower in self.friends:
                    if u in self.friends[follower]:
                        # Follower points to u
                        out_degree = len(self.friends[follower])
                        if out_degree > 0:
                            score += damping * scores[follower] / out_degree

                new_scores[u] = score

            scores = new_scores

        return scores.get(user, 0.0)

    def community_detection_louvain(self) -> Dict[int, int]:
        """
        Detect communities using Louvain method

        Returns: Dict mapping user_id to community_id
        """
        # Simplified community detection
        # Full Louvain algorithm is complex - this is basic version

        communities = {user: user for user in self.friends}
        improved = True

        while improved:
            improved = False

            for user in self.friends:
                # Count connections to each community
                community_connections = defaultdict(int)

                for neighbor in self.friends[user]:
                    community = communities[neighbor]
                    community_connections[community] += 1

                # Move to community with most connections
                if community_connections:
                    best_community = max(community_connections.items(),
                                        key=lambda x: x[1])[0]

                    if best_community != communities[user]:
                        communities[user] = best_community
                        improved = True

        return communities

# Example usage
social = SocialNetwork()

# Add users and friendships
for i in range(10):
    social.add_user(i)

social.add_friendship(0, 1)
social.add_friendship(0, 2)
social.add_friendship(1, 3)
social.add_friendship(2, 3)
social.add_friendship(3, 4)
social.add_friendship(4, 5)
social.add_friendship(5, 6)
social.add_friendship(6, 7)

suggestions = social.friend_suggestions(0, limit=3)
print(f"Friend suggestions for user 0: {suggestions}")

communities = social.community_detection_louvain()
print(f"Communities: {communities}")
```

### 2. Route Planning and Navigation

**Graph Modeling**:
- **Vertices**: Locations (intersections, cities)
- **Edges**: Roads, routes
- **Weights**: Distance, time, traffic

```python
import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class Location:
    """Geographic location"""
    id: int
    name: str
    lat: float  # Latitude
    lon: float  # Longitude

class RouteNavigationSystem:
    """Route planning using graph algorithms"""

    def __init__(self):
        self.locations: Dict[int, Location] = {}
        # Road network: (loc1, loc2) -> (distance, time)
        self.roads: Dict[Tuple[int, int], Tuple[float, float]] = {}

    def add_location(self, location: Location):
        """Add location to map"""
        self.locations[location.id] = location

    def add_road(self, loc1: int, loc2: int,
                distance_km: float, time_min: float,
                bidirectional: bool = True):
        """Add road between locations"""
        self.roads[(loc1, loc2)] = (distance_km, time_min)

        if bidirectional:
            self.roads[(loc2, loc1)] = (distance_km, time_min)

    def haversine_distance(self, loc1_id: int, loc2_id: int) -> float:
        """
        Calculate great-circle distance between two locations

        Used as heuristic for A* algorithm
        """
        loc1 = self.locations[loc1_id]
        loc2 = self.locations[loc2_id]

        # Convert to radians
        lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
        lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in km
        r = 6371

        return r * c

    def find_shortest_route(self, start: int, end: int,
                           optimize_for: str = "distance"
                          ) -> Tuple[List[int], float]:
        """
        Find shortest route using A* with geographic heuristic

        optimize_for: "distance" or "time"
        """
        # A* algorithm with haversine heuristic
        g_score = {start: 0.0}
        f_score = {start: self.haversine_distance(start, end)}
        parents = {start: None}

        pq = [(f_score[start], start)]
        closed = set()

        while pq:
            _, current = heapq.heappop(pq)

            if current == end:
                # Reconstruct path
                path = []
                node = end
                while node is not None:
                    path.append(node)
                    node = parents[node]
                return list(reversed(path)), g_score[end]

            if current in closed:
                continue

            closed.add(current)

            # Explore neighbors
            for (u, v), (dist, time) in self.roads.items():
                if u != current:
                    continue

                if v in closed:
                    continue

                # Choose cost metric
                cost = dist if optimize_for == "distance" else time

                tentative_g = g_score[current] + cost

                if v not in g_score or tentative_g < g_score[v]:
                    g_score[v] = tentative_g
                    h = self.haversine_distance(v, end)
                    f_score[v] = tentative_g + h
                    parents[v] = current

                    heapq.heappush(pq, (f_score[v], v))

        return [], math.inf  # No route found

    def alternative_routes(self, start: int, end: int,
                          num_alternatives: int = 3
                         ) -> List[Tuple[List[int], float]]:
        """
        Find multiple alternative routes using edge penalization

        Algorithm: Find shortest path, increase weights on used edges, repeat
        """
        routes = []
        penalty_factor = 1.5

        # Track edge usage penalties
        penalties: Dict[Tuple[int, int], float] = defaultdict(lambda: 1.0)

        for _ in range(num_alternatives):
            # Temporarily apply penalties to roads
            original_roads = self.roads.copy()

            for (u, v), (dist, time) in list(self.roads.items()):
                penalty = penalties[(u, v)]
                self.roads[(u, v)] = (dist * penalty, time * penalty)

            # Find route with current penalties
            route, cost = self.find_shortest_route(start, end)

            if not route:
                break

            routes.append((route, cost))

            # Increase penalties on used edges
            for i in range(len(route) - 1):
                u, v = route[i], route[i + 1]
                penalties[(u, v)] *= penalty_factor

            # Restore original roads
            self.roads = original_roads

        return routes

# Example usage
nav = RouteNavigationSystem()

# Add locations
nav.add_location(Location(0, "Downtown", 37.7749, -122.4194))
nav.add_location(Location(1, "Airport", 37.6213, -122.3790))
nav.add_location(Location(2, "Suburbs", 37.8272, -122.2913))
nav.add_location(Location(3, "Harbor", 37.7955, -122.3934))

# Add roads
nav.add_road(0, 1, distance_km=20, time_min=25)
nav.add_road(0, 2, distance_km=15, time_min=20)
nav.add_road(1, 3, distance_km=10, time_min=15)
nav.add_road(2, 3, distance_km=12, time_min=18)

route, distance = nav.find_shortest_route(0, 3, optimize_for="distance")
print(f"Shortest route: {route}, distance: {distance:.2f} km")
```

### 3. Dependency Resolution

**Graph Modeling**:
- **Vertices**: Tasks, packages, modules
- **Edges**: Dependencies
- **Properties**: DAG (no circular dependencies)

```python
class DependencyResolver:
    """Build system dependency resolution"""

    def __init__(self):
        # DAG: task -> [dependencies]
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.build_order: List[str] = []

    def add_task(self, task: str, dependencies: List[str] = None):
        """Add task with dependencies"""
        if dependencies is None:
            dependencies = []

        self.dependencies[task] = set(dependencies)

    def topological_sort(self) -> List[str]:
        """
        Compute build order using topological sort

        Returns: List of tasks in build order
        Raises: ValueError if circular dependency detected
        """
        # Kahn's algorithm
        in_degree = defaultdict(int)
        tasks = set(self.dependencies.keys())

        # Add all tasks that are dependencies
        for deps in self.dependencies.values():
            tasks.update(deps)

        # Compute in-degrees
        for task in tasks:
            in_degree[task] = 0

        for deps in self.dependencies.values():
            for dep in deps:
                in_degree[dep] += 1

        # Queue of tasks with no dependencies
        queue = deque([task for task in tasks if in_degree[task] == 0])
        build_order = []

        while queue:
            task = queue.popleft()
            build_order.append(task)

            # Process dependents
            for dependent in tasks:
                if task in self.dependencies[dependent]:
                    in_degree[dependent] -= 1

                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(build_order) != len(tasks):
            raise ValueError("Circular dependency detected")

        return build_order

    def parallel_build_levels(self) -> List[List[str]]:
        """
        Compute parallelizable build levels

        Returns: List of lists, where each inner list can be built in parallel
        """
        in_degree = defaultdict(int)
        tasks = set(self.dependencies.keys())

        for deps in self.dependencies.values():
            tasks.update(deps)

        for task in tasks:
            in_degree[task] = 0

        for deps in self.dependencies.values():
            for dep in deps:
                in_degree[dep] += 1

        levels = []
        current_level = [task for task in tasks if in_degree[task] == 0]

        while current_level:
            levels.append(current_level)
            next_level = []

            for task in current_level:
                # Reduce in-degree of dependents
                for dependent in tasks:
                    if task in self.dependencies[dependent]:
                        in_degree[dependent] -= 1

                        if in_degree[dependent] == 0:
                            next_level.append(dependent)

            current_level = next_level

        return levels

# Example: Build system
build_system = DependencyResolver()

build_system.add_task("install_deps", [])
build_system.add_task("compile_core", ["install_deps"])
build_system.add_task("compile_utils", ["install_deps"])
build_system.add_task("compile_app", ["compile_core", "compile_utils"])
build_system.add_task("run_tests", ["compile_app"])
build_system.add_task("build_docs", ["compile_app"])
build_system.add_task("package", ["run_tests", "build_docs"])

build_order = build_system.topological_sort()
print(f"Build order: {build_order}")

parallel_levels = build_system.parallel_build_levels()
print(f"Parallel build levels: {parallel_levels}")
```

### 4. Recommendation Systems

**Graph Modeling**:
- **Vertices**: Users and items
- **Edges**: User-item interactions, item similarities
- **Weights**: Ratings, similarity scores

```python
class CollaborativeFilteringGraph:
    """Recommendation system using graph-based collaborative filtering"""

    def __init__(self):
        # Bipartite graph: users and items
        self.user_items: Dict[int, Set[int]] = defaultdict(set)
        self.item_users: Dict[int, Set[int]] = defaultdict(set)
        # Ratings: (user, item) -> rating
        self.ratings: Dict[Tuple[int, int], float] = {}

    def add_rating(self, user: int, item: int, rating: float):
        """Add user rating for item"""
        self.user_items[user].add(item)
        self.item_users[item].add(user)
        self.ratings[(user, item)] = rating

    def item_similarity(self, item1: int, item2: int) -> float:
        """
        Compute similarity between items using Jaccard index

        Similarity = |users who rated both| / |users who rated either|
        """
        users1 = self.item_users[item1]
        users2 = self.item_users[item2]

        if not users1 or not users2:
            return 0.0

        intersection = len(users1 & users2)
        union = len(users1 | users2)

        return intersection / union if union > 0 else 0.0

    def recommend_items(self, user: int, limit: int = 10) -> List[int]:
        """
        Recommend items using collaborative filtering

        Algorithm: Find similar users, recommend their highly-rated items
        """
        # Find users with similar taste (Jaccard similarity)
        similar_users = []

        user_items = self.user_items[user]

        for other_user in self.user_items:
            if other_user == user:
                continue

            other_items = self.user_items[other_user]

            if not other_items:
                continue

            # Compute Jaccard similarity
            intersection = len(user_items & other_items)
            union = len(user_items | other_items)
            similarity = intersection / union if union > 0 else 0.0

            if similarity > 0:
                similar_users.append((other_user, similarity))

        # Sort by similarity
        similar_users.sort(key=lambda x: x[1], reverse=True)

        # Collect items from similar users (weighted by similarity)
        item_scores = defaultdict(float)

        for other_user, similarity in similar_users[:20]:  # Top 20 similar users
            for item in self.user_items[other_user]:
                if item not in user_items:  # Not already rated
                    rating = self.ratings.get((other_user, item), 0.0)
                    item_scores[item] += similarity * rating

        # Sort by score
        ranked_items = sorted(item_scores.items(),
                             key=lambda x: x[1],
                             reverse=True)

        return [item for item, _ in ranked_items[:limit]]

# Example usage
recommender = CollaborativeFilteringGraph()

# Add ratings (user, item, rating)
recommender.add_rating(0, 100, 5.0)  # User 0 rates item 100: 5 stars
recommender.add_rating(0, 101, 4.0)
recommender.add_rating(1, 100, 5.0)
recommender.add_rating(1, 102, 3.0)
recommender.add_rating(2, 101, 4.0)
recommender.add_rating(2, 102, 5.0)

recommendations = recommender.recommend_items(0, limit=5)
print(f"Recommendations for user 0: {recommendations}")
```

---

## Quick Reference

### Application → Algorithm Mapping
| Application | Graph Type | Key Algorithms |
|-------------|-----------|----------------|
| Social Networks | Directed, weighted | PageRank, community detection, BFS |
| Route Planning | Weighted, geographic | A*, Dijkstra, alternative paths |
| Dependency Resolution | DAG | Topological sort, parallel levels |
| Recommendations | Bipartite | Collaborative filtering, similarity |
| Network Design | Undirected, weighted | MST, Steiner tree |
| Fraud Detection | Directed, temporal | Pattern matching, anomaly detection |

---

## Related Skills

**Foundations**:
- `graph-theory-fundamentals.md` → Basic graph concepts
- `graph-data-structures.md` → Efficient representations
- `graph-traversal-algorithms.md` → BFS, DFS, topological sort
- `shortest-path-algorithms.md` → Dijkstra, A*, Floyd-Warshall
- `minimum-spanning-tree.md` → Kruskal, Prim
- `network-flow-algorithms.md` → Max flow, bipartite matching
- `advanced-graph-algorithms.md` → Coloring, matching, cliques

---

## Summary

Graph algorithms power diverse real-world applications:
- **Social Networks**: Friend suggestions, influence, communities
- **Navigation**: Shortest paths, alternative routes, real-time traffic
- **Build Systems**: Dependency resolution, parallel builds
- **Recommendations**: Collaborative filtering, item similarity
- **Network Design**: MST for infrastructure optimization

**Key takeaways**:
1. Model real problems as graphs with appropriate vertex/edge semantics
2. Choose algorithms based on graph properties (directed, weighted, DAG)
3. A* with geographic heuristics excels for route planning
4. Topological sort enables dependency resolution and parallel builds
5. Graph-based collaborative filtering finds similar users and items

**Graph theory provides fundamental algorithms for modern systems and applications.**
