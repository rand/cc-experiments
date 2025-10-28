#!/usr/bin/env python3
"""
Integration Test Coverage Analyzer

Analyzes integration test coverage by examining test files, identifying
tested vs untested components, and providing actionable recommendations.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
import xml.etree.ElementTree as ET


VERSION = "1.0.0"


class CoverageAnalyzer:
    """Analyzes integration test coverage across multiple dimensions."""

    def __init__(self, test_dir: str, src_dir: str, verbose: bool = False):
        self.test_dir = Path(test_dir)
        self.src_dir = Path(src_dir)
        self.verbose = verbose

        # Coverage data
        self.tested_endpoints: Set[str] = set()
        self.tested_models: Set[str] = set()
        self.tested_services: Set[str] = set()
        self.tested_repositories: Set[str] = set()
        self.tested_integrations: Set[str] = set()

        # Source code data
        self.all_endpoints: Set[str] = set()
        self.all_models: Set[str] = set()
        self.all_services: Set[str] = set()
        self.all_repositories: Set[str] = set()
        self.all_integrations: Set[str] = set()

        # Test metrics
        self.test_files: List[Path] = []
        self.test_count = 0
        self.test_types: Dict[str, int] = defaultdict(int)

    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def analyze(self) -> Dict:
        """Run complete analysis."""
        self.log("Starting coverage analysis...")

        self._discover_test_files()
        self._analyze_test_files()
        self._discover_source_components()

        return self._generate_report()

    def _discover_test_files(self):
        """Discover all test files in test directory."""
        self.log(f"Discovering test files in {self.test_dir}")

        if not self.test_dir.exists():
            raise FileNotFoundError(f"Test directory not found: {self.test_dir}")

        patterns = ["test_*.py", "*_test.py", "test_*.ts", "*_test.ts", "*_test.go"]

        for pattern in patterns:
            self.test_files.extend(self.test_dir.rglob(pattern))

        self.log(f"Found {len(self.test_files)} test files")

    def _analyze_test_files(self):
        """Analyze test files to identify what's being tested."""
        self.log("Analyzing test files...")

        for test_file in self.test_files:
            self._analyze_test_file(test_file)

        self.log(f"Analyzed {self.test_count} tests")

    def _analyze_test_file(self, test_file: Path):
        """Analyze a single test file."""
        try:
            content = test_file.read_text()

            # Count tests
            test_functions = re.findall(r'def (test_\w+)|it\(["\'](.+?)["\']\)|Test\w+', content)
            self.test_count += len(test_functions)

            # Identify test types
            if "integration" in test_file.name.lower():
                self.test_types["integration"] += 1
            if "api" in test_file.name.lower() or "/api" in str(test_file):
                self.test_types["api"] += 1
                self._extract_tested_endpoints(content)
            if "database" in test_file.name.lower() or "db" in test_file.name.lower():
                self.test_types["database"] += 1
                self._extract_tested_repositories(content)
            if "service" in test_file.name.lower():
                self.test_types["service"] += 1
                self._extract_tested_services(content)

            # Extract tested components
            self._extract_tested_models(content)
            self._extract_tested_integrations(content)

        except Exception as e:
            self.log(f"Error analyzing {test_file}: {e}")

    def _extract_tested_endpoints(self, content: str):
        """Extract API endpoints being tested."""
        # Match patterns like: .get('/users/123'), .post("/api/orders")
        patterns = [
            r'\.(?:get|post|put|patch|delete)\(["\']([^"\']+)["\']',
            r'request\(["\'](?:GET|POST|PUT|PATCH|DELETE)["\']\s*,\s*["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            self.tested_endpoints.update(matches)

    def _extract_tested_models(self, content: str):
        """Extract models being tested."""
        # Match patterns like: User(...), Order.create(), Product(
        patterns = [
            r'(?:from|import)\s+.*?(?:models|entities)\s+import\s+(\w+)',
            r'(\w+)\.objects\.',
            r'(\w+)\.query\.',
            r'new\s+(\w+)\(',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            self.tested_models.update(matches)

    def _extract_tested_services(self, content: str):
        """Extract services being tested."""
        patterns = [
            r'(\w+Service)\(',
            r'(?:from|import)\s+.*?services\s+import\s+(\w+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            self.tested_services.update(matches)

    def _extract_tested_repositories(self, content: str):
        """Extract repositories being tested."""
        patterns = [
            r'(\w+Repository)\(',
            r'(\w+Repo)\(',
            r'(?:from|import)\s+.*?repositories\s+import\s+(\w+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            self.tested_repositories.update(matches)

    def _extract_tested_integrations(self, content: str):
        """Extract external integrations being tested."""
        # Look for common integration patterns
        integrations = {
            "database": ["database", "db", "postgres", "mysql", "mongodb"],
            "cache": ["redis", "memcached", "cache"],
            "queue": ["rabbitmq", "kafka", "celery", "queue"],
            "email": ["email", "smtp", "sendgrid", "mailgun"],
            "storage": ["s3", "blob", "storage", "bucket"],
            "api": ["requests", "httpx", "axios", "fetch"],
        }

        content_lower = content.lower()
        for integration_type, keywords in integrations.items():
            if any(keyword in content_lower for keyword in keywords):
                self.tested_integrations.add(integration_type)

    def _discover_source_components(self):
        """Discover all components in source code."""
        self.log(f"Discovering source components in {self.src_dir}")

        if not self.src_dir.exists():
            self.log(f"Source directory not found: {self.src_dir}")
            return

        # Discover routes/endpoints
        self._discover_endpoints()

        # Discover models
        self._discover_models()

        # Discover services
        self._discover_services()

        # Discover repositories
        self._discover_repositories()

    def _discover_endpoints(self):
        """Discover API endpoints in source code."""
        for src_file in self.src_dir.rglob("*.py"):
            if "routes" in str(src_file) or "api" in str(src_file):
                content = src_file.read_text()
                # Match FastAPI/Flask route decorators
                patterns = [
                    r'@\w+\.(?:get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                    r'@app\.route\(["\']([^"\']+)["\']',
                ]
                for pattern in patterns:
                    self.all_endpoints.update(re.findall(pattern, content))

        for src_file in self.src_dir.rglob("*.ts"):
            if "routes" in str(src_file) or "controller" in str(src_file):
                content = src_file.read_text()
                # Match Express routes
                patterns = [
                    r'router\.(?:get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                    r'app\.(?:get|post|put|patch|delete)\(["\']([^"\']+)["\']',
                ]
                for pattern in patterns:
                    self.all_endpoints.update(re.findall(pattern, content))

    def _discover_models(self):
        """Discover models in source code."""
        for src_file in self.src_dir.rglob("*.py"):
            if "models" in str(src_file) or "entities" in str(src_file):
                content = src_file.read_text()
                # Match class definitions
                models = re.findall(r'class (\w+)\(.*?Model.*?\):', content)
                self.all_models.update(models)

    def _discover_services(self):
        """Discover services in source code."""
        for src_file in self.src_dir.rglob("*.py"):
            if "service" in str(src_file):
                content = src_file.read_text()
                services = re.findall(r'class (\w+Service):', content)
                self.all_services.update(services)

        for src_file in self.src_dir.rglob("*.ts"):
            if "service" in str(src_file):
                content = src_file.read_text()
                services = re.findall(r'class (\w+Service)', content)
                self.all_services.update(services)

    def _discover_repositories(self):
        """Discover repositories in source code."""
        for src_file in self.src_dir.rglob("*.py"):
            if "repository" in str(src_file) or "repo" in str(src_file):
                content = src_file.read_text()
                repos = re.findall(r'class (\w+(?:Repository|Repo)):', content)
                self.all_repositories.update(repos)

    def _calculate_coverage_percentage(self, tested: Set, all_items: Set) -> float:
        """Calculate coverage percentage."""
        if not all_items:
            return 100.0
        return (len(tested) / len(all_items)) * 100

    def _generate_report(self) -> Dict:
        """Generate comprehensive coverage report."""
        report = {
            "summary": {
                "total_test_files": len(self.test_files),
                "total_tests": self.test_count,
                "test_types": dict(self.test_types),
            },
            "coverage": {
                "endpoints": {
                    "tested": sorted(list(self.tested_endpoints)),
                    "all": sorted(list(self.all_endpoints)),
                    "untested": sorted(list(self.all_endpoints - self.tested_endpoints)),
                    "percentage": self._calculate_coverage_percentage(
                        self.tested_endpoints, self.all_endpoints
                    ),
                },
                "models": {
                    "tested": sorted(list(self.tested_models)),
                    "all": sorted(list(self.all_models)),
                    "untested": sorted(list(self.all_models - self.tested_models)),
                    "percentage": self._calculate_coverage_percentage(
                        self.tested_models, self.all_models
                    ),
                },
                "services": {
                    "tested": sorted(list(self.tested_services)),
                    "all": sorted(list(self.all_services)),
                    "untested": sorted(list(self.all_services - self.tested_services)),
                    "percentage": self._calculate_coverage_percentage(
                        self.tested_services, self.all_services
                    ),
                },
                "repositories": {
                    "tested": sorted(list(self.tested_repositories)),
                    "all": sorted(list(self.all_repositories)),
                    "untested": sorted(list(self.all_repositories - self.tested_repositories)),
                    "percentage": self._calculate_coverage_percentage(
                        self.tested_repositories, self.all_repositories
                    ),
                },
                "integrations": {
                    "tested": sorted(list(self.tested_integrations)),
                },
            },
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations."""
        recommendations = []

        # Untested endpoints
        untested_endpoints = self.all_endpoints - self.tested_endpoints
        if untested_endpoints:
            recommendations.append({
                "priority": "high",
                "category": "endpoints",
                "message": f"{len(untested_endpoints)} API endpoints lack integration tests",
                "items": sorted(list(untested_endpoints))[:5],  # Show first 5
                "action": "Add integration tests for these endpoints"
            })

        # Untested services
        untested_services = self.all_services - self.tested_services
        if untested_services:
            recommendations.append({
                "priority": "high",
                "category": "services",
                "message": f"{len(untested_services)} services lack integration tests",
                "items": sorted(list(untested_services))[:5],
                "action": "Add integration tests for service interactions"
            })

        # Untested repositories
        untested_repos = self.all_repositories - self.tested_repositories
        if untested_repos:
            recommendations.append({
                "priority": "medium",
                "category": "repositories",
                "message": f"{len(untested_repos)} repositories lack integration tests",
                "items": sorted(list(untested_repos))[:5],
                "action": "Add database integration tests for repositories"
            })

        # Missing integration test types
        if "database" not in self.test_types:
            recommendations.append({
                "priority": "high",
                "category": "test_types",
                "message": "No database integration tests found",
                "action": "Add tests for database operations (CRUD, transactions, constraints)"
            })

        if "api" not in self.test_types:
            recommendations.append({
                "priority": "high",
                "category": "test_types",
                "message": "No API integration tests found",
                "action": "Add tests for API endpoints (requests, responses, errors)"
            })

        # Missing integration types
        important_integrations = {"database", "cache", "queue"}
        missing_integrations = important_integrations - self.tested_integrations
        if missing_integrations:
            recommendations.append({
                "priority": "medium",
                "category": "integrations",
                "message": f"Missing integration tests for: {', '.join(missing_integrations)}",
                "action": "Add tests for external system integrations"
            })

        # Low test count
        if self.test_count < 10:
            recommendations.append({
                "priority": "high",
                "category": "quantity",
                "message": f"Only {self.test_count} integration tests found",
                "action": "Increase integration test coverage"
            })

        return recommendations


def parse_coverage_xml(coverage_file: Path) -> Dict:
    """Parse coverage.xml file if available."""
    if not coverage_file.exists():
        return {}

    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()

        line_rate = float(root.attrib.get("line-rate", 0))
        branch_rate = float(root.attrib.get("branch-rate", 0))

        return {
            "line_coverage": line_rate * 100,
            "branch_coverage": branch_rate * 100,
        }
    except Exception as e:
        print(f"Warning: Could not parse coverage XML: {e}", file=sys.stderr)
        return {}


def format_report_text(report: Dict) -> str:
    """Format report as human-readable text."""
    lines = []

    lines.append("=" * 70)
    lines.append("INTEGRATION TEST COVERAGE ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    summary = report["summary"]
    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Test Files:  {summary['total_test_files']}")
    lines.append(f"Total Tests: {summary['total_tests']}")
    lines.append("")

    if summary["test_types"]:
        lines.append("Test Types:")
        for test_type, count in sorted(summary["test_types"].items()):
            lines.append(f"  - {test_type}: {count}")
        lines.append("")

    # Coverage
    lines.append("COVERAGE BY COMPONENT")
    lines.append("-" * 70)

    coverage = report["coverage"]
    for component_type in ["endpoints", "services", "repositories", "models"]:
        component = coverage[component_type]
        tested_count = len(component["tested"])
        total_count = len(component["all"])
        percentage = component["percentage"]

        lines.append(f"\n{component_type.upper()}")
        lines.append(f"  Coverage: {percentage:.1f}% ({tested_count}/{total_count})")

        if component["untested"]:
            lines.append(f"  Untested ({len(component['untested'])}):")
            for item in component["untested"][:5]:
                lines.append(f"    - {item}")
            if len(component["untested"]) > 5:
                lines.append(f"    ... and {len(component['untested']) - 5} more")

    # Integrations
    if coverage["integrations"]["tested"]:
        lines.append("\nINTEGRATIONS TESTED")
        lines.append("-" * 70)
        for integration in sorted(coverage["integrations"]["tested"]):
            lines.append(f"  ✓ {integration}")

    # Recommendations
    if report["recommendations"]:
        lines.append("\n")
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 70)

        priority_order = {"high": 1, "medium": 2, "low": 3}
        sorted_recommendations = sorted(
            report["recommendations"],
            key=lambda r: priority_order.get(r["priority"], 999)
        )

        for rec in sorted_recommendations:
            priority_symbol = "⚠️ " if rec["priority"] == "high" else "• "
            lines.append(f"\n{priority_symbol}[{rec['priority'].upper()}] {rec['message']}")
            lines.append(f"  Action: {rec['action']}")

            if "items" in rec:
                lines.append("  Examples:")
                for item in rec["items"]:
                    lines.append(f"    - {item}")

    lines.append("\n" + "=" * 70)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze integration test coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze integration tests
  %(prog)s --test-dir tests/integration --src-dir src

  # Output as JSON
  %(prog)s --test-dir tests/integration --src-dir src --json

  # Include coverage.xml data
  %(prog)s --test-dir tests/integration --src-dir src --coverage-file coverage.xml

  # Verbose output
  %(prog)s --test-dir tests/integration --src-dir src -v
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "--test-dir",
        default="tests/integration",
        help="Integration test directory (default: tests/integration)"
    )
    parser.add_argument(
        "--src-dir",
        default="src",
        help="Source code directory (default: src)"
    )
    parser.add_argument(
        "--coverage-file",
        help="Path to coverage.xml file (optional)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--output",
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    try:
        # Run analysis
        analyzer = CoverageAnalyzer(args.test_dir, args.src_dir, args.verbose)
        report = analyzer.analyze()

        # Add coverage.xml data if available
        if args.coverage_file:
            coverage_data = parse_coverage_xml(Path(args.coverage_file))
            if coverage_data:
                report["code_coverage"] = coverage_data

        # Format output
        if args.json:
            output = json.dumps(report, indent=2)
        else:
            output = format_report_text(report)

        # Write output
        if args.output:
            Path(args.output).write_text(output)
            if not args.json:
                print(f"Report written to: {args.output}")
        else:
            print(output)

        # Exit code based on recommendations
        if report["recommendations"]:
            high_priority = any(r["priority"] == "high" for r in report["recommendations"])
            sys.exit(1 if high_priority else 0)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
