---
name: data-etl-patterns
description: Designing data extraction from multiple sources (databases, APIs, files)
---



# ETL Patterns

**Scope**: Extract-Transform-Load patterns, data sources, transformations, incremental processing
**Lines**: 312
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

## When to Use This Skill

Use this skill when:
- Designing data extraction from multiple sources (databases, APIs, files)
- Implementing transformation logic for data cleansing and enrichment
- Loading data into warehouses or data lakes
- Setting up incremental vs full load strategies
- Handling CDC (Change Data Capture) patterns
- Building batch data pipelines with Python, SQL, or dbt

## Core Concepts

### ETL vs ELT
```
ETL (Extract-Transform-Load)
  → Transform before loading (traditional warehouses)
  → Use when: Limited warehouse resources, complex transformations

ELT (Extract-Load-Transform)
  → Transform after loading (modern cloud warehouses)
  → Use when: Cloud warehouse available (Snowflake, BigQuery, Redshift)
  → Benefits: Leverage warehouse compute, raw data preservation
```

### Load Strategies
```
Full Load
  → Complete dataset replacement
  → Use when: Small datasets, no history tracking needed
  → Pattern: TRUNCATE + INSERT or DROP + CREATE  <!-- ETL operations on target tables -->

Incremental Load
  → Only new/changed records
  → Use when: Large datasets, history preservation
  → Pattern: INSERT WHERE timestamp > last_run

Upsert (Merge)
  → Insert new, update existing
  → Use when: Slowly changing dimensions
  → Pattern: MERGE or INSERT ON CONFLICT UPDATE

Append-Only
  → Always insert, never update
  → Use when: Immutable event streams
  → Pattern: INSERT with deduplication downstream
```

### Change Data Capture (CDC)
```
Trigger-based CDC
  → Database triggers capture changes
  → Overhead on source system

Log-based CDC (Recommended)
  → Read database transaction logs
  → Tools: Debezium, AWS DMS, Fivetran
  → No overhead on source

Timestamp-based CDC
  → Query by updated_at column
  → Simple but requires timestamp column
```

## Patterns

### Pattern 1: Incremental Extraction (Timestamp-based)

```python
# Python with SQLAlchemy
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import pandas as pd

class IncrementalExtractor:
    def __init__(self, source_conn_str, state_table="etl_state"):
        self.engine = create_engine(source_conn_str)
        self.state_table = state_table

    def get_last_watermark(self, table_name: str) -> datetime:
        """Retrieve last processed timestamp"""
        query = text(f"""
            SELECT max_timestamp
            FROM {self.state_table}
            WHERE table_name = :table_name
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"table_name": table_name}).fetchone()
            return result[0] if result else datetime(1970, 1, 1)

    def extract_incremental(
        self,
        table_name: str,
        timestamp_col: str = "updated_at"
    ) -> pd.DataFrame:
        """Extract records since last watermark"""
        last_watermark = self.get_last_watermark(table_name)

        query = text(f"""
            SELECT *
            FROM {table_name}
            WHERE {timestamp_col} > :watermark
            ORDER BY {timestamp_col}
        """)

        df = pd.read_sql(query, self.engine, params={"watermark": last_watermark})
        return df

    def update_watermark(self, table_name: str, new_watermark: datetime):
        """Update state after successful load"""
        query = text(f"""
            INSERT INTO {self.state_table} (table_name, max_timestamp, updated_at)
            VALUES (:table_name, :watermark, :now)
            ON CONFLICT (table_name)
            DO UPDATE SET max_timestamp = :watermark, updated_at = :now
        """)

        with self.engine.connect() as conn:
            conn.execute(query, {
                "table_name": table_name,
                "watermark": new_watermark,
                "now": datetime.now()
            })
            conn.commit()

# Usage
extractor = IncrementalExtractor("postgresql://user:pass@localhost/source")
df = extractor.extract_incremental("orders", "updated_at")

if not df.empty:
    max_timestamp = df["updated_at"].max()
    # ... load to destination ...
    extractor.update_watermark("orders", max_timestamp)
```

### Pattern 2: API Extraction with Pagination

