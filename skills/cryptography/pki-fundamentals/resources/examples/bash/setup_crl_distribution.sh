#!/usr/bin/env bash
#
# CRL Distribution Setup - Production-ready CRL distribution infrastructure
#
# This script sets up a complete CRL distribution system including:
# - Nginx configuration for CRL hosting
# - Automated CRL updates via cron
# - CRL generation and publication
# - Health monitoring
#
# Usage:
#   ./setup_crl_distribution.sh --help
#   ./setup_crl_distribution.sh --ca-dir /opt/ca --crl-dir /var/www/crl --domain crl.example.com
#   ./setup_crl_distribution.sh --update-only --ca-dir /opt/ca

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_DIR=""
CRL_DIR="/var/www/crl"
DOMAIN="crl.example.com"
UPDATE_ONLY=false
NGINX_CONFIG="/etc/nginx/sites-available/crl"
LOG_FILE="/var/log/crl-distribution.log"

function log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

function error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2 | tee -a "$LOG_FILE"
    exit 1
}

function show_help() {
    cat << EOF
CRL Distribution Setup

Usage: $0 [OPTIONS]

Options:
    --ca-dir DIR        CA directory containing certificates and keys (required)
    --crl-dir DIR       CRL distribution directory (default: /var/www/crl)
    --domain DOMAIN     CRL distribution domain (default: crl.example.com)
    --update-only       Only update CRLs without full setup
    --help              Show this help message

Examples:
    # Full setup
    $0 --ca-dir /opt/ca --crl-dir /var/www/crl --domain crl.example.com

    # Update CRLs only
    $0 --update-only --ca-dir /opt/ca

Environment Variables:
    CRL_UPDATE_INTERVAL     Cron schedule for updates (default: "0 */6 * * *")
    NGINX_PORT             HTTP port (default: 80)
    NGINX_HTTPS_PORT       HTTPS port (default: 443)

EOF
}

function parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ca-dir)
                CA_DIR="$2"
                shift 2
                ;;
            --crl-dir)
                CRL_DIR="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --update-only)
                UPDATE_ONLY=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    if [[ -z "$CA_DIR" ]]; then
        error "CA directory is required (--ca-dir)"
    fi

    if [[ ! -d "$CA_DIR" ]]; then
        error "CA directory does not exist: $CA_DIR"
    fi
}

function check_dependencies() {
    log "Checking dependencies..."

    local deps=("openssl" "nginx")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            error "Required dependency not found: $dep"
        fi
    done

    if [[ "$UPDATE_ONLY" == "false" ]] && [[ $EUID -ne 0 ]]; then
        error "Full setup requires root privileges (use sudo)"
    fi

    log "All dependencies satisfied"
}

function setup_directories() {
    log "Setting up directories..."

    mkdir -p "$CRL_DIR"
    chmod 755 "$CRL_DIR"

    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"

    log "Directories created: $CRL_DIR"
}

