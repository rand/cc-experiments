#!/usr/bin/env bash
#
# PostgreSQL Migration Testing Script
#
# Tests migrations in isolated Docker environment with production-like data.
# Supports multiple migration tools and provides rollback testing.
#
# Features:
# - Spin up temporary PostgreSQL instance in Docker
# - Load production schema dump (optional)
# - Apply migrations
# - Test rollback (if supported)
# - Verify schema integrity
# - Cleanup on exit
#
# Usage:
#   ./test_migration.sh --migrations-dir migrations/
#   ./test_migration.sh --tool flyway --db-dump production_dump.sql
#   ./test_migration.sh --tool golang-migrate --test-rollback
#   ./test_migration.sh --json

set -euo pipefail

# Default values
MIGRATIONS_DIR="migrations"
TOOL="auto"
DB_DUMP=""
TEST_ROLLBACK=false
JSON_OUTPUT=false
POSTGRES_VERSION="15"
DB_NAME="migration_test"
DB_USER="postgres"
DB_PASSWORD="test_password"
CONTAINER_NAME="postgres_migration_test_$$"
DB_PORT=$((5432 + (RANDOM % 1000)))

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# JSON result
declare -a TEST_RESULTS=()

log() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"
    fi
}

error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
    fi
}

warn() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARN]${NC} $*"
    fi
}

add_result() {
    local test_name="$1"
    local status="$2"
    local message="${3:-}"

    TEST_RESULTS+=("{\"test\":\"$test_name\",\"status\":\"$status\",\"message\":\"$message\"}")
}

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Test PostgreSQL migrations in isolated Docker environment.

OPTIONS:
    --migrations-dir DIR    Migrations directory (default: migrations/)
    --tool TOOL             Migration tool: flyway, golang-migrate, alembic, dbmate, auto (default: auto)
    --db-dump FILE          PostgreSQL dump file to load before migrations
    --test-rollback         Test rollback (down migrations)
    --postgres-version VER  PostgreSQL version (default: 15)
    --json                  Output results as JSON
    --help                  Show this help message

EXAMPLES:
    # Test migrations with auto-detection
    $0 --migrations-dir migrations/

    # Test with specific tool
    $0 --tool flyway --migrations-dir db/migration/

    # Test with production data
    $0 --db-dump production_dump.sql

    # Test rollback
    $0 --test-rollback

    # JSON output for CI/CD
    $0 --json

MIGRATION TOOLS:
    - flyway: Uses flyway Docker image
    - golang-migrate: Uses golang-migrate CLI
    - alembic: Uses alembic CLI (requires Python)
    - dbmate: Uses dbmate CLI
    - auto: Auto-detect based on migration file naming

EXIT CODES:
    0 - All tests passed
    1 - Tests failed
    2 - Setup error
EOF
}

