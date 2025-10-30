#!/usr/bin/env python3
"""
Arrow Format Converter for PyO3 Data Science

Comprehensive Apache Arrow format conversion, validation, and processing utilities
for PyO3 Rust-Python interop with support for Parquet, CSV, and Arrow IPC formats.

Usage:
    arrow_converter.py convert <input> <output> [options]
    arrow_converter.py validate <file> [options]
    arrow_converter.py inspect <file> [options]
    arrow_converter.py batch <input_dir> <output_dir> [options]

Examples:
    arrow_converter.py convert data.csv data.parquet
    arrow_converter.py validate data.parquet --check-schema
    arrow_converter.py inspect data.arrow --show-stats
    arrow_converter.py batch input/ output/ --format parquet --parallel 4
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyarrow.csv as csv
    import pyarrow.feather as feather
except ImportError:
    print("Error: PyArrow is required. Install with: uv add pyarrow", file=sys.stderr)
    sys.exit(1)


class OutputFormat(Enum):
    """Supported output formats."""
    TEXT = "text"
    JSON = "json"
    PRETTY = "pretty"


class FileFormat(Enum):
    """Supported file formats."""
    CSV = "csv"
    PARQUET = "parquet"
    ARROW = "arrow"
    FEATHER = "feather"
    JSON = "json"


class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    SNAPPY = "snappy"
    GZIP = "gzip"
    BROTLI = "brotli"
    LZ4 = "lz4"
    ZSTD = "zstd"


@dataclass
class ConversionResult:
    """Result of format conversion."""
    success: bool
    input_file: str
    output_file: str
    input_format: str
    output_format: str
    input_size_bytes: int
    output_size_bytes: int
    compression_ratio: float
    row_count: int
    column_count: int
    conversion_time_ms: float
    read_time_ms: float
    write_time_ms: float
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of Arrow file validation."""
    valid: bool
    file_path: str
    file_format: str
    file_size_bytes: int
    row_count: int
    column_count: int
    schema: Optional[Dict[str, str]] = None
    compression: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ColumnStatistics:
    """Statistics for a single column."""
    name: str
    type: str
    null_count: int
    null_percentage: float
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    distinct_count: Optional[int] = None


@dataclass
class InspectionResult:
    """Result of file inspection."""
    file_path: str
    file_format: str
    file_size_bytes: int
    row_count: int
    column_count: int
    schema: Dict[str, str]
    column_stats: List[ColumnStatistics]
    metadata: Dict[str, str]
    memory_usage_bytes: int
    compression: Optional[str] = None


@dataclass
class BatchResult:
    """Result of batch processing."""
    success: bool
    total_files: int
    processed_files: int
    failed_files: int
    total_input_bytes: int
    total_output_bytes: int
    total_time_s: float
    average_time_ms: float
    throughput_mb_s: float
    errors: List[Tuple[str, str]] = field(default_factory=list)


