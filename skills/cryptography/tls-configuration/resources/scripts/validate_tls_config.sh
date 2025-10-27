#!/usr/bin/env bash
# validate_tls_config.sh
# Validate TLS configuration in nginx, apache, or other server configs

set -euo pipefail

VERSION="1.0.0"
SCRIPT_NAME=$(basename "$0")

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE=""
SERVER_TYPE="auto"
JSON_OUTPUT=false
VERBOSE=false
STRICT_MODE=false

# Validation results
ERRORS=0
WARNINGS=0
PASSED=0

show_help() {
    cat << EOF
$SCRIPT_NAME - TLS Configuration Validator

Usage: $SCRIPT_NAME [OPTIONS]

Options:
    -f, --file FILE         Configuration file to validate
    -t, --type TYPE         Server type: nginx, apache, auto (default: auto)
    -s, --strict            Enable strict mode (all warnings become errors)
    -j, --json              Output results in JSON format
    -v, --verbose           Verbose output
    -h, --help              Show this help message
    --version               Show version

Examples:
    $SCRIPT_NAME -f /etc/nginx/sites-available/default
    $SCRIPT_NAME -f /etc/apache2/sites-available/default-ssl.conf -t apache
    $SCRIPT_NAME -f nginx.conf --strict --json > report.json

Exit codes:
    0 - All checks passed
    1 - Errors found
    2 - Invalid arguments
EOF
}

