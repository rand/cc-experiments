#!/usr/bin/env python3
"""
Discover holes in the codebase and generate REFACTOR_IR.md

This script analyzes the current codebase to identify:
- Current state unknowns
- Refactoring needs
- Constraints
- Dependencies between holes
"""

import argparse
import ast
import json
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
import subprocess


@dataclass
class Hole:
    id: str
    type: str
    question: str
    dependencies: List[str]
    status: str = "pending"
    
    
class CodebaseAnalyzer:
    def __init__(self, root_path: Path):
        self.root = root_path
        self.python_files = list(root_path.glob("**/*.py"))
        self.holes: Dict[str, Hole] = {}
        
    def analyze(self):
        """Run all analyses"""
        print("🔍 Analyzing codebase...")
        
        self.analyze_structure()
        self.analyze_dependencies()
        self.analyze_complexity()
        self.analyze_duplication()
        self.analyze_tests()
        
        return self.holes
    
    def analyze_structure(self):
        """Analyze code structure and architecture"""
        print("  📁 Analyzing structure...")
        
        # Check if there's obvious architecture
        dirs = [d for d in self.root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        if len(dirs) < 3:
            self.holes["H0_architecture"] = Hole(
                id="H0_architecture",
                type="current_state",
                question="What is the current architecture? How are modules organized?",
                dependencies=[]
            )
        
        # Check for module boundaries
        self.holes["R1_target_architecture"] = Hole(
            id="R1_target_architecture",
            type="architecture",
            question="What should the ideal architecture be?",
            dependencies=["H0_architecture"] if "H0_architecture" in self.holes else []
        )
        
        self.holes["R2_module_boundaries"] = Hole(
            id="R2_module_boundaries",
            type="architecture",
            question="How should modules be organized?",
            dependencies=["R1_target_architecture"]
        )
    
    def analyze_dependencies(self):
        """Analyze dependency graph"""
        print("  🔗 Analyzing dependencies...")
        
        self.holes["H0_dependency_graph"] = Hole(
            id="H0_dependency_graph",
            type="current_state",
            question="What is the current dependency graph? Are there cycles?",
            dependencies=[]
        )
    
    def analyze_complexity(self):
        """Analyze code complexity"""
        print("  📊 Analyzing complexity...")
        
        try:
            # Try to use radon for complexity analysis
            result = subprocess.run(
                ["radon", "cc", str(self.root), "-a"],
                capture_output=True,
                text=True
            )
            
            if "radon: command not found" not in result.stderr:
                # Parse complexity - if high, flag for refactoring
                if "Average complexity: A" not in result.stdout:
                    self.holes["R4_consolidation_targets"] = Hole(
                        id="R4_consolidation_targets",
                        type="implementation",
                        question="What code has high complexity and should be refactored?",
                        dependencies=["H0_architecture", "R2_module_boundaries"]
                    )
        except FileNotFoundError:
            pass
    
    def analyze_duplication(self):
        """Detect code duplication"""
        print("  🔁 Analyzing duplication...")
        
        # Simple heuristic: look for similar function names
        function_names = []
        for py_file in self.python_files:
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        function_names.append(node.name)
            except:
                continue
        
        # Look for patterns like parse_v1, parse_v2, etc.
        base_names = set()
        for name in function_names:
            if name.endswith(('_v1', '_v2', '_v3', '_old', '_new')):
                base_names.add(name.rsplit('_', 1)[0])
        
        if base_names:
            self.holes["R4_consolidation_targets"] = Hole(
                id="R4_consolidation_targets",
                type="implementation",
                question=f"Found potential duplicates: {base_names}. What should be consolidated?",
                dependencies=["R2_module_boundaries"]
            )
    
    def analyze_tests(self):
        """Analyze test coverage"""
        print("  🧪 Analyzing tests...")
        
        test_files = list(self.root.glob("**/test_*.py")) + list(self.root.glob("**/*_test.py"))
        
        self.holes["H0_test_coverage"] = Hole(
            id="H0_test_coverage",
            type="current_state",
            question=f"Current test coverage? Found {len(test_files)} test files.",
            dependencies=[]
        )
        
        self.holes["R7_test_strategy"] = Hole(
            id="R7_test_strategy",
            type="quality",
            question="What testing strategy validates equivalence after refactoring?",
            dependencies=["H0_test_coverage"]
        )


def generate_refactor_ir(holes: Dict[str, Hole], output_path: Path):
    """Generate REFACTOR_IR.md"""
    print("\n📝 Generating REFACTOR_IR.md...")
    
    content = f"""# Refactor Intermediate Representation (IR)

Generated: {subprocess.check_output(['date']).decode().strip()}

## Executive Summary

This document catalogs all typed holes in the refactoring process. Each hole represents
an unknown that must be resolved to complete the refactoring.

**Total Holes**: {len(holes)}
**Pending**: {sum(1 for h in holes.values() if h.status == 'pending')}
**In Progress**: {sum(1 for h in holes.values() if h.status == 'in_progress')}
**Resolved**: {sum(1 for h in holes.values() if h.status == 'resolved')}

## Hole Catalog

"""
    
    # Group by type
    by_type = {}
    for hole in holes.values():
        by_type.setdefault(hole.type, []).append(hole)
    
    for hole_type in ["current_state", "architecture", "implementation", "quality"]:
        if hole_type not in by_type:
            continue
            
        content += f"\n### {hole_type.replace('_', ' ').title()} Holes\n\n"
        
        for hole in by_type[hole_type]:
            content += f"#### {hole.id}\n\n"
            content += f"**Question**: {hole.question}\n\n"
            content += f"**Dependencies**: {', '.join(hole.dependencies) if hole.dependencies else 'None'}\n\n"
            content += f"**Status**: {hole.status}\n\n"
            content += "**Resolution**: TBD\n\n"
            content += "**Validation**: TBD\n\n"
            content += "---\n\n"
    
    content += """
## Constraints

### Must Preserve
- [ ] C1: All current functionality
- [ ] C2: Backward compatibility for APIs
- [ ] C3: Bead integrity (no overwrite)
- [ ] C4: Commit history (no rebase/force push to main)

### Must Improve
- [ ] C5: Reduce complexity by _%
- [ ] C6: Increase test coverage to _%
- [ ] C7: Reduce code duplication by _%

### Must Maintain
- [ ] C9: Type safety (mypy/pyright clean)
- [ ] C10: Resource limits
- [ ] C11: Security posture

## Dependency Graph

```
# Ready to resolve (no dependencies):
"""
    
    ready = [h for h in holes.values() if not h.dependencies]
    for hole in ready:
        content += f"- {hole.id}\n"
    
    content += """
# Blocked (has dependencies):
"""
    
    blocked = [h for h in holes.values() if h.dependencies]
    for hole in blocked:
        content += f"- {hole.id} ← {', '.join(hole.dependencies)}\n"
    
    content += """
```

## Next Steps

1. Review this hole catalog
2. Prioritize holes to resolve first
3. Write characterization tests (see `tests/characterization/`)
4. Begin hole-by-hole resolution
5. Run `python scripts/next_hole.py` to see next resolvable holes

## Tracking

Use these commands to track progress:

```bash
# See next resolvable holes
python scripts/next_hole.py

# Validate a resolution
python scripts/validate_resolution.py {HOLE_ID}

# Propagate constraints
python scripts/propagate.py {HOLE_ID}

# Check completeness
python scripts/check_completeness.py
```

---

**Status**: ACTIVE
**Last Updated**: {subprocess.check_output(['date']).decode().strip()}
"""
    
    output_path.write_text(content)
    print(f"✅ Generated {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Discover refactoring holes")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Path to codebase to analyze"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("REFACTOR_IR.md"),
        help="Output file for refactor IR"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Typed Holes Refactor - Discovery Phase")
    print(f"📂 Analyzing: {args.path}")
    print()
    
    analyzer = CodebaseAnalyzer(args.path)
    holes = analyzer.analyze()
    
    generate_refactor_ir(holes, args.output)
    
    print()
    print("✨ Discovery complete!")
    print(f"📋 Review {args.output} for hole catalog")
    print("🔬 Next: Write characterization tests in tests/characterization/")
    print("🎯 Then: Run `python scripts/next_hole.py` to start resolution")


if __name__ == "__main__":
    main()
