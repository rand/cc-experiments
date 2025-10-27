#!/usr/bin/env bash
#
# Kubernetes Deployment Testing Script
#
# Tests deployments by:
# - Creating a local test cluster (kind/minikube)
# - Deploying manifests
# - Running validation tests
# - Checking pod health
# - Running smoke tests
# - Cleaning up
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Configuration
CLUSTER_NAME="test-deployment"
CLUSTER_PROVIDER="kind" # kind or minikube
NAMESPACE="test"
TIMEOUT=300
CLEANUP=true
NO_COLOR=false
JSON_OUTPUT=false
SMOKE_TEST_ENABLED=true

# Results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

# Utility functions
log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        if [[ "$NO_COLOR" == "true" ]]; then
            echo "[INFO] $*"
        else
            echo -e "${CYAN}[INFO]${RESET} $*"
        fi
    fi
}

log_success() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        if [[ "$NO_COLOR" == "true" ]]; then
            echo "[SUCCESS] $*"
        else
            echo -e "${GREEN}[SUCCESS]${RESET} $*"
        fi
    fi
}

log_warning() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        if [[ "$NO_COLOR" == "true" ]]; then
            echo "[WARNING] $*"
        else
            echo -e "${YELLOW}[WARNING]${RESET} $*"
        fi
    fi
}

log_error() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        if [[ "$NO_COLOR" == "true" ]]; then
            echo "[ERROR] $*" >&2
        else
            echo -e "${RED}[ERROR]${RESET} $*" >&2
        fi
    fi
}

log_header() {
    if [[ "$JSON_OUTPUT" == "false" && "$NO_COLOR" == "false" ]]; then
        echo -e "\n${BOLD}=== $* ===${RESET}\n"
    fi
}

# Test result tracking
record_test() {
    local test_name="$1"
    local status="$2"
    local message="${3:-}"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [[ "$status" == "PASS" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "✓ $test_name"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_error "✗ $test_name"
        [[ -n "$message" ]] && log_error "  $message"
    fi

    TEST_RESULTS+=("{\"name\":\"$test_name\",\"status\":\"$status\",\"message\":\"$message\"}")
}

# Cleanup function
cleanup() {
    if [[ "$CLEANUP" == "true" ]]; then
        log_header "Cleanup"

        if [[ "$CLUSTER_PROVIDER" == "kind" ]]; then
            log_info "Deleting kind cluster: $CLUSTER_NAME"
            kind delete cluster --name "$CLUSTER_NAME" 2>/dev/null || true
        elif [[ "$CLUSTER_PROVIDER" == "minikube" ]]; then
            log_info "Deleting minikube cluster: $CLUSTER_NAME"
            minikube delete -p "$CLUSTER_NAME" 2>/dev/null || true
        fi

        log_success "Cleanup completed"
    fi
}

# Setup trap for cleanup
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"

    local missing=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing+=("kubectl")
    fi

    # Check cluster provider
    if [[ "$CLUSTER_PROVIDER" == "kind" ]]; then
        if ! command -v kind &> /dev/null; then
            missing+=("kind")
        fi
    elif [[ "$CLUSTER_PROVIDER" == "minikube" ]]; then
        if ! command -v minikube &> /dev/null; then
            missing+=("minikube")
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing[*]}"
        log_info "Install missing tools:"
        for tool in "${missing[@]}"; do
            case "$tool" in
                kubectl)
                    log_info "  kubectl: https://kubernetes.io/docs/tasks/tools/"
                    ;;
                kind)
                    log_info "  kind: https://kind.sigs.k8s.io/docs/user/quick-start/"
                    ;;
                minikube)
                    log_info "  minikube: https://minikube.sigs.k8s.io/docs/start/"
                    ;;
            esac
        done
        exit 1
    fi

    log_success "All prerequisites met"
}

