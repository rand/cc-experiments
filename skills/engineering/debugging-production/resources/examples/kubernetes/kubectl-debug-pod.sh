#!/usr/bin/env bash
#
# Kubernetes pod debugging with ephemeral containers.
#
# Demonstrates:
# - Attaching debug containers to running pods
# - Network debugging in Kubernetes
# - Log collection and analysis
# - Resource inspection
#

set -euo pipefail

POD_NAME="${1:-}"
NAMESPACE="${2:-default}"

if [[ -z "$POD_NAME" ]]; then
    echo "Usage: $0 <pod_name> [namespace]"
    echo ""
    echo "Examples:"
    echo "  $0 myapp-pod-12345 default"
    echo "  $0 myapp-pod-12345 production"
    exit 1
fi

echo "=== Debugging Pod: $POD_NAME in namespace: $NAMESPACE ==="
echo ""

# Check if pod exists
if ! kubectl get pod "$POD_NAME" -n "$NAMESPACE" &>/dev/null; then
    echo "Error: Pod $POD_NAME not found in namespace $NAMESPACE"
    exit 1
fi

# Show pod status
echo "--- Pod Status ---"
kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o wide
echo ""

# Show pod events
echo "--- Recent Events ---"
kubectl get events -n "$NAMESPACE" \
    --field-selector involvedObject.name="$POD_NAME" \
    --sort-by='.lastTimestamp' | tail -10
echo ""

# Show pod logs
echo "--- Pod Logs (last 50 lines) ---"
kubectl logs "$POD_NAME" -n "$NAMESPACE" --tail=50
echo ""

# Show pod resource usage
echo "--- Resource Usage ---"
kubectl top pod "$POD_NAME" -n "$NAMESPACE" 2>/dev/null || \
    echo "metrics-server not available"
echo ""

# Show pod spec
echo "--- Pod Specifications ---"
kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o json | jq '{
    containers: .spec.containers[] | {
        name: .name,
        image: .image,
        resources: .resources,
        ports: .ports
    },
    nodeSelector: .spec.nodeSelector,
    tolerations: .spec.tolerations
}'
echo ""

# Network debugging
echo "--- Network Debug ---"
echo "Attaching ephemeral debug container..."

kubectl debug "$POD_NAME" -n "$NAMESPACE" \
    --image=nicolaka/netshoot \
    --target="$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.containers[0].name}')" \
    -it -- /bin/bash -c "
        echo 'Network Debug Container'
        echo '======================'
        echo ''
        echo 'Network interfaces:'
        ip addr
        echo ''
        echo 'DNS resolution:'
        nslookup kubernetes.default
        echo ''
        echo 'Routing table:'
        ip route
        echo ''
        echo 'Active connections:'
        netstat -tan | head -20
    " || echo "Ephemeral containers not supported or failed"

echo ""
echo "=== Debug session complete ==="
