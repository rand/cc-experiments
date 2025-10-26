---
name: cloud-gcp-databases
description: Google Cloud managed database services including Cloud SQL, Firestore, Bigtable, and Spanner
---

# GCP Database Services

**Scope**: Cloud SQL, Firestore, Bigtable, Spanner, and Memorystore configuration and best practices
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Deploying relational databases with Cloud SQL (MySQL, PostgreSQL, SQL Server)
- Building applications with Firestore document database
- Designing wide-column NoSQL solutions with Bigtable
- Implementing globally distributed SQL databases with Spanner
- Setting up Redis or Memcached caching with Memorystore
- Migrating databases from on-premises or other clouds to GCP
- Configuring high availability, backups, and read replicas
- Optimizing database performance and cost

## Core Concepts

### Concept 1: Cloud SQL Configuration

**Key features**:
- Fully managed MySQL, PostgreSQL, and SQL Server
- Automatic backups, point-in-time recovery, replication
- High availability with automatic failover
- Read replicas for scaling read traffic

```bash
# Create PostgreSQL instance with high availability
gcloud sql instances create production-db \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-4 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4

# Create database and user
gcloud sql databases create appdb --instance=production-db
gcloud sql users create appuser \
  --instance=production-db \
  --password=SECURE_PASSWORD

# Create read replica for scaling reads
gcloud sql instances create production-db-replica \
  --master-instance-name=production-db \
  --tier=db-n1-standard-2 \
  --region=us-central1
```

### Concept 2: Firestore Document Database

**Data model**:
- Collections contain documents (JSON-like)
- Documents contain fields and subcollections
- Automatic indexing for queries
- Real-time listeners for live updates

```python
from google.cloud import firestore

# Initialize Firestore client
db = firestore.Client()

# Create document with auto-generated ID
users_ref = db.collection('users')
new_user = users_ref.add({
    'name': 'Alice Johnson',
    'email': 'alice@example.com',
    'created_at': firestore.SERVER_TIMESTAMP,
    'roles': ['admin', 'editor']
})

# Query documents
active_users = users_ref.where('status', '==', 'active').where('roles', 'array_contains', 'admin').stream()

for user in active_users:
    print(f'{user.id} => {user.to_dict()}')

# Real-time listener for changes
def on_snapshot(collection_snapshot, changes, read_time):
    for change in changes:
        if change.type.name == 'ADDED':
            print(f'New user: {change.document.id}')

users_ref.on_snapshot(on_snapshot)
```

### Concept 3: Bigtable Schema Design

**Key principles**:
- Wide-column NoSQL for massive scale (billions of rows, petabytes)
- Row key design critical for performance (avoid hotspots)
- Column families group related columns
- Time-series data natural fit

```python
from google.cloud import bigtable
from google.cloud.bigtable import column_family, row_filters

# Create Bigtable instance and table
client = bigtable.Client(project='my-project', admin=True)
instance = client.instance('analytics-instance')

# Create table with column family
table = instance.table('events')
cf = table.column_family('metrics', max_age=timedelta(days=30))
cf.create()

# Row key design for time-series: reverse timestamp + user_id (avoid hotspots)
import time
reverse_timestamp = str(2**63 - int(time.time() * 1000))
row_key = f"{reverse_timestamp}#{user_id}".encode()

# Write data
row = table.direct_row(row_key)
row.set_cell('metrics', 'page_views', str(125), timestamp=datetime.utcnow())
row.set_cell('metrics', 'session_duration', str(450), timestamp=datetime.utcnow())
row.commit()

# Read data with prefix scan
rows = table.read_rows(
    start_key=f"{reverse_timestamp}#".encode(),
    limit=100
)
```

### Concept 4: Spanner Global Distribution

**Features**:
- Horizontally scalable SQL database
- Synchronous replication across regions
- External consistency (linearizable transactions)
- SQL with ACID guarantees at global scale

