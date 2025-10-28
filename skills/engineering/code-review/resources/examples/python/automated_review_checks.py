#!/usr/bin/env python3
"""
Automated review checks for Python code.

This script demonstrates how to programmatically check common code review items:
- Import organization
- Function complexity
- Documentation coverage
- Common anti-patterns
- Security issues

Can be integrated into CI/CD pipelines or pre-commit hooks.
"""

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ReviewIssue:
    """Represents a code review issue."""
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    category: str
    message: str


class PythonCodeReviewer:
    """Automated code reviewer for Python files."""

    def __init__(self, max_function_length: int = 50, max_complexity: int = 10):
        self.max_function_length = max_function_length
        self.max_complexity = max_complexity
        self.issues: List[ReviewIssue] = []

    def review_file(self, file_path: Path) -> List[ReviewIssue]:
        """Review a single Python file."""
        self.issues = []

        try:
            with open(file_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))

            # Run various checks
            self._check_imports(tree, file_path)
            self._check_function_length(tree, file_path, content)
            self._check_complexity(tree, file_path)
            self._check_documentation(tree, file_path)
            self._check_naming(tree, file_path)
            self._check_anti_patterns(tree, file_path)
            self._check_security_issues(content, file_path)

        except SyntaxError as e:
            self.issues.append(ReviewIssue(
                file=str(file_path),
                line=e.lineno or 0,
                severity="error",
                category="syntax",
                message=f"Syntax error: {e.msg}"
            ))

        return self.issues

    def _check_imports(self, tree: ast.AST, file_path: Path) -> None:
        """Check import organization and usage."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)

        # Check for wildcard imports
        for imp in imports:
            if isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    if alias.name == '*':
                        self.issues.append(ReviewIssue(
                            file=str(file_path),
                            line=imp.lineno,
                            severity="warning",
                            category="imports",
                            message="Avoid wildcard imports (from X import *)"
                        ))

        # Check for unused imports (simplified - would need scope analysis)
        # This is a demonstration - use tools like autoflake for accurate detection

    def _check_function_length(
        self,
        tree: ast.AST,
        file_path: Path,
        content: str
    ) -> None:
        """Check if functions exceed recommended length."""
        lines = content.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate function length
                start_line = node.lineno
                end_line = node.end_lineno or start_line

                # Count non-empty, non-comment lines
                func_lines = lines[start_line - 1:end_line]
                code_lines = [
                    line for line in func_lines
                    if line.strip() and not line.strip().startswith('#')
                ]

                if len(code_lines) > self.max_function_length:
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=start_line,
                        severity="warning",
                        category="complexity",
                        message=f"Function '{node.name}' is {len(code_lines)} lines "
                               f"(recommended: <{self.max_function_length}). "
                               f"Consider breaking it into smaller functions."
                    ))

    def _check_complexity(self, tree: ast.AST, file_path: Path) -> None:
        """Check cyclomatic complexity of functions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                if complexity > self.max_complexity:
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=node.lineno,
                        severity="warning",
                        category="complexity",
                        message=f"Function '{node.name}' has complexity {complexity} "
                               f"(recommended: <{self.max_complexity}). "
                               f"Consider simplifying or breaking down."
                    ))

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity (simplified)."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Each decision point adds 1
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # And/Or operations add complexity
                complexity += len(child.values) - 1

        return complexity

    def _check_documentation(self, tree: ast.AST, file_path: Path) -> None:
        """Check if public functions have docstrings."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions
                if node.name.startswith('_') and not node.name.startswith('__'):
                    continue

                # Check for docstring
                docstring = ast.get_docstring(node)
                if not docstring:
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=node.lineno,
                        severity="warning",
                        category="documentation",
                        message=f"Public function '{node.name}' lacks docstring"
                    ))

            elif isinstance(node, ast.ClassDef):
                # Check class docstring
                if not node.name.startswith('_'):
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        self.issues.append(ReviewIssue(
                            file=str(file_path),
                            line=node.lineno,
                            severity="warning",
                            category="documentation",
                            message=f"Public class '{node.name}' lacks docstring"
                        ))

    def _check_naming(self, tree: ast.AST, file_path: Path) -> None:
        """Check naming conventions."""
        for node in ast.walk(tree):
            # Check function names (should be snake_case)
            if isinstance(node, ast.FunctionDef):
                if not self._is_snake_case(node.name) and not node.name.startswith('__'):
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=node.lineno,
                        severity="info",
                        category="naming",
                        message=f"Function '{node.name}' should use snake_case"
                    ))

            # Check class names (should be PascalCase)
            elif isinstance(node, ast.ClassDef):
                if not self._is_pascal_case(node.name):
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=node.lineno,
                        severity="info",
                        category="naming",
                        message=f"Class '{node.name}' should use PascalCase"
                    ))

            # Check variable names
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    # Check for single-letter names in module scope (not in functions)
                    if len(node.id) == 1 and node.id not in ('i', 'j', 'k', 'x', 'y', 'z'):
                        # Would need scope analysis to properly detect this
                        pass

    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r'^[a-z_][a-z0-9_]*$', name) is not None

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return re.match(r'^[A-Z][a-zA-Z0-9]*$', name) is not None

    def _check_anti_patterns(self, tree: ast.AST, file_path: Path) -> None:
        """Check for common anti-patterns."""
        for node in ast.walk(tree):
            # Mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.defaults:
                    if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                        self.issues.append(ReviewIssue(
                            file=str(file_path),
                            line=node.lineno,
                            severity="error",
                            category="anti-pattern",
                            message=f"Function '{node.name}' has mutable default argument. "
                                   f"Use None and initialize in function body."
                        ))

            # Bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=node.lineno,
                        severity="warning",
                        category="anti-pattern",
                        message="Bare 'except:' catches all exceptions including KeyboardInterrupt. "
                               "Specify exception types."
                    ))

            # Using 'is' for value comparison
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, (ast.Is, ast.IsNot)):
                        # Check if comparing with literals (except None, True, False)
                        for comparator in node.comparators:
                            if isinstance(comparator, ast.Constant):
                                if comparator.value not in (None, True, False):
                                    self.issues.append(ReviewIssue(
                                        file=str(file_path),
                                        line=node.lineno,
                                        severity="warning",
                                        category="anti-pattern",
                                        message="Use '==' for value comparison, not 'is'. "
                                               "'is' checks identity, not equality."
                                    ))

    def _check_security_issues(self, content: str, file_path: Path) -> None:
        """Check for potential security issues."""
        # NOTE: This function DETECTS security issues in code, it doesn't contain them
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for eval/exec usage
            if re.search(r'\beval\s*\(', line):
                self.issues.append(ReviewIssue(
                    file=str(file_path),
                    line=i,
                    severity="error",
                    category="security",
                    message="Use of 'eval()' is a security risk. "
                           "Consider safer alternatives."
                ))

            if re.search(r'\bexec\s*\(', line):
                self.issues.append(ReviewIssue(
                    file=str(file_path),
                    line=i,
                    severity="error",
                    category="security",
                    message="Use of 'exec()' is a security risk. "
                           "Consider safer alternatives."
                ))

            # Check for pickle usage (can execute arbitrary code)
            if re.search(r'\bpickle\.loads?\s*\(', line):
                self.issues.append(ReviewIssue(
                    file=str(file_path),
                    line=i,
                    severity="warning",
                    category="security",
                    message="pickle.load() can execute arbitrary code. "
                           "Only use with trusted data."
                ))

            # Check for shell=True in subprocess
            if re.search(r'shell\s*=\s*True', line):
                self.issues.append(ReviewIssue(
                    file=str(file_path),
                    line=i,
                    severity="error",
                    category="security",
                    message="subprocess with shell=True is vulnerable to injection. "
                           "Use shell=False and pass command as list."
                ))

            # Check for hardcoded passwords/secrets
            if re.search(r'(password|secret|api[_-]?key|token)\s*=\s*["\'][^"\']+["\']',
                        line, re.IGNORECASE):
                # Skip if it's a variable reference or test value
                if 'test' not in line.lower() and 'example' not in line.lower():
                    self.issues.append(ReviewIssue(
                        file=str(file_path),
                        line=i,
                        severity="error",
                        category="security",
                        message="Possible hardcoded secret. "
                               "Use environment variables or secure storage."
                    ))


def review_directory(directory: Path, recursive: bool = True) -> List[ReviewIssue]:
    """Review all Python files in a directory."""
    reviewer = PythonCodeReviewer()
    all_issues = []

    pattern = "**/*.py" if recursive else "*.py"
    for py_file in directory.glob(pattern):
        # Skip virtual environments and common non-source directories
        if any(part in py_file.parts for part in ('venv', '.venv', 'env', '.env',
                                                    'site-packages', '__pycache__')):
            continue

        issues = reviewer.review_file(py_file)
        all_issues.extend(issues)

    return all_issues


def print_issues(issues: List[ReviewIssue]) -> None:
    """Print issues in a readable format."""
    if not issues:
        print("✓ No issues found!")
        return

    # Group by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    info = [i for i in issues if i.severity == "info"]

    if errors:
        print(f"\n🔴 ERRORS ({len(errors)}):")
        print("=" * 70)
        for issue in errors:
            print(f"{issue.file}:{issue.line}")
            print(f"  [{issue.category}] {issue.message}\n")

    if warnings:
        print(f"\n🟡 WARNINGS ({len(warnings)}):")
        print("=" * 70)
        for issue in warnings:
            print(f"{issue.file}:{issue.line}")
            print(f"  [{issue.category}] {issue.message}\n")

    if info:
        print(f"\n🔵 INFO ({len(info)}):")
        print("=" * 70)
        for issue in info:
            print(f"{issue.file}:{issue.line}")
            print(f"  [{issue.category}] {issue.message}\n")

    # Summary
    print("=" * 70)
    print(f"Total: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated code review checks for Python"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to file or directory to review"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't recurse into subdirectories"
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path '{args.path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Review the path
    if args.path.is_file():
        reviewer = PythonCodeReviewer()
        issues = reviewer.review_file(args.path)
    else:
        issues = review_directory(args.path, recursive=not args.no_recursive)

    # Print results
    print_issues(issues)

    # Exit with error code if there are errors
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
