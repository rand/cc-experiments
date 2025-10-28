---
name: cloud-aws-databases
description: AWS database services - RDS, DynamoDB, ElastiCache, Aurora, migration, backup, and optimization
---

# AWS Databases

**Scope**: AWS databases - RDS, DynamoDB, ElastiCache, Aurora Serverless, migration strategies, backup and recovery
**Lines**: ~350
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Deploying managed relational databases with RDS
- Building NoSQL applications with DynamoDB
- Implementing caching with ElastiCache (Redis/Memcached)
- Setting up Aurora Serverless for variable workloads
- Migrating databases to AWS
- Configuring database backups and point-in-time recovery
- Optimizing database performance and read replicas
- Troubleshooting database connectivity or performance issues

## Core Concepts

### Concept 1: RDS (Relational Database Service)

**RDS engines**:
- **PostgreSQL**: Full-featured, JSON support, extensions
- **MySQL**: Popular, good ecosystem
- **Aurora**: AWS-optimized, 5x MySQL / 3x PostgreSQL performance
- **MariaDB**: MySQL fork, additional features
- **Oracle**: Commercial, enterprise features
- **SQL Server**: Microsoft, Windows integration

```python
import boto3

rds = boto3.client('rds')

def create_rds_instance():
    """Create RDS PostgreSQL instance with Multi-AZ"""

    response = rds.create_db_instance(
        DBInstanceIdentifier='myapp-db',
        DBInstanceClass='db.t3.medium',  # 2 vCPU, 4 GB RAM
        Engine='postgres',
        EngineVersion='15.4',
        MasterUsername='dbadmin',
        MasterUserPassword='SecurePassword123!',  # Example only - use AWS Secrets Manager in production
        AllocatedStorage=100,  # GB
        StorageType='gp3',  # General purpose SSD
        StorageEncrypted=True,
        MultiAZ=True,  # High availability
        DBSubnetGroupName='my-db-subnet-group',
        VpcSecurityGroupIds=['sg-0123456789abcdef0'],
        BackupRetentionPeriod=7,  # Days
        PreferredBackupWindow='03:00-04:00',  # UTC
        PreferredMaintenanceWindow='sun:04:00-sun:05:00',
        EnableCloudwatchLogsExports=['postgresql'],
        Tags=[
            {'Key': 'Name', 'Value': 'myapp-db'},
            {'Key': 'Environment', 'Value': 'production'}
        ]
    )

    print(f"Creating RDS instance: {response['DBInstance']['DBInstanceIdentifier']}")

    return response['DBInstance']['Endpoint']['Address']

def create_read_replica(source_db_id):
    """Create read replica for scaling reads"""

    response = rds.create_db_instance_read_replica(
        DBInstanceIdentifier=f'{source_db_id}-replica-1',
        SourceDBInstanceIdentifier=source_db_id,
        DBInstanceClass='db.t3.medium',
        PubliclyAccessible=False,
        Tags=[
            {'Key': 'Name', 'Value': f'{source_db_id}-replica'},
            {'Key': 'Role', 'Value': 'read-replica'}
        ]
    )

    print(f"Creating read replica: {response['DBInstance']['DBInstanceIdentifier']}")
```

### Concept 2: DynamoDB

**DynamoDB concepts**:
- **Tables**: Primary key (partition + sort key)
- **Indexes**: GSI (global), LSI (local)
- **Capacity modes**: On-demand vs provisioned
- **Streams**: Change data capture

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

