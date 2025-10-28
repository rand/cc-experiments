---
name: apache-iceberg
description: Building data lakes with ACID transaction support and schema evolution
---



# Apache Iceberg

**Scope**: Table format, schema/partition evolution, time travel, ACID transactions, catalog integration, performance optimization
**Lines**: ~390
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Building data lakes with ACID transaction support and schema evolution
- Implementing time travel queries and snapshot-based rollback
- Migrating from Hive tables to modern table formats
- Designing partition strategies that can evolve without data rewrites
- Integrating with Spark, Flink, Trino, or Presto for analytics workloads
- Implementing incremental reads and change data capture (CDC) patterns
- Managing large-scale data with efficient snapshot and metadata management
- Optimizing query performance with hidden partitioning and file layout

## Core Concepts

### Table Format Architecture

**Three-layer metadata hierarchy**:
- **Metadata files**: JSON files tracking table schema, partitioning, snapshots
- **Manifest lists**: Lists of manifest files for each snapshot
- **Manifest files**: Lists of data files with partition information and statistics
- **Data files**: Actual data in Parquet, ORC, or Avro format

**ACID guarantees**:
- Atomic commits via metadata file replacement (optimistic concurrency)
- Isolation through snapshot isolation (readers see consistent snapshot)
- Consistency enforced by schema validation
- Durability through immutable data and metadata files

**Hidden partitioning**:
- Partition columns don't appear in user queries
- Automatically applied based on table metadata
- Evolution without breaking existing queries
- Supports transforms (year, month, day, hour, bucket, truncate)  <!-- NOTE: truncate is Iceberg's data transform function, not SQL TRUNCATE -->

### Catalog Integration

**Catalog types**:
- **Hive Metastore**: Legacy, widely compatible, atomic table updates
- **AWS Glue**: Managed, serverless, integrated with AWS services
- **Nessie**: Git-like versioning, multi-table transactions, branching
- **REST Catalog**: HTTP-based, cloud-native, flexible implementation
- **JDBC**: Direct database storage for metadata

**Catalog configuration**:
```python
# PyIceberg with different catalogs
from pyiceberg.catalog import load_catalog

# Hive Metastore
catalog = load_catalog("hive",
    uri="thrift://localhost:9083",
    warehouse="s3://bucket/warehouse"
)

# AWS Glue
catalog = load_catalog("glue",
    warehouse="s3://bucket/warehouse"
)

# REST Catalog
catalog = load_catalog("rest",
    uri="https://catalog-api.example.com",
    credential="token:abc123"
)
```

### Snapshots and Time Travel

**Snapshot lifecycle**:
- Every write operation creates new snapshot
- Snapshots are immutable and point-in-time consistent
- Metadata tracks parent-child snapshot relationships
- Snapshots can be expired to reclaim storage

**Time travel queries**:
- Query historical data by snapshot ID or timestamp
- Compare data between snapshots for audit/debugging
- Rollback to previous snapshot for error recovery
- Incremental reads between snapshots for CDC

---

## Patterns

### Table Creation with Schema and Partitioning

```sql
-- Spark SQL: Create Iceberg table with partitioning
CREATE TABLE catalog.db.events (
    event_id BIGINT,
    user_id STRING,
    event_type STRING,
    event_time TIMESTAMP,
    properties MAP<STRING, STRING>
)
USING iceberg
PARTITIONED BY (days(event_time), event_type)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd',
    'write.metadata.compression-codec' = 'gzip'
);
```

**Python PyIceberg**:
```python
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, LongType, StringType, TimestampType, MapType
)
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform, IdentityTransform

catalog = load_catalog("default")

schema = Schema(
    NestedField(1, "event_id", LongType(), required=True),
    NestedField(2, "user_id", StringType(), required=True),
    NestedField(3, "event_type", StringType(), required=True),
    NestedField(4, "event_time", TimestampType(), required=True),
    NestedField(5, "properties", MapType(6, StringType(), 7, StringType()))
)

# Hidden partitioning: users query event_time, Iceberg handles partitioning
partition_spec = PartitionSpec(
    PartitionField(source_id=4, field_id=1000, transform=DayTransform(), name="event_day"),
    PartitionField(source_id=3, field_id=1001, transform=IdentityTransform(), name="event_type")
)

table = catalog.create_table(
    identifier="db.events",
    schema=schema,
    partition_spec=partition_spec,
    properties={"write.format.default": "parquet"}
)
```

**When to use**:
- Starting new data lake projects
- Migrating from Hive with schema evolution needs
- Requiring flexible partition strategies

### Schema Evolution