class ArrowConverter:
    """Converts between Arrow-compatible formats."""

    def __init__(self) -> None:
        self.conversion_count = 0

    def convert_file(
        self,
        input_path: str,
        output_path: str,
        compression: CompressionType = CompressionType.SNAPPY,
        chunk_size: int = 1000000
    ) -> ConversionResult:
        """
        Convert file between formats.

        Args:
            input_path: Input file path
            output_path: Output file path
            compression: Compression type for output
            chunk_size: Chunk size for processing

        Returns:
            ConversionResult with conversion details
        """
        result = ConversionResult(
            success=False,
            input_file=input_path,
            output_file=output_path,
            input_format="",
            output_format="",
            input_size_bytes=0,
            output_size_bytes=0,
            compression_ratio=0.0,
            row_count=0,
            column_count=0,
            conversion_time_ms=0.0,
            read_time_ms=0.0,
            write_time_ms=0.0
        )

        try:
            input_path_obj = Path(input_path)
            output_path_obj = Path(output_path)

            if not input_path_obj.exists():
                result.errors.append(f"input file not found: {input_path}")
                return result

            result.input_size_bytes = input_path_obj.stat().st_size
            result.input_format = self._detect_format(input_path_obj)
            result.output_format = self._detect_format(output_path_obj)

            # Read input
            start_time = time.perf_counter()
            table = self._read_file(input_path, result.input_format)
            result.read_time_ms = (time.perf_counter() - start_time) * 1000

            result.row_count = table.num_rows
            result.column_count = table.num_columns

            # Write output
            start_time = time.perf_counter()
            self._write_file(output_path, table, result.output_format, compression)
            result.write_time_ms = (time.perf_counter() - start_time) * 1000

            result.conversion_time_ms = result.read_time_ms + result.write_time_ms

            # Get output size
            if output_path_obj.exists():
                result.output_size_bytes = output_path_obj.stat().st_size
                if result.input_size_bytes > 0:
                    result.compression_ratio = result.input_size_bytes / result.output_size_bytes
                else:
                    result.compression_ratio = 1.0

            result.success = True
            self.conversion_count += 1

        except Exception as e:
            result.errors.append(f"conversion failed: {e}")

        return result

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        suffix = path.suffix.lower()
        format_map = {
            '.csv': 'csv',
            '.parquet': 'parquet',
            '.pq': 'parquet',
            '.arrow': 'arrow',
            '.feather': 'feather',
            '.json': 'json'
        }
        return format_map.get(suffix, 'unknown')

    def _read_file(self, file_path: str, file_format: str) -> pa.Table:
        """Read file into Arrow table."""
        if file_format == 'csv':
            return csv.read_csv(file_path)

        elif file_format == 'parquet':
            return pq.read_table(file_path)

        elif file_format == 'arrow':
            with pa.memory_map(file_path, 'r') as source:
                return pa.ipc.open_file(source).read_all()

        elif file_format == 'feather':
            return feather.read_table(file_path)

        elif file_format == 'json':
            import pandas as pd
            df = pd.read_json(file_path)
            return pa.Table.from_pandas(df)

        else:
            raise ValueError(f"unsupported input format: {file_format}")

    def _write_file(
        self,
        file_path: str,
        table: pa.Table,
        file_format: str,
        compression: CompressionType
    ) -> None:
        """Write Arrow table to file."""
        # Create parent directory if needed
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        compression_str = compression.value if compression != CompressionType.NONE else None

        if file_format == 'csv':
            csv.write_csv(table, file_path)

        elif file_format == 'parquet':
            pq.write_table(table, file_path, compression=compression_str)

        elif file_format == 'arrow':
            with pa.OSFile(file_path, 'wb') as sink:
                with pa.ipc.new_file(sink, table.schema) as writer:
                    writer.write_table(table)

        elif file_format == 'feather':
            feather.write_feather(table, file_path, compression=compression_str)

        elif file_format == 'json':
            df = table.to_pandas()
            df.to_json(file_path, orient='records', lines=True)

        else:
            raise ValueError(f"unsupported output format: {file_format}")


