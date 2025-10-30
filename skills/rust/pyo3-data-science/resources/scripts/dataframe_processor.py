#!/usr/bin/env python3
"""
DataFrame Processor for PyO3 Data Science

Comprehensive DataFrame analysis, profiling, groupby operations, and performance
comparison utilities for PyO3 Rust-Python interop with Pandas and Polars.

Usage:
    dataframe_processor.py analyze <file> [options]
    dataframe_processor.py profile <file> [options]
    dataframe_processor.py groupby <file> <columns> <aggregations> [options]
    dataframe_processor.py compare <file> <operation> [options]
    dataframe_processor.py validate <file> [options]

Examples:
    dataframe_processor.py analyze data.csv --summary
    dataframe_processor.py profile data.parquet --memory
    dataframe_processor.py groupby data.csv "category,region" "sales:sum,count:count"
    dataframe_processor.py compare data.csv groupby --iterations 100
    dataframe_processor.py validate data.csv --schema schema.json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Set

try:
    import pandas as pd
    from pandas import DataFrame
except ImportError:
    print("Error: Pandas is required. Install with: uv add pandas", file=sys.stderr)
    sys.exit(1)

try:
    import polars as pl
except ImportError:
    pl = None  # Polars is optional


class OutputFormat(Enum):
    """Supported output formats."""
    TEXT = "text"
    JSON = "json"
    PRETTY = "pretty"
    TABLE = "table"


class AggregationType(Enum):
    """Supported aggregation types."""
    SUM = "sum"
    MEAN = "mean"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    STD = "std"
    VAR = "var"
    MEDIAN = "median"
    FIRST = "first"
    LAST = "last"


@dataclass
class ColumnStats:
    """Statistics for a single column."""
    name: str
    dtype: str
    count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    memory_usage_bytes: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    quantiles: Optional[Dict[str, float]] = None


@dataclass
class DataFrameAnalysis:
    """Complete DataFrame analysis result."""
    file_path: str
    row_count: int
    column_count: int
    total_memory_bytes: int
    total_null_count: int
    total_null_percentage: float
    dtypes_summary: Dict[str, int]
    columns: List[ColumnStats]
    duplicated_rows: int
    analysis_time_ms: float


@dataclass
class DataFrameProfile:
    """DataFrame profiling result."""
    file_path: str
    row_count: int
    column_count: int
    memory_usage_breakdown: Dict[str, int]
    column_correlations: Optional[Dict[str, Dict[str, float]]] = None
    missing_data_patterns: Optional[Dict[str, Any]] = None
    data_quality_score: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)
    profiling_time_ms: float = 0.0


@dataclass
class GroupByResult:
    """Result of groupby operation."""
    success: bool
    group_columns: List[str]
    aggregations: Dict[str, str]
    result_rows: int
    result_columns: int
    execution_time_ms: float
    memory_usage_bytes: int
    errors: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Performance comparison result between Pandas and Polars."""
    operation: str
    file_path: str
    iterations: int
    pandas_mean_ms: float
    pandas_std_ms: float
    polars_mean_ms: Optional[float] = None
    polars_std_ms: Optional[float] = None
    speedup_factor: Optional[float] = None
    winner: Optional[str] = None


