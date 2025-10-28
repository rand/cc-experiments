# PostgreSQL Migrations Reference

**Scope**: Comprehensive guide to database migrations, schema versioning, zero-downtime deployments, and migration tooling
**Lines**: ~1800
**Last Updated**: 2025-10-27

## Table of Contents

1. [Migration Fundamentals](#migration-fundamentals)
2. [Schema Versioning Strategies](#schema-versioning-strategies)
3. [Migration Tools Deep Dive](#migration-tools-deep-dive)
4. [Writing Safe Migrations](#writing-safe-migrations)
5. [Zero-Downtime Patterns](#zero-downtime-patterns)
6. [PostgreSQL Lock Behavior](#postgresql-lock-behavior)
7. [Data Migrations](#data-migrations)
8. [Testing Migrations](#testing-migrations)
9. [Rollback Strategies](#rollback-strategies)
10. [Common Pitfalls](#common-pitfalls)
11. [Advanced Topics](#advanced-topics)

---

## Migration Fundamentals

### What Are Migrations?

Migrations are **versioned, ordered scripts** that evolve database schema over time.

**Core Properties**:
- **Versioned**: Each migration has a unique identifier (timestamp, sequence number, hash)
- **Ordered**: Applied sequentially to maintain consistency
- **Tracked**: Database maintains record of applied migrations
- **Reversible**: Can roll back changes (ideally)
- **Idempotent**: Safe to run multiple times (ideally)
- **Atomic**: Changes succeed or fail as a unit (when possible)

### Why Migrations Matter

**Without migrations**:
```sql
-- Developer A: Creates table manually
CREATE TABLE users (id INT, email VARCHAR(255));

-- Developer B: Different schema!
CREATE TABLE users (id SERIAL, email TEXT, created_at TIMESTAMP);

-- Production: Who knows what's deployed?
```

**With migrations**:
```sql
-- V1: Everyone runs same migration
-- Version controlled, tested, reproducible
-- Production schema matches development
```

### Migration Lifecycle

```
Development → Testing → Staging → Production
     ↓           ↓         ↓          ↓
  V1, V2      V1, V2    V1, V2     V1, V2
```

**Key principle**: Same migrations run in all environments.

### Migration Tracking

Most tools create a metadata table:

```sql
-- Example: Flyway's schema_version table
CREATE TABLE flyway_schema_history (
    installed_rank INT NOT NULL,
    version VARCHAR(50),
    description VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL,
    script VARCHAR(1000) NOT NULL,
    checksum INT,
    installed_by VARCHAR(100) NOT NULL,
    installed_on TIMESTAMP NOT NULL DEFAULT NOW(),
    execution_time INT NOT NULL,
    success BOOLEAN NOT NULL
);
```

**Query applied migrations**:
```sql
SELECT version, description, installed_on, success
FROM flyway_schema_history
ORDER BY installed_rank;
```

---

## Schema Versioning Strategies

### Strategy 1: Forward-Only Migrations

**Approach**: Only write "up" migrations, never roll back.

```
V1 → V2 → V3 → V4
 ↓    ↓    ↓    ↓
```

**Pros**:
- Simplest approach
- No data loss from rollbacks
- Production always moves forward

**Cons**:
- Can't easily undo mistakes
- Failed migrations require fix-forward

**Best for**: Production systems where rollback is rare.

**Example**:
```sql
-- V1__initial_schema.sql
CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));

-- V2__add_username.sql
ALTER TABLE users ADD COLUMN username VARCHAR(100);

-- V3__add_index.sql
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- V4 (fix for V3 if it failed)
-- V4__retry_index.sql
DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### Strategy 2: Bidirectional Migrations (Up/Down)

**Approach**: Every migration has "up" and "down" version.

```
V1 ⇄ V2 ⇄ V3 ⇄ V4
```

**Pros**:
- Can roll back bad deployments
- Easier to develop locally (apply/revert)
- Better for testing

**Cons**:
- Down migrations can lose data
- More code to maintain
- Rollback may not be safe in production

**Best for**: Development, staging, new projects.

**Example**:
```sql
-- 001_add_users.up.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

-- 001_add_users.down.sql
-- Example of rollback migration - destructive operation for reverting schema
DROP TABLE users;

-- 002_add_username.up.sql
ALTER TABLE users ADD COLUMN username VARCHAR(100);

-- 002_add_username.down.sql
ALTER TABLE users DROP COLUMN username;
```

### Strategy 3: Immutable Migrations

**Approach**: Once applied, migrations NEVER change. Fixes go in new migrations.

**Rule**: Migration files are immutable after merge to main.

```
V1 (bug!) → V2 (fix) → V3
```

**Pros**:
- History preserved
- No checksum conflicts
- Clear audit trail

**Cons**:
- Can't fix typos in old migrations
- Must create new migration for fixes

**Best practice**: Use checksums to detect unauthorized changes.

**Example**:
```sql
-- V1__create_users.sql (has bug: wrong column type)
CREATE TABLE users (id INT, email VARCHAR(50)); -- Bug: email too short!

-- V2__fix_email_length.sql (fix in new migration)
ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(255);
```

### Strategy 4: State-Based Migrations

**Approach**: Define desired state, tool generates migrations.

**Tools**: Atlas, Prisma Migrate, TypeORM with synchronize.

```
Schema Definition (code) → Tool → Generated Migrations
```

**Pros**:
- Less manual SQL
- Auto-detects schema drift
- Type-safe (if using ORM)

**Cons**:
- Less control over migration details
- Can generate suboptimal SQL
- Tool lock-in

**Example (Atlas)**:
```hcl
// schema.hcl
table "users" {
  column "id" { type = serial }
  column "email" { type = varchar(255) }
  primary_key { columns = [column.id] }
}
```

```bash
atlas migrate diff --env local
# Generates: 20231027_initial.sql
```

---

## Migration Tools Deep Dive

### Flyway

**Language**: Java/SQL
**Philosophy**: SQL-first, version-based
**Best for**: Enterprise Java applications

**Features**:
- Simple SQL-based migrations
- Commercial support available
- Callbacks for custom logic
- Out-of-order migrations (advanced)

**Configuration**:
```properties
# flyway.conf
flyway.url=jdbc:postgresql://localhost:5432/mydb
flyway.user=postgres
flyway.password=secret
flyway.locations=filesystem:./migrations
flyway.baselineVersion=1
flyway.baselineOnMigrate=true
```

**Naming Convention**:
```
V{version}__{description}.sql
V1__initial_schema.sql
V2__add_users_table.sql
V2.1__add_users_email_index.sql  # Dot notation for sub-versions
```

**Commands**:
```bash
flyway migrate     # Apply pending migrations
flyway info        # Show migration status
flyway validate    # Validate applied migrations
flyway baseline    # Baseline existing database
flyway repair      # Fix metadata (use with caution)
flyway clean       # Drop all objects (DANGEROUS!)
```

**Callbacks**:
```sql
-- beforeMigrate.sql: Runs before any migration
SET statement_timeout = '30s';

-- afterMigrate.sql: Runs after all migrations
ANALYZE;
```

**Pros**:
- Battle-tested
- Great documentation
- Commercial support

**Cons**:
- Java dependency (JVM required)
- Pro features require license
- No native down migrations

---

### golang-migrate

**Language**: Go/SQL
**Philosophy**: Simple, CLI-focused, up/down pattern
**Best for**: Go microservices

**Features**:
- Native Go binary (no JVM)
- Up/down migrations
- Multiple database support
- Programmatic API

**Installation**:
```bash
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest
```

**Naming Convention**:
```
{version}_{description}.up.sql
{version}_{description}.down.sql

000001_initial_schema.up.sql
000001_initial_schema.down.sql
000002_add_users_table.up.sql
000002_add_users_table.down.sql
```

**Commands**:
```bash
# Create migration
migrate create -ext sql -dir migrations -seq add_users_table

# Apply all up migrations
migrate -database "postgres://localhost:5432/db?sslmode=disable" -path migrations up

# Apply one up migration
migrate -database "$DB_URL" -path migrations up 1

# Rollback one migration
migrate -database "$DB_URL" -path migrations down 1

# Force version (recovery from dirty state)
migrate -database "$DB_URL" -path migrations force 5

# Show current version
migrate -database "$DB_URL" -path migrations version
```

**Programmatic Usage**:
```go
import (
    "github.com/golang-migrate/migrate/v4"
    _ "github.com/golang-migrate/migrate/v4/database/postgres"
    _ "github.com/golang-migrate/migrate/v4/source/file"
)

m, err := migrate.New(
    "file://migrations",
    "postgres://localhost:5432/db?sslmode=disable")

m.Up() // Apply all migrations
m.Steps(2) // Apply 2 migrations
m.Down() // Rollback all (DANGEROUS!)
```

**Pros**:
- Lightweight, single binary
- Native Go integration
- Simple up/down pattern

**Cons**:
- Manual version numbering
- No automatic rollback on failure
- Limited advanced features

---

### Alembic

**Language**: Python/SQL
**Philosophy**: SQLAlchemy integration, auto-generate
**Best for**: Python applications (Flask, FastAPI, Django alternatives)

**Features**:
- Auto-generate from SQLAlchemy models
- Branching/merging migrations
- Offline SQL generation
- Revision history

**Installation**:
```bash
uv add alembic psycopg2-binary
alembic init alembic
```

**Configuration**:
```python
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://localhost:5432/mydb

# alembic/env.py
from myapp.models import Base
target_metadata = Base.metadata
```

**Creating Migrations**:
```bash
# Manual migration
alembic revision -m "add users table"

# Auto-generate from models
alembic revision --autogenerate -m "add users table"
```

**Migration File**:
```python
# alembic/versions/abc123_add_users_table.py
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'def456'  # Previous migration
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_users_email', 'users')
    op.drop_table('users')
```

**Commands**:
```bash
alembic upgrade head        # Apply all migrations
alembic upgrade +1          # Apply one migration
alembic downgrade -1        # Rollback one migration
alembic current             # Show current version
alembic history             # Show migration history
alembic stamp head          # Mark as current without running
alembic revision --sql ...  # Generate SQL without applying
```

**Branching**:
```bash
# Create branch
alembic revision -m "feature A" --head=base --branch-label=feature_a
alembic revision -m "feature B" --head=base --branch-label=feature_b

# Merge branches
alembic merge -m "merge features" feature_a feature_b
```

**Pros**:
- Tight SQLAlchemy integration
- Auto-generate migrations
- Advanced branching/merging

**Cons**:
- Python-only
- Auto-generate not always accurate
- Complex for simple projects

---

### Liquibase

**Language**: Java/XML/YAML/SQL
**Philosophy**: Database-agnostic, change sets
**Best for**: Enterprise multi-database environments

**Features**:
- Database-agnostic (Postgres, MySQL, Oracle, etc.)
- XML/YAML/SQL/JSON formats
- Preconditions and contexts
- Rollback tags

**Example (YAML)**:
```yaml
# changelog.yml
databaseChangeLog:
  - changeSet:
      id: 1
      author: developer
      changes:
        - createTable:
            tableName: users
            columns:
              - column:
                  name: id
                  type: SERIAL
                  constraints:
                    primaryKey: true
              - column:
                  name: email
                  type: VARCHAR(255)
                  constraints:
                    unique: true
                    nullable: false
      rollback:
        - dropTable:
            tableName: users
```

**Pros**:
- Database-agnostic
- Rich feature set
- Enterprise support

**Cons**:
- Complex XML/YAML syntax
- Java dependency
- Steeper learning curve

---

### dbmate

**Language**: Any/SQL
**Philosophy**: Simple, language-agnostic, minimal
**Best for**: Polyglot projects, simple setups

**Features**:
- Single binary
- Simple up/down SQL
- No dependencies
- URL-based configuration

**Installation**:
```bash
# macOS
brew install dbmate

# Or download binary
curl -fsSL -o /usr/local/bin/dbmate https://github.com/amacneil/dbmate/releases/latest/download/dbmate-linux-amd64
chmod +x /usr/local/bin/dbmate
```

**Usage**:
```bash
# Set database URL
export DATABASE_URL="postgres://localhost:5432/mydb?sslmode=disable"

# Create migration
dbmate new add_users_table

# Apply migrations
dbmate up

# Rollback
dbmate down

# Status
dbmate status
```

**Migration File**:
```sql
-- migrations/20231027120000_add_users_table.sql
-- migrate:up
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

-- migrate:down
-- Example of rollback migration - destructive operation for reverting schema
DROP TABLE users;
```

**Pros**:
- Dead simple
- Language-agnostic
- Lightweight

**Cons**:
- Limited features
- No auto-generate
- No branching

---

### Atlas

**Language**: Go/HCL
**Philosophy**: Modern, declarative, schema-as-code
**Best for**: Modern Go applications, GitOps workflows

**Features**:
- Declarative schema definition
- Automatic migration generation
- Schema diffing
- Policy-as-code (Pro)
- Cloud integration (Pro)

**Schema Definition**:
```hcl
// schema.hcl
table "users" {
  schema = schema.public
  column "id" {
    type = serial
  }
  column "email" {
    type = varchar(255)
  }
  primary_key {
    columns = [column.id]
  }
  index "idx_email" {
    unique  = true
    columns = [column.email]
  }
}
```

**Commands**:
```bash
# Inspect current schema
atlas schema inspect -u "postgres://localhost:5432/db" > schema.hcl

# Generate migration
atlas migrate diff add_users --env local

# Apply migrations
atlas migrate apply --env local

# Validate
atlas migrate validate --env local
```

**Pros**:
- Modern, declarative approach
- Type-safe schema definitions
- Great CI/CD integration

**Cons**:
- Newer tool (less mature)
- Pro features require license
- Go-centric

---

## Writing Safe Migrations

### Safety Principles

1. **Idempotency**: Safe to run multiple times
2. **Atomicity**: All-or-nothing changes
3. **Reversibility**: Can undo changes
4. **Non-blocking**: Don't lock tables
5. **Backward compatible**: Old code still works
6. **Testable**: Can verify locally

### Idempotent Migrations

**Problem**: Migration fails halfway, retried, errors on existing objects.

**Solution**: Use `IF NOT EXISTS` / `IF EXISTS`.

```sql
-- ✅ GOOD: Idempotent
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS users_email_unique UNIQUE (email);

-- ✅ GOOD: Idempotent drop (safe cleanup operation)
DROP TABLE IF EXISTS old_temp_table;

DROP INDEX IF EXISTS idx_old_index;
```

**PostgreSQL version check**:
```sql
-- IF NOT EXISTS added in:
-- CREATE TABLE IF NOT EXISTS: 9.1+
-- ALTER TABLE ADD COLUMN IF NOT EXISTS: 9.6+
-- CREATE INDEX IF NOT EXISTS: 9.5+
```

### Transaction Wrapping

**Use transactions when possible**:
```sql
BEGIN;

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    total DECIMAL(10,2) NOT NULL
);

CREATE INDEX idx_orders_user_id ON orders(user_id);

COMMIT;
```

**When NOT to use transactions**:
```sql
-- ❌ Cannot run in transaction block
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
DROP INDEX CONCURRENTLY idx_old_index;
VACUUM;
REINDEX CONCURRENTLY;
```

**Solution**: Split into separate migration files.

```sql
-- V1__add_orders_table.sql (transactional)
BEGIN;
CREATE TABLE orders (...);
COMMIT;

-- V2__add_orders_index.sql (non-transactional)
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

### Checking Constraints Without Locking

**Problem**: `ALTER TABLE ADD CONSTRAINT` locks table for validation.

**Solution**: Add constraint as `NOT VALID`, then validate separately.

```sql
-- Step 1: Add constraint without validation (fast, allows writes)
ALTER TABLE users
ADD CONSTRAINT check_age_positive
CHECK (age > 0) NOT VALID;

-- Step 2: Validate constraint (slow, but doesn't block writes)
ALTER TABLE users VALIDATE CONSTRAINT check_age_positive;
```

**Locking behavior**:
- `ADD CONSTRAINT ... NOT VALID`: ShareUpdateExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)
- `VALIDATE CONSTRAINT`: ShareUpdateExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)

### Creating Indexes Without Locking

**Problem**: `CREATE INDEX` takes AccessExclusiveLock, blocks all queries.

**Solution**: `CREATE INDEX CONCURRENTLY`

```sql
-- ❌ BAD: Locks table
CREATE INDEX idx_users_email ON users(email);

-- ✅ GOOD: No lock
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**Trade-offs**:
- Takes 2-3x longer than regular CREATE INDEX
- Cannot run in transaction
- Can fail and leave invalid index

**Check for invalid indexes**:
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname NOT IN (
    SELECT indexrelid::regclass::text
    FROM pg_index
    WHERE indisvalid
);

-- Or simpler:
SELECT indexrelid::regclass AS index_name
FROM pg_index
WHERE NOT indisvalid;
```

**Clean up invalid index**:
```sql
DROP INDEX CONCURRENTLY idx_users_email;
-- Then retry creation
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### Adding NOT NULL Columns

**Problem**: Adding NOT NULL column to non-empty table fails.

**Solution**: Multi-step approach.

```sql
-- ❌ FAILS on existing rows
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL;
-- ERROR: column "phone" contains null values

-- ✅ GOOD: Multi-step
-- Step 1: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Step 2: Backfill (in batches, see Data Migrations section)
UPDATE users SET phone = 'unknown' WHERE phone IS NULL;

-- Step 3: Add NOT NULL constraint (fast, already validated)
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

**Alternative with default**:
```sql
-- ✅ GOOD: Use default value
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT 'unknown';

-- Optionally remove default after
ALTER TABLE users ALTER COLUMN phone DROP DEFAULT;
```

**Note**: Adding column with DEFAULT rewrites entire table in PG < 11. In PG 11+, it's fast (default stored in metadata).

---

## Zero-Downtime Patterns

### Pattern 1: Adding Nullable Column

**Scenario**: Add new optional column.

**Strategy**: Single-step, backward compatible.

```sql
-- Migration: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

**Deployment**:
1. Apply migration
2. Deploy new code (can read/write phone)

**Compatibility**:
- Old code: Ignores new column
- New code: Reads/writes new column
- Zero downtime

---

### Pattern 2: Adding NOT NULL Column

**Scenario**: Add required column.

**Strategy**: Multi-phase deployment.

**Phase 1 Migration**:
```sql
-- Add nullable column with default
ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active';
```

**Phase 1 Deployment**:
- Deploy code that writes to status
- Old code ignores column, new code writes it

**Phase 2 Migration** (after all instances updated):
```sql
-- Backfill any NULLs (shouldn't be any if Phase 1 worked)
UPDATE users SET status = 'active' WHERE status IS NULL;

-- Add NOT NULL constraint
ALTER TABLE users ALTER COLUMN status SET NOT NULL;

-- Optionally drop default
ALTER TABLE users ALTER COLUMN status DROP DEFAULT;
```

**Timeline**:
- Day 1: Phase 1 migration + deployment
- Day 7: Verify all rows have status set
- Day 7: Phase 2 migration

---

### Pattern 3: Removing Column (Expand-Contract)

**Scenario**: Remove unused column.

**Strategy**: Three-phase deployment.

**Phase 1**: Stop writing (code change only, no migration)
- Deploy code that stops writing to old column
- Old code may still read column

**Phase 2**: Stop reading (code change only, no migration)
- Deploy code that doesn't reference column at all
- Wait for all instances to update

**Phase 3**: Remove column (migration)
```sql
ALTER TABLE users DROP COLUMN old_field;
```

**Timeline**:
- Week 1: Phase 1 - stop writing
- Week 2: Phase 2 - stop reading
- Week 3: Verify no references in logs
- Week 3: Phase 3 - drop column

---

### Pattern 4: Renaming Column (Dual-Write)

**Scenario**: Rename column (email → email_address).

**Strategy**: Four-phase deployment with dual-write.

**Phase 1 Migration**:
```sql
-- Add new column
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);

-- Create trigger for dual-write
CREATE OR REPLACE FUNCTION sync_email_columns()
RETURNS TRIGGER AS $$
BEGIN
    NEW.email_address := NEW.email;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_email_to_email_address
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION sync_email_columns();
```

**Phase 1 Deployment**:
- Application writes to email (trigger copies to email_address)

**Phase 2 Migration**:
```sql
-- Backfill existing rows
UPDATE users SET email_address = email WHERE email_address IS NULL;
```

**Phase 3 Deployment**:
- Application reads from email_address, writes to both

**Phase 4 Migration**:
```sql
-- Drop trigger
DROP TRIGGER sync_email_to_email_address ON users;
DROP FUNCTION sync_email_columns();

-- Drop old column
ALTER TABLE users DROP COLUMN email;

-- Optionally rename (fast metadata change)
-- Or keep email_address as final name
```

**Timeline**:
- Week 1: Phase 1 - add column, trigger
- Week 2: Phase 2 - backfill
- Week 3: Phase 3 - app reads new column
- Week 4: Verify, Phase 4 - drop old column

---

### Pattern 5: Changing Column Type

**Scenario**: Change column type (age INT → age BIGINT).

**Strategy**: Add new column, dual-write, swap.

**Phase 1 Migration**:
```sql
-- Add new column with new type
ALTER TABLE users ADD COLUMN age_new BIGINT;
```

**Phase 1 Deployment**:
- Application writes to both age and age_new

**Phase 2 Migration**:
```sql
-- Backfill
UPDATE users SET age_new = age WHERE age_new IS NULL;
```

**Phase 3 Deployment**:
- Application reads from age_new

**Phase 4 Migration**:
```sql
-- Drop old, rename new
ALTER TABLE users DROP COLUMN age;
ALTER TABLE users RENAME COLUMN age_new TO age;
```

**Shortcut for compatible types**:
```sql
-- Some type changes don't require table rewrite
ALTER TABLE users ALTER COLUMN email TYPE TEXT;  -- VARCHAR → TEXT (fast)
ALTER TABLE users ALTER COLUMN age TYPE BIGINT USING age::BIGINT;  -- May rewrite table
```

**Fast type changes (PG 12+)**:
- VARCHAR(N) → VARCHAR(M) where M > N
- VARCHAR → TEXT
- NUMERIC(a,b) → NUMERIC(c,d) where c >= a and d = b

---

### Pattern 6: Adding Index (CONCURRENTLY)

**Scenario**: Add index without blocking writes.

**Strategy**: CREATE INDEX CONCURRENTLY.

```sql
-- ❌ BAD: Locks table
CREATE INDEX idx_users_email ON users(email);

-- ✅ GOOD: No lock
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**Migration file**:
```sql
-- V5__add_users_email_index.sql
-- NOTE: Cannot run in transaction
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
```

**Handling failures**:
```sql
-- Check for invalid indexes
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;

-- Drop and retry
DROP INDEX CONCURRENTLY idx_users_email;
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

---

### Pattern 7: Adding Foreign Key

**Scenario**: Add foreign key constraint.

**Strategy**: Add NOT VALID, then validate.

```sql
-- Step 1: Add constraint without validation
ALTER TABLE orders
ADD CONSTRAINT fk_orders_user_id
FOREIGN KEY (user_id) REFERENCES users(id)
NOT VALID;

-- Step 2: Validate (allows concurrent reads/writes)
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_user_id;
```

**Locking**:
- Step 1: ShareRowExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)
- Step 2: ShareUpdateExclusiveLock (allows SELECT, INSERT, UPDATE, DELETE)

---

## PostgreSQL Lock Behavior

### Lock Modes Reference

| Lock Mode | SELECT | INSERT | UPDATE | DELETE | DDL |
|-----------|--------|--------|--------|--------|-----|
| AccessShareLock | ✓ | ✓ | ✓ | ✓ | ✗ |
| RowShareLock | ✓ | ✓ | ✓ | ✓ | ✗ |
| RowExclusiveLock | ✓ | ✓ | ✓ | ✓ | ✗ |
| ShareUpdateExclusiveLock | ✓ | ✓ | ✓ | ✓ | ✗ |
| ShareLock | ✓ | ✗ | ✗ | ✗ | ✗ |
| ShareRowExclusiveLock | ✓ | ✗ | ✗ | ✗ | ✗ |
| ExclusiveLock | ✓ | ✗ | ✗ | ✗ | ✗ |
| AccessExclusiveLock | ✗ | ✗ | ✗ | ✗ | ✗ |

### Common DDL Operations and Locks

| Operation | Lock Mode | Blocks Reads? | Blocks Writes? |
|-----------|-----------|---------------|----------------|
| CREATE TABLE | AccessExclusiveLock | ✗ (new table) | ✗ (new table) |
| DROP TABLE | AccessExclusiveLock | ✓ | ✓ |  <!-- Example of operation impact -->
| ALTER TABLE ADD COLUMN | AccessExclusiveLock | ✓ | ✓ |
| ALTER TABLE ADD COLUMN (with DEFAULT, PG 11+) | AccessExclusiveLock (brief) | ✗ (metadata only) | ✗ (metadata only) |
| CREATE INDEX | ShareLock | ✗ | ✓ |
| CREATE INDEX CONCURRENTLY | ShareUpdateExclusiveLock | ✗ | ✗ |
| DROP INDEX | AccessExclusiveLock | ✓ | ✓ |
| DROP INDEX CONCURRENTLY | ShareUpdateExclusiveLock | ✗ | ✗ |
| ADD CONSTRAINT (validated) | AccessExclusiveLock | ✓ | ✓ |
| ADD CONSTRAINT NOT VALID | ShareUpdateExclusiveLock | ✗ | ✗ |
| VALIDATE CONSTRAINT | ShareUpdateExclusiveLock | ✗ | ✗ |

### Monitoring Locks

**View current locks**:
```sql
SELECT
    locktype,
    relation::regclass,
    mode,
    granted,
    pid,
    usename,
    query
FROM pg_locks
JOIN pg_stat_activity USING (pid)
WHERE NOT granted
ORDER BY relation;
```

**View blocking queries**:
```sql
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Set statement timeout for migrations**:
```sql
-- Prevent migration from locking too long
SET statement_timeout = '30s';

-- Then run migration
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

---

## Data Migrations

### Batching Large Updates

**Problem**: `UPDATE users SET status = 'active'` locks rows and can time out.

**Solution**: Batch updates with pg_sleep.

```sql
-- ❌ BAD: Locks entire table
UPDATE users SET status = 'active' WHERE status IS NULL;

-- ✅ GOOD: Batch updates
DO $$
DECLARE
    batch_size INT := 1000;
    rows_updated INT;
    total_updated INT := 0;
BEGIN
    LOOP
        UPDATE users
        SET status = 'active'
        WHERE id IN (
            SELECT id
            FROM users
            WHERE status IS NULL
            LIMIT batch_size
        );

        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        total_updated := total_updated + rows_updated;

        RAISE NOTICE 'Updated % rows (total: %)', rows_updated, total_updated;

        EXIT WHEN rows_updated = 0;

        COMMIT; -- Release locks
        PERFORM pg_sleep(0.1); -- Avoid overwhelming database
    END LOOP;
END $$;
```

**Alternative with external script**:
```python
# batch_update.py
import psycopg2
import time

conn = psycopg2.connect("dbname=mydb")
cursor = conn.cursor()

batch_size = 1000
total_updated = 0

while True:
    cursor.execute("""
        UPDATE users SET status = 'active'
        WHERE id IN (
            SELECT id FROM users WHERE status IS NULL LIMIT %s
        )
    """, (batch_size,))

    rows = cursor.rowcount
    total_updated += rows
    conn.commit()

    print(f"Updated {rows} rows (total: {total_updated})")

    if rows == 0:
        break

    time.sleep(0.1)

cursor.close()
conn.close()
```

### Backfilling Data

**Scenario**: New column needs data from existing columns.

```sql
-- Add column
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);

-- Backfill in batches
DO $$
DECLARE
    batch_size INT := 1000;
    rows_updated INT;
BEGIN
    LOOP
        UPDATE users
        SET full_name = first_name || ' ' || last_name
        WHERE id IN (
            SELECT id
            FROM users
            WHERE full_name IS NULL
            LIMIT batch_size
        );

        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        EXIT WHEN rows_updated = 0;

        COMMIT;
        PERFORM pg_sleep(0.1);
    END LOOP;
END $$;
```

### Complex Data Transformations

**Scenario**: Normalize data (e.g., extract JSON to columns).

```sql
-- Existing: user_data JSONB column
-- New: email, phone columns

ALTER TABLE users ADD COLUMN email VARCHAR(255);
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Backfill
UPDATE users
SET
    email = user_data->>'email',
    phone = user_data->>'phone'
WHERE email IS NULL;
```

**With batching**:
```python
import psycopg2
import time

conn = psycopg2.connect("dbname=mydb")
cursor = conn.cursor()

batch_size = 1000
offset = 0

while True:
    cursor.execute("""
        WITH batch AS (
            SELECT id, user_data
            FROM users
            WHERE email IS NULL
            LIMIT %s OFFSET %s
        )
        UPDATE users
        SET
            email = batch.user_data->>'email',
            phone = batch.user_data->>'phone'
        FROM batch
        WHERE users.id = batch.id
    """, (batch_size, offset))

    rows = cursor.rowcount
    conn.commit()

    if rows == 0:
        break

    offset += batch_size
    time.sleep(0.1)

cursor.close()
conn.close()
```

---

## Testing Migrations

### Local Testing

**1. Test on production-like data**:
```bash
# Dump production schema + sample data
pg_dump -Fc --schema-only production > schema.dump
pg_dump -Fc --data-only --table=users --limit=10000 production > data.dump

# Restore to local
createdb local_test
pg_restore -d local_test schema.dump
pg_restore -d local_test data.dump

# Apply migration
migrate -database "postgres://localhost:5432/local_test" up

# Verify schema
psql local_test -c "\d users"
```

**2. Test rollback**:
```bash
# Apply migration
migrate up

# Test rollback
migrate down

# Re-apply
migrate up

# Verify data integrity
psql local_test -c "SELECT COUNT(*) FROM users"
```

**3. Test application against new schema**:
```bash
# Point application to migrated database
export DATABASE_URL="postgres://localhost:5432/local_test"

# Run tests
pytest tests/
npm test
go test ./...
```

### Staging Testing

**1. Mirror production**:
```bash
# Refresh staging from production
pg_dump -Fc production | pg_restore -d staging

# Apply migration
migrate -database "$STAGING_DB" up
```

**2. Run smoke tests**:
```bash
# API smoke tests
curl https://staging.example.com/api/users
curl https://staging.example.com/api/health

# Load test (optional)
ab -n 1000 -c 10 https://staging.example.com/api/users
```

**3. Monitor**:
```sql
-- Check for slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;
```

### CI/CD Testing

**GitHub Actions example**:
```yaml
name: Test Migrations

on: [push, pull_request]

jobs:
  test-migrations:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Apply migrations
        run: |
          migrate -database "postgres://postgres:postgres@localhost:5432/testdb?sslmode=disable" up

      - name: Verify schema
        run: |
          psql postgres://postgres:postgres@localhost:5432/testdb -c "\d users"

      - name: Test rollback
        run: |
          migrate -database "postgres://postgres:postgres@localhost:5432/testdb?sslmode=disable" down
          migrate -database "postgres://postgres:postgres@localhost:5432/testdb?sslmode=disable" up

      - name: Run application tests
        run: |
          export DATABASE_URL="postgres://postgres:postgres@localhost:5432/testdb"
          pytest tests/
```

---

## Rollback Strategies

### Strategy 1: Down Migrations

**Approach**: Write explicit rollback in down migration.

**Pros**:
- Fast rollback
- Built into migration tool
- Easy to test

**Cons**:
- Data loss if columns dropped
- Not all changes reversible

**Example**:
```sql
-- 001_add_users.up.sql
CREATE TABLE users (id SERIAL PRIMARY KEY, email VARCHAR(255));

-- 001_add_users.down.sql
-- Example of dangerous rollback - loses data! Use data preservation strategies instead.
DROP TABLE users; -- ⚠️  Loses data!
```

**Safe rollback with data preservation**:
```sql
-- 002_add_phone.up.sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- 002_add_phone.down.sql
-- Instead of DROP, could archive to another table
CREATE TABLE IF NOT EXISTS users_phone_archive AS
SELECT id, phone FROM users WHERE phone IS NOT NULL;

ALTER TABLE users DROP COLUMN phone;
```

### Strategy 2: Database Backups

**Approach**: Backup before migration, restore if needed.

```bash
# Before migration
pg_dump -Fc production > backup_$(date +%Y%m%d_%H%M%S).dump

# Apply migration
migrate up

# If rollback needed
pg_restore -d production backup_20231027_120000.dump
```

**Pros**:
- Complete rollback
- Restores data

**Cons**:
- Slow for large databases
- Downtime during restore
- Loses data written after migration

### Strategy 3: Point-in-Time Recovery (PITR)

**Approach**: Use WAL archiving to recover to specific point in time.

**Setup**:
```sql
-- postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /mnt/archive/%f'
```

**Recovery**:
```bash
# Stop database
pg_ctl stop

# ⚠️ WARNING: This permanently deletes all database data
# Always verify backups before running
# Restore base backup
rm -rf $PGDATA/*
tar -xzf base_backup.tar.gz -C $PGDATA

# Create recovery.conf (PG < 12) or recovery.signal (PG 12+)
cat > $PGDATA/recovery.signal <<EOF
restore_command = 'cp /mnt/archive/%f %p'
recovery_target_time = '2023-10-27 12:00:00'
EOF

# Start database
pg_ctl start
```

**Pros**:
- Precise rollback
- No data loss (up to target time)

**Cons**:
- Requires WAL archiving setup
- Complex recovery process
- Downtime

### Strategy 4: Blue-Green Deployment

**Approach**: Run two databases, switch traffic.

```
Blue (current) ←─── Traffic
Green (with migrations)
```

**Process**:
1. Clone Blue → Green
2. Apply migrations to Green
3. Switch traffic Blue → Green
4. If issues, switch back to Blue

**Pros**:
- Instant rollback
- Zero downtime
- Test migrations in production environment

**Cons**:
- Requires load balancer/proxy
- Data sync complexity
- Expensive (two databases)

### Strategy 5: Forward-Fix

**Approach**: Don't roll back, fix forward with new migration.

**Example**:
```sql
-- V5__add_age_column.sql (has bug: wrong type)
ALTER TABLE users ADD COLUMN age INT; -- Should be SMALLINT!

-- Don't rollback, instead:
-- V6__fix_age_column_type.sql
ALTER TABLE users ALTER COLUMN age TYPE SMALLINT;
```

**Pros**:
- No data loss
- Simple
- Maintains migration history

**Cons**:
- Requires quick fix
- Can't undo schema changes immediately

**Best for**: Production systems with continuous deployment.

---

## Common Pitfalls

### Pitfall 1: Adding NOT NULL Without Default

**Problem**:
```sql
-- ❌ Fails on existing rows
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL;
-- ERROR: column "phone" contains null values
```

**Fix**:
```sql
-- ✅ Add with default, or add nullable then backfill
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT 'unknown';

-- Or multi-step:
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
UPDATE users SET phone = 'unknown' WHERE phone IS NULL;
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

---

### Pitfall 2: Renaming Columns Directly

**Problem**:
```sql
-- ❌ Breaks old code immediately
ALTER TABLE users RENAME COLUMN email TO email_address;
```

**Fix**: Use expand-contract pattern (see Zero-Downtime Patterns).

---

### Pitfall 3: Creating Indexes Without CONCURRENTLY

**Problem**:
```sql
-- ❌ Locks table, blocks writes
CREATE INDEX idx_users_email ON users(email);
```

**Fix**:
```sql
-- ✅ No lock
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

---

### Pitfall 4: Large UPDATEs in One Transaction

**Problem**:
```sql
-- ❌ Locks millions of rows, can timeout
UPDATE users SET status = 'active'; -- 10M rows
```

**Fix**: Batch with LIMIT and pg_sleep (see Data Migrations).

---

### Pitfall 5: Changing Column Type Without Care

**Problem**:
```sql
-- ❌ Rewrites entire table, locks
ALTER TABLE users ALTER COLUMN email TYPE TEXT;
```

**Fix**: Check if rewrite needed, or use add/drop pattern.

```sql
-- Fast (no rewrite) in PostgreSQL
ALTER TABLE users ALTER COLUMN email TYPE TEXT;
-- VARCHAR → TEXT is safe, no rewrite

-- Slow (rewrites table)
ALTER TABLE users ALTER COLUMN age TYPE BIGINT USING age::BIGINT;
```

---

### Pitfall 6: Not Testing Rollback

**Problem**: Migration applied, can't be reversed, data lost.

**Fix**: Always test down migration locally.

```bash
migrate up
migrate down  # Test rollback
migrate up    # Re-apply
```

---

### Pitfall 7: Mixing Schema and Data Changes

**Problem**: Hard to debug, slow migrations.

```sql
-- ❌ Mixing concerns
ALTER TABLE users ADD COLUMN status VARCHAR(20);
UPDATE users SET status = 'active' WHERE status IS NULL;
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

**Fix**: Separate migrations.

```sql
-- V1__add_status_column.sql (schema)
ALTER TABLE users ADD COLUMN status VARCHAR(20);

-- V2__backfill_status.sql (data)
UPDATE users SET status = 'active' WHERE status IS NULL;

-- V3__make_status_not_null.sql (schema)
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

---

## Advanced Topics

### Handling Schema Drift

**Problem**: Production schema differs from migration history.

**Detection**:
```bash
# Dump production schema
pg_dump --schema-only production > production_schema.sql

# Apply migrations to clean database
migrate -database "postgres://localhost/test" up
pg_dump --schema-only test > migrated_schema.sql

# Compare
diff production_schema.sql migrated_schema.sql
```

**Fix**:
```bash
# Option 1: Baseline (for tools supporting it)
flyway baseline -baselineVersion=10

# Option 2: Force version
migrate force 10

# Option 3: Manually add/remove from metadata table
INSERT INTO schema_migrations (version) VALUES ('20231027120000');
```

---

### Multi-Tenancy Migrations

**Strategy 1: Shared schema**:
```sql
-- All tenants share same schema
-- Tenant ID in each table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL,
    email VARCHAR(255)
);

-- Migration applies to all tenants
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

**Strategy 2: Schema-per-tenant**:
```sql
-- Each tenant has own schema
CREATE SCHEMA tenant_123;
CREATE TABLE tenant_123.users (...);

CREATE SCHEMA tenant_456;
CREATE TABLE tenant_456.users (...);

-- Migration must run for each schema
DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN
        SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'
    LOOP
        EXECUTE format('ALTER TABLE %I.users ADD COLUMN phone VARCHAR(20)', schema_name);
    END LOOP;
END $$;
```

---

### Handling Enum Changes

**Problem**: Can't modify enum values in place.

```sql
-- Existing enum
CREATE TYPE status_enum AS ENUM ('pending', 'active');

-- ❌ Can't add value to enum in one step in transaction
ALTER TYPE status_enum ADD VALUE 'inactive'; -- Works, but not in transaction
```

**Safe approach**:
```sql
-- Step 1: Create new enum
CREATE TYPE status_enum_new AS ENUM ('pending', 'active', 'inactive');

-- Step 2: Add new column with new enum
ALTER TABLE users ADD COLUMN status_new status_enum_new;

-- Step 3: Migrate data
UPDATE users SET status_new = status::TEXT::status_enum_new;

-- Step 4: Drop old column, rename new
ALTER TABLE users DROP COLUMN status;
ALTER TABLE users RENAME COLUMN status_new TO status;

-- Step 5: Drop old enum
DROP TYPE status_enum;

-- Step 6: Rename new enum (optional)
ALTER TYPE status_enum_new RENAME TO status_enum;
```

---

### Partitioned Tables

**Adding partitions**:
```sql
-- Existing partitioned table
CREATE TABLE events (
    id BIGSERIAL,
    event_date DATE,
    data JSONB
) PARTITION BY RANGE (event_date);

-- Add new partition (safe, no lock on parent)
CREATE TABLE events_2023_11 PARTITION OF events
FOR VALUES FROM ('2023-11-01') TO ('2023-12-01');
```

**Detaching partitions**:
```sql
-- Detach old partition (for archiving)
ALTER TABLE events DETACH PARTITION events_2023_01;

-- Archive
\copy events_2023_01 TO '/archive/events_2023_01.csv' CSV

-- Drop partition after archiving (safe cleanup operation)
DROP TABLE events_2023_01;
```

---

### Managing Long-Running Migrations

**Problem**: Migration takes hours, blocks deployments.

**Solution**: Run migrations outside deployment.

**Workflow**:
1. Run migration manually during low-traffic window
2. Mark as applied in migration metadata
3. Deploy application (skips already-applied migration)

**Example**:
```bash
# Manually apply slow migration
psql production < migrations/V5__add_large_index.sql

# Mark as applied
INSERT INTO schema_migrations (version, description, success)
VALUES ('V5', 'add_large_index', TRUE);

# Deploy application
# Migration tool sees V5 already applied, skips it
```

---

**End of Reference**

This reference covers PostgreSQL migrations comprehensively. For practical scripts and examples, see the `scripts/` and `examples/` directories.
