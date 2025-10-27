#!/usr/bin/env bash
set -euo pipefail

# Integration Test Runner
# Orchestrates integration tests with setup/teardown of test infrastructure

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DOCKER_COMPOSE_FILE="${SCRIPT_DIR}/../examples/docker/docker-compose-test.yml"
TEST_DIR="tests/integration"
REPORT_DIR="test-reports"
PARALLEL=false
KEEP_INFRA=false
VERBOSE=false
JSON_OUTPUT=false
TEST_PATTERN=""
TIMEOUT=600
DB_TYPE="postgres"
COVERAGE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
    fi
}

log_warning() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $*" >&2
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
    fi
}

show_help() {
    cat << EOF
Integration Test Runner v${VERSION}

Orchestrates integration tests with automatic setup/teardown of test infrastructure.

USAGE:
    $(basename "$0") [OPTIONS]

OPTIONS:
    -d, --test-dir DIR          Test directory (default: ${TEST_DIR})
    -p, --pattern PATTERN       Test pattern to match (e.g., "test_api_*")
    -c, --compose-file FILE     Docker Compose file (default: ${DOCKER_COMPOSE_FILE})
    --db-type TYPE              Database type: postgres, mysql, sqlite (default: ${DB_TYPE})
    --parallel                  Run tests in parallel
    --coverage                  Generate coverage report
    --keep-infra                Keep test infrastructure running after tests
    --timeout SECONDS           Test timeout in seconds (default: ${TIMEOUT})
    --report-dir DIR            Report output directory (default: ${REPORT_DIR})
    --json                      Output results as JSON
    -v, --verbose               Verbose output
    -h, --help                  Show this help message
    --version                   Show version

EXAMPLES:
    # Run all integration tests
    $(basename "$0")

    # Run with coverage
    $(basename "$0") --coverage

    # Run specific test pattern
    $(basename "$0") --pattern "test_api_*"

    # Run in parallel with custom test directory
    $(basename "$0") --parallel --test-dir tests/integration/api

    # Keep infrastructure running for debugging
    $(basename "$0") --keep-infra --verbose

    # Output as JSON
    $(basename "$0") --json

    # Run with MySQL instead of PostgreSQL
    $(basename "$0") --db-type mysql

EXIT CODES:
    0 - All tests passed
    1 - Some tests failed
    2 - Infrastructure setup failed
    3 - Invalid arguments
EOF
}

show_version() {
    echo "Integration Test Runner v${VERSION}"
}

cleanup_infrastructure() {
    if [[ "$KEEP_INFRA" == "false" ]]; then
        log_info "Cleaning up test infrastructure..."
        if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
        fi

        # Kill any background processes
        if [[ -n "${BACKGROUND_PIDS:-}" ]]; then
            for pid in $BACKGROUND_PIDS; do
                kill "$pid" 2>/dev/null || true
            done
        fi
    else
        log_warning "Keeping infrastructure running (--keep-infra specified)"
        if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
            log_info "To stop: docker-compose -f $DOCKER_COMPOSE_FILE down"
        fi
    fi
}

setup_infrastructure() {
    log_info "Setting up test infrastructure..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 2
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        return 2
    fi

    # Start services
    if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
        log_info "Starting Docker services from $DOCKER_COMPOSE_FILE"

        if [[ "$VERBOSE" == "true" ]]; then
            docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
        else
            docker-compose -f "$DOCKER_COMPOSE_FILE" up -d &>/dev/null
        fi

        # Wait for health checks
        log_info "Waiting for services to be healthy..."
        local max_attempts=30
        local attempt=0

        while [[ $attempt -lt $max_attempts ]]; do
            if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "unhealthy"; then
                sleep 2
                ((attempt++))
            else
                break
            fi
        done

        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Services failed to become healthy"
            docker-compose -f "$DOCKER_COMPOSE_FILE" ps
            return 2
        fi

        log_success "Test infrastructure is ready"
    else
        log_warning "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        log_info "Tests will run without containerized dependencies"
    fi

    return 0
}

detect_test_framework() {
    if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]]; then
        echo "pytest"
    elif [[ -f "package.json" ]]; then
        if grep -q '"vitest"' package.json; then
            echo "vitest"
        elif grep -q '"jest"' package.json; then
            echo "jest"
        else
            echo "unknown"
        fi
    elif [[ -f "go.mod" ]]; then
        echo "go"
    else
        echo "unknown"
    fi
}

run_pytest() {
    local test_args=()

    test_args+=("$TEST_DIR")

    if [[ -n "$TEST_PATTERN" ]]; then
        test_args+=(-k "$TEST_PATTERN")
    fi

    if [[ "$PARALLEL" == "true" ]]; then
        test_args+=(-n auto)
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        test_args+=(--cov=src --cov-report=html --cov-report=xml --cov-report=term)
    fi

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=(-v)
    fi

    test_args+=(--tb=short)
    test_args+=(--timeout="$TIMEOUT")

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        test_args+=(--json-report --json-report-file="${REPORT_DIR}/pytest_report.json")
    fi

    mkdir -p "$REPORT_DIR"

    log_info "Running pytest with args: ${test_args[*]}"

    if command -v uv &> /dev/null; then
        uv run pytest "${test_args[@]}"
    elif command -v pytest &> /dev/null; then
        pytest "${test_args[@]}"
    else
        python -m pytest "${test_args[@]}"
    fi
}