@dataclass
class ValidationResult:
    """DataFrame validation result."""
    valid: bool
    file_path: str
    row_count: int
    column_count: int
    expected_columns: Optional[List[str]] = None
    missing_columns: List[str] = field(default_factory=list)
    extra_columns: List[str] = field(default_factory=list)
    schema_errors: List[str] = field(default_factory=list)
    data_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DataFrameAnalyzer:
    """Analyzes DataFrames for structure and content."""

    def __init__(self) -> None:
        self.analysis_count = 0

    def analyze_dataframe(
        self,
        df: DataFrame,
        file_path: str,
        include_quantiles: bool = True
    ) -> DataFrameAnalysis:
        """
        Perform comprehensive DataFrame analysis.

        Args:
            df: DataFrame to analyze
            file_path: Source file path
            include_quantiles: Whether to compute quantiles for numeric columns

        Returns:
            DataFrameAnalysis with complete analysis
        """
        start_time = time.perf_counter()

        # Basic stats
        row_count = len(df)
        column_count = len(df.columns)
        total_memory = df.memory_usage(deep=True).sum()
        total_null = df.isnull().sum().sum()
        total_null_pct = (total_null / (row_count * column_count) * 100) if row_count > 0 else 0.0

        # Dtype summary
        dtypes_summary = df.dtypes.value_counts().to_dict()
        dtypes_summary = {str(k): int(v) for k, v in dtypes_summary.items()}

        # Column-level analysis
        columns_stats: List[ColumnStats] = []
        for col in df.columns:
            col_data = df[col]
            col_dtype = str(col_data.dtype)
            col_count = col_data.count()
            col_null = col_data.isnull().sum()
            col_null_pct = (col_null / row_count * 100) if row_count > 0 else 0.0
            col_unique = col_data.nunique()
            col_unique_pct = (col_unique / row_count * 100) if row_count > 0 else 0.0
            col_memory = col_data.memory_usage(deep=True)

            stats = ColumnStats(
                name=col,
                dtype=col_dtype,
                count=int(col_count),
                null_count=int(col_null),
                null_percentage=float(col_null_pct),
                unique_count=int(col_unique),
                unique_percentage=float(col_unique_pct),
                memory_usage_bytes=int(col_memory)
            )

            # Numeric column statistics
            if pd.api.types.is_numeric_dtype(col_data):
                try:
                    stats.min_value = float(col_data.min())
                    stats.max_value = float(col_data.max())
                    stats.mean = float(col_data.mean())
                    stats.median = float(col_data.median())
                    stats.std = float(col_data.std())

                    if include_quantiles:
                        quantiles = col_data.quantile([0.25, 0.50, 0.75]).to_dict()
                        stats.quantiles = {f"q{int(k*100)}": float(v) for k, v in quantiles.items()}
                except Exception:
                    pass  # Skip if computation fails

            # String column statistics
            elif pd.api.types.is_string_dtype(col_data) or pd.api.types.is_object_dtype(col_data):
                try:
                    non_null = col_data.dropna()
                    if len(non_null) > 0:
                        str_lengths = non_null.astype(str).str.len()
                        stats.min_value = int(str_lengths.min())
                        stats.max_value = int(str_lengths.max())
                        stats.mean = float(str_lengths.mean())
                except Exception:
                    pass

            columns_stats.append(stats)

        # Duplicated rows
        duplicated = df.duplicated().sum()

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self.analysis_count += 1

        return DataFrameAnalysis(
            file_path=file_path,
            row_count=row_count,
            column_count=column_count,
            total_memory_bytes=int(total_memory),
            total_null_count=int(total_null),
            total_null_percentage=float(total_null_pct),
            dtypes_summary=dtypes_summary,
            columns=columns_stats,
            duplicated_rows=int(duplicated),
            analysis_time_ms=elapsed_ms
        )

    def infer_column_types(self, df: DataFrame) -> Dict[str, str]:
        """
        Infer semantic column types beyond pandas dtypes.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary mapping column names to inferred types
        """
        inferred_types: Dict[str, str] = {}

        for col in df.columns:
            col_data = df[col].dropna()

            if len(col_data) == 0:
                inferred_types[col] = "empty"
                continue

            dtype = df[col].dtype

            # Numeric types
            if pd.api.types.is_integer_dtype(dtype):
                # Check if it's an ID column
                if col_data.nunique() == len(col_data):
                    inferred_types[col] = "id"
                else:
                    inferred_types[col] = "integer"

            elif pd.api.types.is_float_dtype(dtype):
                inferred_types[col] = "float"

            # Datetime types
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                inferred_types[col] = "datetime"

            # String/object types
            elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
                unique_ratio = col_data.nunique() / len(col_data)

                # Try to parse as datetime
                try:
                    pd.to_datetime(col_data.head(100))
                    inferred_types[col] = "datetime_string"
                    continue
                except Exception:
                    pass

                # Categorical if low cardinality
                if unique_ratio < 0.05:
                    inferred_types[col] = "categorical"
                elif unique_ratio > 0.95:
                    inferred_types[col] = "unique_string"
                else:
                    inferred_types[col] = "string"

            # Boolean types
            elif pd.api.types.is_bool_dtype(dtype):
                inferred_types[col] = "boolean"

            else:
                inferred_types[col] = "unknown"

        return inferred_types


