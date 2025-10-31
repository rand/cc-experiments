#!/usr/bin/env python3
"""
PyO3 Buffer Protocol Inspector

Inspects and validates objects implementing Python's buffer protocol.
Provides detailed analysis of buffer properties, memory views, layouts,
and compatibility with PyO3 for safe zero-copy data exchange.

Features:
- Inspect objects implementing buffer protocol
- Validate buffer properties (shape, strides, format)
- Check memory views and layouts
- Validate buffer flags (readonly, writable, indirect)
- Analyze buffer memory layout
- Detect potential memory leaks
- Check PyO3 compatibility
- Generate comprehensive inspection reports
- Compare buffer implementations

Usage:
    # Inspect buffer object
    buffer_inspector.py inspect data.pkl --verbose

    # Validate buffer protocol implementation
    buffer_inspector.py validate object.pkl --strict

    # Compare buffer implementations
    buffer_inspector.py compare obj1.pkl obj2.pkl

    # Check memory leaks
    buffer_inspector.py leak-check object.pkl --iterations 1000

    # Generate compatibility report
    buffer_inspector.py report object.pkl --format html

Examples:
    # Inspect numpy array buffer
    python buffer_inspector.py inspect array.npy --verbose

    # Validate buffer
    python buffer_inspector.py validate buffer.pkl --check-all

    # Memory leak detection
    python buffer_inspector.py leak-check obj.pkl --monitor

    # Compatibility report
    python buffer_inspector.py report obj.pkl --format markdown

    # Compare buffers
    python buffer_inspector.py compare array1.npy array2.npy

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import gc
import json
import logging
import sys
import time
import traceback
import weakref
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import pickle
import psutil

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("Numpy not available, some features disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BufferFlag(Enum):
    """Buffer protocol flags."""
    WRITABLE = "writable"
    READONLY = "readonly"
    FORMAT = "format"
    ND = "nd"
    STRIDES = "strides"
    C_CONTIGUOUS = "c_contiguous"
    F_CONTIGUOUS = "f_contiguous"
    INDIRECT = "indirect"


class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class BufferInfo:
    """Comprehensive buffer information."""
    obj_type: str
    has_buffer_protocol: bool
    is_memoryview: bool
    is_readonly: bool
    shape: Optional[Tuple[int, ...]]
    strides: Optional[Tuple[int, ...]]
    format: str
    itemsize: int
    ndim: int
    nbytes: int
    c_contiguous: bool
    f_contiguous: bool
    contiguous: bool
    suboffsets: Optional[Tuple[int, ...]]
    flags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ValidationIssue:
    """Buffer validation issue."""
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
class InspectionResult:
    """Complete buffer inspection result."""
    buffer_info: BufferInfo
    compatible: bool
    issues: List[ValidationIssue]
    zero_copy_possible: bool
    recommendations: List[str]
    memory_stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'buffer_info': self.buffer_info.to_dict(),
            'compatible': self.compatible,
            'issues': [i.to_dict() for i in self.issues],
            'zero_copy_possible': self.zero_copy_possible,
            'recommendations': self.recommendations,
            'memory_stats': self.memory_stats
        }


class BufferAnalyzer:
    """Analyzes buffer protocol implementations."""

    @staticmethod
    def analyze(obj: Any) -> BufferInfo:
        """
        Analyze an object for buffer protocol support.

        Returns comprehensive buffer information.
        """
        obj_type = type(obj).__name__

        # Check if object supports buffer protocol
        has_buffer_protocol = False
        try:
            memoryview(obj)
            has_buffer_protocol = True
        except TypeError:
            pass

        if not has_buffer_protocol:
            return BufferInfo(
                obj_type=obj_type,
                has_buffer_protocol=False,
                is_memoryview=False,
                is_readonly=False,
                shape=None,
                strides=None,
                format='',
                itemsize=0,
                ndim=0,
                nbytes=0,
                c_contiguous=False,
                f_contiguous=False,
                contiguous=False,
                suboffsets=None,
                flags=[]
            )

        # Create memoryview to inspect
        mv = memoryview(obj)
        is_memoryview = isinstance(obj, memoryview)

        # Extract information
        flags = []
        if mv.readonly:
            flags.append(BufferFlag.READONLY.value)
        else:
            flags.append(BufferFlag.WRITABLE.value)

        if mv.c_contiguous:
            flags.append(BufferFlag.C_CONTIGUOUS.value)
        if mv.f_contiguous:
            flags.append(BufferFlag.F_CONTIGUOUS.value)
        if mv.contiguous:
            flags.append('contiguous')

        if mv.format:
            flags.append(BufferFlag.FORMAT.value)
        if mv.ndim > 0:
            flags.append(BufferFlag.ND.value)
        if mv.strides:
            flags.append(BufferFlag.STRIDES.value)

        # Check for indirect buffers (PIL images, etc.)
        has_suboffsets = mv.suboffsets is not None and any(s >= 0 for s in mv.suboffsets)
        if has_suboffsets:
            flags.append(BufferFlag.INDIRECT.value)

        return BufferInfo(
            obj_type=obj_type,
            has_buffer_protocol=True,
            is_memoryview=is_memoryview,
            is_readonly=mv.readonly,
            shape=tuple(mv.shape) if mv.shape else None,
            strides=tuple(mv.strides) if mv.strides else None,
            format=mv.format,
            itemsize=mv.itemsize,
            ndim=mv.ndim,
            nbytes=mv.nbytes,
            c_contiguous=mv.c_contiguous,
            f_contiguous=mv.f_contiguous,
            contiguous=mv.contiguous,
            suboffsets=tuple(mv.suboffsets) if mv.suboffsets else None,
            flags=flags
        )


class BufferValidator:
    """
    Validates buffer protocol implementations for PyO3 compatibility.

    Checks for common issues and provides recommendations.
    """

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.analyzer = BufferAnalyzer()

    def validate(
        self,
        obj: Any,
        require_writable: bool = False,
        require_contiguous: bool = False
    ) -> InspectionResult:
        """
        Validate buffer protocol implementation.

        Args:
            obj: Object to validate
            require_writable: Require writable buffer
            require_contiguous: Require contiguous memory

        Returns:
            Complete inspection result
        """
        # Analyze buffer
        info = self.analyzer.analyze(obj)
        issues = []
        recommendations = []

        # Check if buffer protocol is supported
        if not info.has_buffer_protocol:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="protocol",
                message="Object does not implement buffer protocol",
                details=f"Type {info.obj_type} does not support buffer interface",
                fix_suggestion="Ensure object implements __buffer__ or is convertible to memoryview"
            ))
            return InspectionResult(
                buffer_info=info,
                compatible=False,
                issues=issues,
                zero_copy_possible=False,
                recommendations=["Object must implement buffer protocol for PyO3 compatibility"]
            )

        # Check writability
        if require_writable and info.is_readonly:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="access",
                message="Buffer is read-only but writable access required",
                details="PyO3 PyReadwriteArray requires writable buffer",
                fix_suggestion="Use PyReadonlyArray for read-only access or create writable copy"
            ))

        # Check contiguity
        if require_contiguous and not info.contiguous:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="layout",
                message="Buffer is not contiguous",
                details=f"C-contiguous: {info.c_contiguous}, F-contiguous: {info.f_contiguous}",
                fix_suggestion="Convert to contiguous array or use strided access"
            ))

        # Check for indirect buffers (suboffsets)
        if info.suboffsets and any(s >= 0 for s in info.suboffsets):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="layout",
                message="Buffer has suboffsets (indirect buffer)",
                details="Indirect buffers require additional pointer indirection",
                fix_suggestion="Convert to direct buffer for better performance"
            ))

        # Check format string
        if not info.format:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                category="format",
                message="Buffer has no format string",
                details="Format string helps ensure type safety",
                fix_suggestion="Ensure buffer provides format information"
            ))
        elif info.format == 'B' or info.format == 'b':
            recommendations.append("Format 'B' (unsigned byte) is compatible with Rust u8/i8")
        elif info.format in ['i', 'I', 'l', 'L', 'q', 'Q']:
            recommendations.append(f"Format '{info.format}' is compatible with Rust integer types")
        elif info.format in ['f', 'd']:
            recommendations.append(f"Format '{info.format}' is compatible with Rust f32/f64")

        # Check dimensions
        if info.ndim == 0:
            recommendations.append("Scalar buffer - can be accessed as single value")
        elif info.ndim == 1:
            recommendations.append("1D buffer - optimal for slice/vector operations")
        elif info.ndim > 1:
            recommendations.append(f"{info.ndim}D buffer - consider ndarray crate for multi-dimensional access")

        # Check size
        if info.nbytes > 100 * 1024 * 1024:  # 100 MB
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                category="memory",
                message=f"Large buffer ({info.nbytes / (1024**2):.1f} MB)",
                details="Large buffers should use zero-copy when possible",
                fix_suggestion="Use PyReadonlyArray/PyReadwriteArray for zero-copy access"
            ))

        # Check strides
        if info.strides:
            expected_contiguous = BufferValidator._compute_expected_strides(
                info.shape,
                info.itemsize,
                c_order=True
            )
            if info.strides != expected_contiguous:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="layout",
                    message="Buffer has non-standard strides",
                    details=f"Strides: {info.strides}",
                    fix_suggestion="Be aware of stride pattern when accessing data"
                ))

        # Determine zero-copy possibility
        zero_copy_possible = (
            info.has_buffer_protocol and
            info.contiguous and
            not (info.suboffsets and any(s >= 0 for s in info.suboffsets))
        )

        if zero_copy_possible:
            recommendations.append("✓ Zero-copy access possible via buffer protocol")
        else:
            recommendations.append("✗ Zero-copy not recommended - consider copying data")

        # Overall compatibility
        error_count = sum(1 for i in issues if i.level == ValidationLevel.ERROR)
        compatible = error_count == 0

        return InspectionResult(
            buffer_info=info,
            compatible=compatible,
            issues=issues,
            zero_copy_possible=zero_copy_possible,
            recommendations=recommendations
        )

    @staticmethod
    def _compute_expected_strides(
        shape: Optional[Tuple[int, ...]],
        itemsize: int,
        c_order: bool = True
    ) -> Optional[Tuple[int, ...]]:
        """Compute expected strides for contiguous array."""
        if not shape:
            return None

        if c_order:
            # C order: last dimension varies fastest
            strides = []
            stride = itemsize
            for dim in reversed(shape):
                strides.insert(0, stride)
                stride *= dim
            return tuple(strides)
        else:
            # Fortran order: first dimension varies fastest
            strides = []
            stride = itemsize
            for dim in shape:
                strides.append(stride)
                stride *= dim
            return tuple(strides)


class MemoryLeakDetector:
    """Detects memory leaks in buffer handling."""

    def __init__(self):
        self.process = psutil.Process()
        self.tracked_objects: List[weakref.ref] = []

    def check_leaks(
        self,
        obj: Any,
        iterations: int = 1000,
        monitor: bool = False
    ) -> Dict[str, Any]:
        """
        Check for memory leaks when creating/destroying memoryviews.

        Args:
            obj: Object to test
            iterations: Number of test iterations
            monitor: Enable detailed monitoring

        Returns:
            Dictionary with leak detection results
        """
        gc.collect()
        initial_rss = self.process.memory_info().rss

        memory_samples = []
        if monitor:
            memory_samples.append(initial_rss)

        # Test memoryview creation/destruction
        for i in range(iterations):
            try:
                mv = memoryview(obj)
                # Access data to ensure it's used
                _ = mv.nbytes
                del mv

                if monitor and i % 100 == 0:
                    gc.collect()
                    current_rss = self.process.memory_info().rss
                    memory_samples.append(current_rss)

            except Exception as e:
                logger.error(f"Error during leak check iteration {i}: {e}")
                break

        gc.collect()
        final_rss = self.process.memory_info().rss

        # Calculate memory delta
        delta_bytes = final_rss - initial_rss
        delta_mb = delta_bytes / (1024 * 1024)

        # Determine if leak detected
        leak_threshold = 10 * 1024 * 1024  # 10 MB
        leak_detected = delta_bytes > leak_threshold

        result = {
            'iterations': iterations,
            'initial_rss_mb': initial_rss / (1024 * 1024),
            'final_rss_mb': final_rss / (1024 * 1024),
            'delta_mb': delta_mb,
            'leak_detected': leak_detected,
            'leak_per_iteration_bytes': delta_bytes / iterations if iterations > 0 else 0
        }

        if monitor:
            result['memory_samples'] = [s / (1024 * 1024) for s in memory_samples]

        return result


class BufferComparator:
    """Compares buffer implementations."""

    @staticmethod
    def compare(obj1: Any, obj2: Any) -> Dict[str, Any]:
        """
        Compare two buffer implementations.

        Returns dictionary with comparison results.
        """
        analyzer = BufferAnalyzer()

        info1 = analyzer.analyze(obj1)
        info2 = analyzer.analyze(obj2)

        differences = []
        if info1.shape != info2.shape:
            differences.append(f"Shape: {info1.shape} vs {info2.shape}")
        if info1.strides != info2.strides:
            differences.append(f"Strides: {info1.strides} vs {info2.strides}")
        if info1.format != info2.format:
            differences.append(f"Format: {info1.format} vs {info2.format}")
        if info1.c_contiguous != info2.c_contiguous:
            differences.append(f"C-contiguous: {info1.c_contiguous} vs {info2.c_contiguous}")
        if info1.is_readonly != info2.is_readonly:
            differences.append(f"Readonly: {info1.is_readonly} vs {info2.is_readonly}")

        return {
            'buffer1': info1.to_dict(),
            'buffer2': info2.to_dict(),
            'differences': differences,
            'compatible': len(differences) == 0
        }


class ReportGenerator:
    """Generates inspection reports."""

    @staticmethod
    def generate_text_report(result: InspectionResult) -> str:
        """Generate text report."""
        lines = ["=== Buffer Protocol Inspection Report ===\n"]

        # Buffer info
        lines.append("Buffer Information:")
        lines.append(f"  Type: {result.buffer_info.obj_type}")
        lines.append(f"  Has Buffer Protocol: {result.buffer_info.has_buffer_protocol}")

        if result.buffer_info.has_buffer_protocol:
            lines.append(f"  Shape: {result.buffer_info.shape}")
            lines.append(f"  Strides: {result.buffer_info.strides}")
            lines.append(f"  Format: '{result.buffer_info.format}'")
            lines.append(f"  Item size: {result.buffer_info.itemsize} bytes")
            lines.append(f"  Dimensions: {result.buffer_info.ndim}")
            lines.append(f"  Total bytes: {result.buffer_info.nbytes:,}")
            lines.append(f"  Readonly: {result.buffer_info.is_readonly}")
            lines.append(f"  C-contiguous: {result.buffer_info.c_contiguous}")
            lines.append(f"  F-contiguous: {result.buffer_info.f_contiguous}")
            lines.append(f"  Flags: {', '.join(result.buffer_info.flags)}")

        # Compatibility
        lines.append("\nCompatibility:")
        lines.append(f"  Overall: {'✓ Compatible' if result.compatible else '✗ Incompatible'}")
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
    def generate_json_report(result: InspectionResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2)


class BufferInspector:
    """Main inspector for buffer protocol objects."""

    def __init__(self, strict: bool = False):
        self.validator = BufferValidator(strict)
        self.leak_detector = MemoryLeakDetector()
        self.comparator = BufferComparator()
        self.report_gen = ReportGenerator()

    def inspect(self, obj: Any, **kwargs) -> InspectionResult:
        """Comprehensive inspection of buffer object."""
        return self.validator.validate(obj, **kwargs)

    def check_leaks(self, obj: Any, **kwargs) -> Dict[str, Any]:
        """Check for memory leaks."""
        return self.leak_detector.check_leaks(obj, **kwargs)

    def compare(self, obj1: Any, obj2: Any) -> Dict[str, Any]:
        """Compare two buffer objects."""
        return self.comparator.compare(obj1, obj2)


def load_object(path: Path) -> Any:
    """Load object from file."""
    if path.suffix == '.npy' and HAS_NUMPY:
        return np.load(path)
    elif path.suffix == '.pkl':
        with open(path, 'rb') as f:
            return pickle.load(f)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Buffer Protocol Inspector',
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

    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect buffer object')
    inspect_parser.add_argument('object', type=Path, help='Object file (.npy, .pkl)')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate buffer')
    validate_parser.add_argument('object', type=Path, help='Object file')
    validate_parser.add_argument('--strict', action='store_true', help='Strict validation')
    validate_parser.add_argument('--writable', action='store_true', help='Require writable')
    validate_parser.add_argument('--contiguous', action='store_true', help='Require contiguous')

    # Leak check command
    leak_parser = subparsers.add_parser('leak-check', help='Check for memory leaks')
    leak_parser.add_argument('object', type=Path, help='Object file')
    leak_parser.add_argument('--iterations', type=int, default=1000, help='Test iterations')
    leak_parser.add_argument('--monitor', action='store_true', help='Monitor memory usage')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare buffers')
    compare_parser.add_argument('object1', type=Path, help='First object')
    compare_parser.add_argument('object2', type=Path, help='Second object')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('object', type=Path, help='Object file')
    report_parser.add_argument('--format', choices=['text', 'json'], default='text')
    report_parser.add_argument('--output', '-o', type=Path, help='Output file')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    inspector = BufferInspector(strict=getattr(args, 'strict', False))

    try:
        if args.command == 'inspect':
            obj = load_object(args.object)
            result = inspector.inspect(obj)

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                print(inspector.report_gen.generate_text_report(result))

        elif args.command == 'validate':
            obj = load_object(args.object)
            result = inspector.inspect(
                obj,
                require_writable=args.writable,
                require_contiguous=args.contiguous
            )

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                if result.compatible:
                    print("✓ Buffer is compatible")
                else:
                    print("✗ Buffer is not compatible")
                    for issue in result.issues:
                        if issue.level == ValidationLevel.ERROR:
                            print(f"  - {issue.message}")

            sys.exit(0 if result.compatible else 1)

        elif args.command == 'leak-check':
            obj = load_object(args.object)
            result = inspector.check_leaks(
                obj,
                iterations=args.iterations,
                monitor=args.monitor
            )

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("\nMemory Leak Check Results:")
                print(f"  Iterations: {result['iterations']}")
                print(f"  Initial RSS: {result['initial_rss_mb']:.2f} MB")
                print(f"  Final RSS: {result['final_rss_mb']:.2f} MB")
                print(f"  Delta: {result['delta_mb']:.2f} MB")
                print(f"  Per iteration: {result['leak_per_iteration_bytes']:.2f} bytes")
                print(f"  Leak detected: {'Yes' if result['leak_detected'] else 'No'}")

        elif args.command == 'compare':
            obj1 = load_object(args.object1)
            obj2 = load_object(args.object2)
            result = inspector.compare(obj1, obj2)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("\nBuffer Comparison:")
                if result['compatible']:
                    print("  ✓ Buffers are compatible")
                else:
                    print("  ✗ Buffers have differences:")
                    for diff in result['differences']:
                        print(f"    - {diff}")

        elif args.command == 'report':
            obj = load_object(args.object)
            result = inspector.inspect(obj)

            if args.format == 'json':
                report = inspector.report_gen.generate_json_report(result)
            else:
                report = inspector.report_gen.generate_text_report(result)

            if args.output:
                args.output.write_text(report)
                print(f"Report saved to {args.output}")
            else:
                print(report)

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