function generate_crls() {
    log "Generating CRLs..."

    local ca_count=0
    for ca_cert in "$CA_DIR"/*.crt "$CA_DIR"/*.pem; do
        if [[ ! -f "$ca_cert" ]]; then
            continue
        fi

        local ca_name=$(basename "$ca_cert" | sed 's/\.[^.]*$//')
        local ca_key="${CA_DIR}/${ca_name}.key"
        local crl_file="${CRL_DIR}/${ca_name}.crl"

        if [[ ! -f "$ca_key" ]]; then
            log "Warning: CA key not found for $ca_name, skipping"
            continue
        fi

        log "Generating CRL for CA: $ca_name"

        local temp_config=$(mktemp)
        cat > "$temp_config" << 'EOCONF'
[ ca ]
default_ca = CA_default

[ CA_default ]
database = ./index.txt
crlnumber = ./crlnumber
default_crl_days = 30
default_md = sha256

[ crl_ext ]
authorityKeyIdentifier=keyid:always
EOCONF

        local temp_dir=$(mktemp -d)
        pushd "$temp_dir" > /dev/null

        touch index.txt
        echo 1000 > crlnumber

        if openssl ca -config "$temp_config" \
            -gencrl \
            -keyfile "$ca_key" \
            -cert "$ca_cert" \
            -out "$crl_file" \
            -crldays 30 2>> "$LOG_FILE"; then

            log "CRL generated: $crl_file"
            chmod 644 "$crl_file"

            local crl_info=$(openssl crl -in "$crl_file" -noout -lastupdate -nextupdate)
            log "CRL info: $crl_info"

            ca_count=$((ca_count + 1))
        else
            log "Warning: Failed to generate CRL for $ca_name"
        fi

        popd > /dev/null
        rm -rf "$temp_dir" "$temp_config"
    done

    if [[ $ca_count -eq 0 ]]; then
        error "No CRLs generated. Check CA certificates and keys."
    fi

    log "Generated $ca_count CRL(s)"
}

function setup_nginx() {
    log "Configuring Nginx..."

    cat > "$NGINX_CONFIG" << EOF
server {
    listen ${NGINX_PORT:-80};
    listen [::]:${NGINX_PORT:-80};
    server_name $DOMAIN;

    access_log /var/log/nginx/crl-access.log;
    error_log /var/log/nginx/crl-error.log;

    root $CRL_DIR;

    # CRL distribution location
    location ~ \.crl$ {
        add_header Content-Type application/pkix-crl;
        add_header Cache-Control "public, max-age=21600";  # 6 hours
        add_header Access-Control-Allow-Origin "*";
        try_files \$uri =404;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # Directory listing for debugging (disable in production)
    location / {
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
EOF

    if [[ -f "/etc/ssl/certs/${DOMAIN}.crt" ]] && [[ -f "/etc/ssl/private/${DOMAIN}.key" ]]; then
        cat >> "$NGINX_CONFIG" << EOF

# HTTPS configuration
server {
    listen ${NGINX_HTTPS_PORT:-443} ssl http2;
    listen [::]:${NGINX_HTTPS_PORT:-443} ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/ssl/certs/${DOMAIN}.crt;
    ssl_certificate_key /etc/ssl/private/${DOMAIN}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/crl-access-ssl.log;
    error_log /var/log/nginx/crl-error-ssl.log;

    root $CRL_DIR;

    location ~ \.crl$ {
        add_header Content-Type application/pkix-crl;
        add_header Cache-Control "public, max-age=21600";
        add_header Access-Control-Allow-Origin "*";
        try_files \$uri =404;
    }

    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
EOF
    fi

    ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/crl

    if nginx -t 2>> "$LOG_FILE"; then
        systemctl reload nginx
        log "Nginx configured and reloaded"
    else
        error "Nginx configuration test failed"
    fi
}

function setup_cron() {
    log "Setting up automated CRL updates..."

    local cron_script="/usr/local/bin/update-crls.sh"
    cat > "$cron_script" << EOF
#!/bin/bash
set -euo pipefail

LOG_FILE="$LOG_FILE"

function log() {
    echo "[\$(date +'%Y-%m-%d %H:%M:%S')] \$*" >> "\$LOG_FILE"
}

log "Starting scheduled CRL update"

if $0 --update-only --ca-dir "$CA_DIR" >> "\$LOG_FILE" 2>&1; then
    log "CRL update completed successfully"
else
    log "ERROR: CRL update failed"
    exit 1
fi
EOF

    chmod +x "$cron_script"

    local cron_schedule="${CRL_UPDATE_INTERVAL:-0 */6 * * *}"
    local cron_entry="$cron_schedule $cron_script"

    (crontab -l 2>/dev/null | grep -v "update-crls.sh" || true; echo "$cron_entry") | crontab -

    log "Cron job installed: $cron_schedule"
}

function verify_setup() {
    log "Verifying setup..."

    local crl_count=$(find "$CRL_DIR" -name "*.crl" | wc -l)
    if [[ $crl_count -eq 0 ]]; then
        error "Verification failed: No CRLs found in $CRL_DIR"
    fi

    log "Found $crl_count CRL file(s)"

    if [[ "$UPDATE_ONLY" == "false" ]]; then
        if systemctl is-active --quiet nginx; then
            log "Nginx is running"
        else
            error "Nginx is not running"
        fi

        if curl -f "http://localhost/health" > /dev/null 2>&1; then
            log "Health check endpoint responding"
        else
            log "Warning: Health check endpoint not responding"
        fi
    fi

    for crl_file in "$CRL_DIR"/*.crl; do
        if [[ -f "$crl_file" ]]; then
            if openssl crl -in "$crl_file" -noout -text > /dev/null 2>&1; then
                log "CRL valid: $(basename "$crl_file")"
            else
                log "Warning: CRL validation failed: $(basename "$crl_file")"
            fi
        fi
    done

    log "Verification complete"
}

function main() {
    parse_args "$@"

    log "=== CRL Distribution Setup Started ==="
    log "CA Directory: $CA_DIR"
    log "CRL Directory: $CRL_DIR"
    log "Domain: $DOMAIN"
    log "Update Only: $UPDATE_ONLY"

    check_dependencies

    if [[ "$UPDATE_ONLY" == "false" ]]; then
        setup_directories
    fi

    generate_crls

    if [[ "$UPDATE_ONLY" == "false" ]]; then
        setup_nginx
        setup_cron
    fi

    verify_setup

    log "=== CRL Distribution Setup Complete ==="
    log ""
    log "Next steps:"
    log "  1. Verify CRLs: ls -lh $CRL_DIR"
    log "  2. Test HTTP access: curl http://$DOMAIN/your-ca.crl"
    log "  3. Monitor logs: tail -f $LOG_FILE"
    log "  4. Check cron: crontab -l | grep update-crls"
}

main "$@"
