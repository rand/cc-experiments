---
name: database-postgres-migrations
description: Creating database migrations for schema changes
---



# PostgreSQL Migrations

**Scope**: Database migrations, schema versioning, zero-downtime deployments
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Creating database migrations for schema changes
- Managing schema versions across environments
- Planning zero-downtime deployments
- Rolling back migrations safely
- Adding/removing columns, tables, or indexes
- Choosing migration tools or strategies

## Core Concepts

### What Are Migrations?

Migrations are **versioned scripts** that modify database schema over time.

**Key properties**:
- **Versioned**: Each migration has a unique version/timestamp
- **Ordered**: Applied sequentially (v1 → v2 → v3)
- **Tracked**: Database knows which migrations are applied
- **Reversible**: Can roll back (ideally)
- **Idempotent**: Safe to run multiple times (ideally)

### Migration Tools Comparison

| Tool | Languages | Features | Best For |
|------|-----------|----------|----------|
| **Flyway** | Java/SQL | Simple, SQL-first, commercial support | Java apps, enterprise |
| **Liquibase** | Java/XML/YAML/SQL | Complex, rollback support, database-agnostic | Enterprise, multi-DB |
| **golang-migrate** | Go/SQL | Simple, CLI-focused, programmatic | Go apps, microservices |
| **Alembic** | Python/SQL | SQLAlchemy integration, autogenerate | Python apps, Django/Flask |
| **dbmate** | Any/SQL | Simple, language-agnostic, minimal | Simple projects, polyglot |
| **Atlas** | Go/HCL | Modern, declarative, schema-as-code | Modern Go apps, GitOps |

---

## Migration File Structure

### Flyway

```
db/migration/
├── V1__initial_schema.sql
├── V2__add_users_table.sql
├── V3__add_orders_table.sql
└── V4__add_user_email_index.sql
```

**Naming**: `V{version}__{description}.sql`

```sql
-- V1__initial_schema.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### golang-migrate

```
migrations/
├── 000001_initial_schema.up.sql
├── 000001_initial_schema.down.sql
├── 000002_add_users_table.up.sql
├── 000002_add_users_table.down.sql
```

**Up/Down pattern**: Each migration has `.up.sql` (apply) and `.down.sql` (rollback).

```sql
-- 000001_initial_schema.up.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

-- 000001_initial_schema.down.sql
-- Example of rollback migration - destructive operation for reverting schema
DROP TABLE users;
```

### Alembic (Python)

```python
# alembic/versions/abc123_add_users_table.py
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('users')
```

---

## Writing Safe Migrations

### Rule 1: Make Migrations Reversible

```sql
-- ✅ GOOD: Can be reversed
-- Up
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Down
ALTER TABLE users DROP COLUMN phone;
```

```sql
-- ❌ BAD: Cannot fully reverse (data loss)
-- Up
ALTER TABLE users DROP COLUMN phone;