```python
import requests
from typing import Iterator, Dict, Any
import time

class PaginatedAPIExtractor:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def extract_paginated(
        self,
        endpoint: str,
        page_size: int = 100,
        rate_limit_delay: float = 0.5
    ) -> Iterator[Dict[str, Any]]:
        """Extract all records using pagination"""
        page = 1

        while True:
            params = {"page": page, "per_page": page_size}
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            records = data.get("results", [])

            if not records:
                break

            yield from records

            # Check if more pages exist
            if not data.get("has_more", False):
                break

            page += 1
            time.sleep(rate_limit_delay)  # Respect rate limits

# Usage with backoff
from tenacity import retry, stop_after_attempt, wait_exponential

extractor = PaginatedAPIExtractor("https://api.example.com", "key123")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def extract_with_retry():
    records = list(extractor.extract_paginated("customers"))
    return pd.DataFrame(records)

df = extract_with_retry()
```

### Pattern 3: Transformation with Data Quality Checks

```python
from typing import Callable
import pandas as pd
from dataclasses import dataclass

@dataclass
class TransformResult:
    valid_records: pd.DataFrame
    invalid_records: pd.DataFrame
    validation_errors: list

class Transformer:
    def __init__(self):
        self.validators = []

    def add_validator(self, name: str, func: Callable):
        """Add validation rule"""
        self.validators.append((name, func))
        return self

    def transform(self, df: pd.DataFrame) -> TransformResult:
        """Apply transformations and validations"""
        errors = []
        invalid_mask = pd.Series([False] * len(df), index=df.index)

        # Data type conversions
        df = df.copy()

        # Apply validations
        for name, validator in self.validators:
            try:
                valid_mask = df.apply(validator, axis=1)
                invalid_rows = df[~valid_mask]

                if not invalid_rows.empty:
                    errors.append({
                        "rule": name,
                        "count": len(invalid_rows),
                        "sample": invalid_rows.head(5).to_dict('records')
                    })
                    invalid_mask |= ~valid_mask

            except Exception as e:
                errors.append({
                    "rule": name,
                    "error": str(e)
                })

        return TransformResult(
            valid_records=df[~invalid_mask],
            invalid_records=df[invalid_mask],
            validation_errors=errors
        )

# Usage
transformer = Transformer()
transformer.add_validator(
    "email_format",
    lambda row: "@" in str(row.get("email", ""))
)
transformer.add_validator(
    "positive_amount",
    lambda row: float(row.get("amount", 0)) > 0
)
transformer.add_validator(
    "required_fields",
    lambda row: all(pd.notna(row.get(f)) for f in ["id", "created_at"])
)

result = transformer.transform(df)

print(f"Valid: {len(result.valid_records)}")
print(f"Invalid: {len(result.invalid_records)}")
print(f"Errors: {result.validation_errors}")
```

### Pattern 4: Upsert (Merge) Load

```python
# PostgreSQL upsert
def upsert_postgres(df: pd.DataFrame, table_name: str, key_columns: list):
    """Upsert using INSERT ON CONFLICT"""
    from sqlalchemy import create_engine
    from io import StringIO

    engine = create_engine("postgresql://...")

    # Create temp table
    temp_table = f"{table_name}_temp"
    df.to_sql(temp_table, engine, if_exists="replace", index=False)

    # Build upsert query
    all_columns = df.columns.tolist()
    update_columns = [c for c in all_columns if c not in key_columns]

    key_clause = ", ".join(key_columns)
    update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_columns])

    upsert_query = f"""
        INSERT INTO {table_name} ({', '.join(all_columns)})
        SELECT {', '.join(all_columns)} FROM {temp_table}
        ON CONFLICT ({key_clause})
        DO UPDATE SET {update_clause}
    """

    with engine.connect() as conn:
        conn.execute(upsert_query)
        # Clean up temporary staging table after merge
        conn.execute(f"DROP TABLE {temp_table}")
        conn.commit()

# Snowflake merge
def merge_snowflake(df: pd.DataFrame, table_name: str, key_columns: list):
    """Merge using Snowflake MERGE statement"""
    from snowflake.connector.pandas_tools import write_pandas
    import snowflake.connector

    conn = snowflake.connector.connect(...)

    # Write to temp staging table
    stage_table = f"{table_name}_stage"
    write_pandas(conn, df, stage_table, auto_create_table=True)

    # Build merge statement
    key_clause = " AND ".join([f"target.{k} = source.{k}" for k in key_columns])
    update_clause = ", ".join([f"{c} = source.{c}" for c in df.columns])
    insert_columns = ", ".join(df.columns)
    insert_values = ", ".join([f"source.{c}" for c in df.columns])

    merge_query = f"""
        MERGE INTO {table_name} AS target
        USING {stage_table} AS source
        ON {key_clause}
        WHEN MATCHED THEN
            UPDATE SET {update_clause}
        WHEN NOT MATCHED THEN
            INSERT ({insert_columns})
            VALUES ({insert_values})
    """

    cursor = conn.cursor()
    cursor.execute(merge_query)
    # Clean up staging table after successful merge
    cursor.execute(f"DROP TABLE {stage_table}")
    conn.commit()
    cursor.close()
```

