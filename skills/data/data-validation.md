---
name: data-data-validation
description: Validating data schema before processing
---



# Data Validation

**Scope**: Schema validation, data quality checks, anomaly detection
**Lines**: 357
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Validating data schema before processing
- Implementing data quality gates in pipelines
- Detecting anomalies and outliers in datasets
- Ensuring referential integrity across tables
- Monitoring data freshness and completeness
- Building data quality dashboards
- Working with Great Expectations, Pandera, or custom validators

## Core Concepts

### Validation Types
```
Schema Validation
  → Data types, column presence, nullable constraints
  → Use when: Incoming data format can vary
  → Tools: Pandera, Great Expectations, JSON Schema

Business Rules Validation
  → Domain-specific constraints (age > 0, email format)
  → Use when: Enforcing business logic
  → Tools: Custom validators, dbt tests

Statistical Validation
  → Distribution checks, outliers, anomalies
  → Use when: Data quality monitoring
  → Tools: Great Expectations, custom statistics

Referential Integrity
  → Foreign key constraints, cross-table checks
  → Use when: Multi-table relationships
  → Tools: SQL constraints, dbt tests
```

### Validation Strategies
```
Fail Fast
  → Stop pipeline on first error
  → Use when: Downstream depends on quality

Collect All Errors
  → Continue validation, report all issues
  → Use when: Data profiling, quality reporting

Quarantine
  → Separate valid/invalid records
  → Use when: Partial data processing acceptable

Auto-Repair
  → Fix known issues automatically
  → Use when: Predictable, fixable problems
```

### Data Quality Dimensions
```
Completeness: No missing required fields
Accuracy: Values match real-world entities
Consistency: Same value across systems
Timeliness: Data is fresh/current
Uniqueness: No duplicates where not expected
Validity: Values in expected format/range
```

## Patterns

### Pattern 1: Pandera Schema Validation (Python)

```python
import pandas as pd
import pandera as pa
from pandera import Column, Check, DataFrameSchema
from datetime import datetime

# Define schema with constraints
user_schema = DataFrameSchema(
    columns={
        "user_id": Column(
            int,
            checks=[
                Check.greater_than(0),
                Check(lambda s: s.is_unique, error="user_id must be unique")
            ],
            nullable=False
        ),
        "email": Column(
            str,
            checks=Check.str_matches(r'^[\w\.-]+@[\w\.-]+\.\w+$'),
            nullable=False
        ),
        "age": Column(
            int,
            checks=[
                Check.in_range(0, 120),
                Check(lambda s: s >= 18, error="Users must be 18+")
            ],
            nullable=True
        ),
        "created_at": Column(
            pa.DateTime,
            checks=Check.less_than_or_equal_to(datetime.now()),
            nullable=False
        ),
        "status": Column(
            str,
            checks=Check.isin(['active', 'inactive', 'suspended']),
            nullable=False
        )
    },
    strict=True,  # No extra columns allowed
    coerce=True   # Attempt type coercion
)

# Validate DataFrame
def validate_users(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Validate user data, return valid rows and errors"""
    errors = []

    try:
        # Validate entire DataFrame
        validated_df = user_schema.validate(df, lazy=True)
        return validated_df, errors

    except pa.errors.SchemaErrors as e:
        # Collect all validation errors
        for error in e.failure_cases.itertuples():
            errors.append({
                'column': error.column,
                'check': error.check,
                'index': error.index,
                'value': error.failure_case
            })

        # Return rows that passed validation
        valid_indices = set(df.index) - set(e.failure_cases['index'])
        valid_df = df.loc[list(valid_indices)]

        return valid_df, errors

# Usage
df = pd.DataFrame({
    'user_id': [1, 2, 3, 2],  # Duplicate
    'email': ['user1@example.com', 'invalid-email', 'user3@example.com', 'user4@example.com'],
    'age': [25, 15, 30, 200],  # 15 too young, 200 out of range
    'created_at': [datetime(2025, 1, 1)] * 4,
    'status': ['active', 'pending', 'inactive', 'active']  # 'pending' not in allowed
})

valid_df, errors = validate_users(df)
print(f"Valid rows: {len(valid_df)}")
print(f"Errors: {errors}")
```

