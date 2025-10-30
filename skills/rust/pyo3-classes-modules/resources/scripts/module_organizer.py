#!/usr/bin/env python3
"""
PyO3 Module Organizer

Analyzes and organizes PyO3 module structure. Provides tools for validating
module layout, generating templates, checking naming conventions, analyzing
dependencies, and documenting module organization.

Features:
- Analyze module structure and hierarchy
- Validate module organization and conventions
- Generate module templates
- Check naming conventions (PEP 8, PyO3 best practices)
- Analyze inter-module dependencies
- Suggest organizational improvements
- Generate module documentation
- Visualize module hierarchy
- Detect circular dependencies

Usage:
    # Analyze module structure
    module_organizer.py analyze /path/to/module --recursive

    # Validate module organization
    module_organizer.py validate /path/to/module --strict

    # Generate module template
    module_organizer.py generate my_module --type extension

    # Check naming conventions
    module_organizer.py check-names /path/to/module --fix

    # Analyze dependencies
    module_organizer.py deps /path/to/module --visualize

Examples:
    # Analyze and report
    python module_organizer.py analyze ./src --output report.json

    # Validate with strict rules
    python module_organizer.py validate ./src --strict --verbose

    # Generate new module structure
    python module_organizer.py generate data_processor --submodules io,transform,export

    # Check and fix naming
    python module_organizer.py check-names ./src --fix --dry-run

    # Dependency analysis with graph
    python module_organizer.py deps ./src --visualize --output deps.dot

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import ast
import inspect
import json
import logging
import os
import re
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModuleType(Enum):
    """Module type classification."""
    EXTENSION = "extension"  # PyO3 extension module
    PURE_PYTHON = "pure_python"  # Pure Python
    MIXED = "mixed"  # Contains both
    PACKAGE = "package"  # Package with submodules


class IssueLevel(Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class NamingIssue:
    """Naming convention issue."""
    level: IssueLevel
    name: str
    issue: str
    suggestion: str
    location: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'level': self.level.value,
            'name': self.name,
            'issue': self.issue,
            'suggestion': self.suggestion,
            'location': self.location
        }


@dataclass
class ModuleInfo:
    """Information about a module."""
    name: str
    path: Path
    type: ModuleType
    submodules: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    doc: str = ""
    line_count: int = 0
    has_init: bool = False
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['type'] = self.type.value
        data['path'] = str(self.path)
        return data


@dataclass
class DependencyEdge:
    """Dependency between modules."""
    source: str
    target: str
    import_type: str  # 'import', 'from', 'use' (for Rust)
    line_number: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AnalysisResult:
    """Complete module analysis result."""
    modules: List[ModuleInfo]
    naming_issues: List[NamingIssue]
    dependencies: List[DependencyEdge]
    circular_deps: List[List[str]]
    suggestions: List[str]
    statistics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'modules': [m.to_dict() for m in self.modules],
            'naming_issues': [i.to_dict() for i in self.naming_issues],
            'dependencies': [d.to_dict() for d in self.dependencies],
            'circular_deps': self.circular_deps,
            'suggestions': self.suggestions,
            'statistics': self.statistics
        }


class NamingValidator:
    """Validates naming conventions."""

    # PEP 8 patterns
    MODULE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    CLASS_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    FUNCTION_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')
    CONSTANT_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*$')

    # PyO3-specific patterns
    PYCLASS_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    PYFUNCTION_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')

    def validate_module_name(self, name: str) -> Optional[NamingIssue]:
        """Validate module name."""
        if not self.MODULE_PATTERN.match(name):
            suggestion = self._to_snake_case(name)
            return NamingIssue(
                level=IssueLevel.ERROR,
                name=name,
                issue="Module name should be lowercase with underscores",
                suggestion=suggestion,
                location="module"
            )
        return None

    def validate_class_name(self, name: str, location: str) -> Optional[NamingIssue]:
        """Validate class name."""
        if not self.CLASS_PATTERN.match(name):
            suggestion = self._to_pascal_case(name)
            return NamingIssue(
                level=IssueLevel.ERROR,
                name=name,
                issue="Class name should be PascalCase",
                suggestion=suggestion,
                location=location
            )
        return None

    def validate_function_name(self, name: str, location: str) -> Optional[NamingIssue]:
        """Validate function name."""
        if name.startswith('_'):
            return None  # Private functions ok

        if not self.FUNCTION_PATTERN.match(name):
            suggestion = self._to_snake_case(name)
            return NamingIssue(
                level=IssueLevel.WARNING,
                name=name,
                issue="Function name should be lowercase with underscores",
                suggestion=suggestion,
                location=location
            )
        return None

    def validate_constant_name(self, name: str, location: str) -> Optional[NamingIssue]:
        """Validate constant name."""
        if not self.CONSTANT_PATTERN.match(name):
            suggestion = self._to_screaming_snake_case(name)
            return NamingIssue(
                level=IssueLevel.INFO,
                name=name,
                issue="Constant name should be UPPERCASE with underscores",
                suggestion=suggestion,
                location=location
            )
        return None

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert to snake_case."""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before sequences of uppercase
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert to PascalCase."""
        return ''.join(word.capitalize() for word in name.split('_'))

    @staticmethod
    def _to_screaming_snake_case(name: str) -> str:
        """Convert to SCREAMING_SNAKE_CASE."""
        return NamingValidator._to_snake_case(name).upper()


class ModuleAnalyzer:
    """Analyzes Python modules."""

    def __init__(self):
        self.naming_validator = NamingValidator()

    def analyze_file(self, file_path: Path) -> ModuleInfo:
        """Analyze a single Python file."""
        logger.debug(f"Analyzing file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                tree = ast.parse(source, filename=str(file_path))

            module_name = file_path.stem

            classes = []
            functions = []
            imports = []
            exports = []
            doc = ast.get_docstring(tree) or ""

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):
                        functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Check for __all__ to find exports
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == '__all__':
                            if isinstance(node.value, ast.List):
                                exports = [
                                    elt.s for elt in node.value.elts
                                    if isinstance(elt, ast.Constant)
                                ]

            line_count = len(source.splitlines())

            # Determine module type
            module_type = ModuleType.PURE_PYTHON
            if any('pyo3' in imp or 'rust' in imp.lower() for imp in imports):
                module_type = ModuleType.EXTENSION

            return ModuleInfo(
                name=module_name,
                path=file_path,
                type=module_type,
                classes=classes,
                functions=functions,
                imports=imports,
                exports=exports,
                doc=doc,
                line_count=line_count
            )

        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            return ModuleInfo(
                name=file_path.stem,
                path=file_path,
                type=ModuleType.PURE_PYTHON
            )

    def analyze_package(self, package_path: Path, recursive: bool = True) -> List[ModuleInfo]:
        """Analyze a Python package."""
        modules = []

        # Check for __init__.py
        init_file = package_path / '__init__.py'
        has_init = init_file.exists()

        if has_init:
            init_module = self.analyze_file(init_file)
            init_module.has_init = True
            modules.append(init_module)

        # Find Python files
        pattern = '**/*.py' if recursive else '*.py'
        for py_file in package_path.glob(pattern):
            if py_file.name == '__init__.py':
                continue
            if py_file.name.startswith('_'):
                continue

            module = self.analyze_file(py_file)
            modules.append(module)

        return modules

    def check_naming(self, module: ModuleInfo) -> List[NamingIssue]:
        """Check naming conventions for a module."""
        issues = []

        # Check module name
        module_issue = self.naming_validator.validate_module_name(module.name)
        if module_issue:
            issues.append(module_issue)

        # Check class names
        for cls_name in module.classes:
            cls_issue = self.naming_validator.validate_class_name(
                cls_name,
                f"{module.name}.{cls_name}"
            )
            if cls_issue:
                issues.append(cls_issue)

        # Check function names
        for func_name in module.functions:
            func_issue = self.naming_validator.validate_function_name(
                func_name,
                f"{module.name}.{func_name}"
            )
            if func_issue:
                issues.append(func_issue)

        return issues

    def analyze_dependencies(self, modules: List[ModuleInfo]) -> List[DependencyEdge]:
        """Analyze dependencies between modules."""
        dependencies = []
        module_names = {m.name for m in modules}

        for module in modules:
            for imp in module.imports:
                # Check if import is from another module in the package
                imp_parts = imp.split('.')
                for part in imp_parts:
                    if part in module_names and part != module.name:
                        dependencies.append(DependencyEdge(
                            source=module.name,
                            target=part,
                            import_type='import',
                            line_number=0  # Would need AST line number
                        ))

        return dependencies

    def detect_circular_deps(self, dependencies: List[DependencyEdge]) -> List[List[str]]:
        """Detect circular dependencies."""
        # Build adjacency list
        graph = defaultdict(set)
        for dep in dependencies:
            graph[dep.source].add(dep.target)

        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles


class ModuleGenerator:
    """Generates module templates."""

    @staticmethod
    def generate_extension_module(
        name: str,
        submodules: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate PyO3 extension module template.

        Returns dictionary mapping file paths to contents.
        """
        files = {}

        # Generate lib.rs
        lib_rs = f'''//! {name} - PyO3 Extension Module
//!
//! This module provides Python bindings for {name} functionality.

use pyo3::prelude::*;

/// {name} module
#[pymodule]
fn {name}(py: Python, m: &PyModule) -> PyResult<()> {{
    m.add_class::<Example>()?;
    m.add_function(wrap_pyfunction!(example_function, m)?)?;
'''

        if submodules:
            for submod in submodules:
                lib_rs += f'    m.add_submodule({submod}::create_submodule(py)?)?;\n'

        lib_rs += '''    Ok(())
}

/// Example class
#[pyclass]
struct Example {
    value: i64,
}

#[pymethods]
impl Example {
    #[new]
    fn new(value: i64) -> Self {
        Example { value }
    }

    fn get_value(&self) -> i64 {
        self.value
    }
}

/// Example function
#[pyfunction]
fn example_function(x: i64, y: i64) -> i64 {
    x + y
}
'''

        files['src/lib.rs'] = lib_rs

        # Generate Cargo.toml
        cargo_toml = f'''[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "{name}"
crate-type = ["cdylib"]

[dependencies]
pyo3 = {{ version = "0.20", features = ["extension-module"] }}
'''

        files['Cargo.toml'] = cargo_toml

        # Generate pyproject.toml
        pyproject_toml = f'''[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "{name}"
version = "0.1.0"
description = "PyO3 extension module for {name}"
requires-python = ">=3.8"

[tool.maturin]
module-name = "{name}"
python-source = "python"
'''

        files['pyproject.toml'] = pyproject_toml

        # Generate __init__.py
        init_py = f'''"""
{name} - Python package

This package provides Python bindings to {name} Rust implementation.
"""

from .{name} import *

__version__ = "0.1.0"
__all__ = ["Example", "example_function"]
'''

        files[f'python/{name}/__init__.py'] = init_py

        # Generate submodules
        if submodules:
            for submod in submodules:
                submod_rs = f'''//! {submod} submodule

use pyo3::prelude::*;

/// Create {submod} submodule
pub fn create_submodule(py: Python) -> PyResult<&PyModule> {{
    let m = PyModule::new(py, "{submod}")?;
    m.add_class::<{submod.capitalize()}Class>()?;
    Ok(m)
}}

#[pyclass]
struct {submod.capitalize()}Class {{
    // Add fields
}}

#[pymethods]
impl {submod.capitalize()}Class {{
    #[new]
    fn new() -> Self {{
        Self {{}}
    }}
}}
'''
                files[f'src/{submod}.rs'] = submod_rs

        return files

    @staticmethod
    def write_template(
        output_dir: Path,
        files: Dict[str, str],
        dry_run: bool = False
    ) -> None:
        """Write template files to disk."""
        for file_path, content in files.items():
            full_path = output_dir / file_path

            if dry_run:
                logger.info(f"Would create: {full_path}")
                continue

            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            logger.info(f"Created: {full_path}")