# Create test cluster
create_cluster() {
    log_header "Creating Test Cluster"

    if [[ "$CLUSTER_PROVIDER" == "kind" ]]; then
        log_info "Creating kind cluster: $CLUSTER_NAME"

        # Check if cluster already exists
        if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
            log_warning "Cluster $CLUSTER_NAME already exists, deleting..."
            kind delete cluster --name "$CLUSTER_NAME"
        fi

        # Create cluster
        cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF

    elif [[ "$CLUSTER_PROVIDER" == "minikube" ]]; then
        log_info "Creating minikube cluster: $CLUSTER_NAME"

        # Check if cluster already exists
        if minikube profile list -o json 2>/dev/null | grep -q "\"$CLUSTER_NAME\""; then
            log_warning "Cluster $CLUSTER_NAME already exists, deleting..."
            minikube delete -p "$CLUSTER_NAME"
        fi

        # Create cluster
        minikube start -p "$CLUSTER_NAME" --nodes 3
    fi

    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout="${TIMEOUT}s"

    log_success "Cluster created successfully"
}

# Create test namespace
create_namespace() {
    log_header "Creating Test Namespace"

    kubectl create namespace "$NAMESPACE" || true
    kubectl config set-context --current --namespace="$NAMESPACE"

    log_success "Namespace $NAMESPACE created"
}

# Apply manifests
apply_manifests() {
    local manifest_path="$1"

    log_header "Applying Manifests"

    if [[ -f "$manifest_path" ]]; then
        log_info "Applying manifest: $manifest_path"
        kubectl apply -f "$manifest_path" -n "$NAMESPACE"
    elif [[ -d "$manifest_path" ]]; then
        log_info "Applying manifests from directory: $manifest_path"
        kubectl apply -f "$manifest_path" -n "$NAMESPACE" --recursive
    else
        log_error "Manifest path not found: $manifest_path"
        exit 1
    fi

    log_success "Manifests applied"
}

# Wait for deployments
wait_for_deployments() {
    log_header "Waiting for Deployments"

    local deployments
    deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [[ -z "$deployments" ]]; then
        log_warning "No deployments found"
        return
    fi

    for deployment in $deployments; do
        log_info "Waiting for deployment: $deployment"

        if kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
            record_test "Deployment rollout: $deployment" "PASS"
        else
            record_test "Deployment rollout: $deployment" "FAIL" "Deployment failed to roll out"
        fi
    done
}

# Test pod health
test_pod_health() {
    log_header "Testing Pod Health"

    local pods
    pods=$(kubectl get pods -n "$NAMESPACE" -o json)

    local total_pods
    total_pods=$(echo "$pods" | jq -r '.items | length')

    if [[ "$total_pods" -eq 0 ]]; then
        record_test "Pod health check" "FAIL" "No pods found"
        return
    fi

    log_info "Checking $total_pods pod(s)"

    # Check each pod
    for i in $(seq 0 $((total_pods - 1))); do
        local pod_name
        pod_name=$(echo "$pods" | jq -r ".items[$i].metadata.name")

        local phase
        phase=$(echo "$pods" | jq -r ".items[$i].status.phase")

        local ready
        ready=$(echo "$pods" | jq -r ".items[$i].status.conditions[] | select(.type==\"Ready\") | .status")

        if [[ "$phase" == "Running" && "$ready" == "True" ]]; then
            record_test "Pod health: $pod_name" "PASS"
        else
            record_test "Pod health: $pod_name" "FAIL" "Phase: $phase, Ready: $ready"
        fi
    done
}

# Test services
test_services() {
    log_header "Testing Services"

    local services
    services=$(kubectl get services -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [[ -z "$services" ]]; then
        log_info "No services found"
        return
    fi

    for service in $services; do
        local endpoints
        endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o json | jq -r '.subsets[0].addresses | length')

        if [[ "$endpoints" -gt 0 ]]; then
            record_test "Service endpoints: $service" "PASS"
        else
            record_test "Service endpoints: $service" "FAIL" "No endpoints available"
        fi
    done
}