class DataFrameProfiler:
    """Profiles DataFrames for data quality and patterns."""

    def __init__(self) -> None:
        self.profile_count = 0

    def profile_dataframe(
        self,
        df: DataFrame,
        file_path: str,
        include_correlations: bool = True,
        include_patterns: bool = True
    ) -> DataFrameProfile:
        """
        Create comprehensive DataFrame profile.

        Args:
            df: DataFrame to profile
            file_path: Source file path
            include_correlations: Compute column correlations
            include_patterns: Analyze missing data patterns

        Returns:
            DataFrameProfile with profiling results
        """
        start_time = time.perf_counter()

        row_count = len(df)
        column_count = len(df.columns)

        # Memory usage breakdown
        memory_breakdown = df.memory_usage(deep=True).to_dict()
        memory_breakdown = {str(k): int(v) for k, v in memory_breakdown.items()}

        # Column correlations for numeric columns
        correlations = None
        if include_correlations:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                correlations = {}
                for col in numeric_cols:
                    correlations[col] = corr_matrix[col].to_dict()
                    correlations[col] = {str(k): float(v) for k, v in correlations[col].items()}

        # Missing data patterns
        missing_patterns = None
        if include_patterns:
            null_counts = df.isnull().sum()
            cols_with_nulls = null_counts[null_counts > 0]
            if len(cols_with_nulls) > 0:
                missing_patterns = {
                    "columns_with_missing": cols_with_nulls.to_dict(),
                    "rows_with_any_missing": int(df.isnull().any(axis=1).sum()),
                    "rows_with_all_missing": int(df.isnull().all(axis=1).sum())
                }
                missing_patterns["columns_with_missing"] = {
                    str(k): int(v) for k, v in missing_patterns["columns_with_missing"].items()
                }

        # Data quality score (0-100)
        quality_score = self._calculate_quality_score(df)

        # Recommendations
        recommendations = self._generate_recommendations(df)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self.profile_count += 1

        return DataFrameProfile(
            file_path=file_path,
            row_count=row_count,
            column_count=column_count,
            memory_usage_breakdown=memory_breakdown,
            column_correlations=correlations,
            missing_data_patterns=missing_patterns,
            data_quality_score=quality_score,
            recommendations=recommendations,
            profiling_time_ms=elapsed_ms
        )

    def _calculate_quality_score(self, df: DataFrame) -> float:
        """Calculate data quality score (0-100)."""
        score = 100.0

        # Penalize missing data
        null_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        score -= null_ratio * 30

        # Penalize duplicate rows
        dup_ratio = df.duplicated().sum() / len(df) if len(df) > 0 else 0
        score -= dup_ratio * 20

        # Penalize columns with very low variance
        numeric_cols = df.select_dtypes(include=['number']).columns
        low_variance_count = 0
        for col in numeric_cols:
            if df[col].std() == 0:
                low_variance_count += 1
        if len(numeric_cols) > 0:
            low_var_ratio = low_variance_count / len(numeric_cols)
            score -= low_var_ratio * 10

        return max(0.0, min(100.0, score))

    def _generate_recommendations(self, df: DataFrame) -> List[str]:
        """Generate recommendations for DataFrame optimization."""
        recommendations: List[str] = []

        # Check for columns that should be categorical
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                unique_ratio = df[col].nunique() / len(df) if len(df) > 0 else 0
                if unique_ratio < 0.05:
                    recommendations.append(
                        f"Convert '{col}' to categorical dtype (unique ratio: {unique_ratio:.2%})"
                    )

        # Check for datetime strings
        for col in df.select_dtypes(include=['object']).columns:
            try:
                sample = df[col].dropna().head(100)
                if len(sample) > 0:
                    pd.to_datetime(sample)
                    recommendations.append(f"Convert '{col}' to datetime dtype")
            except Exception:
                pass

        # Check for missing data
        null_cols = df.columns[df.isnull().any()].tolist()
        if null_cols:
            recommendations.append(
                f"Handle missing data in {len(null_cols)} columns: {', '.join(null_cols[:3])}"
            )

        # Check for duplicate rows
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            recommendations.append(f"Remove {dup_count} duplicate rows")

        # Check for memory optimization
        memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        if memory_mb > 100:
            recommendations.append(
                f"Optimize memory usage (current: {memory_mb:.1f} MB) by downcasting numeric types"
            )

        return recommendations