### Pattern 2: Great Expectations Integration

```python
import great_expectations as gx
from great_expectations.data_context import DataContext
from great_expectations.checkpoint import SimpleCheckpoint

class GXValidator:
    def __init__(self, context_root_dir: str = None):
        """Initialize Great Expectations context"""
        if context_root_dir:
            self.context = DataContext(context_root_dir)
        else:
            self.context = gx.get_context()

    def create_expectation_suite(self, suite_name: str) -> None:
        """Create expectation suite for a dataset"""
        suite = self.context.add_expectation_suite(suite_name)

        # Define expectations
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column="user_id")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="user_id")
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeInSet(
                column="status",
                value_set=['active', 'inactive', 'suspended']
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="age",
                min_value=18,
                max_value=120
            )
        )
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToMatchRegex(
                column="email",
                regex=r'^[\w\.-]+@[\w\.-]+\.\w+$'
            )
        )

        self.context.save_expectation_suite(suite)

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        suite_name: str,
        datasource_name: str = "pandas_datasource"
    ) -> dict:
        """Validate DataFrame against expectation suite"""
        # Add datasource
        datasource = self.context.sources.add_pandas(datasource_name)
        data_asset = datasource.add_dataframe_asset(name="df_asset")

        # Create batch request
        batch_request = data_asset.build_batch_request(dataframe=df)

        # Create and run checkpoint
        checkpoint = SimpleCheckpoint(
            name="validation_checkpoint",
            data_context=self.context,
            validations=[
                {
                    "batch_request": batch_request,
                    "expectation_suite_name": suite_name
                }
            ]
        )

        result = checkpoint.run()

        return {
            'success': result.success,
            'statistics': result.statistics,
            'results': result.list_validation_results()
        }

# Usage
validator = GXValidator()
validator.create_expectation_suite("user_suite")

result = validator.validate_dataframe(df, "user_suite")
print(f"Validation success: {result['success']}")
print(f"Statistics: {result['statistics']}")
```

### Pattern 3: Custom Statistical Validation