log_info() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_pass() {
    ((PASSED++))
    if [[ "$JSON_OUTPUT" == "false" ]] && [[ "$VERBOSE" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} $1"
    fi
}

log_warn() {
    if [[ "$STRICT_MODE" == "true" ]]; then
        ((ERRORS++))
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            echo -e "${RED}[FAIL]${NC} $1"
        fi
    else
        ((WARNINGS++))
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            echo -e "${YELLOW}[WARN]${NC} $1"
        fi
    fi
}

log_error() {
    ((ERRORS++))
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${RED}[FAIL]${NC} $1"
    fi
}

detect_server_type() {
    local file="$1"

    if grep -q "server_name\|listen.*ssl" "$file" 2>/dev/null; then
        echo "nginx"
    elif grep -q "VirtualHost\|SSLEngine" "$file" 2>/dev/null; then
        echo "apache"
    else
        echo "unknown"
    fi
}

validate_nginx_config() {
    local file="$1"
    local content
    content=$(cat "$file")

    log_info "Validating Nginx TLS configuration..."

    # Check TLS protocols
    if echo "$content" | grep -q "ssl_protocols.*TLSv1\.3"; then
        log_pass "TLS 1.3 enabled"
    else
        log_warn "TLS 1.3 not enabled (recommended)"
    fi

    if echo "$content" | grep -q "ssl_protocols.*TLSv1\.2"; then
        log_pass "TLS 1.2 enabled"
    else
        log_error "TLS 1.2 not enabled (required)"
    fi

    if echo "$content" | grep -qE "ssl_protocols.*(SSLv2|SSLv3|TLSv1\.0|TLSv1\.1)"; then
        log_error "Deprecated protocols enabled (SSLv2/SSLv3/TLS1.0/TLS1.1)"
    else
        log_pass "No deprecated protocols enabled"
    fi

    # Check cipher suites
    if echo "$content" | grep -q "ssl_ciphers"; then
        log_pass "Cipher suites configured"

        if echo "$content" | grep -q "ssl_ciphers.*ECDHE"; then
            log_pass "ECDHE ciphers enabled (forward secrecy)"
        else
            log_warn "ECDHE ciphers not found (forward secrecy recommended)"
        fi

        if echo "$content" | grep -qE "ssl_ciphers.*(GCM|CHACHA20)"; then
            log_pass "AEAD ciphers enabled (GCM or ChaCha20)"
        else
            log_warn "AEAD ciphers not found (GCM or ChaCha20 recommended)"
        fi

        if echo "$content" | grep -qE "ssl_ciphers.*(DES|RC4|MD5|EXPORT)"; then
            log_error "Weak ciphers detected (DES/RC4/MD5/EXPORT)"
        else
            log_pass "No weak ciphers detected"
        fi
    else
        log_warn "No explicit cipher suite configuration (using defaults)"
    fi

    # Check cipher preference
    if echo "$content" | grep -q "ssl_prefer_server_ciphers.*on"; then
        log_pass "Server cipher preference enabled"
    else
        log_warn "Server cipher preference not enabled"
    fi

    # Check OCSP stapling
    if echo "$content" | grep -q "ssl_stapling.*on"; then
        log_pass "OCSP stapling enabled"

        if echo "$content" | grep -q "ssl_stapling_verify.*on"; then
            log_pass "OCSP stapling verification enabled"
        else
            log_warn "OCSP stapling verification not enabled"
        fi
    else
        log_warn "OCSP stapling not enabled (recommended)"
    fi

    # Check session settings
    if echo "$content" | grep -q "ssl_session_cache"; then
        log_pass "SSL session cache configured"
    else
        log_warn "SSL session cache not configured (performance impact)"
    fi

    if echo "$content" | grep -q "ssl_session_tickets.*off"; then
        log_pass "SSL session tickets disabled (better privacy)"
    elif echo "$content" | grep -q "ssl_session_tickets.*on"; then
        log_warn "SSL session tickets enabled (consider disabling for privacy)"
    fi

    # Check HSTS header
    if echo "$content" | grep -q "Strict-Transport-Security"; then
        log_pass "HSTS header configured"

        if echo "$content" | grep -q "max-age=[0-9]*"; then
            local max_age
            max_age=$(echo "$content" | grep -o "max-age=[0-9]*" | head -1 | cut -d= -f2)
            if [[ $max_age -ge 31536000 ]]; then
                log_pass "HSTS max-age >= 1 year ($max_age seconds)"
            else
                log_warn "HSTS max-age < 1 year ($max_age seconds)"
            fi
        fi

        if echo "$content" | grep -q "includeSubDomains"; then
            log_pass "HSTS includeSubDomains enabled"
        else
            log_warn "HSTS includeSubDomains not enabled"
        fi
    else
        log_warn "HSTS header not configured (recommended)"
    fi

    # Check certificate configuration
    if echo "$content" | grep -q "ssl_certificate "; then
        log_pass "SSL certificate configured"
    else
        log_error "SSL certificate not configured"
    fi

    if echo "$content" | grep -q "ssl_certificate_key"; then
        log_pass "SSL certificate key configured"
    else
        log_error "SSL certificate key not configured"
    fi

    # Check HTTP/2
    if echo "$content" | grep -q "listen.*http2"; then
        log_pass "HTTP/2 enabled"
    else
        log_warn "HTTP/2 not enabled (recommended for performance)"
    fi
}

validate_apache_config() {
    local file="$1"
    local content
    content=$(cat "$file")

    log_info "Validating Apache TLS configuration..."

    # Check SSLEngine
    if echo "$content" | grep -q "SSLEngine.*on"; then
        log_pass "SSLEngine enabled"
    else
        log_error "SSLEngine not enabled"
    fi

    # Check TLS protocols
    if echo "$content" | grep -q "SSLProtocol.*TLSv1\.3"; then
        log_pass "TLS 1.3 enabled"
    else
        log_warn "TLS 1.3 not enabled (recommended)"
    fi

    if echo "$content" | grep -q "SSLProtocol.*TLSv1\.2"; then
        log_pass "TLS 1.2 enabled"
    else
        log_error "TLS 1.2 not enabled (required)"
    fi

    if echo "$content" | grep -qE "SSLProtocol.*(SSLv2|SSLv3|TLSv1\.0|TLSv1\.1)"; then
        log_error "Deprecated protocols enabled (SSLv2/SSLv3/TLS1.0/TLS1.1)"
    else
        log_pass "No deprecated protocols enabled"
    fi

    # Check cipher suites
    if echo "$content" | grep -q "SSLCipherSuite"; then
        log_pass "Cipher suites configured"

        if echo "$content" | grep -q "SSLCipherSuite.*ECDHE"; then
            log_pass "ECDHE ciphers enabled (forward secrecy)"
        else
            log_warn "ECDHE ciphers not found (forward secrecy recommended)"
        fi

        if echo "$content" | grep -qE "SSLCipherSuite.*(GCM|CHACHA20)"; then
            log_pass "AEAD ciphers enabled (GCM or ChaCha20)"
        else
            log_warn "AEAD ciphers not found (GCM or ChaCha20 recommended)"
        fi
    else
        log_warn "No explicit cipher suite configuration (using defaults)"
    fi

    # Check cipher preference
    if echo "$content" | grep -q "SSLHonorCipherOrder.*on"; then
        log_pass "Server cipher preference enabled"
    else
        log_warn "Server cipher preference not enabled"
    fi

    # Check OCSP stapling
    if echo "$content" | grep -q "SSLUseStapling.*on"; then
        log_pass "OCSP stapling enabled"
    else
        log_warn "OCSP stapling not enabled (recommended)"
    fi

    # Check HSTS
    if echo "$content" | grep -q "Strict-Transport-Security"; then
        log_pass "HSTS header configured"
    else
        log_warn "HSTS header not configured (recommended)"
    fi

    # Check certificates
    if echo "$content" | grep -q "SSLCertificateFile"; then
        log_pass "SSL certificate configured"
    else
        log_error "SSL certificate not configured"
    fi

    if echo "$content" | grep -q "SSLCertificateKeyFile"; then
        log_pass "SSL certificate key configured"
    else
        log_error "SSL certificate key not configured"
    fi
}

output_json_results() {
    cat << EOF
{
  "version": "$VERSION",
  "file": "$CONFIG_FILE",
  "server_type": "$SERVER_TYPE",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "results": {
    "passed": $PASSED,
    "warnings": $WARNINGS,
    "errors": $ERRORS,
    "total": $((PASSED + WARNINGS + ERRORS))
  },
  "status": "$(if [[ $ERRORS -eq 0 ]]; then echo "pass"; else echo "fail"; fi)",
  "grade": "$(if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then echo "A+"; elif [[ $ERRORS -eq 0 ]]; then echo "B"; else echo "C"; fi)"
}
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -t|--type)
            SERVER_TYPE="$2"
            shift 2
            ;;
        -s|--strict)
            STRICT_MODE=true
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
            show_help
            exit 0
            ;;
        --version)
            echo "$SCRIPT_NAME version $VERSION"
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            show_help
            exit 2
            ;;
    esac