class DataFrameGroupBy:
    """Performs groupby operations on DataFrames."""

    def __init__(self) -> None:
        self.operation_count = 0

    def groupby_aggregate(
        self,
        df: DataFrame,
        group_columns: List[str],
        aggregations: Dict[str, str]
    ) -> GroupByResult:
        """
        Perform groupby with aggregations.

        Args:
            df: DataFrame to group
            group_columns: Columns to group by
            aggregations: Dict mapping column to aggregation function

        Returns:
            GroupByResult with operation results
        """
        start_time = time.perf_counter()
        result = GroupByResult(
            success=False,
            group_columns=group_columns,
            aggregations=aggregations,
            result_rows=0,
            result_columns=0,
            execution_time_ms=0.0,
            memory_usage_bytes=0
        )

        try:
            # Validate group columns
            for col in group_columns:
                if col not in df.columns:
                    result.errors.append(f"group column '{col}' not found")
                    return result

            # Validate aggregation columns
            for col in aggregations.keys():
                if col not in df.columns:
                    result.errors.append(f"aggregation column '{col}' not found")
                    return result

            # Perform groupby
            grouped = df.groupby(group_columns)
            agg_result = grouped.agg(aggregations)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            result.success = True
            result.result_rows = len(agg_result)
            result.result_columns = len(agg_result.columns)
            result.execution_time_ms = elapsed_ms
            result.memory_usage_bytes = agg_result.memory_usage(deep=True).sum()

            self.operation_count += 1

        except Exception as e:
            result.errors.append(f"groupby failed: {e}")

        return result


class DataFrameComparator:
    """Compares performance between Pandas and Polars."""

    def __init__(self) -> None:
        self.comparison_count = 0

    def compare_read_performance(
        self,
        file_path: str,
        iterations: int = 10
    ) -> ComparisonResult:
        """Compare DataFrame read performance."""
        operation = "read_file"

        # Pandas timing
        pandas_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            if file_path.endswith('.csv'):
                pd.read_csv(file_path)
            elif file_path.endswith('.parquet'):
                pd.read_parquet(file_path)
            else:
                raise ValueError(f"unsupported file format")
            elapsed = (time.perf_counter() - start) * 1000
            pandas_times.append(elapsed)

        pandas_mean = sum(pandas_times) / len(pandas_times)
        pandas_std = (sum((x - pandas_mean) ** 2 for x in pandas_times) / len(pandas_times)) ** 0.5

        # Polars timing (if available)
        polars_mean = None
        polars_std = None
        speedup = None
        winner = "pandas"

        if pl is not None:
            polars_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                if file_path.endswith('.csv'):
                    pl.read_csv(file_path)
                elif file_path.endswith('.parquet'):
                    pl.read_parquet(file_path)
                elapsed = (time.perf_counter() - start) * 1000
                polars_times.append(elapsed)

            polars_mean = sum(polars_times) / len(polars_times)
            polars_std = (sum((x - polars_mean) ** 2 for x in polars_times) / len(polars_times)) ** 0.5
            speedup = pandas_mean / polars_mean if polars_mean > 0 else None
            winner = "polars" if speedup and speedup > 1.0 else "pandas"

        self.comparison_count += 1

        return ComparisonResult(
            operation=operation,
            file_path=file_path,
            iterations=iterations,
            pandas_mean_ms=pandas_mean,
            pandas_std_ms=pandas_std,
            polars_mean_ms=polars_mean,
            polars_std_ms=polars_std,
            speedup_factor=speedup,
            winner=winner
        )

    def compare_groupby_performance(
        self,
        df: DataFrame,
        group_columns: List[str],
        aggregations: Dict[str, str],
        iterations: int = 10
    ) -> ComparisonResult:
        """Compare groupby performance."""
        operation = "groupby"

        # Pandas timing
        pandas_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            df.groupby(group_columns).agg(aggregations)
            elapsed = (time.perf_counter() - start) * 1000
            pandas_times.append(elapsed)

        pandas_mean = sum(pandas_times) / len(pandas_times)
        pandas_std = (sum((x - pandas_mean) ** 2 for x in pandas_times) / len(pandas_times)) ** 0.5

        # Polars timing (if available)
        polars_mean = None
        polars_std = None
        speedup = None
        winner = "pandas"

        if pl is not None:
            pl_df = pl.from_pandas(df)
            pl_agg = [pl.col(col).agg_func() for col, agg_func in aggregations.items()]

            polars_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                pl_df.group_by(group_columns).agg(pl_agg)
                elapsed = (time.perf_counter() - start) * 1000
                polars_times.append(elapsed)

            polars_mean = sum(polars_times) / len(polars_times)
            polars_std = (sum((x - polars_mean) ** 2 for x in polars_times) / len(polars_times)) ** 0.5
            speedup = pandas_mean / polars_mean if polars_mean > 0 else None
            winner = "polars" if speedup and speedup > 1.0 else "pandas"

        self.comparison_count += 1

        return ComparisonResult(
            operation=operation,
            file_path="<in-memory>",
            iterations=iterations,
            pandas_mean_ms=pandas_mean,
            pandas_std_ms=pandas_std,
            polars_mean_ms=polars_mean,
            polars_std_ms=polars_std,
            speedup_factor=speedup,
            winner=winner
        )