# Run smoke tests
run_smoke_tests() {
    if [[ "$SMOKE_TEST_ENABLED" == "false" ]]; then
        return
    fi

    log_header "Running Smoke Tests"

    # Test DNS resolution
    log_info "Testing DNS resolution"
    if kubectl run test-dns --image=busybox:1.35 --rm -i --restart=Never -n "$NAMESPACE" -- nslookup kubernetes.default 2>&1 | grep -q "Address:"; then
        record_test "DNS resolution" "PASS"
    else
        record_test "DNS resolution" "FAIL" "DNS resolution failed"
    fi

    # Test pod-to-pod communication
    local services
    services=$(kubectl get services -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')

    if [[ -n "$services" ]]; then
        local first_service
        first_service=$(echo "$services" | awk '{print $1}')

        log_info "Testing pod-to-pod communication via service: $first_service"
        if kubectl run test-connection --image=curlimages/curl:7.85.0 --rm -i --restart=Never -n "$NAMESPACE" -- curl -s --max-time 10 "http://${first_service}" &>/dev/null; then
            record_test "Pod-to-pod communication" "PASS"
        else
            record_test "Pod-to-pod communication" "FAIL" "Could not connect to service"
        fi
    fi
}

# Get cluster info for debugging
get_cluster_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        log_header "Cluster Information (for debugging)"

        log_info "Nodes:"
        kubectl get nodes

        log_info "Pods in namespace $NAMESPACE:"
        kubectl get pods -n "$NAMESPACE" -o wide

        log_info "Services in namespace $NAMESPACE:"
        kubectl get services -n "$NAMESPACE"

        if [[ "$TESTS_FAILED" -gt 0 ]]; then
            log_info "Events in namespace $NAMESPACE:"
            kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp'
        fi
    fi
}

# Print results
print_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # JSON output
        cat <<EOF
{
  "cluster_name": "$CLUSTER_NAME",
  "cluster_provider": "$CLUSTER_PROVIDER",
  "namespace": "$NAMESPACE",
  "tests_run": $TESTS_RUN,
  "tests_passed": $TESTS_PASSED,
  "tests_failed": $TESTS_FAILED,
  "success": $([ "$TESTS_FAILED" -eq 0 ] && echo "true" || echo "false"),
  "test_results": [
    $(IFS=,; echo "${TEST_RESULTS[*]}")
  ]
}
EOF
    else
        log_header "Test Results"

        echo "Tests Run:    $TESTS_RUN"
        echo "Tests Passed: $TESTS_PASSED"
        echo "Tests Failed: $TESTS_FAILED"
        echo ""

        if [[ "$TESTS_FAILED" -eq 0 ]]; then
            log_success "All tests passed! ✓"
            return 0
        else
            log_error "Some tests failed! ✗"
            return 1
        fi
    fi
}

# Usage
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] MANIFEST_PATH

Test Kubernetes deployments in a local cluster.

Arguments:
  MANIFEST_PATH          Path to manifest file or directory

Options:
  --cluster-name NAME    Test cluster name (default: $CLUSTER_NAME)
  --provider PROVIDER    Cluster provider: kind or minikube (default: $CLUSTER_PROVIDER)
  --namespace NS         Kubernetes namespace for testing (default: $NAMESPACE)
  --timeout SECONDS      Timeout for operations (default: $TIMEOUT)
  --no-cleanup           Don't delete cluster after testing
  --no-smoke-tests       Skip smoke tests
  --json                 Output results as JSON
  --no-color             Disable colored output
  -h, --help             Show this help message

Examples:
  # Test a deployment file with kind
  $(basename "$0") deployment.yaml

  # Test manifests directory with minikube
  $(basename "$0") --provider minikube manifests/

  # Test without cleanup for debugging
  $(basename "$0") --no-cleanup deployment.yaml

  # Get JSON output
  $(basename "$0") --json deployment.yaml

EOF
    exit 0
}

# Parse arguments
MANIFEST_PATH=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --cluster-name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --provider)
            CLUSTER_PROVIDER="$2"
            if [[ "$CLUSTER_PROVIDER" != "kind" && "$CLUSTER_PROVIDER" != "minikube" ]]; then
                log_error "Invalid provider: $CLUSTER_PROVIDER (must be 'kind' or 'minikube')"
                exit 1
            fi
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --no-smoke-tests)
            SMOKE_TEST_ENABLED=false
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --no-color)
            NO_COLOR=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$MANIFEST_PATH" ]]; then
                MANIFEST_PATH="$1"
            else
                log_error "Multiple manifest paths not supported"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [[ -z "$MANIFEST_PATH" ]]; then
    log_error "Manifest path required"
    usage
fi

if [[ ! -e "$MANIFEST_PATH" ]]; then
    log_error "Manifest path not found: $MANIFEST_PATH"
    exit 1
fi

# Main execution
main() {
    check_prerequisites
    create_cluster
    create_namespace
    apply_manifests "$MANIFEST_PATH"
    wait_for_deployments
    test_pod_health
    test_services
    run_smoke_tests
    get_cluster_info
    print_results
}

# Run main
main
exit $?