```sql
-- Add column (backward compatible)
ALTER TABLE catalog.db.events
ADD COLUMN session_id STRING;

-- Drop column (forward compatible)
ALTER TABLE catalog.db.events
DROP COLUMN properties;

-- Rename column (maintains column IDs)
ALTER TABLE catalog.db.events
RENAME COLUMN user_id TO customer_id;

-- Type promotion (safe widening)
ALTER TABLE catalog.db.events
ALTER COLUMN event_id TYPE BIGINT;  -- int -> bigint allowed
```

**Python schema updates**:
```python
from pyiceberg.catalog import load_catalog
from pyiceberg.types import StringType, LongType

catalog = load_catalog("default")
table = catalog.load_table("db.events")

# Add column
with table.update_schema() as update:
    update.add_column("session_id", StringType())

# Rename column
with table.update_schema() as update:
    update.rename_column("user_id", "customer_id")

# Type promotion
with table.update_schema() as update:
    update.update_column("event_id", field_type=LongType())
```

**Benefits**:
- No downtime or data rewrites for schema changes
- Column IDs preserve compatibility across renames
- Safe type promotions (int→long, float→double, decimal scale up)

### Partition Evolution

```sql
-- Initial partitioning by day
CREATE TABLE catalog.db.logs (
    log_time TIMESTAMP,
    message STRING
)
USING iceberg
PARTITIONED BY (days(log_time));

-- Later: Add hourly partitioning for recent data
ALTER TABLE catalog.db.logs
REPLACE PARTITION FIELD days(log_time)
WITH hours(log_time);

-- Old data stays partitioned by day, new data by hour
-- Queries work seamlessly across both partition layouts
```

**Partition transform types**:
```python
from pyiceberg.transforms import (
    YearTransform, MonthTransform, DayTransform, HourTransform,
    BucketTransform, TruncateTransform
)

# Date/time transforms
YearTransform()   # Extract year
MonthTransform()  # Extract month
DayTransform()    # Extract day
HourTransform()   # Extract hour

# Distribution transforms
BucketTransform(num_buckets=16)  # Hash bucket for uniform distribution
TruncateTransform(width=10)       # NOTE: Iceberg transform for trimming strings/numbers to width, not SQL TRUNCATE
```

**When to use**:
- Workload patterns change over time (daily → hourly)
- Need to rebalance data distribution
- Optimizing query performance without data migration

### Time Travel and Snapshot Queries

```sql
-- Query as of specific timestamp
SELECT * FROM catalog.db.events
FOR SYSTEM_TIME AS OF TIMESTAMP '2025-10-01 00:00:00';

-- Query specific snapshot by ID
SELECT * FROM catalog.db.events
FOR SYSTEM_VERSION AS OF 1234567890;

-- View all snapshots
SELECT * FROM catalog.db.events.snapshots;

-- View snapshot history
SELECT
    snapshot_id,
    committed_at,
    operation,
    summary
FROM catalog.db.events.history
ORDER BY committed_at DESC;

-- Rollback to previous snapshot
CALL catalog.system.rollback_to_snapshot('db.events', 1234567890);

-- Cherry-pick specific snapshot
CALL catalog.system.cherrypick_snapshot('db.events', 1234567890);
```

**Python time travel**:
```python
from datetime import datetime
from pyiceberg.catalog import load_catalog

catalog = load_catalog("default")
table = catalog.load_table("db.events")

# Read current snapshot
df = table.scan().to_arrow()

# Read specific snapshot
snapshot = table.snapshot_by_id(1234567890)
df_historical = table.scan(snapshot_id=snapshot.snapshot_id).to_arrow()

# Read as of timestamp
timestamp = datetime(2025, 10, 1, 0, 0, 0)
df_time_travel = table.scan(as_of_timestamp=timestamp).to_arrow()

# List all snapshots
for snapshot in table.snapshots():
    print(f"Snapshot {snapshot.snapshot_id} at {snapshot.timestamp_ms}")
```

**When to use**:
- Auditing data changes over time
- Debugging production issues with historical data
- Implementing CDC by comparing snapshots
- Rolling back accidental data corruption

### Incremental Reads and CDC

```python
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import And, EqualTo, GreaterThanOrEqual

catalog = load_catalog("default")
table = catalog.load_table("db.events")

# Get current and previous snapshots
snapshots = list(table.snapshots())
current_snapshot = snapshots[-1]
previous_snapshot = snapshots[-2]

# Incremental read: only files added between snapshots
scan = table.scan(
    snapshot_id=current_snapshot.snapshot_id,
    from_snapshot_id=previous_snapshot.snapshot_id
)

# Filter incremental data
incremental_df = scan.filter(
    GreaterThanOrEqual("event_time", "2025-10-18 00:00:00")
).to_arrow()

print(f"Incremental records: {len(incremental_df)}")
```