class DataFrameValidator:
    """Validates DataFrames against schemas and constraints."""

    def __init__(self) -> None:
        self.validation_count = 0

    def validate_dataframe(
        self,
        df: DataFrame,
        file_path: str,
        schema: Optional[Dict[str, Any]] = None,
        check_nulls: bool = True,
        check_duplicates: bool = True
    ) -> ValidationResult:
        """
        Validate DataFrame against schema and constraints.

        Args:
            df: DataFrame to validate
            file_path: Source file path
            schema: Expected schema (columns and types)
            check_nulls: Check for unexpected null values
            check_duplicates: Check for duplicate rows

        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(
            valid=True,
            file_path=file_path,
            row_count=len(df),
            column_count=len(df.columns)
        )

        # Schema validation
        if schema:
            expected_cols = set(schema.get('columns', []))
            actual_cols = set(df.columns)

            result.expected_columns = list(expected_cols)
            result.missing_columns = list(expected_cols - actual_cols)
            result.extra_columns = list(actual_cols - expected_cols)

            if result.missing_columns:
                result.valid = False
                result.schema_errors.append(
                    f"missing columns: {', '.join(result.missing_columns)}"
                )

            if result.extra_columns:
                result.warnings.append(
                    f"extra columns: {', '.join(result.extra_columns)}"
                )

            # Validate dtypes
            expected_types = schema.get('types', {})
            for col, expected_type in expected_types.items():
                if col in df.columns:
                    actual_type = str(df[col].dtype)
                    if not self._types_compatible(actual_type, expected_type):
                        result.valid = False
                        result.schema_errors.append(
                            f"column '{col}' type mismatch: expected {expected_type}, got {actual_type}"
                        )

        # Null checks
        if check_nulls:
            null_counts = df.isnull().sum()
            cols_with_nulls = null_counts[null_counts > 0]
            if len(cols_with_nulls) > 0:
                result.warnings.append(
                    f"{len(cols_with_nulls)} columns contain null values"
                )

        # Duplicate checks
        if check_duplicates:
            dup_count = df.duplicated().sum()
            if dup_count > 0:
                result.warnings.append(f"{dup_count} duplicate rows found")

        self.validation_count += 1

        return result

    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if actual type is compatible with expected type."""
        type_groups = {
            'int': ['int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64'],
            'float': ['float32', 'float64'],
            'string': ['object', 'string'],
            'bool': ['bool'],
            'datetime': ['datetime64']
        }

        for group_name, group_types in type_groups.items():
            if expected in group_types or expected == group_name:
                return any(t in actual for t in group_types)

        return actual == expected


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
                    for item in value[:10]:  # Limit to first 10
                        if hasattr(item, '__dict__'):
                            lines.append(f"  - {item}")
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


