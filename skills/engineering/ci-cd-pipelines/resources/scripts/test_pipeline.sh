#!/usr/bin/env bash
#
# Pipeline Testing Script
#
# Tests CI/CD pipeline configurations and deployment procedures through dry-runs,
# credential validation, deployment script testing, and rollback verification.
#
# Usage:
#   ./test_pipeline.sh --file .github/workflows/ci.yml --dry-run
#   ./test_pipeline.sh --test-deployment --environment staging
#   ./test_pipeline.sh --test-rollback --namespace production
#   ./test_pipeline.sh --simulate --verbose
#
# Features:
#   - Dry-run pipeline execution locally
#   - Credential and secret validation
#   - Deployment script testing
#   - Rollback procedure verification
#   - Kubernetes deployment simulation
#   - Docker build testing
#   - Full pipeline simulation
#
# Author: Skills Team
# Version: 1.0.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
VERBOSE=false
DRY_RUN=false
PIPELINE_FILE=""
ENVIRONMENT=""
NAMESPACE=""
TEST_MODE=""
FAILED_TESTS=0
PASSED_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*"
    fi
}

# Test result tracking
test_pass() {
    local test_name=$1
    PASSED_TESTS=$((PASSED_TESTS + 1))
    log_success "✓ $test_name"
}

test_fail() {
    local test_name=$1
    local reason=$2
    FAILED_TESTS=$((FAILED_TESTS + 1))
    log_error "✗ $test_name: $reason"
}

# Check dependencies
check_dependencies() {
    local required_tools=("docker" "kubectl" "jq" "curl")
    local missing_tools=()

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_warning "Missing optional tools: ${missing_tools[*]}"
        log_info "Some tests may be skipped"
    fi
}

# Parse YAML file (simplified - requires yq or python)
parse_yaml() {
    local file=$1

    if command -v yq &> /dev/null; then
        yq eval "$file"
    elif command -v python3 &> /dev/null; then
        python3 -c "import yaml, sys, json; json.dump(yaml.safe_load(sys.stdin), sys.stdout, indent=2)" < "$file"
    else
        log_error "Neither yq nor python3 available for YAML parsing"
        return 1
    fi
}

# Test GitHub Actions workflow
test_github_actions() {
    local workflow_file=$1

    log_info "Testing GitHub Actions workflow: $workflow_file"

    # Check if file exists
    if [[ ! -f "$workflow_file" ]]; then
        test_fail "File existence" "Workflow file not found: $workflow_file"
        return 1
    fi

    test_pass "File existence"

    # Validate YAML syntax
    if ! parse_yaml "$workflow_file" > /dev/null 2>&1; then
        test_fail "YAML syntax" "Invalid YAML in workflow file"
        return 1
    fi

    test_pass "YAML syntax"

    # Check for required fields
    local content
    content=$(cat "$workflow_file")

    if ! echo "$content" | grep -q "^name:"; then
        test_fail "Workflow name" "Missing 'name' field"
    else
        test_pass "Workflow name"
    fi

    if ! echo "$content" | grep -q "^on:"; then
        test_fail "Workflow triggers" "Missing 'on' field"
    else
        test_pass "Workflow triggers"
    fi

    if ! echo "$content" | grep -q "^jobs:"; then
        test_fail "Workflow jobs" "Missing 'jobs' field"
    else
        test_pass "Workflow jobs"
    fi

    # Check for checkout step
    if ! echo "$content" | grep -q "actions/checkout"; then
        test_fail "Checkout step" "No checkout step found"
    else
        test_pass "Checkout step"
    fi

    # Check for action versions
    if echo "$content" | grep -q "@master\|@main"; then
        test_fail "Action versions" "Using unstable action versions (@master or @main)"
    else
        test_pass "Action versions"
    fi

    # Check for secrets exposure
    if echo "$content" | grep -q "echo.*secrets\."; then
        test_fail "Secret handling" "Potential secret exposure in echo statements"
    else
        test_pass "Secret handling"
    fi

    # Try act if available (for local testing)
    if command -v act &> /dev/null; then
        log_info "Running act dry-run..."
        if act --dry-run -W "$workflow_file" > /dev/null 2>&1; then
            test_pass "Act dry-run"
        else
            test_fail "Act dry-run" "Act execution failed"
        fi
    else
        log_verbose "act not available, skipping local execution test"
    fi
}

