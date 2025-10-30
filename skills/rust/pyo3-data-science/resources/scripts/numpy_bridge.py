#!/usr/bin/env python3
"""
NumPy Bridge Utilities for PyO3 Data Science

Provides comprehensive NumPy array validation, conversion, creation, and benchmarking
utilities for PyO3 Rust-Python interop in data science applications.

Usage:
    numpy_bridge.py validate <array_spec> [options]
    numpy_bridge.py convert <input_format> <output_format> [options]
    numpy_bridge.py create <shape> <dtype> [options]
    numpy_bridge.py benchmark [options]

Examples:
    numpy_bridge.py validate "float64[1000,100]" --check-contiguous
    numpy_bridge.py convert list numpy --input "[1,2,3]"
    numpy_bridge.py create "1000,1000" float64 --fill random
    numpy_bridge.py benchmark --iterations 1000 --size 10000
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Literal

try:
    import numpy as np
    from numpy.typing import NDArray, DTypeLike
except ImportError:
    print("Error: NumPy is required. Install with: uv add numpy", file=sys.stderr)
    sys.exit(1)


class OutputFormat(Enum):
    """Supported output formats."""
    TEXT = "text"
    JSON = "json"
    PRETTY = "pretty"


class ArrayLayout(Enum):
    """Memory layout options for NumPy arrays."""
    C_CONTIGUOUS = "C"
    F_CONTIGUOUS = "F"
    ANY = "ANY"


class FillStrategy(Enum):
    """Array fill strategies."""
    ZEROS = "zeros"
    ONES = "ones"
    RANDOM = "random"
    ARANGE = "arange"
    LINSPACE = "linspace"


@dataclass
class ValidationResult:
    """Result of array validation."""
    valid: bool
    dtype: Optional[str] = None
    shape: Optional[Tuple[int, ...]] = None
    size: Optional[int] = None
    itemsize: Optional[int] = None
    nbytes: Optional[int] = None
    is_c_contiguous: Optional[bool] = None
    is_f_contiguous: Optional[bool] = None
    has_writeable_flag: Optional[bool] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ConversionResult:
    """Result of array conversion."""
    success: bool
    output_type: Optional[str] = None
    input_shape: Optional[Tuple[int, ...]] = None
    output_shape: Optional[Tuple[int, ...]] = None
    conversion_time_ms: Optional[float] = None
    memory_overhead_bytes: Optional[int] = None
    errors: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


@dataclass
class CreationResult:
    """Result of array creation."""
    success: bool
    shape: Optional[Tuple[int, ...]] = None
    dtype: Optional[str] = None
    size: Optional[int] = None
    nbytes: Optional[int] = None
    creation_time_ms: Optional[float] = None
    fill_strategy: Optional[str] = None
    errors: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


@dataclass
class BenchmarkResult:
    """Result of performance benchmark."""
    operation: str
    iterations: int
    array_size: int
    total_time_s: float
    mean_time_ms: float
    median_time_ms: float
    std_time_ms: float
    min_time_ms: float
    max_time_ms: float
    throughput_mb_s: float


class NumPyValidator:
    """Validates NumPy arrays for PyO3 compatibility."""

    SUPPORTED_DTYPES = {
        'bool', 'int8', 'int16', 'int32', 'int64',
        'uint8', 'uint16', 'uint32', 'uint64',
        'float32', 'float64', 'complex64', 'complex128'
    }

    def __init__(self) -> None:
        self.validation_count = 0
        self.error_count = 0

    def validate_array(
        self,
        array: NDArray[Any],
        expected_dtype: Optional[str] = None,
        expected_shape: Optional[Tuple[int, ...]] = None,
        expected_ndim: Optional[int] = None,
        check_contiguous: bool = False,
        check_writeable: bool = False
    ) -> ValidationResult:
        """
        Validate a NumPy array against specified criteria.

        Args:
            array: NumPy array to validate
            expected_dtype: Expected data type (if any)
            expected_shape: Expected shape (if any)
            expected_ndim: Expected number of dimensions (if any)
            check_contiguous: Whether to check for C-contiguous memory layout
            check_writeable: Whether to check if array is writeable

        Returns:
            ValidationResult with validation details
        """
        self.validation_count += 1
        result = ValidationResult(valid=True)

        # Basic array info
        result.dtype = str(array.dtype)
        result.shape = array.shape
        result.size = array.size
        result.itemsize = array.itemsize
        result.nbytes = array.nbytes
        result.is_c_contiguous = array.flags['C_CONTIGUOUS']
        result.is_f_contiguous = array.flags['F_CONTIGUOUS']
        result.has_writeable_flag = array.flags['WRITEABLE']

        # Validate dtype
        if expected_dtype:
            if str(array.dtype) != expected_dtype:
                result.errors.append(
                    f"dtype mismatch: expected {expected_dtype}, got {array.dtype}"
                )
                result.valid = False

        # Check if dtype is supported for PyO3
        dtype_str = str(array.dtype)
        if dtype_str not in self.SUPPORTED_DTYPES:
            result.warnings.append(
                f"dtype {dtype_str} may not be directly supported in PyO3"
            )

        # Validate shape
        if expected_shape:
            if array.shape != expected_shape:
                result.errors.append(
                    f"shape mismatch: expected {expected_shape}, got {array.shape}"
                )
                result.valid = False

        # Validate ndim
        if expected_ndim is not None:
            if array.ndim != expected_ndim:
                result.errors.append(
                    f"ndim mismatch: expected {expected_ndim}, got {array.ndim}"
                )
                result.valid = False

        # Check contiguous
        if check_contiguous and not result.is_c_contiguous:
            result.errors.append("array is not C-contiguous")
            result.valid = False

        # Check writeable
        if check_writeable and not result.has_writeable_flag:
            result.errors.append("array is not writeable")
            result.valid = False

        # Check for NaN or Inf in float arrays
        if np.issubdtype(array.dtype, np.floating):
            if np.any(np.isnan(array)):
                result.warnings.append("array contains NaN values")
            if np.any(np.isinf(array)):
                result.warnings.append("array contains Inf values")

        if not result.valid:
            self.error_count += 1

        return result

    def validate_dtype(self, dtype: DTypeLike) -> Tuple[bool, Optional[str]]:
        """
        Validate a dtype for PyO3 compatibility.

        Args:
            dtype: NumPy dtype to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            dtype_obj = np.dtype(dtype)
            dtype_str = str(dtype_obj)

            if dtype_str in self.SUPPORTED_DTYPES:
                return True, None
            else:
                return False, f"dtype {dtype_str} not in supported dtypes"

        except TypeError as e:
            return False, f"invalid dtype: {e}"

    def validate_shape(
        self,
        shape: Tuple[int, ...],
        max_ndim: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate array shape.

        Args:
            shape: Shape tuple to validate
            max_ndim: Maximum allowed dimensions (if any)
            max_size: Maximum allowed total size (if any)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not all(isinstance(d, int) and d > 0 for d in shape):
            return False, f"invalid shape: all dimensions must be positive integers"

        if max_ndim is not None and len(shape) > max_ndim:
            return False, f"too many dimensions: {len(shape)} > {max_ndim}"

        total_size = np.prod(shape)
        if max_size is not None and total_size > max_size:
            return False, f"array too large: {total_size} > {max_size}"

        return True, None


class NumPyConverter:
    """Converts between NumPy arrays and other formats."""

    def __init__(self) -> None:
        self.conversion_count = 0

    def list_to_numpy(
        self,
        data: List[Any],
        dtype: Optional[DTypeLike] = None
    ) -> ConversionResult:
        """Convert Python list to NumPy array."""
        start_time = time.perf_counter()
        result = ConversionResult(success=False)

        try:
            array = np.array(data, dtype=dtype)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.output_type = "numpy.ndarray"
            result.output_shape = array.shape
            result.conversion_time_ms = elapsed_ms
            result.memory_overhead_bytes = array.nbytes

            self.conversion_count += 1

        except Exception as e:
            result.errors.append(f"conversion failed: {e}")

        return result

    def numpy_to_list(self, array: NDArray[Any]) -> ConversionResult:
        """Convert NumPy array to Python list."""
        start_time = time.perf_counter()
        result = ConversionResult(success=False)

        try:
            result.input_shape = array.shape
            data_list = array.tolist()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.output_type = "list"
            result.conversion_time_ms = elapsed_ms

            # Estimate memory overhead (approximate)
            result.memory_overhead_bytes = sys.getsizeof(data_list)

            self.conversion_count += 1

        except Exception as e:
            result.errors.append(f"conversion failed: {e}")

        return result

    def bytes_to_numpy(
        self,
        data: bytes,
        dtype: DTypeLike,
        shape: Tuple[int, ...]
    ) -> ConversionResult:
        """Convert bytes to NumPy array."""
        start_time = time.perf_counter()
        result = ConversionResult(success=False)

        try:
            array = np.frombuffer(data, dtype=dtype).reshape(shape)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.output_type = "numpy.ndarray"
            result.output_shape = array.shape
            result.conversion_time_ms = elapsed_ms
            result.memory_overhead_bytes = array.nbytes

            self.conversion_count += 1

        except Exception as e:
            result.errors.append(f"conversion failed: {e}")

        return result

    def numpy_to_bytes(self, array: NDArray[Any]) -> ConversionResult:
        """Convert NumPy array to bytes."""
        start_time = time.perf_counter()
        result = ConversionResult(success=False)

        try:
            result.input_shape = array.shape
            data_bytes = array.tobytes()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.output_type = "bytes"
            result.conversion_time_ms = elapsed_ms
            result.memory_overhead_bytes = len(data_bytes)

            self.conversion_count += 1

        except Exception as e:
            result.errors.append(f"conversion failed: {e}")

        return result

    def ensure_contiguous(
        self,
        array: NDArray[Any],
        layout: ArrayLayout = ArrayLayout.C_CONTIGUOUS
    ) -> Tuple[NDArray[Any], bool]:
        """
        Ensure array has specified memory layout.

        Args:
            array: Input array
            layout: Desired memory layout

        Returns:
            Tuple of (converted_array, was_copied)
        """
        if layout == ArrayLayout.C_CONTIGUOUS:
            if array.flags['C_CONTIGUOUS']:
                return array, False
            return np.ascontiguousarray(array), True

        elif layout == ArrayLayout.F_CONTIGUOUS:
            if array.flags['F_CONTIGUOUS']:
                return array, False
            return np.asfortranarray(array), True

        else:
            return array, False


class NumPyCreator:
    """Creates NumPy arrays with various strategies."""

    def __init__(self) -> None:
        self.creation_count = 0

    def create_array(
        self,
        shape: Tuple[int, ...],
        dtype: DTypeLike,
        fill: FillStrategy = FillStrategy.ZEROS,
        **kwargs: Any
    ) -> CreationResult:
        """
        Create NumPy array with specified parameters.

        Args:
            shape: Array shape
            dtype: Array data type
            fill: Fill strategy
            **kwargs: Additional arguments for fill strategy

        Returns:
            CreationResult with creation details
        """
        start_time = time.perf_counter()
        result = CreationResult(success=False)

        try:
            if fill == FillStrategy.ZEROS:
                array = np.zeros(shape, dtype=dtype)

            elif fill == FillStrategy.ONES:
                array = np.ones(shape, dtype=dtype)

            elif fill == FillStrategy.RANDOM:
                if np.issubdtype(dtype, np.integer):
                    low = kwargs.get('low', 0)
                    high = kwargs.get('high', 100)
                    array = np.random.randint(low, high, size=shape, dtype=dtype)
                else:
                    array = np.random.random(shape).astype(dtype)

            elif fill == FillStrategy.ARANGE:
                start = kwargs.get('start', 0)
                total_size = np.prod(shape)
                array = np.arange(start, start + total_size, dtype=dtype).reshape(shape)

            elif fill == FillStrategy.LINSPACE:
                start = kwargs.get('start', 0)
                stop = kwargs.get('stop', 1)
                total_size = np.prod(shape)
                array = np.linspace(start, stop, total_size, dtype=dtype).reshape(shape)

            else:
                raise ValueError(f"unknown fill strategy: {fill}")

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.shape = array.shape
            result.dtype = str(array.dtype)
            result.size = array.size
            result.nbytes = array.nbytes
            result.creation_time_ms = elapsed_ms
            result.fill_strategy = fill.value

            self.creation_count += 1

        except Exception as e:
            result.errors.append(f"creation failed: {e}")

        return result


class NumPyBenchmark:
    """Benchmarks NumPy operations."""

    def __init__(self) -> None:
        self.results: List[BenchmarkResult] = []

    def benchmark_operation(
        self,
        operation: str,
        setup_fn: Any,
        op_fn: Any,
        iterations: int = 100,
        array_size: int = 10000
    ) -> BenchmarkResult:
        """
        Benchmark a NumPy operation.

        Args:
            operation: Operation name
            setup_fn: Function to set up test data
            op_fn: Operation function to benchmark
            iterations: Number of iterations
            array_size: Size of test arrays

        Returns:
            BenchmarkResult with timing statistics
        """
        times_ms: List[float] = []

        for _ in range(iterations):
            data = setup_fn(array_size)
            start = time.perf_counter()
            op_fn(data)
            elapsed = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed)

        times_array = np.array(times_ms)
        total_time_s = np.sum(times_array) / 1000

        # Calculate throughput
        bytes_per_op = array_size * 8  # Assume float64
        throughput_mb_s = (bytes_per_op * iterations) / (total_time_s * 1024 * 1024)

        result = BenchmarkResult(
            operation=operation,
            iterations=iterations,
            array_size=array_size,
            total_time_s=total_time_s,
            mean_time_ms=float(np.mean(times_array)),
            median_time_ms=float(np.median(times_array)),
            std_time_ms=float(np.std(times_array)),
            min_time_ms=float(np.min(times_array)),
            max_time_ms=float(np.max(times_array)),
            throughput_mb_s=throughput_mb_s
        )

        self.results.append(result)
        return result

    def run_standard_benchmarks(
        self,
        iterations: int = 100,
        size: int = 10000
    ) -> List[BenchmarkResult]:
        """Run standard NumPy operation benchmarks."""
        benchmarks = []

        # Array creation
        benchmarks.append(self.benchmark_operation(
            "create_zeros",
            lambda s: s,
            lambda s: np.zeros(s, dtype=np.float64),
            iterations,
            size
        ))

        benchmarks.append(self.benchmark_operation(
            "create_random",
            lambda s: s,
            lambda s: np.random.random(s),
            iterations,
            size
        ))

        # Array operations
        benchmarks.append(self.benchmark_operation(
            "array_sum",
            lambda s: np.random.random(s),
            lambda a: np.sum(a),
            iterations,
            size
        ))

        benchmarks.append(self.benchmark_operation(
            "array_mean",
            lambda s: np.random.random(s),
            lambda a: np.mean(a),
            iterations,
            size
        ))

        benchmarks.append(self.benchmark_operation(
            "array_std",
            lambda s: np.random.random(s),
            lambda a: np.std(a),
            iterations,
            size
        ))

        # Element-wise operations
        benchmarks.append(self.benchmark_operation(
            "element_multiply",
            lambda s: np.random.random(s),
            lambda a: a * 2.0,
            iterations,
            size
        ))

        benchmarks.append(self.benchmark_operation(
            "element_sqrt",
            lambda s: np.abs(np.random.random(s)),
            lambda a: np.sqrt(a),
            iterations,
            size
        ))

        # Copying
        benchmarks.append(self.benchmark_operation(
            "array_copy",
            lambda s: np.random.random(s),
            lambda a: np.copy(a),
            iterations,
            size
        ))

        return benchmarks


