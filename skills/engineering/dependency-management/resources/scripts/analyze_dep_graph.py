#!/usr/bin/env python3
"""
Dependency graph analysis and visualization tool.

Features:
- Generate dependency graphs
- Detect circular dependencies
- Identify unused dependencies
- Find duplicate dependencies
- Calculate dependency depth
- Visualize with graphviz/mermaid

Usage:
    ./analyze_dep_graph.py --path /path/to/project
    ./analyze_dep_graph.py --path . --format graphviz
    ./analyze_dep_graph.py --path . --detect-circular
    ./analyze_dep_graph.py --path . --find-duplicates
    ./analyze_dep_graph.py --path . --output graph.png
    ./analyze_dep_graph.py --path . --json --verbose
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class Ecosystem(Enum):
    """Package ecosystem types."""
    NPM = "npm"
    YARN = "yarn"
    PNPM = "pnpm"
    PIP = "pip"
    POETRY = "poetry"
    UV = "uv"
    CARGO = "cargo"
    GO = "go"
    UNKNOWN = "unknown"


@dataclass
class DependencyNode:
    """Node in dependency graph."""
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    depth: int = 0
    is_dev: bool = False
    is_duplicate: bool = False
    license: Optional[str] = None


@dataclass
class CircularDependency:
    """Circular dependency information."""
    cycle: List[str]
    depth: int


@dataclass
class GraphAnalysis:
    """Dependency graph analysis results."""
    total_dependencies: int
    direct_dependencies: int
    transitive_dependencies: int
    max_depth: int
    avg_depth: float
    circular_dependencies: List[CircularDependency]
    duplicate_dependencies: Dict[str, List[str]]
    unused_dependencies: List[str]
    heavy_dependencies: List[Tuple[str, int]]


class DependencyGraphAnalyzer:
    """Analyze and visualize dependency graphs."""

    def __init__(self, project_path: str, verbose: bool = False):
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose
        self.ecosystem = self._detect_ecosystem()
        self.graph: Dict[str, DependencyNode] = {}

    def _log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _run_command(self, cmd: List[str], check: bool = True) -> Tuple[str, str, int]:
        """Run shell command and return stdout, stderr, returncode."""
        self._log(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=check,
                timeout=300
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.stderr, e.returncode
        except subprocess.TimeoutExpired:
            return "", "Command timed out", 124
        except FileNotFoundError:
            return "", f"Command not found: {cmd[0]}", 127

    def _detect_ecosystem(self) -> Ecosystem:
        """Detect package ecosystem from project files."""
        if (self.project_path / "package-lock.json").exists():
            return Ecosystem.NPM
        if (self.project_path / "yarn.lock").exists():
            return Ecosystem.YARN
        if (self.project_path / "pnpm-lock.yaml").exists():
            return Ecosystem.PNPM
        if (self.project_path / "poetry.lock").exists():
            return Ecosystem.POETRY
        if (self.project_path / "pyproject.toml").exists():
            return Ecosystem.UV
        if (self.project_path / "requirements.txt").exists():
            return Ecosystem.PIP
        if (self.project_path / "Cargo.lock").exists():
            return Ecosystem.CARGO
        if (self.project_path / "go.sum").exists():
            return Ecosystem.GO

        return Ecosystem.UNKNOWN

    def build_graph(self) -> None:
        """Build dependency graph."""
        self._log(f"Building dependency graph for {self.ecosystem.value}")

        if self.ecosystem in [Ecosystem.NPM, Ecosystem.YARN, Ecosystem.PNPM]:
            self._build_javascript_graph()
        elif self.ecosystem in [Ecosystem.PIP, Ecosystem.POETRY, Ecosystem.UV]:
            self._build_python_graph()
        elif self.ecosystem == Ecosystem.CARGO:
            self._build_rust_graph()
        elif self.ecosystem == Ecosystem.GO:
            self._build_go_graph()
        else:
            raise ValueError(f"Unsupported ecosystem: {self.ecosystem.value}")

        self._calculate_depths()
        self._identify_dependents()

    def _build_javascript_graph(self) -> None:
        """Build dependency graph for JavaScript project."""
        stdout, stderr, code = self._run_command(["npm", "list", "--json", "--all"], check=False)

        if code not in [0, 1]:
            raise RuntimeError(f"npm list failed: {stderr}")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse npm list output: {e}")

        def traverse(node: Dict[str, Any], depth: int = 0, is_dev: bool = False) -> None:
            if "dependencies" in node:
                for name, info in node["dependencies"].items():
                    version = info.get("version", "unknown")
                    node_id = f"{name}@{version}"

                    if node_id not in self.graph:
                        self.graph[node_id] = DependencyNode(
                            name=name,
                            version=version,
                            depth=depth,
                            is_dev=is_dev
                        )

                    if "dependencies" in info:
                        for child_name, child_info in info["dependencies"].items():
                            child_version = child_info.get("version", "unknown")
                            child_id = f"{child_name}@{child_version}"
                            self.graph[node_id].dependencies.append(child_id)

                    traverse(info, depth + 1, is_dev)

        traverse(data)

        if "devDependencies" in data:
            for name, info in data["devDependencies"].items():
                version = info.get("version", "unknown")
                node_id = f"{name}@{version}"

                if node_id not in self.graph:
                    self.graph[node_id] = DependencyNode(
                        name=name,
                        version=version,
                        depth=0,
                        is_dev=True
                    )

                traverse(info, 1, True)

        self._log(f"Built graph with {len(self.graph)} nodes")

    def _build_python_graph(self) -> None:
        """Build dependency graph for Python project."""
        stdout, stderr, code = self._run_command(["pip", "show", "--verbose", "*"], check=False)

        if code == 127:
            stdout, stderr, code = self._run_command(["pip", "list", "--format=json"], check=False)
            if code == 0:
                try:
                    packages = json.loads(stdout)
                    for pkg in packages:
                        node_id = f"{pkg['name']}@{pkg['version']}"
                        self.graph[node_id] = DependencyNode(
                            name=pkg['name'],
                            version=pkg['version']
                        )
                except json.JSONDecodeError:
                    pass

        else:
            current_pkg = None
            for line in stdout.split("\n"):
                line = line.strip()
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                    current_pkg = {"name": name}
                elif line.startswith("Version:") and current_pkg:
                    version = line.split(":", 1)[1].strip()
                    current_pkg["version"] = version
                elif line.startswith("Requires:") and current_pkg:
                    requires = line.split(":", 1)[1].strip()
                    if requires and requires != "":
                        current_pkg["requires"] = [r.strip() for r in requires.split(",")]

                    node_id = f"{current_pkg['name']}@{current_pkg['version']}"
                    deps = current_pkg.get("requires", [])
                    self.graph[node_id] = DependencyNode(
                        name=current_pkg["name"],
                        version=current_pkg["version"],
                        dependencies=[f"{d}@*" for d in deps]
                    )
                    current_pkg = None

        self._log(f"Built graph with {len(self.graph)} nodes")

    def _build_rust_graph(self) -> None:
        """Build dependency graph for Rust project."""
        stdout, stderr, code = self._run_command(["cargo", "tree", "--format", "{p}"], check=False)

        if code != 0:
            raise RuntimeError(f"cargo tree failed: {stderr}")

        lines = stdout.strip().split("\n")
        stack = []

        for line in lines[1:]:
            depth = (len(line) - len(line.lstrip())) // 4
            parts = line.strip().split()

            if not parts:
                continue

            pkg_info = parts[0]
            if " v" in pkg_info:
                name, version = pkg_info.split(" v")
            else:
                name = pkg_info
                version = "unknown"

            node_id = f"{name}@{version}"

            if node_id not in self.graph:
                self.graph[node_id] = DependencyNode(
                    name=name,
                    version=version,
                    depth=depth
                )

            while len(stack) > depth:
                stack.pop()

            if stack:
                parent_id = stack[-1]
                if node_id not in self.graph[parent_id].dependencies:
                    self.graph[parent_id].dependencies.append(node_id)

            stack.append(node_id)

        self._log(f"Built graph with {len(self.graph)} nodes")

    def _build_go_graph(self) -> None:
        """Build dependency graph for Go project."""
        stdout, stderr, code = self._run_command(["go", "mod", "graph"], check=False)

        if code != 0:
            raise RuntimeError(f"go mod graph failed: {stderr}")

        for line in stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split()
            if len(parts) != 2:
                continue

            from_pkg, to_pkg = parts

            if "@" in from_pkg:
                from_name, from_version = from_pkg.rsplit("@", 1)
            else:
                from_name, from_version = from_pkg, "unknown"

            if "@" in to_pkg:
                to_name, to_version = to_pkg.rsplit("@", 1)
            else:
                to_name, to_version = to_pkg, "unknown"

            from_id = f"{from_name}@{from_version}"
            to_id = f"{to_name}@{to_version}"

            if from_id not in self.graph:
                self.graph[from_id] = DependencyNode(
                    name=from_name,
                    version=from_version
                )

            if to_id not in self.graph:
                self.graph[to_id] = DependencyNode(
                    name=to_name,
                    version=to_version
                )

            if to_id not in self.graph[from_id].dependencies:
                self.graph[from_id].dependencies.append(to_id)

        self._log(f"Built graph with {len(self.graph)} nodes")

    def _calculate_depths(self) -> None:
        """Calculate depth of each node using BFS."""
        if not self.graph:
            return

        depths = {node_id: float('inf') for node_id in self.graph}

        roots = [node_id for node_id, node in self.graph.items() if node.depth == 0]

        for root in roots:
            queue = deque([(root, 0)])
            visited = set()

            while queue:
                node_id, depth = queue.popleft()

                if node_id in visited:
                    continue
                visited.add(node_id)

                depths[node_id] = min(depths[node_id], depth)
                self.graph[node_id].depth = depths[node_id]

                for dep_id in self.graph[node_id].dependencies:
                    if dep_id in self.graph:
                        queue.append((dep_id, depth + 1))

    def _identify_dependents(self) -> None:
        """Identify dependents (reverse dependencies) for each node."""
        for node_id, node in self.graph.items():
            for dep_id in node.dependencies:
                if dep_id in self.graph:
                    if node_id not in self.graph[dep_id].dependents:
                        self.graph[dep_id].dependents.append(node_id)

    def detect_circular_dependencies(self) -> List[CircularDependency]:
        """Detect circular dependencies using DFS."""
        circular = []
        visited = set()
        rec_stack = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.append(node_id)

            for dep_id in self.graph.get(node_id, DependencyNode("", "")).dependencies:
                if dep_id not in self.graph:
                    continue

                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    cycle_start = rec_stack.index(dep_id)
                    cycle = rec_stack[cycle_start:] + [dep_id]
                    circular.append(CircularDependency(
                        cycle=cycle,
                        depth=len(cycle)
                    ))
                    return True

            rec_stack.pop()
            return False

        for node_id in self.graph:
            if node_id not in visited:
                rec_stack = []
                dfs(node_id)

        self._log(f"Found {len(circular)} circular dependencies")
        return circular

    def find_duplicate_dependencies(self) -> Dict[str, List[str]]:
        """Find duplicate dependencies (same package, different versions)."""
        by_name = defaultdict(list)

        for node_id, node in self.graph.items():
            by_name[node.name].append(node_id)

        duplicates = {
            name: versions
            for name, versions in by_name.items()
            if len(versions) > 1
        }

        for name, versions in duplicates.items():
            for version in versions:
                if version in self.graph:
                    self.graph[version].is_duplicate = True

        self._log(f"Found {len(duplicates)} duplicate dependencies")
        return dict(duplicates)

    def find_unused_dependencies(self) -> List[str]:
        """Find potentially unused dependencies."""
        unused = []

        direct_deps = [
            node_id for node_id, node in self.graph.items()
            if node.depth == 0 and not node.is_dev
        ]

        for node_id in direct_deps:
            if not self.graph[node_id].dependencies:
                if not self._is_used_in_source(self.graph[node_id].name):
                    unused.append(node_id)

        self._log(f"Found {len(unused)} potentially unused dependencies")
        return unused

    def _is_used_in_source(self, package_name: str) -> bool:
        """Check if package is imported/used in source code."""
        source_dirs = ["src", "lib", "app", "pages", "components"]
        extensions = [".js", ".jsx", ".ts", ".tsx", ".py", ".rs", ".go"]

        for src_dir in source_dirs:
            src_path = self.project_path / src_dir
            if not src_path.exists():
                continue

            for ext in extensions:
                pattern = f"*{ext}"
                for file_path in src_path.rglob(pattern):
                    try:
                        content = file_path.read_text()
                        if package_name in content:
                            return True
                    except (UnicodeDecodeError, PermissionError):
                        continue

        return False

    def find_heavy_dependencies(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """Find dependencies with most transitive dependencies."""
        dep_counts = []

        for node_id, node in self.graph.items():
            count = self._count_transitive_deps(node_id)
            dep_counts.append((node_id, count))

        dep_counts.sort(key=lambda x: x[1], reverse=True)

        self._log(f"Top {top_n} heaviest dependencies identified")
        return dep_counts[:top_n]

    def _count_transitive_deps(self, node_id: str) -> int:
        """Count transitive dependencies of a node."""
        visited = set()
        queue = deque([node_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for dep_id in self.graph.get(current, DependencyNode("", "")).dependencies:
                if dep_id in self.graph:
                    queue.append(dep_id)

        return len(visited) - 1

    def analyze(self) -> GraphAnalysis:
        """Perform comprehensive graph analysis."""
        if not self.graph:
            self.build_graph()

        total = len(self.graph)
        direct = sum(1 for node in self.graph.values() if node.depth == 0)
        transitive = total - direct

        depths = [node.depth for node in self.graph.values()]
        max_depth = max(depths) if depths else 0
        avg_depth = sum(depths) / len(depths) if depths else 0

        circular = self.detect_circular_dependencies()
        duplicates = self.find_duplicate_dependencies()
        unused = self.find_unused_dependencies()
        heavy = self.find_heavy_dependencies()

        return GraphAnalysis(
            total_dependencies=total,
            direct_dependencies=direct,
            transitive_dependencies=transitive,
            max_depth=max_depth,
            avg_depth=avg_depth,
            circular_dependencies=circular,
            duplicate_dependencies=duplicates,
            unused_dependencies=unused,
            heavy_dependencies=heavy
        )

    def generate_graphviz(self, max_depth: Optional[int] = None) -> str:
        """Generate Graphviz DOT format."""
        lines = ["digraph dependencies {"]
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=rounded];')
        lines.append('')

        for node_id, node in self.graph.items():
            if max_depth is not None and node.depth > max_depth:
                continue

            label = f"{node.name}\\n{node.version}"
            color = "red" if node.is_duplicate else ("lightblue" if node.is_dev else "lightgreen")

            lines.append(f'  "{node_id}" [label="{label}", fillcolor="{color}", style="filled,rounded"];')

        lines.append('')

        for node_id, node in self.graph.items():
            if max_depth is not None and node.depth > max_depth:
                continue

            for dep_id in node.dependencies:
                if dep_id in self.graph:
                    if max_depth is None or self.graph[dep_id].depth <= max_depth:
                        lines.append(f'  "{node_id}" -> "{dep_id}";')

        lines.append('}')

        return "\n".join(lines)

    def generate_mermaid(self, max_depth: Optional[int] = None) -> str:
        """Generate Mermaid diagram format."""
        lines = ["graph TD"]

        node_map = {}
        counter = 0

        for node_id, node in self.graph.items():
            if max_depth is not None and node.depth > max_depth:
                continue

            node_key = f"N{counter}"
            node_map[node_id] = node_key
            counter += 1

            label = f"{node.name}@{node.version}"
            if node.is_duplicate:
                lines.append(f'  {node_key}["{label}"]:::duplicate')
            elif node.is_dev:
                lines.append(f'  {node_key}["{label}"]:::dev')
            else:
                lines.append(f'  {node_key}["{label}"]')

        for node_id, node in self.graph.items():
            if max_depth is not None and node.depth > max_depth:
                continue

            if node_id not in node_map:
                continue

            for dep_id in node.dependencies:
                if dep_id in node_map:
                    lines.append(f'  {node_map[node_id]} --> {node_map[dep_id]}')

        lines.append('')
        lines.append('  classDef duplicate fill:#f99,stroke:#f00')
        lines.append('  classDef dev fill:#9cf,stroke:#00f')

        return "\n".join(lines)


from enum import Enum


def format_analysis_text(analysis: GraphAnalysis) -> str:
    """Format analysis results as human-readable text."""
    lines = []

    lines.append("=" * 70)
    lines.append("DEPENDENCY GRAPH ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total Dependencies: {analysis.total_dependencies}")
    lines.append(f"Direct Dependencies: {analysis.direct_dependencies}")
    lines.append(f"Transitive Dependencies: {analysis.transitive_dependencies}")
    lines.append(f"Max Depth: {analysis.max_depth}")
    lines.append(f"Average Depth: {analysis.avg_depth:.2f}")
    lines.append("")

    if analysis.circular_dependencies:
        lines.append("CIRCULAR DEPENDENCIES")
        lines.append("-" * 70)
        for circ in analysis.circular_dependencies:
            cycle_str = " -> ".join(circ.cycle)
            lines.append(f"  {cycle_str}")
        lines.append("")

    if analysis.duplicate_dependencies:
        lines.append("DUPLICATE DEPENDENCIES")
        lines.append("-" * 70)
        for name, versions in analysis.duplicate_dependencies.items():
            lines.append(f"  {name}:")
            for version in versions:
                lines.append(f"    - {version}")
        lines.append("")

    if analysis.unused_dependencies:
        lines.append("POTENTIALLY UNUSED DEPENDENCIES")
        lines.append("-" * 70)
        for dep in analysis.unused_dependencies:
            lines.append(f"  - {dep}")
        lines.append("")

    if analysis.heavy_dependencies:
        lines.append("HEAVIEST DEPENDENCIES")
        lines.append("-" * 70)
        for dep, count in analysis.heavy_dependencies:
            lines.append(f"  {dep}: {count} transitive dependencies")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dependency graph analysis and visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path /path/to/project
  %(prog)s --path . --format graphviz --output graph.dot
  %(prog)s --path . --format mermaid --output graph.mmd
  %(prog)s --path . --detect-circular
  %(prog)s --path . --find-duplicates
  %(prog)s --path . --json --verbose
        """
    )

    parser.add_argument(
        "--path",
        default=".",
        help="Path to project directory (default: current directory)"
    )
    parser.add_argument(
        "--format",
        choices=["graphviz", "mermaid"],
        help="Visualization format"
    )
    parser.add_argument(
        "--output",
        help="Output file path"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum depth to visualize"
    )
    parser.add_argument(
        "--detect-circular",
        action="store_true",
        help="Detect circular dependencies"
    )
    parser.add_argument(
        "--find-duplicates",
        action="store_true",
        help="Find duplicate dependencies"
    )
    parser.add_argument(
        "--find-unused",
        action="store_true",
        help="Find unused dependencies"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    try:
        analyzer = DependencyGraphAnalyzer(args.path, verbose=args.verbose)
        analyzer.build_graph()

        if args.format:
            if args.format == "graphviz":
                output = analyzer.generate_graphviz(args.max_depth)
            else:
                output = analyzer.generate_mermaid(args.max_depth)

            if args.output:
                Path(args.output).write_text(output)
                print(f"Wrote {args.format} graph to {args.output}")
            else:
                print(output)

            return

        analysis = analyzer.analyze()

        if args.json:
            output = {
                "total_dependencies": analysis.total_dependencies,
                "direct_dependencies": analysis.direct_dependencies,
                "transitive_dependencies": analysis.transitive_dependencies,
                "max_depth": analysis.max_depth,
                "avg_depth": analysis.avg_depth,
                "circular_dependencies": [
                    {"cycle": c.cycle, "depth": c.depth}
                    for c in analysis.circular_dependencies
                ],
                "duplicate_dependencies": analysis.duplicate_dependencies,
                "unused_dependencies": analysis.unused_dependencies,
                "heavy_dependencies": [
                    {"name": name, "count": count}
                    for name, count in analysis.heavy_dependencies
                ]
            }
            print(json.dumps(output, indent=2))
        else:
            print(format_analysis_text(analysis))

        has_issues = (
            len(analysis.circular_dependencies) > 0 or
            len(analysis.duplicate_dependencies) > 0 or
            len(analysis.unused_dependencies) > 0
        )
        sys.exit(1 if has_issues else 0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
