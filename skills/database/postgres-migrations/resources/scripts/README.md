# PostgreSQL Migration Scripts

Three production-ready scripts for managing PostgreSQL migrations safely.

## Scripts Overview

### 1. analyze_migration.py

**Purpose**: Analyze migration files for safety issues before applying to production.

**Features**:
- Detects unsafe DDL operations (table locks, rewrites)
- Identifies missing idempotency guards
- Warns about data loss operations
- Checks transaction compatibility
- Suggests safer alternatives

**Usage**:
```bash
# Analyze single migration
./analyze_migration.py migration.sql

# Analyze entire directory
./analyze_migration.py --dir migrations/

# JSON output for CI/CD
./analyze_migration.py --json migration.sql

# Filter by severity
./analyze_migration.py --severity error migration.sql
```

**Example Output**:
```
================================================================================
File: migrations/V1__add_users_table.sql
Status: ✗ UNSAFE
Issues: 2 errors, 1 warnings, 0 info
================================================================================

ERRORS:
  • CREATE INDEX without CONCURRENTLY (line 10)
    Suggestion: Use CREATE INDEX CONCURRENTLY to avoid blocking writes
  • Adding NOT NULL column without DEFAULT (line 5)
    Suggestion: Add column as nullable first, backfill, then add NOT NULL constraint

WARNINGS:
  • CREATE TABLE without IF NOT EXISTS (line 3)
```

**Exit Codes**:
- 0: All migrations safe
- 1: Unsafe migrations found

---

### 2. generate_migration.py

**Purpose**: Generate migration files from templates or schema diffs.

**Features**:
- Supports multiple migration tools (Flyway, golang-migrate, Alembic, dbmate)
- Template-based generation (add table, add column, add index, etc.)
- Auto-generates safe, idempotent SQL
- Includes rollback scripts (where applicable)

**Usage**:
```bash
# Generate add table migration
./generate_migration.py --tool flyway --template add-table \
  --table users --columns id:serial email:varchar name:text

# Generate add column migration
./generate_migration.py --tool golang-migrate --template add-column \
  --table users --column phone:varchar

# Generate add index migration
./generate_migration.py --template add-index --table users \
  --columns email --concurrent --unique

# Generate drop column migration (with warning)
./generate_migration.py --template drop-column --table users --column old_field

# Generate add constraint migration
./generate_migration.py --template add-constraint --table users \
  --constraint check_age_positive --constraint-type CHECK --constraint-def "age > 0"

# Generate rename column migration (with expand-contract pattern)
./generate_migration.py --template rename-column --table users \
  --old-column email --new-column email_address

# Generate custom migration template
./generate_migration.py --name add_custom_logic

# Dry run (preview without writing)
./generate_migration.py --dry-run --template add-table --table orders \
  --columns id:serial total:decimal

# JSON output
./generate_migration.py --json --template add-column --table users --column phone:varchar
```

**Templates**:
- `add-table`: Create new table with columns
- `add-column`: Add column to existing table
- `add-index`: Create index (with CONCURRENTLY by default)
- `drop-column`: Drop column (with data loss warning)
- `add-constraint`: Add constraint (with NOT VALID pattern)
- `rename-column`: Rename column (with expand-contract pattern guide)
- `custom`: Empty migration template

**Migration Tools Supported**:
- `flyway`: V{version}__{description}.sql
- `golang-migrate`: {version}_{name}.up.sql / .down.sql
- `alembic`: Python migration files
- `dbmate`: {timestamp}_{name}.sql with migrate:up/down
- `atlas`: HCL schema definitions

**Column Format**: `name:type` (e.g., `email:varchar(255)`, `age:integer`, `active:boolean`)

---

### 3. test_migration.sh

**Purpose**: Test migrations in isolated Docker environment with production-like data.

**Features**:
- Spins up temporary PostgreSQL instance
- Loads production schema dumps (optional)
- Applies migrations
- Tests rollback (if supported)
- Verifies schema integrity
- Auto-cleanup on exit

**Usage**:
```bash
# Test migrations with auto-detection
./test_migration.sh --migrations-dir migrations/

# Test with specific tool
./test_migration.sh --tool flyway --migrations-dir db/migration/

# Test with production data dump
./test_migration.sh --db-dump production_dump.sql

# Test rollback (for golang-migrate, dbmate, alembic)
./test_migration.sh --tool golang-migrate --test-rollback

# Use specific PostgreSQL version
./test_migration.sh --postgres-version 14

# JSON output for CI/CD
./test_migration.sh --json
```

**Workflow**:
1. Starts PostgreSQL in Docker container
2. Loads database dump (if provided)
3. Applies migrations using specified tool
4. Tests rollback (optional)
5. Verifies schema (checks for invalid indexes)
6. Outputs results (text or JSON)
7. Cleans up Docker container