class ArrowValidator:
    """Validates Arrow files."""

    def __init__(self) -> None:
        self.validation_count = 0

    def validate_file(
        self,
        file_path: str,
        expected_schema: Optional[pa.Schema] = None,
        check_nulls: bool = True
    ) -> ValidationResult:
        """
        Validate Arrow file.

        Args:
            file_path: File to validate
            expected_schema: Expected Arrow schema (if any)
            check_nulls: Check for null values

        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(
            valid=True,
            file_path=file_path,
            file_format="",
            file_size_bytes=0,
            row_count=0,
            column_count=0
        )

        try:
            path = Path(file_path)
            if not path.exists():
                result.valid = False
                result.errors.append(f"file not found: {file_path}")
                return result

            result.file_size_bytes = path.stat().st_size
            result.file_format = self._detect_format(path)

            # Read file
            table = self._read_file(file_path, result.file_format)

            result.row_count = table.num_rows
            result.column_count = table.num_columns

            # Extract schema
            schema_dict = {}
            for field in table.schema:
                schema_dict[field.name] = str(field.type)
            result.schema = schema_dict

            # Extract metadata
            if table.schema.metadata:
                result.metadata = {k.decode('utf-8'): v.decode('utf-8')
                                   for k, v in table.schema.metadata.items()}
            else:
                result.metadata = {}

            # Validate against expected schema
            if expected_schema:
                if not table.schema.equals(expected_schema):
                    result.valid = False
                    result.errors.append("schema mismatch")

                    # Detailed comparison
                    expected_fields = {f.name: f.type for f in expected_schema}
                    actual_fields = {f.name: f.type for f in table.schema}

                    missing = set(expected_fields.keys()) - set(actual_fields.keys())
                    if missing:
                        result.errors.append(f"missing columns: {', '.join(missing)}")

                    extra = set(actual_fields.keys()) - set(expected_fields.keys())
                    if extra:
                        result.warnings.append(f"extra columns: {', '.join(extra)}")

                    for name in set(expected_fields.keys()) & set(actual_fields.keys()):
                        if expected_fields[name] != actual_fields[name]:
                            result.errors.append(
                                f"column '{name}' type mismatch: "
                                f"expected {expected_fields[name]}, got {actual_fields[name]}"
                            )

            # Check for nulls
            if check_nulls:
                for i, column in enumerate(table.columns):
                    null_count = column.null_count
                    if null_count > 0:
                        col_name = table.schema.names[i]
                        null_pct = (null_count / table.num_rows * 100) if table.num_rows > 0 else 0
                        result.warnings.append(
                            f"column '{col_name}' has {null_count} nulls ({null_pct:.1f}%)"
                        )

            # Detect compression for Parquet
            if result.file_format == 'parquet':
                try:
                    parquet_file = pq.ParquetFile(file_path)
                    result.compression = parquet_file.metadata.row_group(0).column(0).compression
                except Exception:
                    pass

            self.validation_count += 1

        except Exception as e:
            result.valid = False
            result.errors.append(f"validation failed: {e}")

        return result

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        suffix = path.suffix.lower()
        format_map = {
            '.csv': 'csv',
            '.parquet': 'parquet',
            '.pq': 'parquet',
            '.arrow': 'arrow',
            '.feather': 'feather',
            '.json': 'json'
        }
        return format_map.get(suffix, 'unknown')

    def _read_file(self, file_path: str, file_format: str) -> pa.Table:
        """Read file into Arrow table."""
        if file_format == 'csv':
            return csv.read_csv(file_path)
        elif file_format == 'parquet':
            return pq.read_table(file_path)
        elif file_format == 'arrow':
            with pa.memory_map(file_path, 'r') as source:
                return pa.ipc.open_file(source).read_all()
        elif file_format == 'feather':
            return feather.read_table(file_path)
        elif file_format == 'json':
            import pandas as pd
            df = pd.read_json(file_path)
            return pa.Table.from_pandas(df)
        else:
            raise ValueError(f"unsupported format: {file_format}")


class ArrowInspector:
    """Inspects Arrow files."""

    def __init__(self) -> None:
        self.inspection_count = 0

    def inspect_file(
        self,
        file_path: str,
        compute_stats: bool = True,
        sample_size: int = 10000
    ) -> InspectionResult:
        """
        Inspect Arrow file and compute statistics.

        Args:
            file_path: File to inspect
            compute_stats: Whether to compute column statistics
            sample_size: Number of rows to sample for statistics

        Returns:
            InspectionResult with inspection details
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")

        file_format = self._detect_format(path)
        file_size = path.stat().st_size

        # Read file
        table = self._read_file(file_path, file_format)

        # Extract schema
        schema_dict = {}
        for field in table.schema:
            schema_dict[field.name] = str(field.type)

        # Extract metadata
        metadata = {}
        if table.schema.metadata:
            metadata = {k.decode('utf-8'): v.decode('utf-8')
                       for k, v in table.schema.metadata.items()}

        # Compute column statistics
        column_stats: List[ColumnStatistics] = []
        if compute_stats:
            sample = table
            if table.num_rows > sample_size:
                indices = pa.array(range(0, table.num_rows, max(1, table.num_rows // sample_size)))
                sample = table.take(indices)

            for i, column in enumerate(sample.columns):
                col_name = table.schema.names[i]
                col_type = str(table.schema.types[i])
                null_count = column.null_count
                null_pct = (null_count / sample.num_rows * 100) if sample.num_rows > 0 else 0

                stats = ColumnStatistics(
                    name=col_name,
                    type=col_type,
                    null_count=null_count,
                    null_percentage=null_pct
                )

                # Compute min/max for numeric types
                if pa.types.is_integer(column.type) or pa.types.is_floating(column.type):
                    try:
                        non_null = column.drop_null()
                        if len(non_null) > 0:
                            stats.min_value = non_null.to_pylist()[0]  # Approximate
                            stats.max_value = non_null.to_pylist()[0]
                            for val in non_null.to_pylist():
                                if val < stats.min_value:
                                    stats.min_value = val
                                if val > stats.max_value:
                                    stats.max_value = val
                    except Exception:
                        pass

                # Compute distinct count (approximate)
                try:
                    stats.distinct_count = len(set(column.to_pylist()))
                except Exception:
                    pass

                column_stats.append(stats)

        # Detect compression
        compression = None
        if file_format == 'parquet':
            try:
                parquet_file = pq.ParquetFile(file_path)
                compression = parquet_file.metadata.row_group(0).column(0).compression
            except Exception:
                pass

        # Estimate memory usage
        memory_usage = table.nbytes

        self.inspection_count += 1

        return InspectionResult(
            file_path=file_path,
            file_format=file_format,
            file_size_bytes=file_size,
            row_count=table.num_rows,
            column_count=table.num_columns,
            schema=schema_dict,
            column_stats=column_stats,
            metadata=metadata,
            memory_usage_bytes=memory_usage,
            compression=compression
        )

    def _detect_format(self, path: Path) -> str:
        """Detect file format from extension."""
        suffix = path.suffix.lower()
        format_map = {
            '.csv': 'csv',
            '.parquet': 'parquet',
            '.pq': 'parquet',
            '.arrow': 'arrow',
            '.feather': 'feather',
            '.json': 'json'
        }
        return format_map.get(suffix, 'unknown')

    def _read_file(self, file_path: str, file_format: str) -> pa.Table:
        """Read file into Arrow table."""
        if file_format == 'csv':
            return csv.read_csv(file_path)
        elif file_format == 'parquet':
            return pq.read_table(file_path)
        elif file_format == 'arrow':
            with pa.memory_map(file_path, 'r') as source:
                return pa.ipc.open_file(source).read_all()
        elif file_format == 'feather':
            return feather.read_table(file_path)
        elif file_format == 'json':
            import pandas as pd
            df = pd.read_json(file_path)
            return pa.Table.from_pandas(df)
        else:
            raise ValueError(f"unsupported format: {file_format}")


class ArrowBatchProcessor:
    """Batch processes Arrow files."""

    def __init__(self) -> None:
        self.batch_count = 0

    def process_batch(
        self,
        input_dir: str,
        output_dir: str,
        output_format: FileFormat,
        compression: CompressionType = CompressionType.SNAPPY,
        parallel: int = 1,
        pattern: str = "*.*"
    ) -> BatchResult:
        """
        Batch process files from input to output directory.

        Args:
            input_dir: Input directory
            output_dir: Output directory
            output_format: Target output format
            compression: Compression type
            parallel: Number of parallel workers
            pattern: File pattern to match

        Returns:
            BatchResult with batch processing results
        """
        start_time = time.perf_counter()

        result = BatchResult(
            success=False,
            total_files=0,
            processed_files=0,
            failed_files=0,
            total_input_bytes=0,
            total_output_bytes=0,
            total_time_s=0.0,
            average_time_ms=0.0,
            throughput_mb_s=0.0
        )

        try:
            input_path = Path(input_dir)
            output_path = Path(output_dir)

            if not input_path.exists():
                result.errors.append(("", f"input directory not found: {input_dir}"))
                return result

            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Find all files
            files = list(input_path.glob(pattern))
            result.total_files = len(files)

            if result.total_files == 0:
                result.errors.append(("", f"no files found matching pattern: {pattern}"))
                return result

            converter = ArrowConverter()

            # Process files
            if parallel > 1:
                # Parallel processing
                with ProcessPoolExecutor(max_workers=parallel) as executor:
                    futures = {}
                    for input_file in files:
                        output_file = output_path / f"{input_file.stem}.{output_format.value}"
                        future = executor.submit(
                            converter.convert_file,
                            str(input_file),
                            str(output_file),
                            compression
                        )
                        futures[future] = str(input_file)

                    for future in as_completed(futures):
                        input_file = futures[future]
                        try:
                            conv_result = future.result()
                            if conv_result.success:
                                result.processed_files += 1
                                result.total_input_bytes += conv_result.input_size_bytes
                                result.total_output_bytes += conv_result.output_size_bytes
                            else:
                                result.failed_files += 1
                                for error in conv_result.errors:
                                    result.errors.append((input_file, error))
                        except Exception as e:
                            result.failed_files += 1
                            result.errors.append((input_file, str(e)))

            else:
                # Sequential processing
                for input_file in files:
                    output_file = output_path / f"{input_file.stem}.{output_format.value}"
                    try:
                        conv_result = converter.convert_file(
                            str(input_file),
                            str(output_file),
                            compression
                        )
                        if conv_result.success:
                            result.processed_files += 1
                            result.total_input_bytes += conv_result.input_size_bytes
                            result.total_output_bytes += conv_result.output_size_bytes
                        else:
                            result.failed_files += 1
                            for error in conv_result.errors:
                                result.errors.append((str(input_file), error))
                    except Exception as e:
                        result.failed_files += 1
                        result.errors.append((str(input_file), str(e)))

            elapsed_s = time.perf_counter() - start_time
            result.total_time_s = elapsed_s

            if result.processed_files > 0:
                result.average_time_ms = (elapsed_s * 1000) / result.processed_files
                input_mb = result.total_input_bytes / (1024 * 1024)
                result.throughput_mb_s = input_mb / elapsed_s if elapsed_s > 0 else 0.0

            result.success = result.failed_files == 0

            self.batch_count += 1

        except Exception as e:
            result.errors.append(("", f"batch processing failed: {e}"))

        return result


def format_output(data: Any, output_format: OutputFormat) -> str:
    """Format output based on specified format."""
    if output_format == OutputFormat.JSON:
        if hasattr(data, '__dict__'):
            return json.dumps(asdict(data), indent=2, default=str)
        return json.dumps(data, indent=2, default=str)

    elif output_format == OutputFormat.PRETTY:
        if isinstance(data, list):
            return "\n\n".join(format_output(item, OutputFormat.PRETTY) for item in data)

        if hasattr(data, '__dict__'):
            lines = [f"{'='*60}", f"{data.__class__.__name__}", f"{'='*60}"]
            data_dict = asdict(data)
            for key, value in data_dict.items():
                if isinstance(value, list) and value:
                    lines.append(f"\n{key}:")
                    for item in value[:10]:
                        if hasattr(item, '__dict__'):
                            item_str = str(item).replace('\n', '\n    ')
                            lines.append(f"  - {item_str}")
                        else:
                            lines.append(f"  - {item}")
                    if len(value) > 10:
                        lines.append(f"  ... and {len(value) - 10} more")
                elif isinstance(value, dict):
                    lines.append(f"\n{key}:")
                    for k, v in list(value.items())[:10]:
                        lines.append(f"  {k}: {v}")
                    if len(value) > 10:
                        lines.append(f"  ... and {len(value) - 10} more")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)

        return str(data)

    else:  # TEXT
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)


def cmd_convert(args: argparse.Namespace) -> int:
    """Execute convert command."""
    converter = ArrowConverter()

    compression = CompressionType(args.compression) if args.compression else CompressionType.SNAPPY

    result = converter.convert_file(
        args.input,
        args.output,
        compression=compression,
        chunk_size=args.chunk_size
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.success else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute validate command."""
    validator = ArrowValidator()

    expected_schema = None
    if args.schema:
        try:
            with open(args.schema, 'r') as f:
                schema_dict = json.load(f)
                fields = [pa.field(name, pa.type_for_alias(dtype))
                         for name, dtype in schema_dict.items()]
                expected_schema = pa.schema(fields)
        except Exception as e:
            print(f"Error loading schema: {e}", file=sys.stderr)
            return 1

    result = validator.validate_file(
        args.file,
        expected_schema=expected_schema,
        check_nulls=args.check_nulls
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.valid else 1


def cmd_inspect(args: argparse.Namespace) -> int:
    """Execute inspect command."""
    inspector = ArrowInspector()

    result = inspector.inspect_file(
        args.file,
        compute_stats=args.stats,
        sample_size=args.sample_size
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Execute batch command."""
    processor = ArrowBatchProcessor()

    output_format = FileFormat(args.output_format)
    compression = CompressionType(args.compression)

    result = processor.process_batch(
        args.input_dir,
        args.output_dir,
        output_format=output_format,
        compression=compression,
        parallel=args.parallel,
        pattern=args.pattern
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.success else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Arrow Format Converter for PyO3 Data Science",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json', 'pretty'],
        default='pretty',
        help='output format (default: pretty)'
    )

    subparsers = parser.add_subparsers(dest='command', help='command to execute')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='convert between formats')
    convert_parser.add_argument('input', help='input file path')
    convert_parser.add_argument('output', help='output file path')
    convert_parser.add_argument('--compression', choices=['none', 'snappy', 'gzip', 'brotli', 'lz4', 'zstd'],
                                default='snappy', help='compression type (default: snappy)')
    convert_parser.add_argument('--chunk-size', type=int, default=1000000,
                                help='chunk size for processing (default: 1000000)')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='validate Arrow file')
    validate_parser.add_argument('file', help='file to validate')
    validate_parser.add_argument('--schema', help='expected schema JSON file')
    validate_parser.add_argument('--check-nulls', action='store_true', help='check for null values')

    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='inspect Arrow file')
    inspect_parser.add_argument('file', help='file to inspect')
    inspect_parser.add_argument('--stats', action='store_true', help='compute column statistics')
    inspect_parser.add_argument('--sample-size', type=int, default=10000,
                                help='sample size for statistics (default: 10000)')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='batch process files')
    batch_parser.add_argument('input_dir', help='input directory')
    batch_parser.add_argument('output_dir', help='output directory')
    batch_parser.add_argument('--output-format', choices=['csv', 'parquet', 'arrow', 'feather', 'json'],
                              default='parquet', help='output format (default: parquet)')
    batch_parser.add_argument('--compression', choices=['none', 'snappy', 'gzip', 'brotli', 'lz4', 'zstd'],
                              default='snappy', help='compression type (default: snappy)')
    batch_parser.add_argument('--parallel', type=int, default=1,
                              help='number of parallel workers (default: 1)')
    batch_parser.add_argument('--pattern', default='*.*',
                              help='file pattern to match (default: *.*)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'convert':
            return cmd_convert(args)
        elif args.command == 'validate':
            return cmd_validate(args)
        elif args.command == 'inspect':
            return cmd_inspect(args)
        elif args.command == 'batch':
            return cmd_batch(args)
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