class ModuleOrganizer:
    """Main organizer for module analysis and management."""

    def __init__(self):
        self.analyzer = ModuleAnalyzer()
        self.generator = ModuleGenerator()

    def analyze(
        self,
        path: Path,
        recursive: bool = True
    ) -> AnalysisResult:
        """
        Perform complete analysis of module(s).

        Returns comprehensive analysis results.
        """
        logger.info(f"Analyzing: {path}")

        if path.is_file():
            modules = [self.analyzer.analyze_file(path)]
        else:
            modules = self.analyzer.analyze_package(path, recursive)

        # Check naming
        naming_issues = []
        for module in modules:
            issues = self.analyzer.check_naming(module)
            naming_issues.extend(issues)

        # Analyze dependencies
        dependencies = self.analyzer.analyze_dependencies(modules)

        # Detect circular dependencies
        circular_deps = self.analyzer.detect_circular_deps(dependencies)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            modules,
            naming_issues,
            circular_deps
        )

        # Calculate statistics
        statistics = {
            'total_modules': len(modules),
            'total_classes': sum(len(m.classes) for m in modules),
            'total_functions': sum(len(m.functions) for m in modules),
            'total_lines': sum(m.line_count for m in modules),
            'naming_issues': len(naming_issues),
            'dependencies': len(dependencies),
            'circular_deps': len(circular_deps)
        }

        return AnalysisResult(
            modules=modules,
            naming_issues=naming_issues,
            dependencies=dependencies,
            circular_deps=circular_deps,
            suggestions=suggestions,
            statistics=statistics
        )

    def _generate_suggestions(
        self,
        modules: List[ModuleInfo],
        naming_issues: List[NamingIssue],
        circular_deps: List[List[str]]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        # Large modules
        for module in modules:
            if module.line_count > 1000:
                suggestions.append(
                    f"Consider splitting {module.name} ({module.line_count} lines) "
                    "into smaller modules"
                )

        # Modules with many classes
        for module in modules:
            if len(module.classes) > 10:
                suggestions.append(
                    f"Module {module.name} has {len(module.classes)} classes. "
                    "Consider organizing into submodules"
                )

        # Missing __init__.py
        init_modules = [m for m in modules if m.has_init]
        if not init_modules and len(modules) > 1:
            suggestions.append("Add __init__.py to make this a proper package")

        # Circular dependencies
        if circular_deps:
            suggestions.append(
                f"Found {len(circular_deps)} circular dependencies. "
                "Refactor to remove cycles"
            )

        # Naming issues
        error_count = sum(1 for i in naming_issues if i.level == IssueLevel.ERROR)
        if error_count > 0:
            suggestions.append(
                f"Fix {error_count} naming convention errors for better code quality"
            )

        return suggestions


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Module Organizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze module structure')
    analyze_parser.add_argument('path', type=Path, help='Module path')
    analyze_parser.add_argument('--recursive', '-r', action='store_true', help='Recursive analysis')
    analyze_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate module organization')
    validate_parser.add_argument('path', type=Path, help='Module path')
    validate_parser.add_argument('--strict', action='store_true', help='Strict validation')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate module template')
    generate_parser.add_argument('name', help='Module name')
    generate_parser.add_argument('--type', choices=['extension', 'pure'], default='extension')
    generate_parser.add_argument('--submodules', help='Comma-separated submodules')
    generate_parser.add_argument('--output', '-o', type=Path, default=Path('.'))
    generate_parser.add_argument('--dry-run', action='store_true', help='Show what would be created')

    # Check names command
    check_parser = subparsers.add_parser('check-names', help='Check naming conventions')
    check_parser.add_argument('path', type=Path, help='Module path')
    check_parser.add_argument('--fix', action='store_true', help='Suggest fixes')

    # Dependencies command
    deps_parser = subparsers.add_parser('deps', help='Analyze dependencies')
    deps_parser.add_argument('path', type=Path, help='Module path')
    deps_parser.add_argument('--visualize', action='store_true', help='Generate graph')
    deps_parser.add_argument('--output', '-o', type=Path, help='Output file')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    organizer = ModuleOrganizer()

    try:
        if args.command == 'analyze':
            result = organizer.analyze(args.path, args.recursive)

            if args.json:
                output = json.dumps(result.to_dict(), indent=2)
            else:
                lines = [
                    f"\n=== Module Analysis: {args.path} ===\n",
                    f"Statistics:",
                    f"  Modules: {result.statistics['total_modules']}",
                    f"  Classes: {result.statistics['total_classes']}",
                    f"  Functions: {result.statistics['total_functions']}",
                    f"  Total Lines: {result.statistics['total_lines']:,}",
                    f"\nNaming Issues: {result.statistics['naming_issues']}",
                    f"Dependencies: {result.statistics['dependencies']}",
                    f"Circular Dependencies: {result.statistics['circular_deps']}",
                ]

                if result.suggestions:
                    lines.append("\nSuggestions:")
                    for suggestion in result.suggestions:
                        lines.append(f"  - {suggestion}")

                output = "\n".join(lines)

            if args.output:
                args.output.write_text(output)
                print(f"Analysis saved to {args.output}")
            else:
                print(output)

        elif args.command == 'validate':
            result = organizer.analyze(args.path, recursive=True)

            error_count = sum(1 for i in result.naming_issues if i.level == IssueLevel.ERROR)
            warning_count = sum(1 for i in result.naming_issues if i.level == IssueLevel.WARNING)

            if args.json:
                validation_result = {
                    'valid': error_count == 0 if args.strict else error_count == 0 and warning_count == 0,
                    'errors': error_count,
                    'warnings': warning_count,
                    'circular_deps': len(result.circular_deps),
                    'issues': [i.to_dict() for i in result.naming_issues]
                }
                print(json.dumps(validation_result, indent=2))
            else:
                print(f"\nValidation Results:")
                print(f"  Errors: {error_count}")
                print(f"  Warnings: {warning_count}")
                print(f"  Circular Dependencies: {len(result.circular_deps)}")

                if error_count > 0 or (args.strict and warning_count > 0):
                    print("\n✗ Validation failed")
                    sys.exit(1)
                else:
                    print("\n✓ Validation passed")

        elif args.command == 'generate':
            submodules = args.submodules.split(',') if args.submodules else None

            if args.type == 'extension':
                files = organizer.generator.generate_extension_module(args.name, submodules)
            else:
                # Could add pure Python template
                print("Pure Python template not yet implemented")
                sys.exit(1)

            organizer.generator.write_template(args.output, files, args.dry_run)
            print(f"Generated module template: {args.name}")

        elif args.command == 'check-names':
            result = organizer.analyze(args.path)

            if args.json:
                print(json.dumps([i.to_dict() for i in result.naming_issues], indent=2))
            else:
                if not result.naming_issues:
                    print("✓ No naming issues found")
                else:
                    print(f"\nFound {len(result.naming_issues)} naming issues:\n")
                    for issue in result.naming_issues:
                        symbol = "✗" if issue.level == IssueLevel.ERROR else "⚠"
                        print(f"{symbol} {issue.name} ({issue.location})")
                        print(f"    {issue.issue}")
                        if args.fix:
                            print(f"    Suggestion: {issue.suggestion}")

        elif args.command == 'deps':
            result = organizer.analyze(args.path)

            if args.json:
                print(json.dumps([d.to_dict() for d in result.dependencies], indent=2))
            else:
                print(f"\nFound {len(result.dependencies)} dependencies:")
                for dep in result.dependencies:
                    print(f"  {dep.source} → {dep.target}")

                if result.circular_deps:
                    print(f"\n⚠ Found {len(result.circular_deps)} circular dependencies:")
                    for cycle in result.circular_deps:
                        print(f"  {' → '.join(cycle)}")

            if args.visualize and args.output:
                # Generate Graphviz DOT format
                lines = ["digraph dependencies {"]
                for dep in result.dependencies:
                    lines.append(f'  "{dep.source}" -> "{dep.target}";')
                lines.append("}")
                args.output.write_text("\n".join(lines))
                print(f"Dependency graph saved to {args.output}")

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