**Requirements**:
- Docker installed and running
- Migration tool installed (flyway uses Docker image, others need CLI)

**Example Output**:
```
[12:34:56] Starting PostgreSQL 15 container...
[12:34:58] Waiting for PostgreSQL to be ready...
[12:35:00] PostgreSQL is ready!
[12:35:01] Testing golang-migrate migrations...
[12:35:03] Applied 5 migrations successfully
[12:35:03] Current migration version: 5
[12:35:04] Testing rollback...
[12:35:05] Rollback successful
[12:35:06] Re-applying migrations...
[12:35:07] Re-applied migrations
[12:35:08] Verifying schema...
[12:35:08] Found 3 tables in schema

=========================================
          TEST SUMMARY
=========================================
Total tests: 6
Passed: 6
Failed: 0
Warnings: 0
=========================================
```

**Exit Codes**:
- 0: All tests passed
- 1: Tests failed
- 2: Setup error (Docker, tool not found, etc.)

---

## Workflow Example

Complete workflow for safe migration development:

```bash
# 1. Generate migration from template
./generate_migration.py --tool golang-migrate --template add-column \
  --table users --column phone:varchar

# Created: migrations/000005_add_phone_to_users.up.sql
# Created: migrations/000005_add_phone_to_users.down.sql

# 2. Analyze migration for safety issues
./analyze_migration.py migrations/000005_add_phone_to_users.up.sql

# Status: ✓ SAFE
# Issues: 0 errors, 0 warnings, 0 info

# 3. Test migration in Docker
./test_migration.sh --tool golang-migrate --test-rollback

# All tests passed! Safe to apply to staging.

# 4. Apply to staging
migrate -database "$STAGING_DB_URL" -path migrations up

# 5. After verification, apply to production
migrate -database "$PRODUCTION_DB_URL" -path migrations up
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Migrations

on: [push, pull_request]

jobs:
  test-migrations:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Analyze migrations
        run: |
          ./skills/database/postgres-migrations/resources/scripts/analyze_migration.py \
            --dir migrations/ --json > analysis.json

          # Fail if any errors
          if jq -e '.summary.total_errors > 0' analysis.json; then
            echo "Migration analysis failed!"
            exit 1
          fi

      - name: Test migrations
        run: |
          ./skills/database/postgres-migrations/resources/scripts/test_migration.sh \
            --migrations-dir migrations/ --json > test-results.json

          # Fail if any tests failed
          if jq -e '.summary.failed > 0' test-results.json; then
            echo "Migration tests failed!"
            exit 1
          fi

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: migration-results
          path: |
            analysis.json
            test-results.json
```

---

## Requirements

**Python Scripts** (analyze_migration.py, generate_migration.py):
- Python 3.8+
- No external dependencies (uses standard library only)

**Bash Script** (test_migration.sh):
- Bash 4.0+
- Docker
- Migration tool CLI (golang-migrate, dbmate, alembic) OR uses Docker image (Flyway)

**Installation**:
```bash
# Make scripts executable
chmod +x *.py *.sh

# Install migration tools (choose one or more)
# golang-migrate
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# dbmate
brew install dbmate

# alembic
pip install alembic psycopg2-binary

# Flyway (uses Docker, no install needed)
```

---

## Best Practices

1. **Always analyze before applying**:
   ```bash
   ./analyze_migration.py migration.sql
   ```

2. **Test in Docker before staging**:
   ```bash
   ./test_migration.sh --test-rollback
   ```

3. **Use templates for consistency**:
   ```bash
   ./generate_migration.py --template add-column ...
   ```

4. **Test with production data dumps**:
   ```bash
   ./test_migration.sh --db-dump production_dump.sql
   ```

5. **Integrate into CI/CD pipeline** for automated safety checks

---

## Troubleshooting

**analyze_migration.py reports false positives**:
- Review the suggestion to understand the issue
- Add comments to migration explaining why it's safe
- Use `--severity error` to filter out warnings in CI

**generate_migration.py creates wrong format**:
- Verify `--tool` matches your migration setup
- Check `--migrations-dir` points to correct location
- Use `--dry-run` to preview before writing

**test_migration.sh fails to start Docker**:
- Ensure Docker is running: `docker ps`
- Check port conflicts: Script uses random port 5432-6432
- Review Docker logs: `docker logs postgres_migration_test_*`

**test_migration.sh says tool not found**:
- Install the migration CLI tool (golang-migrate, dbmate, alembic)
- Or use Flyway which runs in Docker (no install needed)
- Check PATH: `which migrate` or `which dbmate`

---

## License

MIT License - Use freely in your projects.
