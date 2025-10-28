#!/bin/bash
# curl HTTP/3 Examples
# Demonstrates various curl commands for testing HTTP/3
#
# Requirements:
#   - curl 7.66+ with HTTP/3 support
#
# Build curl with HTTP/3 (using quiche):
#   git clone --recursive https://github.com/curl/curl.git
#   cd curl
#   ./buildconf
#   ./configure --with-openssl --with-quiche=/path/to/quiche
#   make && make install
#
# Or install via package manager:
#   # Debian/Ubuntu (if available)
#   apt-get install curl
#
#   # macOS with Homebrew
#   brew install curl --with-quiche

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[*]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if curl supports HTTP/3
check_http3_support() {
    log "Checking curl HTTP/3 support..."

    if curl --version | grep -q "HTTP3"; then
        info "✓ curl supports HTTP/3"
        curl --version | grep -i http3
    else
        warn "✗ curl does not support HTTP/3"
        echo "Build curl with quiche or install a version with HTTP/3 support"
        exit 1
    fi
}

# Example 1: Basic HTTP/3 request
example_basic() {
    log "Example 1: Basic HTTP/3 request"

    curl --http3 https://cloudflare-quic.com

    echo
}

# Example 2: HTTP/3 with verbose output
example_verbose() {
    log "Example 2: HTTP/3 with verbose output"

    curl --http3 -v https://cloudflare-quic.com 2>&1 | grep -E "(QUIC|HTTP/3|Alt-Svc|TLS)"

    echo
}

# Example 3: Force HTTP/3 only (fail if unavailable)
example_http3_only() {
    log "Example 3: Force HTTP/3 only (fail if unavailable)"

    curl --http3-only https://cloudflare-quic.com || {
        warn "Server does not support HTTP/3"
    }

    echo
}

# Example 4: Check headers (Alt-Svc)
example_headers() {
    log "Example 4: Check Alt-Svc header"

    curl -I https://cloudflare-quic.com | grep -i alt-svc

    echo
}

# Example 5: Download file with HTTP/3
example_download() {
    log "Example 5: Download file with HTTP/3"

    curl --http3 -o /tmp/test.html https://cloudflare-quic.com

    info "Downloaded to /tmp/test.html ($(wc -c < /tmp/test.html) bytes)"

    rm -f /tmp/test.html

    echo
}

# Example 6: POST request with HTTP/3
example_post() {
    log "Example 6: POST request with HTTP/3"

    curl --http3 -X POST \
        -H "Content-Type: application/json" \
        -d '{"test": "data"}' \
        https://httpbin.org/post

    echo
}

# Example 7: Custom headers with HTTP/3
example_custom_headers() {
    log "Example 7: Custom headers with HTTP/3"

    curl --http3 \
        -H "User-Agent: curl-http3-test/1.0" \
        -H "X-Custom-Header: test-value" \
        https://httpbin.org/headers

    echo
}

# Example 8: Measure performance
example_performance() {
    log "Example 8: Measure performance (time to first byte)"

    # Create format file
    cat > /tmp/curl-format.txt <<'EOF'
    time_namelookup:  %{time_namelookup}s\n
       time_connect:  %{time_connect}s\n
    time_appconnect:  %{time_appconnect}s\n
   time_pretransfer:  %{time_pretransfer}s\n
      time_redirect:  %{time_redirect}s\n
 time_starttransfer:  %{time_starttransfer}s\n
                    ----------\n
         time_total:  %{time_total}s\n
EOF

    info "HTTP/3 performance:"
    curl --http3 -w "@/tmp/curl-format.txt" -o /dev/null -s https://cloudflare-quic.com

    rm -f /tmp/curl-format.txt

    echo
}

# Example 9: Compare HTTP/3 vs HTTP/2
example_compare() {
    log "Example 9: Compare HTTP/3 vs HTTP/2"

    echo "HTTP/3:"
    curl --http3 -w "  Time: %{time_total}s\n" -o /dev/null -s https://cloudflare-quic.com

    echo "HTTP/2:"
    curl --http2 -w "  Time: %{time_total}s\n" -o /dev/null -s https://cloudflare-quic.com

    echo
}

# Example 10: Test multiple URLs
example_multiple() {
    log "Example 10: Test multiple URLs with HTTP/3"

    urls=(
        "https://cloudflare-quic.com"
        "https://www.google.com"
        "https://www.facebook.com"
    )

    for url in "${urls[@]}"; do
        info "Testing $url..."
        if curl --http3-only -I "$url" &>/dev/null; then
            echo "  ✓ HTTP/3 supported"
        else
            echo "  ✗ HTTP/3 not supported"
        fi
    done

    echo
}

# Example 11: Save response headers
example_save_headers() {
    log "Example 11: Save response headers"

    curl --http3 -D /tmp/headers.txt -o /dev/null -s https://cloudflare-quic.com

    info "Headers saved to /tmp/headers.txt:"
    cat /tmp/headers.txt

    rm -f /tmp/headers.txt

    echo
}

# Example 12: HTTP/3 with authentication
example_auth() {
    log "Example 12: HTTP/3 with authentication"

    curl --http3 -u "user:pass" https://httpbin.org/basic-auth/user/pass

    echo
}

# Example 13: Follow redirects with HTTP/3
example_redirect() {
    log "Example 13: Follow redirects with HTTP/3"

    curl --http3 -L https://httpbin.org/redirect/3

    echo
}

# Example 14: HTTP/3 with cookies
example_cookies() {
    log "Example 14: HTTP/3 with cookies"

    # Set cookie
    curl --http3 -c /tmp/cookies.txt https://httpbin.org/cookies/set/test/value

    # Send cookie
    curl --http3 -b /tmp/cookies.txt https://httpbin.org/cookies

    rm -f /tmp/cookies.txt

    echo
}

# Example 15: Test QUIC version
example_quic_version() {
    log "Example 15: Check QUIC version"

    curl --http3 -v https://cloudflare-quic.com 2>&1 | grep -i "quic\|version"

    echo
}

# Main function
main() {
    echo "======================================"
    echo "curl HTTP/3 Examples"
    echo "======================================"
    echo

    check_http3_support

    echo
    echo "Running examples..."
    echo

    # Run all examples (comment out to run specific ones)
    example_basic
    example_verbose
    example_http3_only
    example_headers
    example_download
    # example_post
    # example_custom_headers
    example_performance
    example_compare
    example_multiple
    # example_save_headers
    # example_auth
    # example_redirect
    # example_cookies
    # example_quic_version

    echo "======================================"
    echo "Examples complete!"
    echo "======================================"
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