```python
from google.cloud import spanner

# Create Spanner instance with multi-region configuration
spanner_client = spanner.Client()
instance = spanner_client.instance(
    'global-instance',
    configuration_name='nam-eur-asia1',  # Multi-region
    node_count=3
)

database = instance.database('orders')

# Insert with transaction
def insert_order(transaction):
    transaction.execute_update(
        """INSERT INTO Orders (OrderId, CustomerId, Amount, CreatedAt)
           VALUES (@order_id, @customer_id, @amount, CURRENT_TIMESTAMP())""",
        params={'order_id': 'ORD-123', 'customer_id': 'CUST-456', 'amount': 99.99},
        param_types={'order_id': spanner.param_types.STRING,
                     'customer_id': spanner.param_types.STRING,
                     'amount': spanner.param_types.FLOAT64}
    )

database.run_in_transaction(insert_order)

# Query with strong consistency
with database.snapshot() as snapshot:
    results = snapshot.execute_sql(
        """SELECT o.OrderId, o.Amount, c.Name
           FROM Orders o JOIN Customers c ON o.CustomerId = c.CustomerId
           WHERE o.CreatedAt > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)"""
    )
    for row in results:
        print(f"Order {row[0]}: ${row[1]} - {row[2]}")
```

---

## Patterns

### Pattern 1: Cloud SQL High Availability

**When to use**:
- Production databases requiring 99.95% SLA
- Automatic failover to standby instance

```bash
# ❌ Bad: Single-zone instance (no automatic failover)
gcloud sql instances create db \
  --tier=db-n1-standard-2 \
  --region=us-central1
# Zone failure causes downtime

# ✅ Good: Regional HA instance with automatic failover
gcloud sql instances create db \
  --tier=db-n1-standard-2 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --enable-bin-log

# Standby instance automatically promoted on primary failure
# Typically <60 seconds of downtime
```

**Benefits**:
- 99.95% SLA (vs 99.5% for zonal)
- Automatic failover with minimal downtime
- Synchronous replication to standby

### Pattern 2: Firestore Security Rules

**Use case**: Secure document access based on authentication and data content

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own documents
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    // Public read, authenticated write
    match /posts/{postId} {
      allow read: if true;
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null &&
                               request.auth.uid == resource.data.author_id;
    }

    // Admin-only collection
    match /admin/{document=**} {
      allow read, write: if request.auth.token.admin == true;
    }
  }
}
```

### Pattern 3: Bigtable Row Key Design for Time Series

**Use case**: Store sensor data with efficient time-range queries

```python
# ❌ Bad: Sequential timestamps create hotspot on single tablet
row_key = f"{sensor_id}#{timestamp}".encode()
# All recent writes go to same tablet server

# ✅ Good: Hash prefix distributes writes, reverse timestamp for recent scans
import hashlib

def create_row_key(sensor_id, timestamp):
    # Hash prefix (first 2 hex chars) distributes writes across tablets
    prefix = hashlib.md5(sensor_id.encode()).hexdigest()[:2]
    # Reverse timestamp for efficient recent-data scans
    reverse_ts = str(2**63 - int(timestamp * 1000))
    return f"{prefix}#{sensor_id}#{reverse_ts}".encode()

# Write to Bigtable
row = table.direct_row(create_row_key('sensor-42', time.time()))
row.set_cell('data', 'temperature', '72.5')
row.commit()

# Read recent data for sensor with prefix scan
prefix = hashlib.md5('sensor-42'.encode()).hexdigest()[:2]
rows = table.read_rows(
    start_key=f"{prefix}#sensor-42#".encode(),
    end_key=f"{prefix}#sensor-42#~".encode(),
    limit=100
)
```

### Pattern 4: Spanner Interleaved Tables

**Use case**: Physically co-locate related rows for faster joins

```sql
-- ❌ Bad: Separate tables (data distributed, slow joins)
CREATE TABLE Customers (
  CustomerId STRING(36),
  Name STRING(100)
) PRIMARY KEY (CustomerId);

CREATE TABLE Orders (
  OrderId STRING(36),
  CustomerId STRING(36),
  Amount FLOAT64
) PRIMARY KEY (OrderId);
-- Orders scattered across nodes, expensive joins

-- ✅ Good: Interleave Orders within Customers
CREATE TABLE Customers (
  CustomerId STRING(36),
  Name STRING(100)
) PRIMARY KEY (CustomerId);

CREATE TABLE Orders (
  CustomerId STRING(36),
  OrderId STRING(36),
  Amount FLOAT64
) PRIMARY KEY (CustomerId, OrderId),
  INTERLEAVE IN PARENT Customers ON DELETE CASCADE;

