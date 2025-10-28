#!/usr/bin/env bash
#
# Security Headers Testing Script
#
# Tests security headers across multiple domains and environments.
# Supports batch testing, header validation, and comparison reports.

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
OUTPUT_FORMAT="text"
TIMEOUT=10
FOLLOW_REDIRECTS=true
PARALLEL_JOBS=5
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS] <url1> [url2 ...]

Test security headers across multiple domains.

OPTIONS:
    -f, --file FILE         Read URLs from file (one per line)
    -o, --output FORMAT     Output format: text, json, csv (default: text)
    -t, --timeout SECONDS   Request timeout (default: 10)
    -n, --no-redirects      Don't follow redirects
    -j, --jobs N            Parallel jobs (default: 5)
    -v, --verbose           Verbose output
    -c, --compare           Compare headers across URLs
    -h, --help              Show this help message

EXAMPLES:
    # Test single domain
    $(basename "$0") https://example.com

    # Test multiple domains
    $(basename "$0") example.com example.org example.net

    # Test domains from file
    $(basename "$0") -f domains.txt

    # JSON output for CI/CD
    $(basename "$0") --output json example.com > results.json

    # Compare headers across environments
    $(basename "$0") --compare staging.example.com production.example.com

    # Parallel testing with verbose output
    $(basename "$0") -j 10 -v -f domains.txt

EOF
    exit 0
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" >&2
}

# Check dependencies
check_dependencies() {
    local missing=()

    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi

    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing[*]}"
        log_info "Install with: brew install ${missing[*]} (macOS) or apt-get install ${missing[*]} (Linux)"
        exit 1
    fi
}