def create_dynamodb_table():
    """Create DynamoDB table with indexes"""

    table = dynamodb.create_table(
        TableName='Users',
        KeySchema=[
            {'AttributeName': 'userId', 'KeyType': 'HASH'},  # Partition key
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userId', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
            {'AttributeName': 'createdAt', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'email-index',
                'KeySchema': [
                    {'AttributeName': 'email', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'created-index',
                'KeySchema': [
                    {'AttributeName': 'createdAt', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'KEYS_ONLY'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        },
        StreamSpecification={
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        Tags=[
            {'Key': 'Environment', 'Value': 'production'}
        ]
    )

    # Wait for table to be created
    table.wait_until_exists()
    print(f"Created table: {table.table_name}")

    return table

# CRUD operations
table = dynamodb.Table('Users')

def create_user(user_id, email, name):
    """Create user item"""
    table.put_item(
        Item={
            'userId': user_id,
            'email': email,
            'name': name,
            'createdAt': datetime.utcnow().isoformat(),
            'status': 'active'
        }
    )

def get_user(user_id):
    """Get user by ID"""
    response = table.get_item(Key={'userId': user_id})
    return response.get('Item')

def query_by_email(email):
    """Query using GSI"""
    response = table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq(email)
    )
    return response['Items']

def update_user(user_id, name):
    """Update user with atomic increment"""
    response = table.update_item(
        Key={'userId': user_id},
        UpdateExpression='SET #name = :name, updatedAt = :timestamp ADD loginCount :inc',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={
            ':name': name,
            ':timestamp': datetime.utcnow().isoformat(),
            ':inc': 1
        },
        ReturnValues='ALL_NEW'
    )
    return response['Attributes']
```

### Concept 3: ElastiCache

**Redis vs Memcached**:
- **Redis**: Data structures, persistence, replication, pub/sub
- **Memcached**: Simple key-value, multi-threaded, faster for simple caching

```python
import boto3
import redis

elasticache = boto3.client('elasticache')

def create_redis_cluster():
    """Create ElastiCache Redis cluster"""

    response = elasticache.create_replication_group(
        ReplicationGroupId='myapp-redis',
        ReplicationGroupDescription='Redis cluster for myapp',
        Engine='redis',
        EngineVersion='7.0',
        CacheNodeType='cache.t3.medium',
        NumCacheClusters=2,  # Primary + 1 replica
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName='my-cache-subnet-group',
        SecurityGroupIds=['sg-0123456789abcdef0'],
        AtRestEncryptionEnabled=True,
        TransitEncryptionEnabled=True,
        SnapshotRetentionLimit=5,
        SnapshotWindow='03:00-05:00',
        Tags=[
            {'Key': 'Name', 'Value': 'myapp-redis'},
            {'Key': 'Environment', 'Value': 'production'}
        ]
    )

    print(f"Creating Redis cluster: {response['ReplicationGroup']['ReplicationGroupId']}")

# Use Redis client
def connect_to_redis(endpoint, port=6379):
    """Connect to ElastiCache Redis"""

    # For encrypted connections
    client = redis.Redis(
        host=endpoint,
        port=port,
        decode_responses=True,
        ssl=True,
        ssl_cert_reqs=None  # For self-signed certs
    )

    return client

# Caching pattern
def get_user_cached(user_id, redis_client):
    """Get user with Redis caching"""

    cache_key = f'user:{user_id}'

    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Cache miss - fetch from DB
    user = get_user_from_db(user_id)

    # Store in cache (1 hour TTL)
    redis_client.setex(
        cache_key,
        3600,
        json.dumps(user)
    )

    return user
```

### Concept 4: Aurora Serverless

**Aurora Serverless use cases**:
- Variable workloads (dev/test environments)
- Unpredictable traffic patterns
- Multi-tenant applications
- Infrequent usage (pauses when idle)

```python
def create_aurora_serverless_cluster():
    """Create Aurora Serverless v2 cluster"""

    response = rds.create_db_cluster(
        DBClusterIdentifier='myapp-aurora',
        Engine='aurora-postgresql',
        EngineVersion='15.4',
        MasterUsername='dbadmin',
        MasterUserPassword='SecurePassword123!',  # Example only - use AWS Secrets Manager in production
        DatabaseName='myapp',
        DBSubnetGroupName='my-db-subnet-group',
        VpcSecurityGroupIds=['sg-0123456789abcdef0'],
        ServerlessV2ScalingConfiguration={
            'MinCapacity': 0.5,  # ACUs (Aurora Capacity Units)
            'MaxCapacity': 2.0
        },
        EnableHttpEndpoint=True,  # Data API
        StorageEncrypted=True,
        BackupRetentionPeriod=7,
        Tags=[
            {'Key': 'Name', 'Value': 'myapp-aurora'},
            {'Key': 'Type', 'Value': 'serverless'}
        ]
    )

    cluster_id = response['DBCluster']['DBClusterIdentifier']

    # Create serverless instance
    rds.create_db_instance(
        DBInstanceIdentifier=f'{cluster_id}-instance-1',
        DBInstanceClass='db.serverless',
        Engine='aurora-postgresql',
        DBClusterIdentifier=cluster_id
    )

    print(f"Created Aurora Serverless cluster: {cluster_id}")
```

---

## Patterns

### Pattern 1: Database Migration with DMS

**When to use**: Migrate databases to AWS with minimal downtime

```python
import boto3

dms = boto3.client('dms')

def create_dms_replication():
    """Create DMS replication instance and task"""

    # Create replication instance
    replication_response = dms.create_replication_instance(
        ReplicationInstanceIdentifier='myapp-migration',
        ReplicationInstanceClass='dms.t3.medium',
        AllocatedStorage=100,
        VpcSecurityGroupIds=['sg-0123456789abcdef0'],
        MultiAZ=False,
        EngineVersion='3.4.7',
        PubliclyAccessible=False
    )

    # Wait for instance to be available
    waiter = dms.get_waiter('replication_instance_available')
    waiter.wait(
        Filters=[
            {'Name': 'replication-instance-id', 'Values': ['myapp-migration']}
        ]
    )

    # Create source endpoint (on-premises database)
    source_endpoint = dms.create_endpoint(
        EndpointIdentifier='source-postgres',
        EndpointType='source',
        EngineName='postgres',
        ServerName='onprem-db.example.com',
        Port=5432,
        DatabaseName='myapp',
        Username='migration_user',
        Password='migration_password'  # Example only - use AWS Secrets Manager in production
    )

    # Create target endpoint (RDS)
    target_endpoint = dms.create_endpoint(
        EndpointIdentifier='target-rds',
        EndpointType='target',
        EngineName='postgres',
        ServerName='myapp-db.abc123.us-east-1.rds.amazonaws.com',
        Port=5432,
        DatabaseName='myapp',
        Username='dbadmin',
        Password='SecurePassword123!'  # Example only - use AWS Secrets Manager in production
    )

    # Create migration task
    dms.create_replication_task(
        ReplicationTaskIdentifier='myapp-full-load',
        SourceEndpointArn=source_endpoint['Endpoint']['EndpointArn'],
        TargetEndpointArn=target_endpoint['Endpoint']['EndpointArn'],
        ReplicationInstanceArn=replication_response['ReplicationInstance']['ReplicationInstanceArn'],
        MigrationType='full-load-and-cdc',  # Full load + ongoing replication
        TableMappings=json.dumps({
            'rules': [
                {
                    'rule-type': 'selection',
                    'rule-id': '1',
                    'rule-name': 'include-all',
                    'object-locator': {
                        'schema-name': 'public',
                        'table-name': '%'
                    },
                    'rule-action': 'include'
                }
            ]
        })
    )

    print("Created DMS replication task")
```

### Pattern 2: Connection Pooling

**Use case**: Manage database connections efficiently

```python
import psycopg2
from psycopg2 import pool

# Create connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    host='myapp-db.abc123.us-east-1.rds.amazonaws.com',
    port=5432,
    database='myapp',
    user='dbadmin',
    password='SecurePassword123!'  # Example only - use AWS Secrets Manager in production
)

def execute_query(query, params=None):
    """Execute query using connection from pool"""

    conn = None
    try:
        # Get connection from pool
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Execute query
        cursor.execute(query, params)

        # Fetch results
        if cursor.description:
            results = cursor.fetchall()
        else:
            results = None

        # Commit transaction
        conn.commit()

        return results

    except Exception as e:
        if conn:
            conn.rollback()
        raise e

    finally:
        # Return connection to pool
        if conn:
            db_pool.putconn(conn)

# Lambda function with connection pooling
connection_pool = None

def lambda_handler(event, context):
    """Lambda with persistent connection pool"""
    global connection_pool

    # Initialize pool once (outside handler reuses)
    if not connection_pool:
        connection_pool = create_connection_pool()

    # Use pooled connection
    results = execute_query_pooled(connection_pool, "SELECT * FROM users LIMIT 10")

    return {
        'statusCode': 200,
        'body': json.dumps({'users': results})
    }
```

### Pattern 3: DynamoDB Batch Operations

**Use case**: Efficient bulk reads/writes

```python
def batch_write_items(table_name, items):
    """Batch write up to 25 items at a time"""

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # DynamoDB limits batch to 25 items
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f"Batch wrote {len(items)} items")

def batch_get_items(table_name, keys):
    """Batch get up to 100 items at a time"""

    dynamodb = boto3.resource('dynamodb')

    response = dynamodb.batch_get_item(
        RequestItems={
            table_name: {
                'Keys': keys,
                'ConsistentRead': True
            }
        }
    )

    items = response['Responses'][table_name]

    # Handle unprocessed keys
    while response.get('UnprocessedKeys'):
        response = dynamodb.batch_get_item(
            RequestItems=response['UnprocessedKeys']
        )
        items.extend(response['Responses'][table_name])

    return items
```

### Pattern 4: Database Backup and Restore

**Use case**: Point-in-time recovery and snapshots

```python
def create_rds_snapshot(db_instance_id):
    """Create manual snapshot"""

    snapshot_id = f"{db_instance_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    response = rds.create_db_snapshot(
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceIdentifier=db_instance_id,
        Tags=[
            {'Key': 'Type', 'Value': 'manual'},
            {'Key': 'CreatedBy', 'Value': 'automation'}
        ]
    )

    print(f"Creating snapshot: {snapshot_id}")

    return snapshot_id

def restore_from_snapshot(snapshot_id, new_instance_id):
    """Restore database from snapshot"""

    response = rds.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=new_instance_id,
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceClass='db.t3.medium',
        PubliclyAccessible=False,
        MultiAZ=True
    )

    print(f"Restoring {new_instance_id} from {snapshot_id}")

def point_in_time_restore(source_db_id, target_db_id, restore_time):
    """Restore to specific point in time"""

    response = rds.restore_db_instance_to_point_in_time(
        SourceDBInstanceIdentifier=source_db_id,
        TargetDBInstanceIdentifier=target_db_id,
        RestoreTime=restore_time,  # datetime object
        DBInstanceClass='db.t3.medium'
    )

    print(f"Restoring {target_db_id} to {restore_time}")
```

---

## Quick Reference

### Database Service Selection

| Use Case | Service | Type | Best For |
|----------|---------|------|----------|
| Relational, ACID | RDS | SQL | Structured data, transactions |
| Key-value, high scale | DynamoDB | NoSQL | Serverless, millisecond latency |
| Caching, sessions | ElastiCache | In-memory | Performance optimization |
| Variable workload | Aurora Serverless | SQL | Cost optimization |
| Graph data | Neptune | Graph | Relationships, social networks |
| Time series | Timestream | Time series | IoT, metrics, logs |

### RDS Instance Sizing

```
Workload Type      | Instance Class | Example       | vCPU | RAM
-------------------|----------------|---------------|------|-------
Dev/test           | db.t3.micro    | db.t3.micro   | 2    | 1 GB
Small production   | db.t3.medium   | db.t3.medium  | 2    | 4 GB
Medium production  | db.m5.large    | db.m5.large   | 2    | 8 GB
Large production   | db.r5.xlarge   | db.r5.xlarge  | 4    | 32 GB
Memory-intensive   | db.r5.4xlarge  | db.r5.4xlarge | 16   | 128 GB
```

### Key Guidelines

```
✅ DO: Enable Multi-AZ for production RDS instances
✅ DO: Use read replicas to scale read traffic
✅ DO: Enable automated backups (7-35 days retention)
✅ DO: Use connection pooling for Lambda functions
✅ DO: Enable encryption at rest and in transit
✅ DO: Use IAM database authentication when possible
✅ DO: Monitor performance with CloudWatch

❌ DON'T: Use DynamoDB scans for large tables (use queries)
❌ DON'T: Expose databases publicly (use VPC endpoints)
❌ DON'T: Ignore read replica lag for critical queries
❌ DON'T: Use provisioned capacity without monitoring
❌ DON'T: Store large objects in DynamoDB (use S3 + pointers)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Create new connection per Lambda invocation
def lambda_handler(event, context):
    conn = psycopg2.connect(
        host='db.example.com',
        database='myapp',
        user='dbadmin',
        password='password'
    )
    # New connection every time = connection exhaustion

# ✅ CORRECT: Reuse connection across invocations
connection = None

def lambda_handler(event, context):
    global connection

    if not connection or connection.closed:
        connection = psycopg2.connect(...)

    # Reuse connection
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users")
```

❌ **New connection per invocation**: Exhausts database connections, high latency

✅ **Correct approach**: Initialize outside handler, reuse across warm invocations

### Common Mistakes

```python
# ❌ Don't scan entire DynamoDB table
response = table.scan()
items = response['Items']
# Consumes read capacity, expensive, slow

# ✅ Correct: Use query with key condition
response = table.query(
    IndexName='email-index',
    KeyConditionExpression=Key('email').eq(user_email)
)
items = response['Items']
# Efficient, targeted read
```

❌ **DynamoDB scan**: High latency, expensive, consumes capacity

✅ **Better**: Use query with partition key, add GSI if needed

---

## Related Skills

- `aws-lambda-functions.md` - Lambda integration with databases
- `aws-storage.md` - S3 for database backups and large objects
- `aws-networking.md` - VPC endpoints for private database access
- `aws-iam-security.md` - IAM database authentication and permissions

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