-- Orders stored physically with parent Customer row
-- Fast queries for customer's orders
SELECT * FROM Customers c JOIN Orders o USING (CustomerId)
WHERE c.CustomerId = 'CUST-123';  -- Efficient, single node
```

### Pattern 5: Cloud SQL Connection Pooling

**Use case**: Avoid connection exhaustion in serverless environments

```python
import sqlalchemy
from sqlalchemy import create_engine

# ❌ Bad: Create new connection per request (connection exhaustion)
def query_database():
    engine = create_engine('postgresql://user:pass@host/db')
    with engine.connect() as conn:
        result = conn.execute("SELECT * FROM users")
    return result

# ✅ Good: Reuse connection pool across requests
# Cloud SQL Proxy handles connection pooling
connection_pool = create_engine(
    'postgresql+pg8000://',
    creator=lambda: connector.connect(
        'project:region:instance',
        'pg8000',
        user='appuser',
        password='SECRET',
        db='appdb'
    ),
    pool_size=5,  # Max 5 concurrent connections
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800  # Recycle connections every 30 min
)

def query_database():
    with connection_pool.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT * FROM users"))
    return result
```

### Pattern 6: Firestore Composite Indexes

**Use case**: Enable complex queries on multiple fields

```python
# Query requiring composite index
users_ref = db.collection('users')
query = users_ref.where('status', '==', 'active') \
                 .where('country', '==', 'US') \
                 .order_by('created_at', direction=firestore.Query.DESCENDING)

# Firestore automatically prompts to create index via error message
# Or create via index configuration:
```

```json
{
  "indexes": [
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "country", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    }
  ]
}
```

### Pattern 7: Memorystore for Database Caching

**Use case**: Cache frequently accessed database queries in Redis

```python
import redis
from google.cloud import secretmanager

# Connect to Memorystore Redis
redis_client = redis.Redis(
    host='10.0.0.3',  # Memorystore instance IP
    port=6379,
    decode_responses=True
)

def get_user(user_id):
    # Try cache first
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)

    if cached_user:
        return json.loads(cached_user)

    # Cache miss - query database
    with connection_pool.connect() as conn:
        result = conn.execute(
            sqlalchemy.text("SELECT * FROM users WHERE id = :id"),
            {"id": user_id}
        )
        user = dict(result.fetchone())

    # Store in cache (expire after 1 hour)
    redis_client.setex(cache_key, 3600, json.dumps(user))
    return user
```

### Pattern 8: Database Migration with Database Migration Service

**Use case**: Migrate from on-premises or other clouds to Cloud SQL

```bash
# Create migration job from MySQL source to Cloud SQL
gcloud database-migration migration-jobs create migrate-prod-db \
  --region=us-central1 \
  --type=CONTINUOUS \
  --source=on-prem-mysql \
  --destination=projects/my-project/instances/production-db \
  --dump-path=gs://migration-bucket/dumps

# Monitor migration progress
gcloud database-migration migration-jobs describe migrate-prod-db \
  --region=us-central1

# Promote Cloud SQL instance (cutover)
gcloud database-migration migration-jobs promote migrate-prod-db \
  --region=us-central1
```

---

## Quick Reference

### Database Service Selection

```
Service      | Type           | Scale         | Use Case
-------------|----------------|---------------|---------------------------
Cloud SQL    | SQL (managed)  | Up to 64 TB   | Traditional SQL apps
Firestore    | Document NoSQL | Unlimited     | Mobile/web apps, real-time
Bigtable     | Wide-column    | Petabyte+     | Time-series, analytics
Spanner      | Global SQL     | Petabyte+     | Global apps, strong consistency
Memorystore  | In-memory      | Up to 300 GB  | Caching, session storage
```

### Cloud SQL Tiers

```
Tier              | vCPUs | Memory  | Use Case
------------------|-------|---------|------------------
db-f1-micro       | 1     | 0.6 GB  | Dev/test
db-g1-small       | 1     | 1.7 GB  | Small apps
db-n1-standard-1  | 1     | 3.75 GB | Production start
db-n1-standard-4  | 4     | 15 GB   | Medium workloads
db-n1-standard-16 | 16    | 60 GB   | Large workloads
```

### Key gcloud Commands

```bash
# Cloud SQL
gcloud sql instances create NAME --database-version=POSTGRES_15 --tier=TIER
gcloud sql instances list
gcloud sql databases create DB --instance=INSTANCE
gcloud sql backups create --instance=INSTANCE
gcloud sql instances failover INSTANCE  # Manual failover test