run_vitest() {
    local test_args=()

    if [[ -n "$TEST_PATTERN" ]]; then
        test_args+=("$TEST_PATTERN")
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        test_args+=(--coverage)
    fi

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        test_args+=(--reporter=json --outputFile="${REPORT_DIR}/vitest_report.json")
    fi

    mkdir -p "$REPORT_DIR"

    log_info "Running vitest with args: ${test_args[*]}"

    if command -v pnpm &> /dev/null; then
        pnpm vitest run "${test_args[@]}"
    elif command -v npm &> /dev/null; then
        npm run test -- "${test_args[@]}"
    else
        log_error "Neither pnpm nor npm found"
        return 1
    fi
}

run_jest() {
    local test_args=()

    test_args+=(--testPathPattern="$TEST_DIR")

    if [[ -n "$TEST_PATTERN" ]]; then
        test_args+=(--testNamePattern="$TEST_PATTERN")
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        test_args+=(--coverage)
    fi

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        test_args+=(--json --outputFile="${REPORT_DIR}/jest_report.json")
    fi

    mkdir -p "$REPORT_DIR"

    log_info "Running jest with args: ${test_args[*]}"

    if command -v pnpm &> /dev/null; then
        pnpm jest "${test_args[@]}"
    elif command -v npm &> /dev/null; then
        npm run test -- "${test_args[@]}"
    else
        log_error "Neither pnpm nor npm found"
        return 1
    fi
}

run_go_tests() {
    local test_args=()

    test_args+=("./$TEST_DIR/...")

    if [[ -n "$TEST_PATTERN" ]]; then
        test_args+=(-run "$TEST_PATTERN")
    fi

    if [[ "$PARALLEL" == "true" ]]; then
        test_args+=(-parallel 4)
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        test_args+=(-coverprofile="${REPORT_DIR}/coverage.out")
    fi

    if [[ "$VERBOSE" == "true" ]]; then
        test_args+=(-v)
    fi

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        test_args+=(-json)
    fi

    mkdir -p "$REPORT_DIR"

    log_info "Running go test with args: ${test_args[*]}"

    go test "${test_args[@]}"
}

run_tests() {
    local framework
    framework=$(detect_test_framework)

    log_info "Detected test framework: $framework"

    case "$framework" in
        pytest)
            run_pytest
            ;;
        vitest)
            run_vitest
            ;;
        jest)
            run_jest
            ;;
        go)
            run_go_tests
            ;;
        *)
            log_error "Unknown test framework. Please specify test command manually."
            return 1
            ;;
    esac
}

generate_summary() {
    local exit_code=$1

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cat << EOF
{
  "success": $([ "$exit_code" -eq 0 ] && echo "true" || echo "false"),
  "exit_code": $exit_code,
  "test_dir": "$TEST_DIR",
  "pattern": "$TEST_PATTERN",
  "parallel": $PARALLEL,
  "coverage": $COVERAGE,
  "report_dir": "$REPORT_DIR",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    else
        echo ""
        echo "======================================"
        if [[ $exit_code -eq 0 ]]; then
            log_success "All integration tests passed!"
        else
            log_error "Some integration tests failed (exit code: $exit_code)"
        fi
        echo "======================================"
        echo ""

        if [[ "$COVERAGE" == "true" ]]; then
            log_info "Coverage report available in: $REPORT_DIR"
        fi

        if [[ -d "$REPORT_DIR" ]]; then
            log_info "Test reports available in: $REPORT_DIR"
        fi
    fi
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            -d|--test-dir)
                TEST_DIR="$2"
                shift 2
                ;;
            -p|--pattern)
                TEST_PATTERN="$2"
                shift 2
                ;;
            -c|--compose-file)
                DOCKER_COMPOSE_FILE="$2"
                shift 2
                ;;
            --db-type)
                DB_TYPE="$2"
                shift 2
                ;;
            --parallel)
                PARALLEL=true
                shift
                ;;
            --coverage)
                COVERAGE=true
                shift
                ;;
            --keep-infra)
                KEEP_INFRA=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --report-dir)
                REPORT_DIR="$2"
                shift 2
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 3
                ;;
        esac
    done

    # Validate test directory
    if [[ ! -d "$TEST_DIR" ]]; then
        log_error "Test directory not found: $TEST_DIR"
        exit 3
    fi

    # Setup trap for cleanup
    trap cleanup_infrastructure EXIT INT TERM

    # Setup infrastructure
    if ! setup_infrastructure; then
        log_error "Failed to setup test infrastructure"
        exit 2
    fi

    # Set environment variables for tests
    export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://test:test@localhost:5432/testdb}"
    export TEST_REDIS_URL="${TEST_REDIS_URL:-redis://localhost:6379}"
    export TEST_ENVIRONMENT="integration"

    # Run tests
    local exit_code=0
    if run_tests; then
        exit_code=0
    else
        exit_code=$?
    fi

    # Generate summary
    generate_summary $exit_code

    exit $exit_code
}

main "$@"
