#!/usr/bin/env python3
"""
PyO3 Numpy Array Validator

Validates numpy arrays for PyO3 compatibility. Checks array layout, dtypes,
memory alignment, dimensions, ownership, and provides comprehensive validation
reports for safe Rust-Python interop.

Features:
- Validate array compatibility with PyO3
- Check array layout (C-contiguous, F-contiguous, strided)
- Validate dtypes against Rust types
- Check memory alignment requirements
- Validate dimensions and shape
- Check for memory ownership and views
- Detect common issues (non-contiguous, byte order, etc.)
- Generate detailed validation reports
- Performance impact analysis

Usage:
    # Validate array compatibility
    numpy_validator.py validate array.npy --verbose

    # Check specific requirements
    numpy_validator.py check array.npy --layout c --dtype float64

    # Validate directory of arrays
    numpy_validator.py batch /path/to/arrays --output report.json

    # Generate compatibility report
    numpy_validator.py report array.npy --format html

    # Test conversion overhead
    numpy_validator.py benchmark array.npy --iterations 1000

Examples:
    # Validate single array
    python numpy_validator.py validate data.npy --verbose

    # Batch validation
    python numpy_validator.py batch ./arrays --recursive --json

    # Check layout compatibility
    python numpy_validator.py check data.npy --layout c --strict

    # Performance test
    python numpy_validator.py benchmark data.npy --compare

    # Generate report
    python numpy_validator.py report data.npy --format markdown

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import json
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import numpy as np
import warnings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ArrayLayout(Enum):
    """Array memory layout types."""
    C_CONTIGUOUS = "c_contiguous"
    F_CONTIGUOUS = "f_contiguous"
    CONTIGUOUS = "contiguous"  # Either C or F
    STRIDED = "strided"
    NON_CONTIGUOUS = "non_contiguous"


class DTypeCompatibility(Enum):
    """Numpy dtype compatibility with Rust."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    NEEDS_CONVERSION = "needs_conversion"


@dataclass
class ValidationIssue:
    """Single validation issue."""
    level: ValidationLevel
    category: str
    message: str
    details: str = ""
    fix_suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'level': self.level.value,
            'category': self.category,
            'message': self.message,
            'details': self.details,
            'fix_suggestion': self.fix_suggestion
        }


@dataclass
class ArrayInfo:
    """Comprehensive array information."""
    shape: Tuple[int, ...]
    dtype: str
    size: int
    ndim: int
    itemsize: int
    nbytes: int
    layout: ArrayLayout
    c_contiguous: bool
    f_contiguous: bool
    is_view: bool
    is_writeable: bool
    is_aligned: bool
    byte_order: str
    strides: Tuple[int, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['layout'] = self.layout.value
        return data


@dataclass
class ValidationResult:
    """Complete validation result."""
    array_info: ArrayInfo
    compatible: bool
    issues: List[ValidationIssue]
    dtype_compatibility: DTypeCompatibility
    layout_compatible: bool
    zero_copy_possible: bool
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'array_info': self.array_info.to_dict(),
            'compatible': self.compatible,
            'issues': [i.to_dict() for i in self.issues],
            'dtype_compatibility': self.dtype_compatibility.value,
            'layout_compatible': self.layout_compatible,
            'zero_copy_possible': self.zero_copy_possible,
            'recommendations': self.recommendations
        }


class DTypeMapper:
    """Maps numpy dtypes to Rust types."""

    # Numpy -> Rust type mapping
    DTYPE_MAP = {
        'bool': 'bool',
        'int8': 'i8',
        'int16': 'i16',
        'int32': 'i32',
        'int64': 'i64',
        'uint8': 'u8',
        'uint16': 'u16',
        'uint32': 'u32',
        'uint64': 'u64',
        'float32': 'f32',
        'float64': 'f64',
        'complex64': 'Complex<f32>',
        'complex128': 'Complex<f64>',
    }

    @classmethod
    def to_rust_type(cls, dtype: np.dtype) -> Optional[str]:
        """Convert numpy dtype to Rust type."""
        dtype_str = str(dtype)
        return cls.DTYPE_MAP.get(dtype_str)

    @classmethod
    def is_compatible(cls, dtype: np.dtype) -> DTypeCompatibility:
        """Check if dtype is compatible with PyO3."""
        rust_type = cls.to_rust_type(dtype)

        if rust_type:
            return DTypeCompatibility.COMPATIBLE
        elif dtype.kind in ['O', 'U', 'S']:  # Object, Unicode, String
            return DTypeCompatibility.INCOMPATIBLE
        else:
            return DTypeCompatibility.NEEDS_CONVERSION