**Spark incremental reads**:
```scala
// Read changes between two snapshots
val incrementalDF = spark.read
  .format("iceberg")
  .option("start-snapshot-id", "1234567890")
  .option("end-snapshot-id", "1234567891")
  .load("catalog.db.events")

// Read all changes since timestamp
val cdcDF = spark.read
  .format("iceberg")
  .option("start-timestamp", "2025-10-18 00:00:00")
  .load("catalog.db.events")
```

**When to use**:
- Building incremental ETL pipelines
- Streaming data processing with batch catchup
- Change data capture for downstream systems
- Reducing processing by reading only new data

### ACID Transactions with Spark

```scala
import org.apache.spark.sql.SparkSession
import org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

val spark = SparkSession.builder()
  .appName("Iceberg ACID")
  .config("spark.sql.extensions",
    "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
  .config("spark.sql.catalog.catalog", "org.apache.iceberg.spark.SparkCatalog")
  .config("spark.sql.catalog.catalog.type", "hive")
  .getOrCreate()

// Atomic write: all or nothing
val newEvents = spark.read.json("s3://bucket/raw/events/")
newEvents.writeTo("catalog.db.events")
  .append()  // Atomic commit

// Upsert with MERGE INTO (atomic)
spark.sql("""
  MERGE INTO catalog.db.events t
  USING updates s
  ON t.event_id = s.event_id
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *
""")

// Delete with predicate (atomic)
spark.sql("""
  DELETE FROM catalog.db.events
  WHERE event_time < TIMESTAMP '2024-01-01'
""")

// Multi-table transaction (via WAP - Write-Audit-Publish)
spark.conf.set("spark.wap.id", "staging-branch")

// Write to staging branch
df.writeTo("catalog.db.events").append()

// Validate data
val count = spark.sql("SELECT COUNT(*) FROM catalog.db.events").collect()

// Publish if valid (atomic promotion)
if (count.head.getLong(0) > 0) {
  spark.sql("CALL catalog.system.cherrypick_snapshot('db.events', 'staging-branch')")
}
```

**When to use**:
- Ensuring data consistency across failures
- Implementing upsert/delete operations
- Multi-stage ETL with validation gates

### Table Maintenance and Optimization

```sql
-- Expire old snapshots (free storage)
CALL catalog.system.expire_snapshots(
  table => 'db.events',
  older_than => TIMESTAMP '2025-09-01 00:00:00',
  retain_last => 10
);

-- Remove orphan files (unreferenced data files)
CALL catalog.system.remove_orphan_files(
  table => 'db.events',
  older_than => TIMESTAMP '2025-10-01 00:00:00'
);

-- Rewrite small files into larger files
CALL catalog.system.rewrite_data_files(
  table => 'db.events',
  options => map('target-file-size-bytes', '536870912')  -- 512 MB
);

-- Rewrite manifest files for faster planning
CALL catalog.system.rewrite_manifests('db.events');

-- Compact data files in partition
CALL catalog.system.rewrite_data_files(
  table => 'db.events',
  where => 'event_date = DATE "2025-10-18"'
);
```

**Python maintenance**:
```python
from pyiceberg.catalog import load_catalog
from datetime import datetime, timedelta

catalog = load_catalog("default")
table = catalog.load_table("db.events")

# Expire snapshots older than 30 days
expire_before = datetime.now() - timedelta(days=30)
table.expire_snapshots(
    older_than=expire_before,
    retain_last=10  # Keep at least 10 snapshots
)

# Get table statistics
metadata = table.metadata
print(f"Snapshots: {len(metadata.snapshots)}")
print(f"Schema version: {metadata.current_schema_id}")
print(f"Partition spec: {metadata.default_spec_id}")
```

**When to use**:
- Regular maintenance (weekly/monthly)
- After bulk deletes or updates
- When query planning is slow (too many small files)
- Storage cost optimization

### Integration with Flink for Streaming

```java
import org.apache.flink.table.api.TableEnvironment;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;

StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
TableEnvironment tEnv = TableEnvironment.create(env);

// Configure Iceberg catalog
tEnv.executeSql(
  "CREATE CATALOG iceberg_catalog WITH (" +
  "  'type'='iceberg'," +
  "  'catalog-type'='hive'," +
  "  'uri'='thrift://localhost:9083'," +
  "  'warehouse'='s3://bucket/warehouse'" +
  ")"
);

tEnv.useCatalog("iceberg_catalog");

// Create Iceberg table from Flink
tEnv.executeSql(
  "CREATE TABLE events (" +
  "  event_id BIGINT," +
  "  user_id STRING," +
  "  event_time TIMESTAMP(6)," +
  "  PRIMARY KEY (event_id) NOT ENFORCED" +
  ") PARTITIONED BY (event_type)" +
  " WITH ('write.format.default'='parquet')"
);

// Stream write to Iceberg (micro-batch commits)
tEnv.executeSql(
  "INSERT INTO events " +
  "SELECT event_id, user_id, event_time FROM kafka_source"
);

// Stream read from Iceberg
tEnv.executeSql(
  "SELECT * FROM events " +
  "/*+ OPTIONS('streaming'='true', 'monitor-interval'='10s') */"
);
```

