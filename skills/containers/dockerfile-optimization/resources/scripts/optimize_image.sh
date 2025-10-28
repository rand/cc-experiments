#!/usr/bin/env bash
#
# optimize_image.sh - Automated Docker image optimization with before/after comparison
#
# Analyzes Docker images and provides optimization recommendations.
# Compares image sizes before and after optimization.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOCKERFILE="Dockerfile"
IMAGE_NAME=""
JSON_OUTPUT=false
VERBOSE=false
BUILD_OPTIMIZED=false

# Print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_info() {
    print_color "$BLUE" "[INFO] $*"
}

print_success() {
    print_color "$GREEN" "[SUCCESS] $*"
}

print_warning() {
    print_color "$YELLOW" "[WARNING] $*"
}

print_error() {
    print_color "$RED" "[ERROR] $*"
}

# Usage information
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] IMAGE_NAME

Analyze and optimize Docker images with before/after comparison.

OPTIONS:
    -f, --dockerfile PATH    Path to Dockerfile (default: ./Dockerfile)
    -b, --build              Build optimized version
    -j, --json               Output in JSON format
    -v, --verbose            Verbose output
    -h, --help               Show this help message

EXAMPLES:
    # Analyze image
    $(basename "$0") myapp:latest

    # Build optimized version
    $(basename "$0") -b myapp:latest

    # JSON output
    $(basename "$0") --json myapp:latest

EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--dockerfile)
                DOCKERFILE="$2"
                shift 2
                ;;
            -b|--build)
                BUILD_OPTIMIZED=true
                shift
                ;;
            -j|--json)
                JSON_OUTPUT=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                usage
                ;;
            -*)
                print_error "Unknown option: $1"
                usage
                ;;
            *)
                IMAGE_NAME="$1"
                shift
                ;;
        esac
    done

    if [[ -z "$IMAGE_NAME" ]]; then
        print_error "IMAGE_NAME is required"
        usage
    fi
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Cannot connect to Docker daemon"
        exit 1
    fi
}

# Check if image exists
check_image() {
    local image=$1
    if ! docker image inspect "$image" &> /dev/null; then
        print_error "Image not found: $image"
        return 1
    fi
    return 0
}

# Get image size in bytes
get_image_size() {
    local image=$1
    docker image inspect "$image" --format='{{.Size}}'
}