class ArrayAnalyzer:
    """Analyzes numpy arrays."""

    @staticmethod
    def analyze(array: np.ndarray) -> ArrayInfo:
        """Analyze array and return comprehensive information."""
        # Determine layout
        if array.flags.c_contiguous and array.flags.f_contiguous:
            # Degenerate case (1D or scalar)
            layout = ArrayLayout.C_CONTIGUOUS
        elif array.flags.c_contiguous:
            layout = ArrayLayout.C_CONTIGUOUS
        elif array.flags.f_contiguous:
            layout = ArrayLayout.F_CONTIGUOUS
        elif array.flags.contiguous:
            layout = ArrayLayout.CONTIGUOUS
        else:
            # Check if it's strided but regular
            if ArrayAnalyzer._is_strided_regular(array):
                layout = ArrayLayout.STRIDED
            else:
                layout = ArrayLayout.NON_CONTIGUOUS

        # Determine byte order
        byte_order = array.dtype.byteorder
        if byte_order == '=':
            byte_order = 'native'
        elif byte_order == '<':
            byte_order = 'little'
        elif byte_order == '>':
            byte_order = 'big'

        return ArrayInfo(
            shape=array.shape,
            dtype=str(array.dtype),
            size=array.size,
            ndim=array.ndim,
            itemsize=array.itemsize,
            nbytes=array.nbytes,
            layout=layout,
            c_contiguous=array.flags.c_contiguous,
            f_contiguous=array.flags.f_contiguous,
            is_view=not array.flags.owndata,
            is_writeable=array.flags.writeable,
            is_aligned=array.flags.aligned,
            byte_order=byte_order,
            strides=array.strides
        )

    @staticmethod
    def _is_strided_regular(array: np.ndarray) -> bool:
        """Check if array has regular strides."""
        if array.ndim == 0:
            return True

        # Check if strides follow a regular pattern
        expected_strides = []
        stride = array.itemsize

        for i in range(array.ndim - 1, -1, -1):
            expected_strides.insert(0, stride)
            stride *= array.shape[i]

        return array.strides == tuple(expected_strides)