# Firestore (via Firebase CLI)
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes

# Spanner
gcloud spanner instances create INSTANCE --config=CONFIG --nodes=3
gcloud spanner databases create DB --instance=INSTANCE
```

### Key Guidelines

```
✅ DO: Enable automated backups for all production databases
✅ DO: Use read replicas to scale read traffic
✅ DO: Implement connection pooling for Cloud SQL
✅ DO: Design Bigtable row keys to avoid hotspots
✅ DO: Use Firestore security rules for access control
✅ DO: Test failover procedures regularly

❌ DON'T: Use Spanner for small databases (expensive, use Cloud SQL)
❌ DON'T: Create Bigtable row keys with sequential timestamps
❌ DON'T: Store large blobs in Firestore documents (max 1 MB)
❌ DON'T: Disable binary logging on Cloud SQL HA instances
❌ DON'T: Use Firestore for analytics queries (use BigQuery)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Store large files in Firestore documents
db.collection('users').document('user-123').set({
    'name': 'Alice',
    'profile_image': base64_encode(image_data)  # 10MB image - FAILS!
})
# Firestore has 1MB document size limit

# ✅ CORRECT: Store files in Cloud Storage, reference in Firestore
from google.cloud import storage

storage_client = storage.Client()
bucket = storage_client.bucket('user-uploads')
blob = bucket.blob(f'profiles/{user_id}.jpg')
blob.upload_from_filename(image_path)

db.collection('users').document('user-123').set({
    'name': 'Alice',
    'profile_image_url': f'gs://user-uploads/profiles/{user_id}.jpg'
})
```

❌ **Large documents in Firestore**: Documents are limited to 1MB. Storing large files causes write failures.
✅ **Correct approach**: Store files in Cloud Storage, save references in Firestore documents.

### Common Mistakes

```python
# ❌ Don't: Use sequential row keys in Bigtable
row_key = f"{timestamp}#{sensor_id}".encode()
# Creates hotspot - all writes go to single tablet server

# ✅ Correct: Distribute writes with hash prefix or reverse timestamp
import hashlib
prefix = hashlib.md5(sensor_id.encode()).hexdigest()[:2]
reverse_ts = str(2**63 - int(timestamp * 1000))
row_key = f"{prefix}#{sensor_id}#{reverse_ts}".encode()
```

❌ **Sequential Bigtable keys**: Sequential row keys create hotspots where all writes go to a single tablet server.
✅ **Better**: Use hash prefixes or reverse timestamps to distribute writes across tablet servers.

```bash
# ❌ Don't: Use Spanner for small databases
gcloud spanner instances create small-app-db --config=regional-us-central1 --nodes=1
# Minimum cost: ~$650/month for single node!

# ✅ Correct: Use Cloud SQL for small/medium databases
gcloud sql instances create small-app-db \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-1
# Cost: ~$50/month
```

❌ **Spanner for small databases**: Spanner has high minimum cost. Using it for small databases wastes money.
✅ **Better**: Use Cloud SQL for databases <1TB. Only use Spanner when you need global distribution or horizontal scaling.

```python
# ❌ Don't: Perform analytics queries on Firestore
# Query all orders from last year (millions of documents)
orders = db.collection('orders').where('created_at', '>', last_year).stream()
total_revenue = sum(order.to_dict()['amount'] for order in orders)
# Slow, expensive, and hits quota limits

# ✅ Correct: Export to BigQuery for analytics
# Use Firestore-BigQuery extension or scheduled export
# Then query in BigQuery:
"""
SELECT SUM(amount) as total_revenue
FROM `project.dataset.orders`
WHERE created_at > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 YEAR)
"""
```

❌ **Firestore for analytics**: Firestore is optimized for transactional queries, not large-scale analytics.
✅ **Better**: Export Firestore data to BigQuery for analytics and reporting queries.

---

## Related Skills

- `gcp-compute.md` - Connecting Compute Engine instances to databases
- `gcp-storage.md` - Database backups to Cloud Storage
- `gcp-iam-security.md` - Database user management and service account access
- `gcp-networking.md` - Private IP configuration for database security

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