# Test single URL for security headers
test_url() {
    local url="$1"
    local output_file="$2"

    # Add https:// if no protocol
    if [[ ! "$url" =~ ^https?:// ]]; then
        url="https://$url"
    fi

    local curl_opts=(-s -I -L --max-time "$TIMEOUT" -w "\n\nHTTP_CODE:%{http_code}\nREDIRECT_URL:%{url_effective}")

    if [ "$FOLLOW_REDIRECTS" = false ]; then
        curl_opts=(-s -I --max-time "$TIMEOUT" -w "\n\nHTTP_CODE:%{http_code}")
    fi

    if [ "$VERBOSE" = true ]; then
        log_info "Testing $url"
    fi

    # Fetch headers
    local response
    if ! response=$(curl "${curl_opts[@]}" "$url" 2>&1); then
        log_error "Failed to fetch $url"
        return 1
    fi

    # Parse response
    local http_code
    http_code=$(echo "$response" | grep "^HTTP_CODE:" | cut -d: -f2)

    local redirect_url
    redirect_url=$(echo "$response" | grep "^REDIRECT_URL:" | cut -d: -f2- || echo "$url")

    # Extract headers
    local strict_transport_security
    strict_transport_security=$(echo "$response" | grep -i "^strict-transport-security:" | cut -d: -f2- | xargs || echo "")

    local content_security_policy
    content_security_policy=$(echo "$response" | grep -i "^content-security-policy:" | cut -d: -f2- | xargs || echo "")

    local x_frame_options
    x_frame_options=$(echo "$response" | grep -i "^x-frame-options:" | cut -d: -f2- | xargs || echo "")

    local x_content_type_options
    x_content_type_options=$(echo "$response" | grep -i "^x-content-type-options:" | cut -d: -f2- | xargs || echo "")

    local referrer_policy
    referrer_policy=$(echo "$response" | grep -i "^referrer-policy:" | cut -d: -f2- | xargs || echo "")

    local permissions_policy
    permissions_policy=$(echo "$response" | grep -i "^permissions-policy:" | cut -d: -f2- | xargs || echo "")

    local feature_policy
    feature_policy=$(echo "$response" | grep -i "^feature-policy:" | cut -d: -f2- | xargs || echo "")

    local x_xss_protection
    x_xss_protection=$(echo "$response" | grep -i "^x-xss-protection:" | cut -d: -f2- | xargs || echo "")

    # Score calculation
    local score=0
    local max_score=100

    # HSTS (20 points)
    if [ -n "$strict_transport_security" ]; then
        score=$((score + 20))
    fi

    # CSP (30 points)
    if [ -n "$content_security_policy" ]; then
        score=$((score + 30))
    fi

    # X-Frame-Options (15 points)
    if [ -n "$x_frame_options" ]; then
        score=$((score + 15))
    fi

    # X-Content-Type-Options (15 points)
    if [ -n "$x_content_type_options" ]; then
        score=$((score + 15))
    fi

    # Referrer-Policy (10 points)
    if [ -n "$referrer_policy" ]; then
        score=$((score + 10))
    fi

    # Permissions-Policy (10 points)
    if [ -n "$permissions_policy" ] || [ -n "$feature_policy" ]; then
        score=$((score + 10))
    fi

    # Calculate grade
    local grade
    if [ "$score" -ge 90 ]; then
        grade="A"
    elif [ "$score" -ge 80 ]; then
        grade="B"
    elif [ "$score" -ge 70 ]; then
        grade="C"
    elif [ "$score" -ge 60 ]; then
        grade="D"
    else
        grade="F"
    fi

    # Output based on format
    case "$OUTPUT_FORMAT" in
        json)
            cat > "$output_file" <<EOF
{
  "url": "$url",
  "final_url": "$redirect_url",
  "http_code": $http_code,
  "grade": "$grade",
  "score": $score,
  "max_score": $max_score,
  "headers": {
    "strict_transport_security": $(if [ -n "$strict_transport_security" ]; then echo "\"$strict_transport_security\""; else echo "null"; fi),
    "content_security_policy": $(if [ -n "$content_security_policy" ]; then echo "\"$content_security_policy\""; else echo "null"; fi),
    "x_frame_options": $(if [ -n "$x_frame_options" ]; then echo "\"$x_frame_options\""; else echo "null"; fi),
    "x_content_type_options": $(if [ -n "$x_content_type_options" ]; then echo "\"$x_content_type_options\""; else echo "null"; fi),
    "referrer_policy": $(if [ -n "$referrer_policy" ]; then echo "\"$referrer_policy\""; else echo "null"; fi),
    "permissions_policy": $(if [ -n "$permissions_policy" ]; then echo "\"$permissions_policy\""; else echo "null"; fi),
    "feature_policy": $(if [ -n "$feature_policy" ]; then echo "\"$feature_policy\""; else echo "null"; fi),
    "x_xss_protection": $(if [ -n "$x_xss_protection" ]; then echo "\"$x_xss_protection\""; else echo "null"; fi)
  }
}
EOF
            ;;

        csv)
            # CSV header (if first file)
            if [ ! -s "$output_file" ]; then
                echo "URL,Grade,Score,HSTS,CSP,X-Frame-Options,X-Content-Type-Options,Referrer-Policy,Permissions-Policy" > "$output_file"
            fi

            # CSV data
            echo "\"$url\",\"$grade\",$score,$([ -n "$strict_transport_security" ] && echo "Yes" || echo "No"),$([ -n "$content_security_policy" ] && echo "Yes" || echo "No"),$([ -n "$x_frame_options" ] && echo "Yes" || echo "No"),$([ -n "$x_content_type_options" ] && echo "Yes" || echo "No"),$([ -n "$referrer_policy" ] && echo "Yes" || echo "No"),$([ -n "$permissions_policy" ] && echo "Yes" || echo "No")" >> "$output_file"
            ;;

        text|*)
            cat > "$output_file" <<EOF
================================================================================
Security Headers Test: $url
================================================================================
Status Code: $http_code
Final URL: $redirect_url
Grade: $grade ($score/$max_score)

Headers:
  [$([ -n "$strict_transport_security" ] && echo "✓" || echo "✗")] Strict-Transport-Security
      $strict_transport_security

  [$([ -n "$content_security_policy" ] && echo "✓" || echo "✗")] Content-Security-Policy
      $content_security_policy

  [$([ -n "$x_frame_options" ] && echo "✓" || echo "✗")] X-Frame-Options
      $x_frame_options

  [$([ -n "$x_content_type_options" ] && echo "✓" || echo "✗")] X-Content-Type-Options
      $x_content_type_options

  [$([ -n "$referrer_policy" ] && echo "✓" || echo "✗")] Referrer-Policy
      $referrer_policy

  [$([ -n "$permissions_policy" ] && echo "✓" || echo "✗")] Permissions-Policy
      $permissions_policy

  [$([ -n "$feature_policy" ] && echo "✓" || echo "✗")] Feature-Policy (deprecated)
      $feature_policy

  [$([ -n "$x_xss_protection" ] && echo "✓" || echo "✗")] X-XSS-Protection
      $x_xss_protection