```python
import numpy as np
from scipy import stats
from typing import Dict, Any, List
import pandas as pd

class StatisticalValidator:
    def __init__(self, baseline_stats: Dict[str, Any] = None):
        """Initialize with baseline statistics"""
        self.baseline_stats = baseline_stats or {}

    def calculate_baseline(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate baseline statistics for numeric columns"""
        baseline = {}

        for col in df.select_dtypes(include=[np.number]).columns:
            baseline[col] = {
                'mean': df[col].mean(),
                'std': df[col].std(),
                'median': df[col].median(),
                'q1': df[col].quantile(0.25),
                'q3': df[col].quantile(0.75),
                'min': df[col].min(),
                'max': df[col].max(),
                'null_rate': df[col].isnull().mean()
            }

        self.baseline_stats = baseline
        return baseline

    def detect_outliers_iqr(
        self,
        df: pd.DataFrame,
        column: str,
        multiplier: float = 1.5
    ) -> pd.Series:
        """Detect outliers using IQR method"""
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        is_outlier = (df[column] < lower_bound) | (df[column] > upper_bound)
        return is_outlier

    def detect_outliers_zscore(
        self,
        df: pd.DataFrame,
        column: str,
        threshold: float = 3.0
    ) -> pd.Series:
        """Detect outliers using Z-score method"""
        z_scores = np.abs(stats.zscore(df[column].dropna()))
        is_outlier = pd.Series([False] * len(df), index=df.index)
        is_outlier[df[column].notna()] = z_scores > threshold
        return is_outlier

    def validate_distribution(
        self,
        df: pd.DataFrame,
        column: str,
        drift_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """Check if distribution has drifted from baseline"""
        if column not in self.baseline_stats:
            return {'error': 'No baseline for column'}

        baseline = self.baseline_stats[column]
        current_mean = df[column].mean()
        current_std = df[column].std()

        # Calculate drift
        mean_drift = abs(current_mean - baseline['mean']) / baseline['mean']
        std_drift = abs(current_std - baseline['std']) / baseline['std']

        return {
            'column': column,
            'mean_drift': mean_drift,
            'std_drift': std_drift,
            'drift_detected': mean_drift > drift_threshold or std_drift > drift_threshold,
            'baseline_mean': baseline['mean'],
            'current_mean': current_mean,
            'baseline_std': baseline['std'],
            'current_std': current_std
        }

    def validate_completeness(
        self,
        df: pd.DataFrame,
        required_columns: List[str],
        max_null_rate: float = 0.05
    ) -> Dict[str, Any]:
        """Check data completeness"""
        results = {}

        for col in required_columns:
            if col not in df.columns:
                results[col] = {'error': 'Column missing'}
                continue

            null_rate = df[col].isnull().mean()
            results[col] = {
                'null_rate': null_rate,
                'passes': null_rate <= max_null_rate,
                'null_count': df[col].isnull().sum(),
                'total_count': len(df)
            }

        return results

# Usage
validator = StatisticalValidator()

# Calculate baseline from historical data
historical_df = pd.DataFrame({
    'revenue': np.random.normal(1000, 200, 10000),
    'quantity': np.random.poisson(50, 10000)
})
validator.calculate_baseline(historical_df)

# Validate new data
new_df = pd.DataFrame({
    'revenue': np.random.normal(1200, 250, 1000),  # Drifted
    'quantity': np.random.poisson(51, 1000)
})

# Check distribution drift
drift = validator.validate_distribution(new_df, 'revenue')
print(f"Distribution drift: {drift}")

# Detect outliers
outliers = validator.detect_outliers_iqr(new_df, 'revenue')
print(f"Outliers detected: {outliers.sum()}")
```

### Pattern 4: Cross-Table Validation

```python
from sqlalchemy import create_engine, text
from typing import List, Dict

class CrossTableValidator:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    def validate_referential_integrity(
        self,
        child_table: str,
        child_column: str,
        parent_table: str,
        parent_column: str
    ) -> Dict[str, Any]:
        """Check foreign key integrity"""
        query = text(f"""
            SELECT
                COUNT(*) as orphan_count,
                ARRAY_AGG(DISTINCT c.{child_column}) as orphan_values
            FROM {child_table} c
            LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
            WHERE p.{parent_column} IS NULL
                AND c.{child_column} IS NOT NULL
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query).fetchone()

            return {
                'valid': result.orphan_count == 0,
                'orphan_count': result.orphan_count,
                'orphan_values': result.orphan_values[:10]  # Sample
            }

    def validate_aggregates(
        self,
        detail_table: str,
        summary_table: str,
        group_column: str,
        agg_column: str,
        tolerance: float = 0.01
    ) -> Dict[str, Any]:
        """Validate summary table against detail table"""
        query = text(f"""
            WITH detail_agg AS (
                SELECT
                    {group_column},
                    SUM({agg_column}) as detail_sum
                FROM {detail_table}
                GROUP BY {group_column}
            ),
            comparison AS (
                SELECT
                    d.{group_column},
                    d.detail_sum,
                    s.{agg_column} as summary_sum,
                    ABS(d.detail_sum - s.{agg_column}) / NULLIF(d.detail_sum, 0) as diff_pct
                FROM detail_agg d
                FULL OUTER JOIN {summary_table} s
                    ON d.{group_column} = s.{group_column}
            )
            SELECT
                COUNT(*) as total_groups,
                SUM(CASE WHEN diff_pct > :tolerance THEN 1 ELSE 0 END) as mismatches,
                ARRAY_AGG(
                    {group_column} ORDER BY diff_pct DESC
                ) FILTER (WHERE diff_pct > :tolerance) as mismatch_groups
            FROM comparison
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {'tolerance': tolerance}).fetchone()

            return {
                'valid': result.mismatches == 0,
                'total_groups': result.total_groups,
                'mismatch_count': result.mismatches,
                'mismatch_groups': result.mismatch_groups[:10]
            }

    def validate_freshness(
        self,
        table: str,
        timestamp_column: str,
        max_age_hours: int = 24
    ) -> Dict[str, Any]:
        """Check data freshness"""
        query = text(f"""
            SELECT
                MAX({timestamp_column}) as latest_timestamp,
                EXTRACT(EPOCH FROM (NOW() - MAX({timestamp_column}))) / 3600 as age_hours
            FROM {table}
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query).fetchone()

            return {
                'valid': result.age_hours <= max_age_hours,
                'latest_timestamp': result.latest_timestamp,
                'age_hours': result.age_hours,
                'max_age_hours': max_age_hours
            }

# Usage
validator = CrossTableValidator("postgresql://user:pass@localhost/db")

# Check foreign keys
fk_result = validator.validate_referential_integrity(
    'orders', 'customer_id',
    'customers', 'id'
)
print(f"Referential integrity: {fk_result}")

# Validate aggregates
agg_result = validator.validate_aggregates(
    'order_items', 'order_totals',
    'order_id', 'amount'
)
print(f"Aggregate validation: {agg_result}")

# Check freshness
fresh_result = validator.validate_freshness(
    'events', 'created_at', max_age_hours=2
)
print(f"Data freshness: {fresh_result}")
```