**When to use**:
- Real-time streaming ingestion to data lake
- Streaming analytics on Iceberg tables
- Combining batch and streaming workloads

---

## Quick Reference

### Core Commands

| Operation | Spark SQL | Python PyIceberg |
|-----------|-----------|------------------|
| Create table | `CREATE TABLE ... USING iceberg` | `catalog.create_table()` |
| Add column | `ALTER TABLE ... ADD COLUMN` | `table.update_schema().add_column()` |
| Rename column | `ALTER TABLE ... RENAME COLUMN` | `table.update_schema().rename_column()` |
| Time travel | `FOR SYSTEM_TIME AS OF` | `table.scan(as_of_timestamp=...)` |
| Expire snapshots | `CALL system.expire_snapshots()` | `table.expire_snapshots()` |
| Rewrite files | `CALL system.rewrite_data_files()` | N/A (use Spark) |

### Partition Transforms

```
Transform         | Example                    | Use Case
------------------|----------------------------|-----------------------
years(ts)         | PARTITIONED BY (years(ts)) | Long-term archives
months(ts)        | PARTITIONED BY (months(ts))| Monthly aggregations
days(ts)          | PARTITIONED BY (days(ts))  | Daily pipelines
hours(ts)         | PARTITIONED BY (hours(ts)) | Streaming ingestion
bucket(N, id)     | PARTITIONED BY (bucket(16, id)) | Uniform distribution
truncate(W, str)  | PARTITIONED BY (truncate(10, str)) | String prefixes  <!-- NOTE: Iceberg transform function -->
```

### Configuration Best Practices

```properties
# Write performance
write.format.default=parquet
write.parquet.compression-codec=zstd
write.target-file-size-bytes=536870912  # 512 MB

# Metadata optimization
write.metadata.compression-codec=gzip
write.metadata.metrics.default=truncate(16)  # NOTE: Iceberg's truncate transform for metrics, not SQL TRUNCATE

# Commit behavior
commit.retry.num-retries=4
commit.retry.min-wait-ms=100

# Snapshot expiration
history.expire.max-snapshot-age-ms=432000000  # 5 days
```

### Catalog URLs

```
Catalog Type | URI Format                              | Example
-------------|------------------------------------------|------------------
Hive         | thrift://host:port                      | thrift://localhost:9083
Glue         | (use AWS config)                        | N/A
REST         | https://catalog-host/path               | https://api.example.com
JDBC         | jdbc:postgresql://host:port/db          | jdbc:postgresql://localhost:5432/iceberg
Nessie       | https://nessie-host/api/v1              | https://nessie.example.com/api/v1
```

---

## Anti-Patterns

❌ **Partitioning by high-cardinality columns**: Creating too many partitions (user_id, session_id)
✅ Use bucketing for high-cardinality: `PARTITIONED BY (bucket(256, user_id))`

❌ **Manually managing partition columns in queries**: `WHERE date_partition = '2025-10-18'`
✅ Use hidden partitioning: `WHERE event_time >= '2025-10-18'` (Iceberg handles partitions)

❌ **Never expiring snapshots**: Unbounded metadata growth, slow query planning
✅ Schedule regular snapshot expiration: `CALL system.expire_snapshots()` weekly

❌ **Creating many small files**: Thousands of tiny files per partition
✅ Rewrite to target file size (512 MB - 1 GB): `CALL system.rewrite_data_files()`

❌ **Using Hive table format for schema evolution**: Requires full table rewrites
✅ Use Iceberg's built-in schema evolution: `ALTER TABLE ... ADD COLUMN`

❌ **Querying without partition filters**: Full table scans on large datasets
✅ Always filter on partition columns: `WHERE event_time BETWEEN ... AND ...`

❌ **Ignoring snapshot metadata**: Missing opportunities for incremental processing
✅ Use snapshot IDs for incremental reads: `scan(from_snapshot_id=...)`

❌ **Mixing partition schemes without evolution**: Manual partition column changes
✅ Use partition evolution: `REPLACE PARTITION FIELD ... WITH ...`

---

## Related Skills

- `spark-optimization.md` - Optimizing Spark jobs for Iceberg table reads/writes
- `delta-lake.md` - Alternative lakehouse format, comparison with Iceberg
- `hudi.md` - Another lakehouse format, streaming use cases
- `parquet-optimization.md` - Understanding underlying data file format
- `aws-glue-catalog.md` - Managing Iceberg tables with AWS Glue
- `dbt-data-modeling.md` - Building data models on top of Iceberg tables

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