EOF
            ;;
    esac

    if [ "$VERBOSE" = true ]; then
        log_success "$url: $grade ($score/$max_score)"
    fi
}

# Compare headers across URLs
compare_headers() {
    local urls=("$@")

    echo "Header Comparison Report"
    echo "========================"
    echo ""

    # Headers to compare
    local headers=(
        "strict-transport-security"
        "content-security-policy"
        "x-frame-options"
        "x-content-type-options"
        "referrer-policy"
        "permissions-policy"
    )

    for header in "${headers[@]}"; do
        echo "$(echo "$header" | tr '[:lower:]' '[:upper:]' | tr '-' ' '):"

        for url in "${urls[@]}"; do
            # Add https:// if no protocol
            if [[ ! "$url" =~ ^https?:// ]]; then
                url="https://$url"
            fi

            local response
            response=$(curl -s -I -L --max-time "$TIMEOUT" "$url" 2>&1 || echo "")

            local value
            value=$(echo "$response" | grep -i "^$header:" | cut -d: -f2- | xargs || echo "")

            if [ -n "$value" ]; then
                echo "  ✓ $url"
                echo "    $value"
            else
                echo "  ✗ $url"
                echo "    (missing)"
            fi
        done

        echo ""
    done
}

# Parse command line arguments
URLS=()
URL_FILE=""
COMPARE_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -f|--file)
            URL_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -n|--no-redirects)
            FOLLOW_REDIRECTS=false
            shift
            ;;
        -j|--jobs)
            PARALLEL_JOBS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--compare)
            COMPARE_MODE=true
            shift
            ;;
        *)
            URLS+=("$1")
            shift
            ;;
    esac
done

# Check dependencies
check_dependencies

# Load URLs from file if specified
if [ -n "$URL_FILE" ]; then
    if [ ! -f "$URL_FILE" ]; then
        log_error "File not found: $URL_FILE"
        exit 1
    fi

    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        URLS+=("$line")
    done < "$URL_FILE"
fi

# Validate we have URLs
if [ ${#URLS[@]} -eq 0 ]; then
    log_error "No URLs provided"
    usage
fi

# Compare mode
if [ "$COMPARE_MODE" = true ]; then
    compare_headers "${URLS[@]}"
    exit 0
fi

# Test URLs
log_info "Testing ${#URLS[@]} URL(s)"

# Create temp directory for results
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT  # Test cleanup - safe in test context

# Test URLs in parallel
export -f test_url log_info log_success log_error log_warning
export OUTPUT_FORMAT TIMEOUT FOLLOW_REDIRECTS VERBOSE
export BLUE GREEN YELLOW RED NC

# Use GNU parallel if available, otherwise xargs
if command -v parallel &> /dev/null; then
    printf "%s\n" "${URLS[@]}" | parallel -j "$PARALLEL_JOBS" test_url {} "$TEMP_DIR/{#}"
else
    printf "%s\n" "${URLS[@]}" | xargs -P "$PARALLEL_JOBS" -I {} bash -c "test_url '{}' '$TEMP_DIR/\$(echo {} | md5sum | cut -d' ' -f1)'"
fi

# Combine results
case "$OUTPUT_FORMAT" in
    json)
        echo "["
        first=true
        for file in "$TEMP_DIR"/*; do
            if [ "$first" = false ]; then
                echo ","
            fi
            cat "$file"
            first=false
        done
        echo "]"
        ;;

    csv)
        # Combine CSV files (header from first, data from all)
        first_file=$(find "$TEMP_DIR" -type f | head -n1)
        if [ -n "$first_file" ]; then
            head -n1 "$first_file"
            for file in "$TEMP_DIR"/*; do
                tail -n+2 "$file"
            done
        fi
        ;;

    text|*)
        for file in "$TEMP_DIR"/*; do
            cat "$file"
            echo ""
        done
        ;;
esac

log_success "Testing complete"