-- Down (can't restore data!)
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

### Rule 2: Make Migrations Idempotent

```sql
-- ✅ GOOD: Safe to run multiple times
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

```sql
-- ❌ BAD: Fails if run twice
CREATE TABLE users (...);  -- ERROR: relation "users" already exists
ALTER TABLE users ADD COLUMN phone VARCHAR(20);  -- ERROR: column already exists
```

### Rule 3: Test Migrations Before Production

```bash
# 1. Apply migration on local copy of production data
pg_dump production | psql local_test
migrate up

# 2. Verify schema
psql local_test -c "\d users"

# 3. Test rollback
migrate down
migrate up

# 4. Test application against new schema
npm test
```

### Rule 4: Use Transactions (When Possible)

```sql
BEGIN;

ALTER TABLE users ADD COLUMN phone VARCHAR(20);
CREATE INDEX idx_users_phone ON users(phone);

COMMIT;
```

**Note**: Some operations can't be in transactions:
- `CREATE INDEX CONCURRENTLY`
- `DROP INDEX CONCURRENTLY`
- `VACUUM`

For these, split into separate migration files.

---

## Zero-Downtime Migration Patterns

### Pattern 1: Adding a Column (Nullable)

**Simple case**: Adding a nullable column is safe.

```sql
-- Migration 1: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

**Deploy**: Apply migration → Deploy new code (can read/write phone).

**No downtime** because:
- Old code ignores new column
- New code reads/writes new column

### Pattern 2: Adding a Column (NOT NULL)

**Problem**: `ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL` locks table and fails if existing rows exist.

**Solution**: Multi-step approach.

```sql
-- Step 1: Add nullable column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Step 2: Backfill existing rows (in batches)
UPDATE users SET phone = 'unknown' WHERE phone IS NULL;

-- Step 3: Add NOT NULL constraint
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
```

**Deploy sequence**:
1. Apply Step 1 → Deploy code that writes to phone
2. Run Step 2 backfill (batch UPDATE with limits)
3. Apply Step 3 → Deploy code that requires phone

### Pattern 3: Removing a Column (Multi-Phase)

**Problem**: Removing a column immediately breaks old code.

**Solution**: Expand-Contract pattern.

**Phase 1 (Expand)**: Stop writing to column
```sql
-- No migration yet, just deploy code that ignores the column
-- Old code still reads column, new code ignores it
```

**Phase 2 (Wait)**: Ensure all old code is gone (all instances updated)

**Phase 3 (Contract)**: Remove column
```sql
-- Migration: Remove column
ALTER TABLE users DROP COLUMN phone;
```

**Timeline**:
- Week 1: Deploy code that stops writing to `phone`
- Week 2: Verify no reads/writes in logs
- Week 3: Drop column via migration

### Pattern 4: Renaming a Column (Multi-Phase)

**Problem**: Renaming breaks old code.

**Solution**: Dual-write pattern.

**Phase 1**: Add new column, dual-write
```sql
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);

-- Trigger or application code writes to both columns
CREATE TRIGGER sync_email_to_email_address
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION sync_email_columns();
```

**Phase 2**: Backfill old data
```sql
UPDATE users SET email_address = email WHERE email_address IS NULL;
```

**Phase 3**: Switch reads to new column
```sql
-- Deploy code that reads email_address instead of email
```

**Phase 4**: Remove old column
```sql
DROP TRIGGER sync_email_to_email_address ON users;
ALTER TABLE users DROP COLUMN email;
```

### Pattern 5: Adding an Index (CONCURRENTLY)

**Problem**: `CREATE INDEX` locks table for writes.

**Solution**: `CREATE INDEX CONCURRENTLY`

```sql
-- ✅ GOOD: No write lock, builds index in background
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**Trade-offs**:
- Takes longer than regular `CREATE INDEX`
- Can't run inside a transaction
- Can fail and leave invalid index (must clean up)

**Check for invalid indexes**:
```sql
SELECT indexrelid::regclass, indisvalid
FROM pg_index
WHERE NOT indisvalid;

-- Drop invalid index
DROP INDEX CONCURRENTLY idx_users_email;
```

### Pattern 6: Adding a Constraint (Multi-Phase)

**Problem**: `ALTER TABLE users ADD CONSTRAINT ... NOT VALID` requires table scan.

**Solution**: Add constraint without validation first, then validate.

```sql
-- Step 1: Add constraint without validation (fast, allows new writes)
ALTER TABLE users ADD CONSTRAINT check_age_positive CHECK (age > 0) NOT VALID;

-- Step 2: Validate constraint (slow, but allows concurrent reads/writes)
ALTER TABLE users VALIDATE CONSTRAINT check_age_positive;
```

**Benefit**: Step 1 is fast, Step 2 doesn't block writes.

---

## Data Migrations vs Schema Migrations

### Schema Migrations

Changes to structure:
- `CREATE TABLE`
- `ALTER TABLE ADD COLUMN`
- `CREATE INDEX`
- `ALTER TABLE ADD CONSTRAINT`

**Fast**: DDL operations (with CONCURRENTLY for indexes).

### Data Migrations

Changes to data:
- `UPDATE users SET status = 'active' WHERE status IS NULL;`
- Backfilling new columns
- Data transformations

**Slow**: Can lock tables, requires batching.

### Best Practice: Separate Data and Schema

```sql
-- Migration 1: Schema change (fast)
ALTER TABLE users ADD COLUMN status VARCHAR(20);

-- Migration 2: Data backfill (slow, run separately)
-- Run in batches to avoid long locks
DO $$
DECLARE
    batch_size INT := 1000;
    rows_updated INT;
BEGIN
    LOOP
        UPDATE users
        SET status = 'active'
        WHERE id IN (
            SELECT id FROM users WHERE status IS NULL LIMIT batch_size
        );

        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        EXIT WHEN rows_updated = 0;

        COMMIT; -- Release locks between batches
        PERFORM pg_sleep(0.1); -- Avoid overwhelming DB
    END LOOP;
END $$;
```

---

## Rollback Strategies

### Strategy 1: Down Migrations (Ideal)

```sql
-- Migration up
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Migration down
ALTER TABLE users DROP COLUMN phone;
```

**Limitations**:
- Some changes are irreversible (data deletion)
- Complex migrations are hard to reverse

### Strategy 2: Backup Before Migration

```bash
# Backup before migration
pg_dump -Fc -f backup_before_migration.dump production_db

# Apply migration
migrate up

# If rollback needed
pg_restore -d production_db backup_before_migration.dump
```

**Trade-offs**:
- Safe, but slow for large databases
- Downtime during restore

### Strategy 3: Blue-Green Deployment

1. **Blue**: Current production database
2. **Green**: New database with migrations applied
3. Switch traffic from Blue → Green
4. If issues, switch back Blue

**Benefit**: Instant rollback.
**Cost**: Requires data replication, complex setup.

---

## Common Migration Patterns

### Adding a Table

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
```

**Safe for zero-downtime**: Yes (old code ignores new table).

### Dropping a Table

```sql
-- Example of safe table drop - requires careful coordination with code deployment
DROP TABLE IF EXISTS old_logs;
```

**Safe for zero-downtime**: Only if no code references it (ensure via code deployment first).

### Changing Column Type (Dangerous)

```sql
-- ❌ DANGEROUS: Locks table, can fail
ALTER TABLE users ALTER COLUMN age TYPE BIGINT;
```

**Better approach**:
1. Add new column with new type
2. Dual-write to both columns
3. Backfill old column → new column
4. Switch reads to new column
5. Drop old column

```sql
-- Step 1
ALTER TABLE users ADD COLUMN age_bigint BIGINT;

-- Step 2: Application writes to both

-- Step 3: Backfill
UPDATE users SET age_bigint = age WHERE age_bigint IS NULL;

-- Step 4: Application reads from age_bigint

-- Step 5
ALTER TABLE users DROP COLUMN age;
ALTER TABLE users RENAME COLUMN age_bigint TO age;
```

---

## Migration Workflow

### Step 1: Create Migration

```bash
# Flyway
flyway migrate

# golang-migrate
migrate create -ext sql -dir migrations -seq add_users_table

# Alembic
alembic revision -m "add users table"
```

### Step 2: Write Migration SQL/Code

```sql
-- V1__add_users_table.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);
```

### Step 3: Test Locally

```bash
# Apply migration
migrate up

# Verify schema
psql -c "\d users"

# Test rollback
migrate down
migrate up
```

### Step 4: Code Review

**Checklist**:
- [ ] Migration is idempotent?
- [ ] Migration is reversible?
- [ ] Tested locally with production-like data?
- [ ] Zero-downtime compatible?
- [ ] Indexes created with CONCURRENTLY?
- [ ] Large data migrations batched?

### Step 5: Apply to Staging

```bash
migrate -database "postgres://staging" up
```

**Verify**: Run application tests against staging.

### Step 6: Apply to Production

```bash
# Backup first
pg_dump -Fc production > backup_$(date +%Y%m%d).dump

# Apply migration
migrate -database "postgres://production" up

# Monitor
tail -f /var/log/postgresql/postgresql.log
```

### Step 7: Monitor

Watch for:
- Migration completion
- Application errors
- Query performance changes
- Lock contention

---

## Quick Reference

### Migration Tool Commands

**Flyway**:
```bash
flyway migrate           # Apply migrations
flyway info             # Show migration status
flyway validate         # Validate applied migrations
flyway repair           # Fix migration metadata
```

**golang-migrate**:
```bash
migrate up              # Apply all migrations
migrate up 1            # Apply one migration
migrate down 1          # Rollback one migration
migrate version         # Show current version
migrate force VERSION   # Force version (fix broken state)
```

**Alembic**:
```bash
alembic upgrade head    # Apply all migrations
alembic downgrade -1    # Rollback one migration
alembic current         # Show current version
alembic history         # Show migration history
```

### Safety Checklist

```
Before Running Migrations:
[ ] Backup database
[ ] Test migration locally with production-like data
[ ] Verify migration is idempotent
[ ] Verify migration is reversible (or document why not)
[ ] Check for table locks (avoid during high traffic)
[ ] Use CONCURRENTLY for index creation
[ ] Batch large data migrations
[ ] Plan rollback strategy
[ ] Schedule during low-traffic window (if needed)
[ ] Notify team of maintenance window
```

---

## Common Pitfalls

❌ **Adding NOT NULL column without default** - Fails on existing rows
✅ Add as nullable first, backfill, then add NOT NULL

❌ **Creating indexes without CONCURRENTLY** - Locks table
✅ Use `CREATE INDEX CONCURRENTLY`

❌ **Renaming columns directly** - Breaks old code
✅ Use expand-contract pattern (add new, dual-write, drop old)

❌ **Running large UPDATEs in one transaction** - Long locks
✅ Batch updates with LIMIT and pg_sleep()

❌ **Not testing rollback** - Can't recover from failed migration
✅ Always test `migrate down` locally

❌ **Mixing schema and data changes** - Hard to debug
✅ Separate schema migrations from data migrations

---

## Related Skills

- `postgres-query-optimization.md` - Index strategies for migrations
- `postgres-schema-design.md` - Designing schemas that are migration-friendly
- `database-connection-pooling.md` - Migration impact on connections
- `orm-patterns.md` - ORM-specific migration tools (Alembic, etc.)

---

## Level 3: Resources

**Location**: `/Users/rand/src/cc-polymath/skills/database/postgres-migrations/resources/`

This skill includes comprehensive Level 3 resources for advanced migration management:

### REFERENCE.md (~1,800 lines)
Comprehensive reference covering:
- Migration fundamentals and best practices
- Schema versioning strategies (forward-only, bidirectional, immutable)
- Deep dive into migration tools (Flyway, golang-migrate, Alembic, Liquibase, dbmate, Atlas)
- Writing safe migrations (idempotency, transactions, constraints)
- Zero-downtime patterns (add column, add index, rename, change type)
- PostgreSQL lock behavior reference
- Data migrations and batching strategies
- Testing migrations (local, staging, CI/CD)
- Rollback strategies (down migrations, backups, PITR, blue-green)
- Common pitfalls and solutions
- Advanced topics (schema drift, multi-tenancy, partitions)

### Scripts (3 production-ready tools)

**analyze_migration.py** - Migration safety analyzer
- Detects unsafe DDL operations (locks, table rewrites)
- Identifies missing idempotency guards
- Warns about data loss operations
- Checks transaction compatibility
- Suggests safer alternatives
- JSON output for CI/CD integration

**generate_migration.py** - Migration file generator
- Supports multiple migration tools (Flyway, golang-migrate, Alembic, dbmate)
- Template-based generation (add table, add column, add index, etc.)
- Auto-generates safe, idempotent SQL
- Includes rollback scripts
- Dry-run mode for preview

**test_migration.sh** - Docker-based migration tester
- Spins up temporary PostgreSQL instance
- Loads production schema dumps
- Applies migrations
- Tests rollback (for supported tools)
- Verifies schema integrity
- Auto-cleanup on exit
- JSON output for CI/CD

### Examples

**python/alembic_migrations/** - Complete Alembic setup
- Configuration files (alembic.ini, env.py)
- Example migrations (initial schema, add tables)
- README with setup and usage instructions

**sql/safe_migrations/** - Safe migration patterns
- Add nullable column
- Add index concurrently
- Add table with constraints
- Add constraint with NOT VALID pattern

**sql/unsafe_migrations/** - What NOT to do
- Add NOT NULL column without default
- Create index without CONCURRENTLY
- Rename column directly
- Large UPDATE without batching

**docker/** - Testing environment
- docker-compose.yml with PostgreSQL + Flyway + pgAdmin
- Complete testing workflows
- CI/CD integration examples

### Usage

```bash
# Analyze migration for safety
./resources/scripts/analyze_migration.py migration.sql

# Generate migration from template
./resources/scripts/generate_migration.py --tool flyway --template add-column \
  --table users --column phone:varchar

# Test migration in Docker
./resources/scripts/test_migration.sh --migrations-dir migrations/ --test-rollback
```

See `resources/scripts/README.md` for complete documentation.

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