# Test GitLab CI configuration
test_gitlab_ci() {
    local config_file=$1

    log_info "Testing GitLab CI configuration: $config_file"

    # Check file existence
    if [[ ! -f "$config_file" ]]; then
        test_fail "File existence" "Config file not found: $config_file"
        return 1
    fi

    test_pass "File existence"

    # Validate YAML syntax
    if ! parse_yaml "$config_file" > /dev/null 2>&1; then
        test_fail "YAML syntax" "Invalid YAML in config file"
        return 1
    fi

    test_pass "YAML syntax"

    # Check for stages
    if grep -q "^stages:" "$config_file"; then
        test_pass "Stages defined"
    else
        test_warning "Stages" "No stages defined (may use default)"
    fi

    # Check for jobs
    local job_count
    job_count=$(grep -c "^[a-zA-Z0-9_-]*:" "$config_file" || true)
    if [[ $job_count -gt 0 ]]; then
        test_pass "Jobs defined"
    else
        test_fail "Jobs defined" "No jobs found"
    fi

    # GitLab CI linter (if gitlab-ci-linter available)
    if command -v gitlab-ci-linter &> /dev/null; then
        if gitlab-ci-linter "$config_file"; then
            test_pass "GitLab CI linter"
        else
            test_fail "GitLab CI linter" "Linting failed"
        fi
    fi
}

# Test deployment credentials
test_credentials() {
    log_info "Testing deployment credentials..."

    # Test Kubernetes credentials
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info > /dev/null 2>&1; then
            test_pass "Kubernetes credentials"
            log_verbose "Cluster: $(kubectl config current-context)"
        else
            test_fail "Kubernetes credentials" "Cannot connect to cluster"
        fi
    else
        log_verbose "kubectl not available, skipping K8s credential test"
    fi

    # Test Docker credentials
    if command -v docker &> /dev/null; then
        if docker info > /dev/null 2>&1; then
            test_pass "Docker daemon"
        else
            test_fail "Docker daemon" "Docker daemon not accessible"
        fi
    fi

    # Test cloud provider credentials
    if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]] || [[ -f ~/.aws/credentials ]]; then
        if command -v aws &> /dev/null; then
            if aws sts get-caller-identity > /dev/null 2>&1; then
                test_pass "AWS credentials"
            else
                test_fail "AWS credentials" "Invalid or expired"
            fi
        fi
    fi

    if command -v gcloud &> /dev/null; then
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "@"; then
            test_pass "GCP credentials"
        else
            test_warning "GCP credentials" "No active GCP authentication"
        fi
    fi

    if command -v az &> /dev/null; then
        if az account show > /dev/null 2>&1; then
            test_pass "Azure credentials"
        else
            test_warning "Azure credentials" "No active Azure authentication"
        fi
    fi
}

# Test deployment scripts
test_deployment_scripts() {
    local environment=$1

    log_info "Testing deployment scripts for environment: $environment"

    # Common deployment script locations
    local script_paths=(
        "./deploy.sh"
        "./scripts/deploy.sh"
        "./deployment/deploy.sh"
        "./.github/scripts/deploy.sh"
    )

    local script_found=false
    for script_path in "${script_paths[@]}"; do
        if [[ -f "$script_path" ]]; then
            script_found=true
            log_info "Found deployment script: $script_path"

            # Check if executable
            if [[ -x "$script_path" ]]; then
                test_pass "Script executable"
            else
                test_fail "Script executable" "$script_path is not executable"
            fi

            # Check for help option
            if "$script_path" --help > /dev/null 2>&1 || "$script_path" -h > /dev/null 2>&1; then
                test_pass "Help option"
            else
                test_warning "Help option" "Script doesn't support --help"
            fi

            # Dry-run deployment
            if [[ "$DRY_RUN" == "true" ]]; then
                log_info "Running deployment dry-run..."
                if "$script_path" "$environment" --dry-run > /dev/null 2>&1; then
                    test_pass "Dry-run execution"
                else
                    test_warning "Dry-run execution" "Dry-run not supported or failed"
                fi
            fi

            break
        fi
    done

    if [[ "$script_found" == "false" ]]; then
        test_fail "Deployment script" "No deployment script found"
    fi
}

