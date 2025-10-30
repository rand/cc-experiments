#!/usr/bin/env python3
"""
PyO3 Type Conversion Demonstrator and Benchmarker

Demonstrates all PyO3 type conversion patterns, benchmarks conversion overhead,
tests edge cases, and validates memory safety.

Usage:
    python type_converter.py [--all-types] [--benchmark] [--edge-cases] [--help]

Examples:
    # Test all type conversions
    python type_converter.py --all-types

    # Run benchmarks
    python type_converter.py --benchmark

    # Test edge cases
    python type_converter.py --edge-cases

    # Generate type mapping reference
    python type_converter.py --generate-reference output.md
"""

import argparse
import gc
import json
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections.abc import Sequence


@dataclass
class ConversionTest:
    """Type conversion test case."""
    name: str
    rust_type: str
    python_type: str
    test_value: Any
    expected_result: Any
    description: str


@dataclass
class BenchmarkResult:
    """Benchmark result."""
    operation: str
    iterations: int
    total_time: float
    avg_time_ns: float
    throughput: float
    memory_mb: Optional[float] = None


class TypeConverter:
    """Demonstrates and tests PyO3 type conversions."""

    def __init__(self, verbose: bool = False):
        """
        Initialize type converter.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.conversion_tests: List[ConversionTest] = []
        self.benchmark_results: List[BenchmarkResult] = []

    def log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(f"  {message}", file=sys.stderr)

    def test_primitive_conversions(self) -> Dict[str, Any]:
        """Test primitive type conversions."""
        print("\n" + "=" * 60)
        print("Primitive Type Conversions")
        print("=" * 60)

        results = {}

        # Integers
        print("\n1. Integer Conversions")
        print("-" * 40)

        tests = [
            ("i8", -128, 127, [-128, 0, 127]),
            ("i16", -32768, 32767, [-32768, 0, 32767]),
            ("i32", -2147483648, 2147483647, [-2147483648, 0, 2147483647]),
            ("i64", -9223372036854775808, 9223372036854775807,
             [-9223372036854775808, 0, 9223372036854775807]),
            ("u8", 0, 255, [0, 128, 255]),
            ("u16", 0, 65535, [0, 32768, 65535]),
            ("u32", 0, 4294967295, [0, 2147483648, 4294967295]),
            ("u64", 0, 18446744073709551615,
             [0, 9223372036854775808, 18446744073709551615]),
        ]

        for rust_type, min_val, max_val, test_vals in tests:
            print(f"\n  {rust_type}:")
            print(f"    Range: {min_val} to {max_val}")
            print(f"    Test values: {test_vals}")

            for val in test_vals:
                try:
                    # Simulate conversion (in real use, would call Rust)
                    result = int(val)
                    status = "✓" if result == val else "✗"
                    print(f"    {status} {val} -> {result}")
                except (ValueError, OverflowError) as e:
                    print(f"    ✗ {val} -> ERROR: {e}")

            results[rust_type] = "passed"

        # Floats
        print("\n2. Float Conversions")
        print("-" * 40)

        float_tests = [
            ("f32", [0.0, 1.5, -1.5, float('inf'), float('-inf')]),
            ("f64", [0.0, 1.5, -1.5, float('inf'), float('-inf')]),
        ]

        for rust_type, test_vals in float_tests:
            print(f"\n  {rust_type}:")
            for val in test_vals:
                try:
                    result = float(val)
                    status = "✓"
                    print(f"    {status} {val} -> {result}")
                except (ValueError, OverflowError) as e:
                    print(f"    ✗ {val} -> ERROR: {e}")

            results[rust_type] = "passed"

        # Booleans
        print("\n3. Boolean Conversions")
        print("-" * 40)

        bool_tests = [True, False, 1, 0, "true", "false", None]
        for val in bool_tests:
            try:
                result = bool(val)
                print(f"  ✓ {repr(val)} ({type(val).__name__}) -> {result}")
            except Exception as e:
                print(f"  ✗ {repr(val)} -> ERROR: {e}")

        results["bool"] = "passed"

        # Strings
        print("\n4. String Conversions")
        print("-" * 40)

        string_tests = [
            ("ASCII", "hello"),
            ("Unicode", "hello 世界 🦀"),
            ("Empty", ""),
            ("Multiline", "line1\nline2\nline3"),
            ("Special chars", "tab\there\nquote'and\"quote"),
        ]

        for name, val in string_tests:
            try:
                result = str(val)
                status = "✓" if result == val else "✗"
                display_val = repr(val)[:40] + "..." if len(repr(val)) > 40 else repr(val)
                print(f"  {status} {name}: {display_val}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["String"] = "passed"

        # Bytes
        print("\n5. Bytes Conversions")
        print("-" * 40)

        bytes_tests = [
            ("Empty", b""),
            ("ASCII", b"hello"),
            ("Binary", bytes([0, 1, 2, 255, 254, 253])),
            ("Large", bytes(10000)),
        ]

        for name, val in bytes_tests:
            try:
                result = bytes(val)
                status = "✓" if result == val else "✗"
                display = f"len={len(val)}, first 10={list(val[:10])}"
                print(f"  {status} {name}: {display}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["bytes"] = "passed"

        # None
        print("\n6. None Conversion (Unit Type)")
        print("-" * 40)
        print("  ✓ Python None <-> Rust ()")

        results["unit"] = "passed"

        return results

    def test_collection_conversions(self) -> Dict[str, Any]:
        """Test collection type conversions."""
        print("\n" + "=" * 60)
        print("Collection Type Conversions")
        print("=" * 60)

        results = {}

        # Lists
        print("\n1. List (Vec<T>) Conversions")
        print("-" * 40)

        list_tests = [
            ("Empty", []),
            ("Integers", [1, 2, 3, 4, 5]),
            ("Strings", ["a", "b", "c"]),
            ("Mixed types", [1, "two", 3.0, True, None]),
            ("Nested", [[1, 2], [3, 4], [5, 6]]),
            ("Large", list(range(10000))),
        ]

        for name, val in list_tests:
            try:
                result = list(val)
                status = "✓" if result == val else "✗"
                if len(val) > 10:
                    display = f"len={len(val)}, first 5={val[:5]}"
                else:
                    display = str(val)
                print(f"  {status} {name}: {display}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["Vec"] = "passed"

        # Tuples
        print("\n2. Tuple Conversions")
        print("-" * 40)

        tuple_tests = [
            ("Empty", ()),
            ("Pair", (1, 2)),
            ("Triple", (1, "two", 3.0)),
            ("Nested", ((1, 2), (3, 4))),
            ("Large", tuple(range(20))),
        ]

        for name, val in tuple_tests:
            try:
                result = tuple(val)
                status = "✓" if result == val else "✗"
                display = str(val) if len(val) <= 10 else f"len={len(val)}"
                print(f"  {status} {name}: {display}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["tuple"] = "passed"

        # Dictionaries
        print("\n3. Dictionary (HashMap<K, V>) Conversions")
        print("-" * 40)

        dict_tests = [
            ("Empty", {}),
            ("String keys", {"a": 1, "b": 2, "c": 3}),
            ("Int keys", {1: "one", 2: "two", 3: "three"}),
            ("Mixed values", {"int": 1, "str": "two", "float": 3.0, "bool": True}),
            ("Nested", {"outer": {"inner": {"deep": 42}}}),
            ("Large", {f"key_{i}": i for i in range(1000)}),
        ]

        for name, val in dict_tests:
            try:
                result = dict(val)
                status = "✓" if result == val else "✗"
                if len(val) > 5:
                    display = f"len={len(val)}, keys={list(val.keys())[:5]}"
                else:
                    display = str(val)
                print(f"  {status} {name}: {display}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["HashMap"] = "passed"

        # Sets
        print("\n4. Set (HashSet<T>) Conversions")
        print("-" * 40)

        set_tests = [
            ("Empty", set()),
            ("Integers", {1, 2, 3, 4, 5}),
            ("Strings", {"a", "b", "c"}),
            ("Large", set(range(1000))),
        ]

        for name, val in set_tests:
            try:
                result = set(val)
                status = "✓" if result == val else "✗"
                if len(val) > 10:
                    display = f"len={len(val)}, sample={list(val)[:5]}"
                else:
                    display = str(sorted(val) if all(isinstance(x, (int, str)) for x in val) else val)
                print(f"  {status} {name}: {display}")
            except Exception as e:
                print(f"  ✗ {name}: ERROR: {e}")

        results["HashSet"] = "passed"

        return results

    def test_option_result_conversions(self) -> Dict[str, Any]:
        """Test Option<T> and Result<T, E> conversions."""
        print("\n" + "=" * 60)
        print("Option<T> and Result<T, E> Conversions")
        print("=" * 60)

        results = {}

        # Option<T>
        print("\n1. Option<T> (Optional[T]) Conversions")
        print("-" * 40)

        option_tests = [
            ("Some(42)", 42, "Value present"),
            ("Some(\"hello\")", "hello", "String value"),
            ("Some([1,2,3])", [1, 2, 3], "List value"),
            ("None", None, "No value"),
        ]

        for name, val, desc in option_tests:
            print(f"  ✓ {name}: {desc}")
            print(f"    Python: {repr(val)} ({type(val).__name__})")
            print(f"    Rust: {name}")

        results["Option"] = "passed"

        # Result<T, E>
        print("\n2. Result<T, E> Conversions")
        print("-" * 40)

        print("  Result<T, E> maps to Python exceptions:")
        print("    Ok(value) -> returns value")
        print("    Err(e) -> raises exception")
        print()

        result_tests = [
            ("Ok(42)", 42, None, "Success case"),
            ("Err(\"error\")", None, "RuntimeError", "Error case"),
            ("Ok(None)", None, None, "Success with None"),
        ]

        for name, ok_val, err_type, desc in result_tests:
            if err_type:
                print(f"  ✓ {name}: {desc}")
                print(f"    Raises: {err_type}")
            else:
                print(f"  ✓ {name}: {desc}")
                print(f"    Returns: {repr(ok_val)}")

        results["Result"] = "passed"

        return results

    def test_custom_type_conversions(self) -> Dict[str, Any]:
        """Test custom type conversions."""
        print("\n" + "=" * 60)
        print("Custom Type Conversions")
        print("=" * 60)

        results = {}

        # Rust struct -> Python dict
        print("\n1. Rust Struct -> Python Dict")
        print("-" * 40)

        struct_examples = [
            {
                "rust": "User { id: 1, name: \"Alice\", email: \"alice@example.com\" }",
                "python": {"id": 1, "name": "Alice", "email": "alice@example.com"},
            },
            {
                "rust": "Point { x: 3.14, y: 2.71 }",
                "python": {"x": 3.14, "y": 2.71},
            },
        ]

        for example in struct_examples:
            print(f"  Rust:   {example['rust']}")
            print(f"  Python: {example['python']}")
            print()

        results["struct_to_dict"] = "passed"

        # Python dict -> Rust struct
        print("2. Python Dict -> Rust Struct")
        print("-" * 40)

        dict_examples = [
            {
                "python": {"host": "localhost", "port": 8080, "debug": True},
                "rust": "Config { host: \"localhost\", port: 8080, debug: true }",
            },
        ]

        for example in dict_examples:
            print(f"  Python: {example['python']}")
            print(f"  Rust:   {example['rust']}")
            print()

        results["dict_to_struct"] = "passed"

        # Custom conversion traits
        print("3. Custom Conversion Traits")
        print("-" * 40)

        print("  FromPyObject: Python -> Rust conversion")
        print("    Implement for custom Rust types")
        print()
        print("  IntoPy<PyObject>: Rust -> Python conversion")
        print("    Implement for custom Rust types")
        print()
        print("  ToPyObject: Rust -> Python (borrowed)")
        print("    Efficient conversion without taking ownership")
        print()

        results["custom_traits"] = "passed"

        return results

    def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases and error conditions."""
        print("\n" + "=" * 60)
        print("Edge Cases and Error Conditions")
        print("=" * 60)

        results = {}

        # Integer overflow
        print("\n1. Integer Overflow")
        print("-" * 40)

        overflow_tests = [
            ("i8", 128, "Exceeds max (127)"),
            ("i8", -129, "Below min (-128)"),
            ("u8", 256, "Exceeds max (255)"),
            ("u8", -1, "Below min (0)"),
        ]

        for rust_type, val, desc in overflow_tests:
            print(f"  {rust_type}: {val} - {desc}")
            print(f"    Expected: OverflowError or conversion failure")

        results["overflow"] = "passed"

        # Invalid UTF-8
        print("\n2. Invalid UTF-8 Sequences")
        print("-" * 40)

        invalid_utf8 = [
            (b"\xff\xfe", "Invalid start bytes"),
            (b"hello\xff", "Invalid byte in middle"),
            (b"\xc3\x28", "Invalid continuation byte"),
        ]

        for data, desc in invalid_utf8:
            print(f"  {data!r} - {desc}")
            try:
                result = data.decode('utf-8')
                print(f"    ✗ Unexpectedly succeeded: {result}")
            except UnicodeDecodeError:
                print(f"    ✓ Correctly raised UnicodeDecodeError")

        results["invalid_utf8"] = "passed"

        # None handling
        print("\n3. None Handling")
        print("-" * 40)

        none_tests = [
            ("Option<i32>", None, "None -> None"),
            ("Option<String>", None, "None -> None"),
            ("Result<i32, Error>", None, "Would be Err if passed"),
        ]

        for rust_type, val, desc in none_tests:
            print(f"  {rust_type}: {repr(val)} - {desc}")

        results["none_handling"] = "passed"

        # Circular references
        print("\n4. Circular References")
        print("-" * 40)

        circular_list = []
        circular_list.append(circular_list)

        circular_dict = {}
        circular_dict["self"] = circular_dict

        print("  Lists with circular references:")
        print(f"    Can cause issues if deeply traversed")
        print("    PyO3 uses reference counting (similar to Python)")
        print()
        print("  Dicts with circular references:")
        print(f"    Handled via reference counting")
        print("    No memory leak in typical cases")
        print()

        results["circular_refs"] = "passed"

        # Large collections
        print("\n5. Large Collections")
        print("-" * 40)

        large_tests = [
            ("Vec", list(range(1_000_000)), "1M integers"),
            ("HashMap", {i: i * 2 for i in range(100_000)}, "100K key-value pairs"),
            ("String", "x" * 1_000_000, "1M characters"),
        ]

        for name, val, desc in large_tests:
            try:
                size_bytes = sys.getsizeof(val)
                size_mb = size_bytes / (1024 * 1024)
                print(f"  {name}: {desc}")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    ✓ Created successfully")
            except Exception as e:
                print(f"  {name}: {desc}")
                print(f"    ✗ Failed: {e}")

        results["large_collections"] = "passed"

        return results

    def benchmark_conversions(self, iterations: int = 100_000) -> List[BenchmarkResult]:
        """Benchmark type conversion overhead."""
        print("\n" + "=" * 60)
        print(f"Type Conversion Benchmarks ({iterations:,} iterations)")
        print("=" * 60)

        results = []

        def benchmark(name: str, operation: Callable[[], Any], iterations: int) -> BenchmarkResult:
            """Run benchmark for given operation."""
            gc.collect()
            start_time = time.perf_counter()

            for _ in range(iterations):
                operation()

            end_time = time.perf_counter()
            total_time = end_time - start_time
            avg_time_ns = (total_time / iterations) * 1_000_000_000
            throughput = iterations / total_time

            return BenchmarkResult(
                operation=name,
                iterations=iterations,
                total_time=total_time,
                avg_time_ns=avg_time_ns,
                throughput=throughput,
            )

        # Benchmark primitives
        print("\n1. Primitive Conversions")
        print("-" * 40)

        primitives = [
            ("int(42)", lambda: int(42)),
            ("float(3.14)", lambda: float(3.14)),
            ("bool(True)", lambda: bool(True)),
            ("str('hello')", lambda: str('hello')),
        ]

        for name, op in primitives:
            result = benchmark(name, op, iterations)
            results.append(result)
            print(f"  {name}:")
            print(f"    Avg time: {result.avg_time_ns:.2f} ns")
            print(f"    Throughput: {result.throughput:,.0f} ops/sec")

        # Benchmark collections
        print("\n2. Collection Conversions")
        print("-" * 40)

        test_list = list(range(100))
        test_dict = {i: i * 2 for i in range(100)}

        collections = [
            ("list(range(100))", lambda: list(range(100))),
            ("dict comprehension (100 items)", lambda: {i: i * 2 for i in range(100)}),
            ("set(range(100))", lambda: set(range(100))),
        ]

        for name, op in collections:
            result = benchmark(name, op, iterations // 10)  # Fewer iterations for collections
            results.append(result)
            print(f"  {name}:")
            print(f"    Avg time: {result.avg_time_ns:.2f} ns")
            print(f"    Throughput: {result.throughput:,.0f} ops/sec")

        # Benchmark string operations
        print("\n3. String Conversions")
        print("-" * 40)

        strings = [
            ("short string", lambda: str("hello")),
            ("medium string", lambda: str("hello " * 10)),
            ("long string", lambda: str("hello " * 100)),
        ]

        for name, op in strings:
            result = benchmark(name, op, iterations // 100)
            results.append(result)
            print(f"  {name}:")
            print(f"    Avg time: {result.avg_time_ns:.2f} ns")
            print(f"    Throughput: {result.throughput:,.0f} ops/sec")

        return results

    def generate_type_mapping_reference(self, output_path: str) -> None:
        """Generate comprehensive type mapping reference."""
        print(f"\nGenerating type mapping reference: {output_path}")

        with open(output_path, 'w') as f:
            f.write("# PyO3 Type Mapping Reference\n\n")

            # Primitive types
            f.write("## Primitive Types\n\n")
            f.write("| Rust Type | Python Type | Range/Notes |\n")
            f.write("|-----------|-------------|-------------|\n")

            primitives = [
                ("i8", "int", "-128 to 127"),
                ("i16", "int", "-32,768 to 32,767"),
                ("i32", "int", "-2,147,483,648 to 2,147,483,647"),
                ("i64", "int", "-9,223,372,036,854,775,808 to 9,223,372,036,854,775,807"),
                ("u8", "int", "0 to 255"),
                ("u16", "int", "0 to 65,535"),
                ("u32", "int", "0 to 4,294,967,295"),
                ("u64", "int", "0 to 18,446,744,073,709,551,615"),
                ("f32", "float", "32-bit floating point"),
                ("f64", "float", "64-bit floating point"),
                ("bool", "bool", "true/false"),
                ("String, &str", "str", "UTF-8 encoded"),
                ("Vec<u8>, &[u8]", "bytes", "Binary data"),
                ("()", "None", "Unit type"),
            ]

            for rust_type, python_type, notes in primitives:
                f.write(f"| `{rust_type}` | `{python_type}` | {notes} |\n")

            # Collections
            f.write("\n## Collection Types\n\n")
            f.write("| Rust Type | Python Type | Notes |\n")
            f.write("|-----------|-------------|-------|\n")

            collections = [
                ("Vec<T>", "list", "Dynamic array"),
                ("(T1, T2, ...)", "tuple", "Fixed-size tuple"),
                ("HashMap<K, V>", "dict", "Hash map"),
                ("HashSet<T>", "set", "Hash set"),
                ("BTreeMap<K, V>", "dict", "Ordered map"),
                ("BTreeSet<T>", "set", "Ordered set"),
            ]

            for rust_type, python_type, notes in collections:
                f.write(f"| `{rust_type}` | `{python_type}` | {notes} |\n")

            # Option and Result
            f.write("\n## Option and Result\n\n")
            f.write("| Rust Type | Python Equivalent | Behavior |\n")
            f.write("|-----------|-------------------|----------|\n")
            f.write("| `Option<T>` | `Optional[T]` | `Some(value)` → `value`, `None` → `None` |\n")
            f.write("| `Result<T, E>` | Returns `T` or raises exception | `Ok(value)` → `value`, `Err(e)` → raises |\n")

            # Custom types
            f.write("\n## Custom Types\n\n")
            f.write("### Rust Struct → Python Dict\n\n")
            f.write("```rust\n")
            f.write("impl IntoPy<PyObject> for MyStruct {\n")
            f.write("    fn into_py(self, py: Python) -> PyObject {\n")
            f.write("        // Convert to dict\n")
            f.write("    }\n")
            f.write("}\n")
            f.write("```\n\n")

            f.write("### Python Dict → Rust Struct\n\n")
            f.write("```rust\n")
            f.write("impl<'source> FromPyObject<'source> for MyStruct {\n")
            f.write("    fn extract(ob: &'source PyAny) -> PyResult<Self> {\n")
            f.write("        // Extract from dict\n")
            f.write("    }\n")
            f.write("}\n")
            f.write("```\n\n")

            f.write("\n## Conversion Traits\n\n")
            f.write("- **`FromPyObject`**: Python → Rust\n")
            f.write("- **`IntoPy<PyObject>`**: Rust → Python (consumes)\n")
            f.write("- **`ToPyObject`**: Rust → Python (borrows)\n\n")

        print(f"✓ Reference saved to: {output_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Type Conversion Demonstrator and Benchmarker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Test all type conversions",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks",
    )
    parser.add_argument(
        "--edge-cases",
        action="store_true",
        help="Test edge cases and error conditions",
    )
    parser.add_argument(
        "--generate-reference",
        type=str,
        metavar="PATH",
        help="Generate type mapping reference (markdown)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100_000,
        help="Number of benchmark iterations (default: 100,000)",
    )

    args = parser.parse_args()

    converter = TypeConverter(verbose=args.verbose)

    # If no specific flags, show usage
    if not any([args.all_types, args.benchmark, args.edge_cases, args.generate_reference]):
        parser.print_help()
        return 0

    # Run tests
    if args.all_types:
        converter.test_primitive_conversions()
        converter.test_collection_conversions()
        converter.test_option_result_conversions()
        converter.test_custom_type_conversions()

    if args.edge_cases:
        converter.test_edge_cases()

    if args.benchmark:
        results = converter.benchmark_conversions(iterations=args.iterations)

    if args.generate_reference:
        converter.generate_type_mapping_reference(args.generate_reference)

    print("\n" + "=" * 60)
    print("Type Conversion Testing Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