class NumpyValidator:
    """
    Validates numpy arrays for PyO3 compatibility.

    Checks layout, dtypes, alignment, and provides detailed reports.
    """

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.dtype_mapper = DTypeMapper()
        self.analyzer = ArrayAnalyzer()

    def validate(
        self,
        array: np.ndarray,
        required_layout: Optional[ArrayLayout] = None,
        required_dtype: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate array for PyO3 compatibility.

        Args:
            array: Numpy array to validate
            required_layout: Required memory layout (optional)
            required_dtype: Required dtype (optional)

        Returns:
            ValidationResult with detailed analysis
        """
        # Analyze array
        info = self.analyzer.analyze(array)
        issues = []
        recommendations = []

        # Check dtype compatibility
        dtype_compat = self.dtype_mapper.is_compatible(array.dtype)

        if dtype_compat == DTypeCompatibility.INCOMPATIBLE:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="dtype",
                message=f"Incompatible dtype: {info.dtype}",
                details="Object, string, and unicode dtypes cannot be directly used with PyO3",
                fix_suggestion="Convert to a compatible numeric dtype or use custom conversion"
            ))

        elif dtype_compat == DTypeCompatibility.NEEDS_CONVERSION:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="dtype",
                message=f"Dtype {info.dtype} may need conversion",
                details="This dtype is not directly mapped to a Rust type",
                fix_suggestion="Consider converting to a standard numeric type"
            ))

        # Check required dtype
        if required_dtype and info.dtype != required_dtype:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="dtype",
                message=f"Expected dtype {required_dtype}, got {info.dtype}",
                fix_suggestion=f"Convert array to {required_dtype}: array.astype('{required_dtype}')"
            ))

        # Check layout compatibility
        layout_compatible = True

        if required_layout:
            if required_layout == ArrayLayout.C_CONTIGUOUS and not info.c_contiguous:
                layout_compatible = False
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="layout",
                    message="Array is not C-contiguous",
                    details=f"Current layout: {info.layout.value}",
                    fix_suggestion="Use np.ascontiguousarray(array) to make C-contiguous"
                ))

            elif required_layout == ArrayLayout.F_CONTIGUOUS and not info.f_contiguous:
                layout_compatible = False
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category="layout",
                    message="Array is not F-contiguous",
                    details=f"Current layout: {info.layout.value}",
                    fix_suggestion="Use np.asfortranarray(array) to make F-contiguous"
                ))

        # Check if non-contiguous (potential performance issue)
        if info.layout == ArrayLayout.NON_CONTIGUOUS:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="layout",
                message="Array is non-contiguous",
                details="Non-contiguous arrays may have performance penalties",
                fix_suggestion="Consider using np.ascontiguousarray(array)"
            ))

        # Check if view (memory safety)
        if info.is_view:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                category="memory",
                message="Array is a view",
                details="This array does not own its data",
                fix_suggestion="If passing to Rust, ensure base array lifetime is managed"
            ))

        # Check writability
        if not info.is_writeable:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="memory",
                message="Array is read-only",
                details="Cannot modify array from Rust",
                fix_suggestion="Create writable copy if modification needed: array.copy()"
            ))

        # Check alignment
        if not info.is_aligned:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="memory",
                message="Array is not properly aligned",
                details="Misaligned arrays may cause performance issues or crashes",
                fix_suggestion="Create aligned copy: array.copy()"
            ))

        # Check byte order
        if info.byte_order not in ['native', 'little']:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="dtype",
                message=f"Non-native byte order: {info.byte_order}",
                details="May require byte swapping when passing to Rust",
                fix_suggestion="Convert to native byte order: array.astype(array.dtype.newbyteorder('='))"
            ))

        # Determine if zero-copy is possible
        zero_copy_possible = (
            dtype_compat == DTypeCompatibility.COMPATIBLE and
            (info.c_contiguous or info.f_contiguous) and
            info.is_aligned and
            info.byte_order in ['native', 'little']
        )

        if zero_copy_possible:
            recommendations.append(
                "✓ Zero-copy transfer possible - use PyReadonlyArray or PyReadwriteArray"
            )
        else:
            recommendations.append(
                "✗ Zero-copy not possible - data copy required"
            )

        # Additional recommendations
        if info.c_contiguous:
            recommendations.append("Array is C-contiguous - optimal for row-major access")
        elif info.f_contiguous:
            recommendations.append("Array is F-contiguous - optimal for column-major access")

        if info.size > 1_000_000:
            recommendations.append(
                f"Large array ({info.nbytes / (1024**2):.1f} MB) - "
                "consider using zero-copy if possible"
            )

        # Overall compatibility
        compatible = (
            dtype_compat != DTypeCompatibility.INCOMPATIBLE and
            layout_compatible and
            (not self.strict or zero_copy_possible)
        )

        return ValidationResult(
            array_info=info,
            compatible=compatible,
            issues=issues,
            dtype_compatibility=dtype_compat,
            layout_compatible=layout_compatible,
            zero_copy_possible=zero_copy_possible,
            recommendations=recommendations
        )

    def validate_batch(
        self,
        arrays: Dict[str, np.ndarray]
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple arrays.

        Args:
            arrays: Dictionary mapping names to arrays

        Returns:
            Dictionary mapping names to validation results
        """
        results = {}

        for name, array in arrays.items():
            logger.debug(f"Validating: {name}")
            results[name] = self.validate(array)

        return results

    def benchmark_conversion(
        self,
        array: np.ndarray,
        iterations: int = 1000
    ) -> Dict[str, float]:
        """
        Benchmark conversion overhead.

        Compares zero-copy view vs copy performance.
        """
        import time

        results = {}

        # Benchmark view creation (zero-copy)
        start = time.perf_counter()
        for _ in range(iterations):
            _ = array.view()
        view_time = (time.perf_counter() - start) / iterations
        results['view_ns'] = view_time * 1e9

        # Benchmark copy
        start = time.perf_counter()
        for _ in range(iterations):
            _ = array.copy()
        copy_time = (time.perf_counter() - start) / iterations
        results['copy_ns'] = copy_time * 1e9

        # Benchmark contiguous conversion if needed
        if not array.flags.c_contiguous:
            start = time.perf_counter()
            for _ in range(iterations):
                _ = np.ascontiguousarray(array)
            contiguous_time = (time.perf_counter() - start) / iterations
            results['ascontiguous_ns'] = contiguous_time * 1e9

        results['speedup'] = results['copy_ns'] / results['view_ns']

        return results


class ReportGenerator:
    """Generates validation reports."""

    @staticmethod
    def generate_text_report(result: ValidationResult) -> str:
        """Generate text report."""
        lines = ["=== Numpy Array Validation Report ===\n"]

        # Array info
        lines.append("Array Information:")
        lines.append(f"  Shape: {result.array_info.shape}")
        lines.append(f"  Dtype: {result.array_info.dtype}")
        lines.append(f"  Size: {result.array_info.size:,} elements")
        lines.append(f"  Memory: {result.array_info.nbytes / (1024**2):.2f} MB")
        lines.append(f"  Layout: {result.array_info.layout.value}")
        lines.append(f"  Byte order: {result.array_info.byte_order}")

        # Compatibility
        lines.append("\nCompatibility:")
        lines.append(f"  Overall: {'✓ Compatible' if result.compatible else '✗ Incompatible'}")
        lines.append(f"  Dtype: {result.dtype_compatibility.value}")
        lines.append(f"  Layout: {'✓' if result.layout_compatible else '✗'}")
        lines.append(f"  Zero-copy: {'✓ Possible' if result.zero_copy_possible else '✗ Not possible'}")

        # Issues
        if result.issues:
            lines.append(f"\nIssues ({len(result.issues)}):")
            for issue in result.issues:
                symbol = {"error": "✗", "warning": "⚠", "info": "ℹ"}[issue.level.value]
                lines.append(f"\n  {symbol} [{issue.category.upper()}] {issue.message}")
                if issue.details:
                    lines.append(f"      {issue.details}")
                if issue.fix_suggestion:
                    lines.append(f"      Fix: {issue.fix_suggestion}")

        # Recommendations
        if result.recommendations:
            lines.append("\nRecommendations:")
            for rec in result.recommendations:
                lines.append(f"  {rec}")

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(result: ValidationResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)

    @staticmethod
    def generate_markdown_report(result: ValidationResult) -> str:
        """Generate Markdown report."""
        lines = ["# Numpy Array Validation Report\n"]

        # Array info
        lines.append("## Array Information\n")
        lines.append(f"- **Shape**: {result.array_info.shape}")
        lines.append(f"- **Dtype**: `{result.array_info.dtype}`")
        lines.append(f"- **Size**: {result.array_info.size:,} elements")
        lines.append(f"- **Memory**: {result.array_info.nbytes / (1024**2):.2f} MB")
        lines.append(f"- **Layout**: {result.array_info.layout.value}")

        # Compatibility
        lines.append("\n## Compatibility\n")
        compat_symbol = "✅" if result.compatible else "❌"
        lines.append(f"- **Overall**: {compat_symbol} {'Compatible' if result.compatible else 'Incompatible'}")
        lines.append(f"- **Dtype**: {result.dtype_compatibility.value}")
        lines.append(f"- **Zero-copy**: {'✅ Possible' if result.zero_copy_possible else '❌ Not possible'}")

        # Issues
        if result.issues:
            lines.append(f"\n## Issues\n")
            for issue in result.issues:
                lines.append(f"### {issue.category.upper()}: {issue.message}\n")
                lines.append(f"**Level**: {issue.level.value}\n")
                if issue.details:
                    lines.append(f"**Details**: {issue.details}\n")
                if issue.fix_suggestion:
                    lines.append(f"**Fix**: {issue.fix_suggestion}\n")

        return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Numpy Array Validator',
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

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate array')
    validate_parser.add_argument('array', type=Path, help='Array file (.npy)')
    validate_parser.add_argument('--strict', action='store_true', help='Strict validation')
    validate_parser.add_argument('--layout', type=str, choices=['c', 'f'], help='Required layout')
    validate_parser.add_argument('--dtype', type=str, help='Required dtype')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check specific requirements')
    check_parser.add_argument('array', type=Path, help='Array file (.npy)')
    check_parser.add_argument('--layout', type=str, choices=['c', 'f'], help='Required layout')
    check_parser.add_argument('--dtype', type=str, help='Required dtype')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Validate multiple arrays')
    batch_parser.add_argument('directory', type=Path, help='Directory with .npy files')
    batch_parser.add_argument('--recursive', '-r', action='store_true', help='Recursive search')
    batch_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('array', type=Path, help='Array file (.npy)')
    report_parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='text')
    report_parser.add_argument('--output', '-o', type=Path, help='Output file')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark conversion')
    benchmark_parser.add_argument('array', type=Path, help='Array file (.npy)')
    benchmark_parser.add_argument('--iterations', type=int, default=1000, help='Iterations')
    benchmark_parser.add_argument('--compare', action='store_true', help='Compare strategies')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    validator = NumpyValidator(strict=getattr(args, 'strict', False))
    report_gen = ReportGenerator()

    try:
        if args.command == 'validate':
            array = np.load(args.array)

            layout = None
            if args.layout == 'c':
                layout = ArrayLayout.C_CONTIGUOUS
            elif args.layout == 'f':
                layout = ArrayLayout.F_CONTIGUOUS

            result = validator.validate(array, layout, args.dtype)

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(report_gen.generate_text_report(result))

            sys.exit(0 if result.compatible else 1)

        elif args.command == 'check':
            array = np.load(args.array)

            layout = None
            if args.layout == 'c':
                layout = ArrayLayout.C_CONTIGUOUS
            elif args.layout == 'f':
                layout = ArrayLayout.F_CONTIGUOUS

            result = validator.validate(array, layout, args.dtype)

            error_count = sum(1 for i in result.issues if i.level == ValidationLevel.ERROR)

            if args.json:
                print(json.dumps({'compatible': result.compatible, 'errors': error_count}, indent=2))
            else:
                if result.compatible:
                    print("✓ Array is compatible")
                else:
                    print(f"✗ Array is not compatible ({error_count} errors)")
                    for issue in result.issues:
                        if issue.level == ValidationLevel.ERROR:
                            print(f"  - {issue.message}")

            sys.exit(0 if result.compatible else 1)

        elif args.command == 'batch':
            pattern = '**/*.npy' if args.recursive else '*.npy'
            array_files = list(args.directory.glob(pattern))

            logger.info(f"Found {len(array_files)} array files")

            results = {}
            for array_file in array_files:
                try:
                    array = np.load(array_file)
                    result = validator.validate(array)
                    results[str(array_file)] = result
                except Exception as e:
                    logger.error(f"Failed to validate {array_file}: {e}")

            if args.json:
                output = json.dumps({k: v.to_dict() for k, v in results.items()}, indent=2)
            else:
                compatible_count = sum(1 for r in results.values() if r.compatible)
                output = f"\nBatch Validation Results:\n"
                output += f"  Total: {len(results)}\n"
                output += f"  Compatible: {compatible_count}\n"
                output += f"  Incompatible: {len(results) - compatible_count}\n"

            if args.output:
                args.output.write_text(output)
                print(f"Results saved to {args.output}")
            else:
                print(output)

        elif args.command == 'report':
            array = np.load(args.array)
            result = validator.validate(array)

            if args.format == 'json':
                report = report_gen.generate_json_report(result)
            elif args.format == 'markdown':
                report = report_gen.generate_markdown_report(result)
            else:
                report = report_gen.generate_text_report(result)

            if args.output:
                args.output.write_text(report)
                print(f"Report saved to {args.output}")
            else:
                print(report)

        elif args.command == 'benchmark':
            array = np.load(args.array)
            bench_results = validator.benchmark_conversion(array, args.iterations)

            if args.json:
                print(json.dumps(bench_results, indent=2))
            else:
                print("\nConversion Benchmark Results:")
                print(f"  View (zero-copy): {bench_results['view_ns']:.2f} ns")
                print(f"  Copy: {bench_results['copy_ns']:.2f} ns")
                if 'ascontiguous_ns' in bench_results:
                    print(f"  As-contiguous: {bench_results['ascontiguous_ns']:.2f} ns")
                print(f"  Speedup (copy vs view): {bench_results['speedup']:.1f}x")

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
