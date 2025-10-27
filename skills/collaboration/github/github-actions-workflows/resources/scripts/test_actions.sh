#!/usr/bin/env bash
#
# GitHub Actions Local Testing Script
#
# Tests GitHub Actions workflows locally using act (nektos/act)
# Measures execution time, validates outputs, and tests different event triggers.
#
# Dependencies:
#   - act: https://github.com/nektos/act (brew install act / gh extension install nektos/gh-act)
#   - docker: Required by act for running workflows
#
# Usage:
#   ./test_actions.sh --workflow ci.yml --event push
#   ./test_actions.sh --workflow ci.yml --event pull_request --json
#   ./test_actions.sh --list
#   ./test_actions.sh --help

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
WORKFLOW=""
EVENT="push"
JOB=""
OUTPUT_JSON=false
LIST_WORKFLOWS=false
VERBOSE=false
DRY_RUN=false
PLATFORM="ubuntu-latest"
ACT_FLAGS=()

# Check if act is installed
check_dependencies() {
    if ! command -v act &> /dev/null; then
        echo -e "${RED}Error: 'act' is not installed${NC}" >&2
        echo "Install with:" >&2
        echo "  brew install act" >&2
        echo "  # OR" >&2
        echo "  gh extension install nektos/gh-act" >&2
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not running${NC}" >&2
        echo "act requires Docker to run workflows" >&2
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}" >&2
        exit 1
    fi
}

# Show help
show_help() {
    cat << EOF
GitHub Actions Local Testing Script

Usage: $0 [OPTIONS]

Options:
    --workflow FILE         Workflow file to test (e.g., ci.yml)
    --event EVENT          Event type to trigger (default: push)
                           Options: push, pull_request, schedule, workflow_dispatch
    --job JOB_ID          Run specific job only
    --platform PLATFORM   Runner platform (default: ubuntu-latest)
                           Options: ubuntu-latest, ubuntu-20.04, ubuntu-22.04
    --list                List all workflows in .github/workflows/
    --json                Output results as JSON
    --verbose             Enable verbose output
    --dry-run             Show what would be executed without running
    --help                Show this help message

Examples:
    # Test a workflow with push event
    $0 --workflow ci.yml --event push

    # Test specific job
    $0 --workflow ci.yml --job build

    # Test with pull_request event and JSON output
    $0 --workflow ci.yml --event pull_request --json

    # List all workflows
    $0 --list

    # Dry run to see what would be executed
    $0 --workflow ci.yml --dry-run

Event Types:
    push                  Code push to repository
    pull_request         Pull request opened/synchronized
    schedule             Scheduled workflow (cron)
    workflow_dispatch    Manual workflow trigger
    release              Release created/published
    issue_comment        Comment on issue or PR

Note: This script uses 'act' to run GitHub Actions locally.
      Some features may not work exactly as on GitHub.

EOF
}

# List workflows
list_workflows() {
    local workflows_dir=".github/workflows"

    if [[ ! -d "$workflows_dir" ]]; then
        echo -e "${RED}Error: No workflows directory found${NC}" >&2
        exit 1
    fi

    echo -e "${BLUE}Available workflows in $workflows_dir:${NC}\n"

    local count=0
    for workflow in "$workflows_dir"/*.{yml,yaml} 2>/dev/null; do
        if [[ -f "$workflow" ]]; then
            count=$((count + 1))
            local basename=$(basename "$workflow")

            # Extract workflow name from file
            local name=$(grep -E "^name:" "$workflow" | head -1 | sed 's/name: *//' | tr -d '"' | tr -d "'")

            if [[ -z "$name" ]]; then
                name="(unnamed)"
            fi

            echo -e "${GREEN}$count. $basename${NC}"
            echo "   Name: $name"

            # Extract triggers
            local triggers=$(awk '/^on:/{flag=1;next}/^[a-zA-Z]/{flag=0}flag' "$workflow" | grep -v "^$" | sed 's/^  //' | tr '\n' ', ' | sed 's/, $//')
            if [[ -n "$triggers" ]]; then
                echo "   Triggers: $triggers"
            fi

            # Count jobs
            local job_count=$(grep -E "^  [a-z][a-z_-]+:" "$workflow" | wc -l | tr -d ' ')
            echo "   Jobs: $job_count"
            echo
        fi
    done

    if [[ $count -eq 0 ]]; then
        echo -e "${YELLOW}No workflow files found${NC}"
    else
        echo -e "${BLUE}Total workflows: $count${NC}"
    fi
}

# Validate workflow file
validate_workflow() {
    local workflow_path="$1"

    if [[ ! -f "$workflow_path" ]]; then
        # Try in .github/workflows/
        local alt_path=".github/workflows/$workflow_path"
        if [[ -f "$alt_path" ]]; then
            echo "$alt_path"
            return 0
        fi

        echo -e "${RED}Error: Workflow file not found: $workflow_path${NC}" >&2
        return 1
    fi

    echo "$workflow_path"
}

# Get workflow jobs
get_workflow_jobs() {
    local workflow_path="$1"

    if [[ ! -f "$workflow_path" ]]; then
        return 1
    fi

    # Extract job names
    grep -E "^  [a-z][a-z_-]+:" "$workflow_path" | sed 's/:$//' | sed 's/^  //' || true
}