done

# Validate arguments
if [[ -z "$CONFIG_FILE" ]]; then
    echo "Error: Configuration file is required (-f/--file)" >&2
    show_help
    exit 2
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: File not found: $CONFIG_FILE" >&2
    exit 2
fi

# Auto-detect server type if needed
if [[ "$SERVER_TYPE" == "auto" ]]; then
    SERVER_TYPE=$(detect_server_type "$CONFIG_FILE")
    if [[ "$SERVER_TYPE" == "unknown" ]]; then
        echo "Error: Could not detect server type. Please specify with -t/--type" >&2
        exit 2
    fi
fi

# Validate based on server type
case "$SERVER_TYPE" in
    nginx)
        validate_nginx_config "$CONFIG_FILE"
        ;;
    apache)
        validate_apache_config "$CONFIG_FILE"
        ;;
    *)
        echo "Error: Unsupported server type: $SERVER_TYPE" >&2
        echo "Supported types: nginx, apache" >&2
        exit 2
        ;;
esac

# Output results
if [[ "$JSON_OUTPUT" == "true" ]]; then
    output_json_results
else
    echo ""
    echo "================================"
    echo "Validation Summary"
    echo "================================"
    echo "File: $CONFIG_FILE"
    echo "Type: $SERVER_TYPE"
    echo "Passed: $PASSED"
    echo "Warnings: $WARNINGS"
    echo "Errors: $ERRORS"
    echo "================================"

    if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
        echo -e "${GREEN}Grade: A+ (Perfect!)${NC}"
    elif [[ $ERRORS -eq 0 ]]; then
        echo -e "${YELLOW}Grade: B (Some warnings)${NC}"
    else
        echo -e "${RED}Grade: C (Errors found)${NC}"
    fi
fi

# Exit with appropriate code
if [[ $ERRORS -gt 0 ]]; then
    exit 1
else
    exit 0
fi