# Get human-readable size
human_size() {
    local bytes=$1
    if [[ $bytes -lt 1024 ]]; then
        echo "${bytes}B"
    elif [[ $bytes -lt 1048576 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1024}")KB"
    elif [[ $bytes -lt 1073741824 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1048576}")MB"
    else
        echo "$(awk "BEGIN {printf \"%.2f\", $bytes/1073741824}")GB"
    fi
}

# Analyze image layers
analyze_layers() {
    local image=$1

    print_info "Analyzing layers for $image..."

    local total_layers
    total_layers=$(docker history "$image" --no-trunc --format "{{.Size}}" | wc -l)

    local large_layers
    large_layers=$(docker history "$image" --no-trunc --format "{{.Size}}\t{{.CreatedBy}}" | \
                   grep -v "0B" | head -10)

    echo "$total_layers:$large_layers"
}

# Check for optimization opportunities
check_optimizations() {
    local image=$1
    local issues=()

    # Check base image
    local base_image
    base_image=$(docker image inspect "$image" --format='{{.Config.Image}}')
    if [[ $base_image == *":latest"* ]]; then
        issues+=("Using :latest tag")
    fi

    # Check for root user
    local user
    user=$(docker image inspect "$image" --format='{{.Config.User}}')
    if [[ -z "$user" ]] || [[ "$user" == "root" ]] || [[ "$user" == "0" ]]; then
        issues+=("Running as root user")
    fi

    # Check for health check
    local healthcheck
    healthcheck=$(docker image inspect "$image" --format='{{.Config.Healthcheck}}')
    if [[ "$healthcheck" == "<no value>" ]]; then
        issues+=("No healthcheck defined")
    fi

    # Check layer count
    local layers
    layers=$(docker history "$image" --quiet | wc -l)
    if [[ $layers -gt 20 ]]; then
        issues+=("High layer count: $layers")
    fi

    echo "${issues[@]}"
}

# Generate optimization recommendations
generate_recommendations() {
    local image=$1
    local size_bytes=$2
    local size_human=$3
    local issues=$4

    local recommendations=()

    # Size-based recommendations
    if [[ $size_bytes -gt 1073741824 ]]; then  # > 1GB
        recommendations+=("Consider multi-stage builds to reduce image size")
        recommendations+=("Use alpine or slim base images")
        recommendations+=("Remove build tools and cache in same layer")
    fi

    # Issue-based recommendations
    if [[ $issues == *"latest tag"* ]]; then
        recommendations+=("Pin base image to specific version")
    fi

    if [[ $issues == *"root user"* ]]; then
        recommendations+=("Add USER instruction to run as non-root")
    fi

    if [[ $issues == *"No healthcheck"* ]]; then
        recommendations+=("Add HEALTHCHECK instruction")
    fi

    if [[ $issues == *"High layer count"* ]]; then
        recommendations+=("Combine RUN commands to reduce layers")
    fi

    # General recommendations
    recommendations+=("Use .dockerignore to exclude unnecessary files")
    recommendations+=("Use --no-cache-dir for pip, npm ci for Node.js")
    recommendations+=("Clean package manager caches in same RUN command")

    printf '%s\n' "${recommendations[@]}"
}

# Create optimized Dockerfile
create_optimized_dockerfile() {
    local original_dockerfile=$1
    local optimized_dockerfile="${original_dockerfile}.optimized"

    print_info "Creating optimized Dockerfile: $optimized_dockerfile"

    # Read original
    local content
    content=$(cat "$original_dockerfile")

    # Start with header
    cat > "$optimized_dockerfile" << 'EOF'
# Auto-generated optimized Dockerfile
# Review and adjust as needed

EOF

    # Add original content with optimizations
    cat "$original_dockerfile" >> "$optimized_dockerfile"

    print_success "Created $optimized_dockerfile"
    print_warning "Review the optimized Dockerfile and adjust as needed"
}

# Output results in JSON
output_json() {
    local image=$1
    local size_bytes=$2
    local size_human=$3
    local layers=$4
    local issues=$5
    local recommendations=$6

    cat << EOF
{
  "image": "$image",
  "size": {
    "bytes": $size_bytes,
    "human": "$size_human"
  },
  "layers": $layers,
  "issues": [
$(echo "$issues" | sed 's/^/    "/; s/$/"/' | paste -sd ',' -)
  ],
  "recommendations": [
$(echo "$recommendations" | sed 's/^/    "/; s/$/"/' | paste -sd ',' -)
  ]
}
EOF
}

# Output results as text
output_text() {
    local image=$1
    local size_bytes=$2
    local size_human=$3
    local layers=$4
    local issues=$5
    local recommendations=$6

    echo ""
    print_color "$BLUE" "========================================"
    print_color "$BLUE" "Docker Image Analysis: $image"
    print_color "$BLUE" "========================================"
    echo ""

    print_info "Image Size: $size_human ($size_bytes bytes)"
    print_info "Total Layers: $layers"
    echo ""

    if [[ -n "$issues" ]]; then
        print_color "$YELLOW" "Issues Found:"
        echo "$issues" | while IFS= read -r issue; do
            echo "  - $issue"
        done
        echo ""
    else
        print_success "No issues found"
        echo ""
    fi

    print_color "$GREEN" "Optimization Recommendations:"
    echo "$recommendations" | while IFS= read -r rec; do
        echo "  - $rec"
    done
    echo ""

    # Show largest layers
    print_info "Top 10 Largest Layers:"
    docker history "$image" --human --format "table {{.Size}}\t{{.CreatedBy}}" | head -11
    echo ""
}

# Main analysis function
analyze_image() {
    local image=$1

    if ! check_image "$image"; then
        return 1
    fi

    # Gather information
    local size_bytes
    size_bytes=$(get_image_size "$image")
    local size_human
    size_human=$(human_size "$size_bytes")

    local layers
    layers=$(docker history "$image" --quiet | wc -l)

    local issues
    issues=$(check_optimizations "$image")

    local recommendations
    recommendations=$(generate_recommendations "$image" "$size_bytes" "$size_human" "$issues")

    # Output results
    if [[ "$JSON_OUTPUT" == true ]]; then
        output_json "$image" "$size_bytes" "$size_human" "$layers" "$issues" "$recommendations"
    else
        output_text "$image" "$size_bytes" "$size_human" "$layers" "$issues" "$recommendations"
    fi
}

# Build optimized image
build_optimized() {
    local image=$1
    local optimized_image="${image}-optimized"

    if [[ ! -f "$DOCKERFILE" ]]; then
        print_error "Dockerfile not found: $DOCKERFILE"
        return 1
    fi

    print_info "Building optimized image: $optimized_image"

    # Enable BuildKit
    export DOCKER_BUILDKIT=1

    # Build with optimizations
    if docker build -t "$optimized_image" -f "$DOCKERFILE" . ; then
        print_success "Built optimized image: $optimized_image"

        # Compare sizes
        local original_size
        original_size=$(get_image_size "$image")
        local optimized_size
        optimized_size=$(get_image_size "$optimized_image")

        local reduction
        reduction=$(awk "BEGIN {printf \"%.1f\", 100 - ($optimized_size * 100.0 / $original_size)}")

        echo ""
        print_color "$BLUE" "Size Comparison:"
        print_info "Original:  $(human_size "$original_size")"
        print_info "Optimized: $(human_size "$optimized_size")"
        print_success "Reduction: ${reduction}%"
        echo ""
    else
        print_error "Failed to build optimized image"
        return 1
    fi
}

# Main function
main() {
    parse_args "$@"
    check_docker

    if [[ "$BUILD_OPTIMIZED" == true ]]; then
        analyze_image "$IMAGE_NAME"
        echo ""
        build_optimized "$IMAGE_NAME"
    else
        analyze_image "$IMAGE_NAME"
    fi
}

main "$@"