# Run workflow with act
run_workflow() {
    local workflow_path="$1"
    local event="$2"
    local job="${3:-}"

    local start_time=$(date +%s)

    echo -e "${BLUE}Testing workflow: $(basename "$workflow_path")${NC}"
    echo -e "${BLUE}Event: $event${NC}"
    if [[ -n "$job" ]]; then
        echo -e "${BLUE}Job: $job${NC}"
    fi
    echo -e "${BLUE}Platform: $PLATFORM${NC}"
    echo

    # Build act command
    local act_cmd="act"

    # Add event
    act_cmd="$act_cmd $event"

    # Add workflow file
    act_cmd="$act_cmd -W $workflow_path"

    # Add platform
    act_cmd="$act_cmd -P $PLATFORM=ghcr.io/catthehacker/ubuntu:act-latest"

    # Add job if specified
    if [[ -n "$job" ]]; then
        act_cmd="$act_cmd -j $job"
    fi

    # Add verbose flag
    if [[ "$VERBOSE" == "true" ]]; then
        act_cmd="$act_cmd -v"
    fi

    # Add any additional flags
    for flag in "${ACT_FLAGS[@]}"; do
        act_cmd="$act_cmd $flag"
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}Dry run - would execute:${NC}"
        echo "$act_cmd"
        return 0
    fi

    # Run act
    local exit_code=0
    local output_file=$(mktemp)

    echo -e "${BLUE}Running workflow...${NC}\n"

    if ! $act_cmd 2>&1 | tee "$output_file"; then
        exit_code=$?
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Parse results
    local success=false
    if [[ $exit_code -eq 0 ]]; then
        success=true
    fi

    # Count jobs
    local job_count=$(grep -c "Job succeeded" "$output_file" || echo "0")
    local failed_jobs=$(grep -c "Job failed" "$output_file" || echo "0")

    # Generate report
    echo
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Results${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo

    if [[ "$success" == "true" ]]; then
        echo -e "${GREEN}✓ Workflow completed successfully${NC}"
    else
        echo -e "${RED}✗ Workflow failed${NC}"
    fi

    echo
    echo "Execution time: ${duration}s"
    echo "Jobs succeeded: $job_count"

    if [[ $failed_jobs -gt 0 ]]; then
        echo -e "${RED}Jobs failed: $failed_jobs${NC}"
    fi

    # Check for specific issues
    if grep -q "OCI runtime error" "$output_file"; then
        echo -e "\n${YELLOW}Warning: Container runtime errors detected${NC}"
        echo "This may be due to Docker resource limits or incompatible images"
    fi

    if grep -q "Error: exit status" "$output_file"; then
        echo -e "\n${YELLOW}Note: Some steps failed. Check output above for details.${NC}"
    fi

    # Output JSON if requested
    if [[ "$OUTPUT_JSON" == "true" ]]; then
        local workflow_name=$(basename "$workflow_path")

        cat << JSON
{
  "workflow": "$workflow_name",
  "event": "$event",
  "job": "$job",
  "platform": "$PLATFORM",
  "success": $success,
  "duration_seconds": $duration,
  "jobs_succeeded": $job_count,
  "jobs_failed": $failed_jobs,
  "exit_code": $exit_code,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
JSON
    fi

    rm -f "$output_file"

    return $exit_code
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --workflow)
                WORKFLOW="$2"
                shift 2
                ;;
            --event)
                EVENT="$2"
                shift 2
                ;;
            --job)
                JOB="$2"
                shift 2
                ;;
            --platform)
                PLATFORM="$2"
                shift 2
                ;;
            --json)
                OUTPUT_JSON=true
                shift
                ;;
            --list)
                LIST_WORKFLOWS=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown option: $1${NC}" >&2
                echo "Use --help for usage information" >&2
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    parse_args "$@"

    # Check dependencies
    check_dependencies

    # List workflows if requested
    if [[ "$LIST_WORKFLOWS" == "true" ]]; then
        list_workflows
        exit 0
    fi

    # Validate workflow is specified
    if [[ -z "$WORKFLOW" ]]; then
        echo -e "${RED}Error: --workflow is required${NC}" >&2
        echo "Use --list to see available workflows" >&2
        echo "Use --help for usage information" >&2
        exit 1
    fi

    # Validate workflow file
    local workflow_path
    if ! workflow_path=$(validate_workflow "$WORKFLOW"); then
        exit 1
    fi

    # Validate event type
    local valid_events=("push" "pull_request" "schedule" "workflow_dispatch" "release" "issue_comment" "issues" "pull_request_target")
    local event_valid=false

    for valid_event in "${valid_events[@]}"; do
        if [[ "$EVENT" == "$valid_event" ]]; then
            event_valid=true
            break
        fi
    done

    if [[ "$event_valid" == "false" ]]; then
        echo -e "${YELLOW}Warning: '$EVENT' may not be a valid event type${NC}" >&2
        echo "Valid events: ${valid_events[*]}" >&2
    fi

    # Run workflow
    run_workflow "$workflow_path" "$EVENT" "$JOB"
}

# Run main if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