## Quick Reference

### Common Validation Checks
```python
# Null checks
df['column'].isnull().any()
df['column'].notna().all()

# Uniqueness
df['column'].is_unique
df.duplicated(subset=['col1', 'col2']).any()

# Range checks
df['column'].between(min_val, max_val).all()
(df['column'] >= 0).all()

# Set membership
df['column'].isin(allowed_values).all()

# Regex pattern
df['column'].str.match(r'^pattern$').all()

# Type checks
df['column'].dtype == 'int64'
pd.api.types.is_numeric_dtype(df['column'])

# Relationships
df['col1'].sum() == df['col2'].sum()  # Balance check
```

### Pandera Quick Syntax
```python
schema = pa.DataFrameSchema({
    "col": pa.Column(int, checks=pa.Check.greater_than(0)),
    "email": pa.Column(str, checks=pa.Check.str_matches(r'@')),
    "status": pa.Column(str, checks=pa.Check.isin(['A', 'B']))
})

validated_df = schema.validate(df)
```

### Great Expectations Quick Setup
```bash
# Initialize
great_expectations init

# Create expectation suite
great_expectations suite new

# Edit expectations
great_expectations suite edit my_suite

# Run checkpoint
great_expectations checkpoint run my_checkpoint
```

## Anti-Patterns

```
❌ NEVER: Validate after transformation
   → Validate raw data first, then transform

❌ NEVER: Silently drop invalid records
   → Log, alert, or quarantine for review

❌ NEVER: Use generic error messages
   → Specify column, check, and value that failed

❌ NEVER: Validate only in production
   → Run same validations in dev/staging

❌ NEVER: Skip statistical validation
   → Check distributions, not just schema

❌ NEVER: Ignore data drift
   → Monitor and alert on statistical changes

❌ NEVER: Fail pipeline without retry logic
   → Transient issues may resolve on retry

❌ NEVER: Hardcode validation rules in code
   → Use configuration files or database

❌ NEVER: Validate samples instead of full dataset
   → Sample for profiling, validate all for quality

❌ NEVER: Skip cross-table validation
   → Verify referential integrity and aggregates
```

## Related Skills

- `etl-patterns.md` - Integrating validation into ETL
- `batch-processing.md` - Adding validation tasks to DAGs
- `stream-processing.md` - Real-time validation patterns
- `pipeline-orchestration.md` - Orchestrating validation workflows

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
