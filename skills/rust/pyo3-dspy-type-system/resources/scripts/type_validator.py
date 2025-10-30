#!/usr/bin/env python3
"""
Type Validator for PyO3-DSPy Type System

Validates type conversions between Python and Rust with comprehensive testing.
Tests type mapping correctness, Rust compilation, edge cases, and performance.

Usage:
    python type_validator.py validate types.rs
    python type_validator.py test-roundtrip --type "List[str]" --value '["a","b"]'
    python type_validator.py benchmark --iterations 1000
    python type_validator.py test-compilation types.rs
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re


class TypeValidator:
    """Validates type conversions between Python and Rust."""

    TYPE_MAPPINGS = {
        'str': 'String',
        'int': 'i64',
        'float': 'f64',
        'bool': 'bool',
        'List[str]': 'Vec<String>',
        'List[int]': 'Vec<i64>',
        'List[float]': 'Vec<f64>',
        'Dict[str, str]': 'HashMap<String, String>',
        'Dict[str, int]': 'HashMap<String, i64>',
        'Optional[str]': 'Option<String>',
        'Optional[int]': 'Option<i64>',
        'Optional[float]': 'Option<f64>',
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = []

    def log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"[{level}] {message}", file=sys.stderr)

    def validate_type_mapping(self, python_type: str) -> Dict[str, Any]:
        """Validate that a Python type has a correct Rust mapping."""
        self.log(f"Validating type mapping: {python_type}")

        result = {
            "python_type": python_type,
            "valid": False,
            "rust_type": None,
            "errors": []
        }

        if python_type not in self.TYPE_MAPPINGS:
            result["errors"].append(f"No mapping found for type: {python_type}")
            return result

        rust_type = self.TYPE_MAPPINGS[python_type]
        result["rust_type"] = rust_type
        result["valid"] = True

        self.log(f"  → {rust_type}")
        return result

    def test_roundtrip(self, python_type: str, value: Any) -> Dict[str, Any]:
        """Test round-trip conversion: Python → Rust → Python."""
        self.log(f"Testing round-trip: {python_type} with value {value}")

        result = {
            "python_type": python_type,
            "input_value": value,
            "output_value": None,
            "success": False,
            "errors": []
        }

        try:
            # Validate type mapping exists
            mapping = self.validate_type_mapping(python_type)
            if not mapping["valid"]:
                result["errors"].extend(mapping["errors"])
                return result

            # Simulate conversion (in real implementation, this would use PyO3)
            converted = self._simulate_conversion(python_type, value)
            result["output_value"] = converted

            # Validate round-trip preserves value
            if self._values_equal(value, converted):
                result["success"] = True
                self.log(f"  ✓ Round-trip successful")
            else:
                result["errors"].append(f"Value mismatch: {value} != {converted}")
                self.log(f"  ✗ Value mismatch", "ERROR")

        except Exception as e:
            result["errors"].append(str(e))
            self.log(f"  ✗ {e}", "ERROR")

        return result

    def _simulate_conversion(self, python_type: str, value: Any) -> Any:
        """Simulate type conversion through Rust (placeholder for PyO3 binding)."""
        # Type validation
        if python_type == 'str':
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value).__name__}")
            return value

        elif python_type == 'int':
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Expected int, got {type(value).__name__}")
            return value

        elif python_type == 'float':
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"Expected float, got {type(value).__name__}")
            return float(value)

        elif python_type == 'bool':
            if not isinstance(value, bool):
                raise TypeError(f"Expected bool, got {type(value).__name__}")
            return value

        elif python_type.startswith('List['):
            if not isinstance(value, list):
                raise TypeError(f"Expected list, got {type(value).__name__}")
            inner_type = python_type[5:-1]
            return [self._simulate_conversion(inner_type, v) for v in value]

        elif python_type.startswith('Dict['):
            if not isinstance(value, dict):
                raise TypeError(f"Expected dict, got {type(value).__name__}")
            # Extract key and value types
            match = re.match(r'Dict\[(\w+),\s*(\w+)\]', python_type)
            if not match:
                raise ValueError(f"Invalid Dict type: {python_type}")
            key_type, val_type = match.groups()
            return {
                self._simulate_conversion(key_type, k): self._simulate_conversion(val_type, v)
                for k, v in value.items()
            }

        elif python_type.startswith('Optional['):
            if value is None:
                return None
            inner_type = python_type[9:-1]
            return self._simulate_conversion(inner_type, value)

        else:
            raise ValueError(f"Unsupported type: {python_type}")

    def _values_equal(self, a: Any, b: Any) -> bool:
        """Check if two values are equal, handling different types appropriately."""
        if type(a) != type(b):
            return False

        if isinstance(a, (list, tuple)):
            return len(a) == len(b) and all(self._values_equal(x, y) for x, y in zip(a, b))

        if isinstance(a, dict):
            return (a.keys() == b.keys() and
                    all(self._values_equal(a[k], b[k]) for k in a.keys()))

        return a == b

    def test_edge_cases(self, python_type: str) -> List[Dict[str, Any]]:
        """Test edge cases for a given type."""
        self.log(f"Testing edge cases for: {python_type}")

        edge_cases = self._get_edge_cases(python_type)
        results = []

        for case_name, value in edge_cases:
            self.log(f"  Testing: {case_name}")
            result = self.test_roundtrip(python_type, value)
            result["case_name"] = case_name
            results.append(result)

        return results

    def _get_edge_cases(self, python_type: str) -> List[Tuple[str, Any]]:
        """Get edge case test values for a type."""
        if python_type == 'str':
            return [
                ("empty", ""),
                ("unicode", "Hello 世界 🚀"),
                ("long", "x" * 10000),
                ("special_chars", "\n\t\r\\\"'"),
            ]

        elif python_type == 'int':
            return [
                ("zero", 0),
                ("negative", -42),
                ("large", 2**62),
                ("small", -(2**62)),
            ]

        elif python_type == 'float':
            return [
                ("zero", 0.0),
                ("negative", -3.14),
                ("scientific", 1.23e-10),
                ("large", 1.79e308),
            ]

        elif python_type == 'bool':
            return [
                ("true", True),
                ("false", False),
            ]

        elif python_type == 'List[str]':
            return [
                ("empty", []),
                ("single", ["hello"]),
                ("multiple", ["a", "b", "c"]),
                ("duplicates", ["x", "x", "x"]),
            ]

        elif python_type == 'List[int]':
            return [
                ("empty", []),
                ("single", [42]),
                ("mixed_signs", [-1, 0, 1]),
                ("large", list(range(1000))),
            ]

        elif python_type == 'Dict[str, str]':
            return [
                ("empty", {}),
                ("single", {"key": "value"}),
                ("multiple", {"a": "1", "b": "2", "c": "3"}),
            ]

        elif python_type.startswith('Optional['):
            inner_type = python_type[9:-1]
            inner_cases = self._get_edge_cases(inner_type)
            return [("none", None)] + inner_cases

        return []

    def test_compilation(self, rust_file: Path) -> Dict[str, Any]:
        """Test that Rust code with generated types compiles."""
        self.log(f"Testing compilation: {rust_file}")

        result = {
            "file": str(rust_file),
            "compiles": False,
            "errors": [],
            "warnings": [],
            "duration": 0.0
        }

        if not rust_file.exists():
            result["errors"].append(f"File not found: {rust_file}")
            return result

        try:
            start_time = time.time()

            # Check if it's a Cargo project or standalone file
            if rust_file.name == "lib.rs" or rust_file.name == "main.rs":
                # Part of Cargo project
                project_dir = rust_file.parent
                while project_dir != project_dir.parent:
                    if (project_dir / "Cargo.toml").exists():
                        cmd = ["cargo", "check", "--message-format=json"]
                        proc = subprocess.run(
                            cmd,
                            cwd=project_dir,
                            capture_output=True,
                            text=True
                        )
                        break
                    project_dir = project_dir.parent
                else:
                    result["errors"].append("Not in a Cargo project")
                    return result
            else:
                # Standalone file - use rustc
                cmd = ["rustc", "--crate-type", "lib", str(rust_file), "--error-format=json"]
                proc = subprocess.run(cmd, capture_output=True, text=True)

            result["duration"] = time.time() - start_time

            # Parse output
            if proc.returncode == 0:
                result["compiles"] = True
                self.log(f"  ✓ Compilation successful ({result['duration']:.2f}s)")
            else:
                result["errors"].append(f"Compilation failed with code {proc.returncode}")

                # Parse JSON error messages
                for line in proc.stdout.splitlines():
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            if msg.get("reason") == "compiler-message":
                                level = msg["message"]["level"]
                                text = msg["message"]["message"]

                                if level == "error":
                                    result["errors"].append(text)
                                elif level == "warning":
                                    result["warnings"].append(text)
                        except json.JSONDecodeError:
                            pass

                self.log(f"  ✗ Compilation failed", "ERROR")

        except FileNotFoundError:
            result["errors"].append("Rust compiler not found (cargo/rustc)")
            self.log(f"  ✗ Compiler not found", "ERROR")
        except Exception as e:
            result["errors"].append(str(e))
            self.log(f"  ✗ {e}", "ERROR")

        return result

    def benchmark(self, iterations: int = 1000) -> Dict[str, Any]:
        """Benchmark type conversion performance."""
        self.log(f"Running benchmark with {iterations} iterations")

        results = {
            "iterations": iterations,
            "benchmarks": []
        }

        test_cases = [
            ("str", "hello world"),
            ("int", 42),
            ("List[str]", ["a", "b", "c", "d", "e"]),
            ("List[int]", list(range(100))),
            ("Dict[str, str]", {f"key{i}": f"val{i}" for i in range(10)}),
        ]

        for python_type, value in test_cases:
            self.log(f"  Benchmarking: {python_type}")

            start_time = time.time()
            for _ in range(iterations):
                self._simulate_conversion(python_type, value)
            duration = time.time() - start_time

            benchmark = {
                "type": python_type,
                "total_time": duration,
                "avg_time": duration / iterations,
                "ops_per_sec": iterations / duration
            }
            results["benchmarks"].append(benchmark)

            self.log(f"    {benchmark['ops_per_sec']:.0f} ops/sec")

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate type conversions between Python and Rust",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate types.rs
  %(prog)s test-roundtrip --type "List[str]" --value '["a","b"]'
  %(prog)s benchmark --iterations 1000
  %(prog)s test-compilation types.rs
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate type mappings')
    validate_parser.add_argument('file', type=Path, nargs='?',
                                 help='Rust file to validate (optional)')
    validate_parser.add_argument('--type', dest='type_name',
                                 help='Specific Python type to validate')

    # Test roundtrip command
    roundtrip_parser = subparsers.add_parser('test-roundtrip',
                                              help='Test round-trip conversion')
    roundtrip_parser.add_argument('--type', dest='type_name', required=True,
                                   help='Python type to test')
    roundtrip_parser.add_argument('--value', required=True,
                                   help='JSON value to test')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark',
                                             help='Benchmark type conversions')
    benchmark_parser.add_argument('--iterations', type=int, default=1000,
                                  help='Number of iterations (default: 1000)')

    # Test compilation command
    compile_parser = subparsers.add_parser('test-compilation',
                                           help='Test Rust code compilation')
    compile_parser.add_argument('file', type=Path,
                                help='Rust file to compile')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    validator = TypeValidator(verbose=args.verbose)
    output = {}

    try:
        if args.command == 'validate':
            if args.type_name:
                result = validator.validate_type_mapping(args.type_name)
                output = result
            else:
                # Validate all known types
                output["validations"] = [
                    validator.validate_type_mapping(t)
                    for t in validator.TYPE_MAPPINGS.keys()
                ]

                if args.file:
                    compile_result = validator.test_compilation(args.file)
                    output["compilation"] = compile_result

        elif args.command == 'test-roundtrip':
            try:
                value = json.loads(args.value)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON value: {e}", file=sys.stderr)
                return 1

            result = validator.test_roundtrip(args.type_name, value)

            # Also test edge cases
            edge_results = validator.test_edge_cases(args.type_name)

            output = {
                "roundtrip": result,
                "edge_cases": edge_results
            }

        elif args.command == 'benchmark':
            output = validator.benchmark(args.iterations)

        elif args.command == 'test-compilation':
            output = validator.test_compilation(args.file)

        # Output results
        if args.json:
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            if args.command == 'validate':
                if args.type_name:
                    if output["valid"]:
                        print(f"✓ {output['python_type']} → {output['rust_type']}")
                    else:
                        print(f"✗ {output['python_type']}: {', '.join(output['errors'])}")
                        return 1
                else:
                    total = len(output.get("validations", []))
                    valid = sum(1 for v in output.get("validations", []) if v["valid"])
                    print(f"Validated {valid}/{total} type mappings")

                    if "compilation" in output:
                        comp = output["compilation"]
                        if comp["compiles"]:
                            print(f"✓ Compilation successful ({comp['duration']:.2f}s)")
                        else:
                            print(f"✗ Compilation failed")
                            return 1

            elif args.command == 'test-roundtrip':
                rt = output["roundtrip"]
                if rt["success"]:
                    print(f"✓ Round-trip successful: {rt['python_type']}")
                else:
                    print(f"✗ Round-trip failed: {', '.join(rt['errors'])}")
                    return 1

                # Show edge case results
                edge_success = sum(1 for e in output["edge_cases"] if e["success"])
                edge_total = len(output["edge_cases"])
                print(f"Edge cases: {edge_success}/{edge_total} passed")

            elif args.command == 'benchmark':
                print(f"Benchmark results ({output['iterations']} iterations):")
                for b in output["benchmarks"]:
                    print(f"  {b['type']:20s} {b['ops_per_sec']:>12,.0f} ops/sec")

            elif args.command == 'test-compilation':
                if output["compiles"]:
                    print(f"✓ Compilation successful ({output['duration']:.2f}s)")
                else:
                    print(f"✗ Compilation failed:")
                    for err in output["errors"]:
                        print(f"  {err}")
                    return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