### Pattern 5: Full ETL Pipeline with State Management

```python
from pathlib import Path
import json
from datetime import datetime

class ETLPipeline:
    def __init__(self, name: str, state_file: Path):
        self.name = name
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"runs": []}

    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2, default=str))

    def run(self, extract_fn, transform_fn, load_fn):
        """Execute ETL with error handling and state tracking"""
        run_id = datetime.now().isoformat()
        run_state = {
            "run_id": run_id,
            "started_at": run_id,
            "status": "running"
        }

        try:
            # Extract
            print(f"[{self.name}] Extracting...")
            raw_data = extract_fn()
            run_state["extracted_count"] = len(raw_data)

            # Transform
            print(f"[{self.name}] Transforming...")
            result = transform_fn(raw_data)
            run_state["valid_count"] = len(result.valid_records)
            run_state["invalid_count"] = len(result.invalid_records)

            # Load
            print(f"[{self.name}] Loading...")
            load_fn(result.valid_records)

            run_state["status"] = "success"
            run_state["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            run_state["status"] = "failed"
            run_state["error"] = str(e)
            raise

        finally:
            self.state["runs"].append(run_state)
            self.state["last_run"] = run_state
            self._save_state()

        return run_state

# Usage
pipeline = ETLPipeline("orders_etl", Path("/tmp/orders_state.json"))

result = pipeline.run(
    extract_fn=lambda: extractor.extract_incremental("orders"),
    transform_fn=lambda df: transformer.transform(df),
    load_fn=lambda df: upsert_postgres(df, "orders", ["order_id"])
)
```

## Quick Reference

### Common Extraction Sources
```python
# PostgreSQL/MySQL
pd.read_sql("SELECT * FROM table", engine)

# REST API
requests.get(url, headers=headers).json()

# CSV/Parquet
pd.read_csv("file.csv")
pd.read_parquet("file.parquet")

# S3
s3 = boto3.client('s3')
obj = s3.get_object(Bucket='bucket', Key='key')
pd.read_csv(obj['Body'])
```

### Transformation Functions
```python
# Type casting
df['date'] = pd.to_datetime(df['date'])
df['amount'] = df['amount'].astype(float)

# Null handling
df.fillna({'column': default_value})
df.dropna(subset=['required_col'])

# String cleaning
df['email'] = df['email'].str.lower().str.strip()

# Deduplication
df.drop_duplicates(subset=['key'], keep='last')
```

### Load Patterns
```python
# Append
df.to_sql('table', engine, if_exists='append', index=False)

# Replace
df.to_sql('table', engine, if_exists='replace', index=False)

# Bulk insert (faster)
from sqlalchemy import insert
records = df.to_dict('records')
with engine.connect() as conn:
    conn.execute(insert(table), records)
    conn.commit()
```

## Anti-Patterns

```
❌ NEVER: Extract entire table when incremental is possible
   → Use timestamp or ID-based incremental extraction

❌ NEVER: Load without validation
   → Always validate data quality before loading

❌ NEVER: Hardcode connection strings
   → Use environment variables or secrets manager

❌ NEVER: Skip error handling
   → Wrap extract/load in try-except, log failures

❌ NEVER: Load invalid records silently
   → Route to quarantine table for inspection

❌ NEVER: Run full loads on large tables
   → Use incremental or partitioned loads

❌ NEVER: Skip state management
   → Track watermarks, run history for recovery

❌ NEVER: Transform before validating schema
   → Validate source schema before transformations

❌ NEVER: Use SELECT * in production
   → Specify columns explicitly for stability
```

## Related Skills

- `stream-processing.md` - Real-time alternatives to batch ETL
- `batch-processing.md` - Orchestrating ETL with Airflow
- `data-validation.md` - Advanced schema and quality validation
- `pipeline-orchestration.md` - Workflow management for ETL

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