def load_dataframe(file_path: str) -> DataFrame:
    """Load DataFrame from file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")

    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.parquet'):
        return pd.read_parquet(file_path)
    elif file_path.endswith('.json'):
        return pd.read_json(file_path)
    else:
        raise ValueError(f"unsupported file format: {path.suffix}")


def cmd_analyze(args: argparse.Namespace) -> int:
    """Execute analyze command."""
    try:
        df = load_dataframe(args.file)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        return 1

    analyzer = DataFrameAnalyzer()
    result = analyzer.analyze_dataframe(
        df,
        args.file,
        include_quantiles=args.quantiles
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """Execute profile command."""
    try:
        df = load_dataframe(args.file)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        return 1

    profiler = DataFrameProfiler()
    result = profiler.profile_dataframe(
        df,
        args.file,
        include_correlations=args.correlations,
        include_patterns=args.patterns
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0


def cmd_groupby(args: argparse.Namespace) -> int:
    """Execute groupby command."""
    try:
        df = load_dataframe(args.file)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        return 1

    # Parse group columns
    group_columns = [col.strip() for col in args.columns.split(',')]

    # Parse aggregations (format: "col:agg,col:agg")
    agg_pairs = [pair.strip() for pair in args.aggregations.split(',')]
    aggregations = {}
    for pair in agg_pairs:
        if ':' not in pair:
            print(f"Error: invalid aggregation format: {pair}", file=sys.stderr)
            return 1
        col, agg = pair.split(':', 1)
        aggregations[col.strip()] = agg.strip()

    groupby = DataFrameGroupBy()
    result = groupby.groupby_aggregate(df, group_columns, aggregations)

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.success else 1


def cmd_compare(args: argparse.Namespace) -> int:
    """Execute compare command."""
    comparator = DataFrameComparator()

    if args.operation == 'read':
        result = comparator.compare_read_performance(args.file, args.iterations)
    else:
        print(f"Error: unsupported operation: {args.operation}", file=sys.stderr)
        return 1

    print(format_output(result, OutputFormat(args.format)))

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute validate command."""
    try:
        df = load_dataframe(args.file)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        return 1

    schema = None
    if args.schema:
        try:
            with open(args.schema, 'r') as f:
                schema = json.load(f)
        except Exception as e:
            print(f"Error loading schema: {e}", file=sys.stderr)
            return 1

    validator = DataFrameValidator()
    result = validator.validate_dataframe(
        df,
        args.file,
        schema=schema,
        check_nulls=args.check_nulls,
        check_duplicates=args.check_duplicates
    )

    print(format_output(result, OutputFormat(args.format)))

    return 0 if result.valid else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DataFrame Processor for PyO3 Data Science",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json', 'pretty', 'table'],
        default='pretty',
        help='output format (default: pretty)'
    )

    subparsers = parser.add_subparsers(dest='command', help='command to execute')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='analyze DataFrame structure and content')
    analyze_parser.add_argument('file', help='input file path')
    analyze_parser.add_argument('--quantiles', action='store_true', help='include quantiles for numeric columns')

    # Profile command
    profile_parser = subparsers.add_parser('profile', help='profile DataFrame for quality and patterns')
    profile_parser.add_argument('file', help='input file path')
    profile_parser.add_argument('--correlations', action='store_true', help='compute column correlations')
    profile_parser.add_argument('--patterns', action='store_true', help='analyze missing data patterns')

    # GroupBy command
    groupby_parser = subparsers.add_parser('groupby', help='perform groupby operations')
    groupby_parser.add_argument('file', help='input file path')
    groupby_parser.add_argument('columns', help='comma-separated group columns')
    groupby_parser.add_argument('aggregations', help='comma-separated col:agg pairs')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='compare Pandas vs Polars performance')
    compare_parser.add_argument('file', help='input file path')
    compare_parser.add_argument('operation', choices=['read', 'groupby'], help='operation to compare')
    compare_parser.add_argument('--iterations', type=int, default=10, help='iterations (default: 10)')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='validate DataFrame against schema')
    validate_parser.add_argument('file', help='input file path')
    validate_parser.add_argument('--schema', help='schema JSON file path')
    validate_parser.add_argument('--check-nulls', action='store_true', help='check for null values')
    validate_parser.add_argument('--check-duplicates', action='store_true', help='check for duplicate rows')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'analyze':
            return cmd_analyze(args)
        elif args.command == 'profile':
            return cmd_profile(args)
        elif args.command == 'groupby':
            return cmd_groupby(args)
        elif args.command == 'compare':
            return cmd_compare(args)
        elif args.command == 'validate':
            return cmd_validate(args)
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