# Test Kubernetes deployment
test_kubernetes_deployment() {
    local namespace=${1:-default}

    log_info "Testing Kubernetes deployment configuration..."

    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not available, skipping Kubernetes tests"
        return
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info > /dev/null 2>&1; then
        test_fail "Cluster connectivity" "Cannot connect to Kubernetes cluster"
        return
    fi

    test_pass "Cluster connectivity"

    # Check namespace
    if kubectl get namespace "$namespace" > /dev/null 2>&1; then
        test_pass "Namespace exists"
    else
        test_fail "Namespace exists" "Namespace '$namespace' not found"
        return
    fi

    # Find Kubernetes manifests
    local manifest_paths=(
        "./k8s/"
        "./kubernetes/"
        "./manifests/"
        "./.kube/"
    )

    local manifests_found=false
    for manifest_dir in "${manifest_paths[@]}"; do
        if [[ -d "$manifest_dir" ]]; then
            manifests_found=true
            log_info "Found Kubernetes manifests in: $manifest_dir"

            # Validate manifests
            for yaml_file in "$manifest_dir"/*.{yaml,yml} 2>/dev/null; do
                if [[ -f "$yaml_file" ]]; then
                    log_verbose "Validating: $yaml_file"
                    if kubectl apply --dry-run=client -f "$yaml_file" > /dev/null 2>&1; then
                        test_pass "Manifest valid: $(basename "$yaml_file")"
                    else
                        test_fail "Manifest valid: $(basename "$yaml_file")" "Invalid Kubernetes manifest"
                    fi
                fi
            done
            break
        fi
    done

    if [[ "$manifests_found" == "false" ]]; then
        test_warning "K8s manifests" "No Kubernetes manifests found"
    fi

    # Check for existing deployments
    if kubectl get deployments -n "$namespace" > /dev/null 2>&1; then
        local deployment_count
        deployment_count=$(kubectl get deployments -n "$namespace" --no-headers 2>/dev/null | wc -l)
        log_info "Found $deployment_count deployment(s) in namespace $namespace"
        test_pass "Deployments exist"
    else
        test_warning "Deployments" "No deployments found in namespace"
    fi
}

# Test Docker build
test_docker_build() {
    log_info "Testing Docker build..."

    if ! command -v docker &> /dev/null; then
        log_warning "Docker not available, skipping Docker tests"
        return
    fi

    # Find Dockerfile
    local dockerfile_paths=(
        "./Dockerfile"
        "./docker/Dockerfile"
        "./build/Dockerfile"
    )

    local dockerfile_found=false
    for dockerfile in "${dockerfile_paths[@]}"; do
        if [[ -f "$dockerfile" ]]; then
            dockerfile_found=true
            log_info "Found Dockerfile: $dockerfile"

            # Validate Dockerfile
            if docker build --dry-run -f "$dockerfile" . > /dev/null 2>&1; then
                test_pass "Dockerfile valid"
            else
                # Try regular build check
                if grep -q "^FROM" "$dockerfile"; then
                    test_pass "Dockerfile syntax"
                else
                    test_fail "Dockerfile syntax" "Invalid Dockerfile"
                fi
            fi

            # Check for best practices
            if grep -q "COPY --from=" "$dockerfile"; then
                test_pass "Multi-stage build"
            else
                test_warning "Multi-stage build" "Consider using multi-stage build"
            fi

            if grep -q "^USER " "$dockerfile"; then
                test_pass "Non-root user"
            else
                test_warning "Non-root user" "Running as root (security concern)"
            fi

            # Build image if dry-run
            if [[ "$DRY_RUN" == "true" ]]; then
                log_info "Building Docker image (dry-run)..."
                if docker build -f "$dockerfile" -t test-image:latest . > /dev/null 2>&1; then
                    test_pass "Docker build"
                    # Cleanup
                    docker rmi test-image:latest > /dev/null 2>&1 || true
                else
                    test_fail "Docker build" "Build failed"
                fi
            fi

            break
        fi
    done

    if [[ "$dockerfile_found" == "false" ]]; then
        test_warning "Dockerfile" "No Dockerfile found"
    fi
}

# Test rollback procedures
test_rollback() {
    local namespace=${1:-default}

    log_info "Testing rollback procedures..."

    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not available, skipping rollback tests"
        return
    fi

    # Check cluster connectivity
    if ! kubectl cluster-info > /dev/null 2>&1; then
        test_fail "Cluster connectivity" "Cannot connect to Kubernetes cluster"
        return
    fi

    # Get deployments
    local deployments
    deployments=$(kubectl get deployments -n "$namespace" --no-headers 2>/dev/null | awk '{print $1}')

    if [[ -z "$deployments" ]]; then
        test_warning "Rollback test" "No deployments found to test rollback"
        return
    fi

    for deployment in $deployments; do
        log_verbose "Checking rollback for deployment: $deployment"

        # Check rollout history
        if kubectl rollout history deployment/"$deployment" -n "$namespace" > /dev/null 2>&1; then
            local revision_count
            revision_count=$(kubectl rollout history deployment/"$deployment" -n "$namespace" | grep -c "^[0-9]" || echo "0")

            if [[ $revision_count -gt 1 ]]; then
                test_pass "Rollback available: $deployment"
                log_verbose "  Revisions: $revision_count"

                # Test dry-run rollback
                if [[ "$DRY_RUN" == "true" ]]; then
                    if kubectl rollout undo deployment/"$deployment" -n "$namespace" --dry-run=client > /dev/null 2>&1; then
                        test_pass "Rollback simulation: $deployment"
                    else
                        test_fail "Rollback simulation: $deployment" "Rollback simulation failed"
                    fi
                fi
            else
                test_warning "Rollback history: $deployment" "Only 1 revision (cannot rollback)"
            fi
        else
            test_fail "Rollback history: $deployment" "Cannot get rollout history"
        fi
    done

    # Check for rollback script
    local rollback_scripts=(
        "./rollback.sh"
        "./scripts/rollback.sh"
        "./deployment/rollback.sh"
    )

    for script in "${rollback_scripts[@]}"; do
        if [[ -f "$script" ]]; then
            test_pass "Rollback script exists"
            if [[ -x "$script" ]]; then
                test_pass "Rollback script executable"
            else
                test_fail "Rollback script executable" "Script not executable"
            fi
            break
        fi
    done
}

# Simulate full pipeline
simulate_pipeline() {
    log_info "Simulating full pipeline execution..."

    # Stage 1: Lint and validate
    log_info "Stage 1: Lint and Validate"
    test_github_actions "${PIPELINE_FILE:-.github/workflows/ci.yml}"

    # Stage 2: Build
    log_info "Stage 2: Build"
    test_docker_build

    # Stage 3: Test
    log_info "Stage 3: Test"
    if [[ -f "package.json" ]]; then
        if command -v npm &> /dev/null; then
            log_info "Running npm tests..."
            if npm test > /dev/null 2>&1; then
                test_pass "Tests execution"
            else
                test_warning "Tests execution" "Tests failed or not configured"
            fi
        fi
    fi

    # Stage 4: Security scan
    log_info "Stage 4: Security Scan"
    if command -v trivy &> /dev/null; then
        if trivy fs . > /dev/null 2>&1; then
            test_pass "Security scan"
        else
            test_warning "Security scan" "Trivy scan found issues"
        fi
    else
        log_verbose "trivy not available, skipping security scan"
    fi

    # Stage 5: Deploy
    log_info "Stage 5: Deploy"
    test_credentials
    test_kubernetes_deployment "$NAMESPACE"

    # Stage 6: Verify
    log_info "Stage 6: Verify"
    test_rollback "$NAMESPACE"
}

# Health check for deployed services
test_service_health() {
    local url=$1

    log_info "Testing service health: $url"

    if ! command -v curl &> /dev/null; then
        log_warning "curl not available, skipping health check"
        return
    fi

    # Test health endpoint
    local health_endpoints=("/health" "/healthz" "/ping" "/ready")

    for endpoint in "${health_endpoints[@]}"; do
        local full_url="${url}${endpoint}"
        log_verbose "Checking: $full_url"

        if curl -sf "$full_url" > /dev/null 2>&1; then
            test_pass "Health endpoint: $endpoint"
            return
        fi
    done

    test_warning "Health check" "No health endpoint responded"
}

# Print test summary
print_summary() {
    local total_tests=$((PASSED_TESTS + FAILED_TESTS))

    echo ""
    echo "======================================================================"
    echo "TEST SUMMARY"
    echo "======================================================================"
    echo "Total Tests:  $total_tests"
    echo "Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo "Failed:       ${RED}$FAILED_TESTS${NC}"

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo ""
        echo "${GREEN}✓ All tests passed!${NC}"
        echo "======================================================================"
        return 0
    else
        echo ""
        echo "${RED}✗ Some tests failed${NC}"
        echo "======================================================================"
        return 1
    fi
}

# Display help
show_help() {
    cat << EOF
Pipeline Testing Script

Usage: $0 [OPTIONS]

OPTIONS:
    --file FILE              Pipeline configuration file to test
    --platform PLATFORM      Platform: github-actions, gitlab, jenkins
    --dry-run               Run in dry-run mode
    --test-deployment       Test deployment scripts
    --test-rollback         Test rollback procedures
    --test-credentials      Test deployment credentials
    --environment ENV       Target environment (dev, staging, prod)
    --namespace NS          Kubernetes namespace
    --simulate              Simulate full pipeline execution
    --verbose               Verbose output
    --help                  Show this help message

EXAMPLES:
    # Test GitHub Actions workflow
    $0 --file .github/workflows/ci.yml --dry-run

    # Test deployment to staging
    $0 --test-deployment --environment staging

    # Test rollback procedures
    $0 --test-rollback --namespace production

    # Simulate full pipeline
    $0 --simulate --verbose

    # Test credentials
    $0 --test-credentials

EOF
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --file)
                PIPELINE_FILE="$2"
                shift 2
                ;;
            --platform)
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --test-deployment)
                TEST_MODE="deployment"
                shift
                ;;
            --test-rollback)
                TEST_MODE="rollback"
                shift
                ;;
            --test-credentials)
                TEST_MODE="credentials"
                shift
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --simulate)
                TEST_MODE="simulate"
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Check dependencies
    check_dependencies

    # Execute based on test mode
    case $TEST_MODE in
        deployment)
            if [[ -z "$ENVIRONMENT" ]]; then
                log_error "Environment required for deployment test"
                exit 1
            fi
            test_deployment_scripts "$ENVIRONMENT"
            ;;
        rollback)
            test_rollback "${NAMESPACE:-default}"
            ;;
        credentials)
            test_credentials
            ;;
        simulate)
            simulate_pipeline
            ;;
        *)
            # Default: test pipeline file
            if [[ -z "$PIPELINE_FILE" ]]; then
                PIPELINE_FILE=".github/workflows/ci.yml"
            fi

            if [[ -f "$PIPELINE_FILE" ]]; then
                test_github_actions "$PIPELINE_FILE"
            else
                log_error "Pipeline file not found: $PIPELINE_FILE"
                exit 1
            fi
            ;;
    esac

    # Print summary
    print_summary
    exit $?
}

# Run main
main "$@"