detect_migration_tool() {
    local migrations_dir="$1"

    if [[ ! -d "$migrations_dir" ]]; then
        error "Migrations directory not found: $migrations_dir"
        exit 2
    fi

    # Check for Flyway naming pattern: V{version}__{description}.sql
    if ls "$migrations_dir"/V*__*.sql &>/dev/null; then
        echo "flyway"
        return
    fi

    # Check for golang-migrate naming: {version}_{name}.up.sql
    if ls "$migrations_dir"/*_*.up.sql &>/dev/null; then
        echo "golang-migrate"
        return
    fi

    # Check for dbmate naming: {timestamp}_{name}.sql with migrate:up
    if ls "$migrations_dir"/[0-9]*_*.sql &>/dev/null; then
        # Check if file contains migrate:up marker
        if grep -q "^-- migrate:up" "$migrations_dir"/[0-9]*_*.sql 2>/dev/null; then
            echo "dbmate"
            return
        fi
    fi

    # Check for Alembic: Python files in versions/
    if [[ -d "$migrations_dir/versions" ]] && ls "$migrations_dir"/versions/*.py &>/dev/null; then
        echo "alembic"
        return
    fi

    error "Could not auto-detect migration tool. Use --tool to specify."
    exit 2
}

start_postgres() {
    log "Starting PostgreSQL $POSTGRES_VERSION container..."

    docker run -d \
        --name "$CONTAINER_NAME" \
        -e POSTGRES_DB="$DB_NAME" \
        -e POSTGRES_USER="$DB_USER" \
        -e POSTGRES_PASSWORD="$DB_PASSWORD" \
        -p "$DB_PORT:5432" \
        "postgres:$POSTGRES_VERSION" \
        >/dev/null

    log "Waiting for PostgreSQL to be ready..."

    for i in {1..30}; do
        if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" &>/dev/null; then
            log "PostgreSQL is ready!"
            return 0
        fi
        sleep 1
    done

    error "PostgreSQL failed to start within 30 seconds"
    exit 2
}

stop_postgres() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log "Stopping and removing PostgreSQL container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

load_dump() {
    local dump_file="$1"

    if [[ ! -f "$dump_file" ]]; then
        error "Dump file not found: $dump_file"
        exit 2
    fi

    log "Loading database dump: $dump_file"

    if [[ "$dump_file" == *.sql ]]; then
        docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$dump_file"
    elif [[ "$dump_file" == *.dump ]]; then
        cat "$dump_file" | docker exec -i "$CONTAINER_NAME" pg_restore -U "$DB_USER" -d "$DB_NAME"
    else
        error "Unsupported dump format. Use .sql or .dump"
        exit 2
    fi

    add_result "load_dump" "passed" "Loaded dump: $dump_file"
}

run_psql() {
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" "$@"
}

test_flyway_migrations() {
    log "Testing Flyway migrations..."

    # Use Flyway Docker image
    docker run --rm \
        --network host \
        -v "$(pwd)/$MIGRATIONS_DIR:/flyway/sql" \
        flyway/flyway:latest \
        -url="jdbc:postgresql://localhost:$DB_PORT/$DB_NAME" \
        -user="$DB_USER" \
        -password="$DB_PASSWORD" \
        migrate

    add_result "apply_migrations" "passed" "Flyway migrations applied"

    # Verify migration history
    local count
    count=$(run_psql -t -c "SELECT COUNT(*) FROM flyway_schema_history WHERE success = true;" | tr -d ' ')

    log "Applied $count migrations successfully"
    add_result "migration_count" "passed" "Applied $count migrations"
}

test_golang_migrate_migrations() {
    log "Testing golang-migrate migrations..."

    # Check if migrate is installed
    if ! command -v migrate &>/dev/null; then
        error "golang-migrate not found. Install: go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest"
        add_result "apply_migrations" "failed" "golang-migrate not installed"
        return 1
    fi

    local db_url="postgres://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME?sslmode=disable"

    # Apply migrations
    migrate -database "$db_url" -path "$MIGRATIONS_DIR" up

    add_result "apply_migrations" "passed" "golang-migrate migrations applied"

    # Check version
    local version
    version=$(migrate -database "$db_url" -path "$MIGRATIONS_DIR" version 2>&1 || echo "unknown")

    log "Current migration version: $version"
    add_result "migration_version" "passed" "Version: $version"

    # Test rollback if requested
    if [[ "$TEST_ROLLBACK" == "true" ]]; then
        log "Testing rollback..."

        migrate -database "$db_url" -path "$MIGRATIONS_DIR" down 1

        add_result "rollback" "passed" "Rollback successful"

        log "Re-applying migrations..."
        migrate -database "$db_url" -path "$MIGRATIONS_DIR" up

        add_result "reapply" "passed" "Re-applied migrations"
    fi
}

test_dbmate_migrations() {
    log "Testing dbmate migrations..."

    # Check if dbmate is installed
    if ! command -v dbmate &>/dev/null; then
        error "dbmate not found. Install: brew install dbmate or download from GitHub"
        add_result "apply_migrations" "failed" "dbmate not installed"
        return 1
    fi

    export DATABASE_URL="postgres://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME?sslmode=disable"

    # Apply migrations
    dbmate -d "$MIGRATIONS_DIR" up

    add_result "apply_migrations" "passed" "dbmate migrations applied"

    # Test rollback if requested
    if [[ "$TEST_ROLLBACK" == "true" ]]; then
        log "Testing rollback..."

        dbmate -d "$MIGRATIONS_DIR" down

        add_result "rollback" "passed" "Rollback successful"

        log "Re-applying migrations..."
        dbmate -d "$MIGRATIONS_DIR" up

        add_result "reapply" "passed" "Re-applied migrations"
    fi
}

test_alembic_migrations() {
    log "Testing Alembic migrations..."

    # Check if alembic is installed
    if ! command -v alembic &>/dev/null; then
        error "alembic not found. Install: pip install alembic psycopg2-binary"
        add_result "apply_migrations" "failed" "alembic not installed"
        return 1
    fi

    # Set database URL in environment
    export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"

    # Apply migrations
    alembic upgrade head

    add_result "apply_migrations" "passed" "Alembic migrations applied"

    # Test rollback if requested
    if [[ "$TEST_ROLLBACK" == "true" ]]; then
        log "Testing rollback..."

        alembic downgrade -1

        add_result "rollback" "passed" "Rollback successful"

        log "Re-applying migrations..."
        alembic upgrade head

        add_result "reapply" "passed" "Re-applied migrations"
    fi
}

verify_schema() {
    log "Verifying schema..."

    # List all tables
    local tables
    tables=$(run_psql -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

    log "Found $tables tables in schema"
    add_result "schema_verification" "passed" "Found $tables tables"

    # Check for invalid indexes
    local invalid_indexes
    invalid_indexes=$(run_psql -t -c "SELECT COUNT(*) FROM pg_index WHERE NOT indisvalid;" | tr -d ' ')

    if [[ "$invalid_indexes" -gt 0 ]]; then
        warn "Found $invalid_indexes invalid indexes!"
        add_result "invalid_indexes" "warning" "Found $invalid_indexes invalid indexes"
    else
        add_result "invalid_indexes" "passed" "No invalid indexes"
    fi
}

output_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Output JSON
        echo -n '{"results":['
        printf '%s' "${TEST_RESULTS[@]}" | paste -sd ','
        echo -n '],"summary":{'
        echo -n "\"total\":${#TEST_RESULTS[@]},"
        echo -n "\"passed\":$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"passed"'),"
        echo -n "\"failed\":$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"failed"' || echo 0)"
        echo '}}'
    else
        # Human-readable summary
        echo ""
        echo "========================================="
        echo "          TEST SUMMARY"
        echo "========================================="
        echo "Total tests: ${#TEST_RESULTS[@]}"
        echo "Passed: $(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"passed"')"
        echo "Failed: $(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"failed"' || echo 0)"
        echo "Warnings: $(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"warning"' || echo 0)"
        echo "========================================="
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --migrations-dir)
            MIGRATIONS_DIR="$2"
            shift 2
            ;;
        --tool)
            TOOL="$2"
            shift 2
            ;;
        --db-dump)
            DB_DUMP="$2"
            shift 2
            ;;
        --test-rollback)
            TEST_ROLLBACK=true
            shift
            ;;
        --postgres-version)
            POSTGRES_VERSION="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 2
            ;;
    esac
done

# Main execution
main() {
    # Trap cleanup on exit
    trap stop_postgres EXIT

    # Auto-detect tool if needed
    if [[ "$TOOL" == "auto" ]]; then
        TOOL=$(detect_migration_tool "$MIGRATIONS_DIR")
        log "Detected migration tool: $TOOL"
    fi

    # Start PostgreSQL
    start_postgres

    # Load dump if provided
    if [[ -n "$DB_DUMP" ]]; then
        load_dump "$DB_DUMP"
    fi

    # Run migrations based on tool
    case "$TOOL" in
        flyway)
            test_flyway_migrations
            ;;
        golang-migrate)
            test_golang_migrate_migrations
            ;;
        dbmate)
            test_dbmate_migrations
            ;;
        alembic)
            test_alembic_migrations
            ;;
        *)
            error "Unsupported migration tool: $TOOL"
            exit 2
            ;;
    esac

    # Verify schema
    verify_schema

    # Output results
    output_results

    # Determine exit code
    local failed_count
    failed_count=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c '"status":"failed"' || echo 0)

    if [[ "$failed_count" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

main