def format_output(data: Any, output_format: OutputFormat) -> str:
    """Format output based on specified format."""
    if output_format == OutputFormat.JSON:
        if hasattr(data, '__dict__'):
            return json.dumps(asdict(data), indent=2)
        return json.dumps(data, indent=2)

    elif output_format == OutputFormat.PRETTY:
        if isinstance(data, list):
            return "\n".join(format_output(item, OutputFormat.PRETTY) for item in data)

        if hasattr(data, '__dict__'):
            lines = [f"{data.__class__.__name__}:"]
            for key, value in asdict(data).items():
                if isinstance(value, list) and value:
                    lines.append(f"  {key}:")
                    for item in value:
                        lines.append(f"    - {item}")
                elif isinstance(value, dict):
                    lines.append(f"  {key}:")
                    for k, v in value.items():
                        lines.append(f"    {k}: {v}")
                else:
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)

        return str(data)

    else:  # TEXT
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)


def parse_shape(shape_str: str) -> Tuple[int, ...]:
    """Parse shape string like '1000,100' into tuple."""
    try:
        return tuple(int(x.strip()) for x in shape_str.split(','))
    except ValueError as e:
        raise ValueError(f"invalid shape format: {e}")


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute validate command."""
    validator = NumPyValidator()

    # Parse array spec (e.g., "float64[1000,100]")
    spec = args.array_spec
    if '[' in spec and ']' in spec:
        dtype_str, shape_str = spec.split('[')
        shape_str = shape_str.rstrip(']')
        dtype = dtype_str
        shape = parse_shape(shape_str)

        # Create test array
        array = np.zeros(shape, dtype=dtype)
    else:
        print(f"Error: invalid array spec format: {spec}", file=sys.stderr)
        print("Expected format: dtype[shape] (e.g., float64[1000,100])", file=sys.stderr)
        return 1

    # Validate
    result = validator.validate_array(
        array,
        check_contiguous=args.check_contiguous,
        check_writeable=args.check_writeable
    )

    # Output
    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.valid else 1


def cmd_convert(args: argparse.Namespace) -> int:
    """Execute convert command."""
    converter = NumPyConverter()

    input_format = args.input_format.lower()
    output_format = args.output_format.lower()

    result: Optional[ConversionResult] = None

    if input_format == "list" and output_format == "numpy":
        try:
            data = json.loads(args.input)
            result = converter.list_to_numpy(data, dtype=args.dtype)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON input: {e}", file=sys.stderr)
            return 1

    elif input_format == "numpy" and output_format == "list":
        print("Error: numpy to list conversion requires array from file", file=sys.stderr)
        return 1

    else:
        print(f"Error: unsupported conversion: {input_format} -> {output_format}", file=sys.stderr)
        return 1

    if result:
        print(format_output(result, OutputFormat(args.format)))
        return 0 if result.success else 1

    return 1


def cmd_create(args: argparse.Namespace) -> int:
    """Execute create command."""
    creator = NumPyCreator()

    shape = parse_shape(args.shape)
    dtype = args.dtype
    fill = FillStrategy(args.fill)

    kwargs = {}
    if args.low is not None:
        kwargs['low'] = args.low
    if args.high is not None:
        kwargs['high'] = args.high
    if args.start is not None:
        kwargs['start'] = args.start
    if args.stop is not None:
        kwargs['stop'] = args.stop

    result = creator.create_array(shape, dtype, fill, **kwargs)

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.success else 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Execute benchmark command."""
    benchmark = NumPyBenchmark()

    results = benchmark.run_standard_benchmarks(
        iterations=args.iterations,
        size=args.size
    )

    print(format_output(results, OutputFormat(args.format)))

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NumPy Bridge Utilities for PyO3 Data Science",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json', 'pretty'],
        default='pretty',
        help='output format (default: pretty)'
    )

    subparsers = parser.add_subparsers(dest='command', help='command to execute')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='validate array specification')
    validate_parser.add_argument('array_spec', help='array specification (e.g., float64[1000,100])')
    validate_parser.add_argument('--check-contiguous', action='store_true', help='check C-contiguous layout')
    validate_parser.add_argument('--check-writeable', action='store_true', help='check writeable flag')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='convert between formats')
    convert_parser.add_argument('input_format', choices=['list', 'numpy', 'bytes'], help='input format')
    convert_parser.add_argument('output_format', choices=['list', 'numpy', 'bytes'], help='output format')
    convert_parser.add_argument('--input', required=True, help='input data (JSON for list)')
    convert_parser.add_argument('--dtype', help='data type for numpy conversion')

    # Create command
    create_parser = subparsers.add_parser('create', help='create array')
    create_parser.add_argument('shape', help='array shape (e.g., 1000,100)')
    create_parser.add_argument('dtype', help='data type (e.g., float64)')
    create_parser.add_argument('--fill', choices=['zeros', 'ones', 'random', 'arange', 'linspace'],
                               default='zeros', help='fill strategy (default: zeros)')
    create_parser.add_argument('--low', type=int, help='low value for random integers')
    create_parser.add_argument('--high', type=int, help='high value for random integers')
    create_parser.add_argument('--start', type=float, help='start value for arange/linspace')
    create_parser.add_argument('--stop', type=float, help='stop value for linspace')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='run performance benchmarks')
    benchmark_parser.add_argument('--iterations', type=int, default=100, help='iterations per benchmark (default: 100)')
    benchmark_parser.add_argument('--size', type=int, default=10000, help='array size (default: 10000)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'validate':
            return cmd_validate(args)
        elif args.command == 'convert':
            return cmd_convert(args)
        elif args.command == 'create':
            return cmd_create(args)
        elif args.command == 'benchmark':
            return cmd_benchmark(args)
        else:
            print(f"Error: unknown command: {args.command}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.format == 'json':
            error_result = {"success": False, "error": str(e)}
            print(json.dumps(error_result, indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
