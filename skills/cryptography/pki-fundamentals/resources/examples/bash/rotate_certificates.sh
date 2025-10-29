#!/usr/bin/env bash
#
# Automated Certificate Rotation with Zero Downtime
#
# This script automates certificate rotation for services with zero downtime:
# - Validates current certificates
# - Generates new certificates before expiration
# - Performs rolling updates
# - Maintains service availability
# - Provides rollback capability
#
# Usage:
#   ./rotate_certificates.sh --help
#   ./rotate_certificates.sh --service nginx --cert-path /etc/ssl/certs --ca-url https://ca.example.com
#   ./rotate_certificates.sh --service haproxy --cert-path /etc/haproxy/certs --notify-email admin@example.com
#   ./rotate_certificates.sh --dry-run --service nginx

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE=""
CERT_PATH=""
CA_URL=""
NOTIFY_EMAIL=""
DRY_RUN=false
ROLLBACK=false
EXPIRY_THRESHOLD=30
LOG_FILE="/var/log/cert-rotation.log"
STATE_FILE="/var/lib/cert-rotation/state.json"

function log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

function error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2 | tee -a "$LOG_FILE"
    exit 1
}

function show_help() {
    cat << EOF
Automated Certificate Rotation

Usage: $0 [OPTIONS]

Options:
    --service SERVICE       Service to rotate certificates for (nginx, haproxy, apache, etc.)
    --cert-path PATH        Path to certificate directory
    --ca-url URL            CA server URL for certificate renewal
    --notify-email EMAIL    Email address for notifications
    --expiry-threshold DAYS Rotate certificates expiring within N days (default: 30)
    --dry-run               Show what would be done without making changes
    --rollback              Rollback to previous certificates
    --help                  Show this help message

Supported Services:
    nginx       - Nginx web server
    haproxy     - HAProxy load balancer
    apache      - Apache HTTP server
    docker      - Docker daemon
    kubernetes  - Kubernetes components

Examples:
    # Rotate nginx certificates
    $0 --service nginx --cert-path /etc/ssl/certs --ca-url https://ca.example.com

    # Dry run to preview changes
    $0 --dry-run --service nginx --cert-path /etc/ssl/certs

    # Rollback to previous certificates
    $0 --rollback --service nginx

Environment Variables:
    CERT_ROTATION_CA_URL        CA server URL
    CERT_ROTATION_NOTIFY_EMAIL  Notification email
    CERT_ROTATION_THRESHOLD     Expiry threshold in days

EOF
}

function parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --service)
                SERVICE="$2"
                shift 2
                ;;
            --cert-path)
                CERT_PATH="$2"
                shift 2
                ;;
            --ca-url)
                CA_URL="$2"
                shift 2
                ;;
            --notify-email)
                NOTIFY_EMAIL="$2"
                shift 2
                ;;
            --expiry-threshold)
                EXPIRY_THRESHOLD="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
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

    if [[ -z "$SERVICE" ]]; then
        error "Service is required (--service)"
    fi

    CA_URL="${CA_URL:-${CERT_ROTATION_CA_URL:-}}"
    NOTIFY_EMAIL="${NOTIFY_EMAIL:-${CERT_ROTATION_NOTIFY_EMAIL:-}}"
    EXPIRY_THRESHOLD="${EXPIRY_THRESHOLD:-${CERT_ROTATION_THRESHOLD:-30}}"
}

function check_dependencies() {
    log "Checking dependencies..."

    local deps=("openssl" "jq" "curl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            error "Required dependency not found: $dep"
        fi
    done

    if ! systemctl list-units --type=service | grep -q "$SERVICE"; then
        log "Warning: Service $SERVICE not found in systemd"
    fi

    log "Dependencies satisfied"
}

function save_state() {
    local state_dir=$(dirname "$STATE_FILE")
    mkdir -p "$state_dir"

    local state=$(cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "service": "$SERVICE",
  "cert_path": "$CERT_PATH",
  "backup_path": "$1",
  "rotation_count": ${2:-1}
}
EOF
)

    echo "$state" > "$STATE_FILE"
    log "State saved: $STATE_FILE"
}

function load_state() {
    if [[ ! -f "$STATE_FILE" ]]; then
        log "No previous state found"
        return 1
    fi

    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE"
    fi
}

function check_certificate_expiry() {
    local cert_file="$1"

    if [[ ! -f "$cert_file" ]]; then
        error "Certificate not found: $cert_file"
    fi

    local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry_date" +%s)
    local now_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - now_epoch) / 86400 ))

    echo "$days_until_expiry"
}

function backup_certificates() {
    local backup_dir="/var/backups/certificates/$(date +%Y%m%d_%H%M%S)"

    log "Backing up certificates to: $backup_dir"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would create backup at: $backup_dir"
        return
    fi

    mkdir -p "$backup_dir"

    if [[ -d "$CERT_PATH" ]]; then
        cp -r "$CERT_PATH"/* "$backup_dir/" 2>> "$LOG_FILE" || true
    fi

    log "Backup complete: $backup_dir"
    echo "$backup_dir"
}

function generate_new_certificate() {
    local cert_name="$1"
    local domain="$2"

    log "Generating new certificate for: $domain"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would generate certificate for: $domain"
        return
    fi

    local key_file="${CERT_PATH}/${cert_name}.key"
    local csr_file="${CERT_PATH}/${cert_name}.csr"
    local cert_file="${CERT_PATH}/${cert_name}.crt"
    local new_key_file="${CERT_PATH}/${cert_name}.key.new"
    local new_cert_file="${CERT_PATH}/${cert_name}.crt.new"

    openssl genrsa -out "$new_key_file" 4096 2>> "$LOG_FILE"

    openssl req -new -key "$new_key_file" -out "$csr_file" \
        -subj "/C=US/ST=California/L=San Francisco/O=Example Org/CN=${domain}" \
        2>> "$LOG_FILE"

    if [[ -n "$CA_URL" ]]; then
        log "Requesting certificate from CA: $CA_URL"
        curl -f -X POST "$CA_URL/api/sign" \
            --data-binary "@${csr_file}" \
            -H "Content-Type: application/pkcs10" \
            -o "$new_cert_file" 2>> "$LOG_FILE" || {
                error "Failed to obtain certificate from CA"
            }
    else
        log "Self-signing certificate (no CA URL provided)"
        openssl x509 -req -in "$csr_file" \
            -signkey "$new_key_file" \
            -out "$new_cert_file" \
            -days 365 \
            -sha256 2>> "$LOG_FILE"
    fi

    openssl x509 -in "$new_cert_file" -noout -text >> "$LOG_FILE"

    log "New certificate generated: $new_cert_file"
}

function validate_certificate() {
    local cert_file="$1"

    log "Validating certificate: $cert_file"

    if ! openssl x509 -in "$cert_file" -noout -text > /dev/null 2>&1; then
        error "Certificate validation failed: $cert_file"
    fi

    local expiry=$(check_certificate_expiry "$cert_file")
    if [[ $expiry -lt 0 ]]; then
        error "Certificate is expired: $cert_file"
    fi

    log "Certificate is valid"
}

function rotate_service_certificates() {
    local service="$1"

    log "Rotating certificates for service: $service"

    case "$service" in
        nginx)
            rotate_nginx_certificates
            ;;
        haproxy)
            rotate_haproxy_certificates
            ;;
        apache)
            rotate_apache_certificates
            ;;
        docker)
            rotate_docker_certificates
            ;;
        kubernetes)
            rotate_kubernetes_certificates
            ;;
        *)
            error "Unsupported service: $service"
            ;;
    esac
}

function rotate_nginx_certificates() {
    log "Rotating Nginx certificates"

    local cert_files=$(find "$CERT_PATH" -name "*.crt" -type f)

    for cert_file in $cert_files; do
        local days_until_expiry=$(check_certificate_expiry "$cert_file")

        if [[ $days_until_expiry -le $EXPIRY_THRESHOLD ]]; then
            log "Certificate expiring in $days_until_expiry days: $cert_file"

            local cert_name=$(basename "$cert_file" .crt)
            local domain=$(openssl x509 -in "$cert_file" -noout -subject | sed 's/.*CN = //')

            generate_new_certificate "$cert_name" "$domain"

            if [[ "$DRY_RUN" == "false" ]]; then
                mv "${CERT_PATH}/${cert_name}.crt.new" "$cert_file"
                mv "${CERT_PATH}/${cert_name}.key.new" "${CERT_PATH}/${cert_name}.key"

                nginx -t 2>> "$LOG_FILE" || {
                    error "Nginx configuration test failed after certificate rotation"
                }

                systemctl reload nginx
                log "Nginx reloaded with new certificate"
            fi
        else
            log "Certificate valid for $days_until_expiry days: $cert_file"
        fi
    done
}

function rotate_haproxy_certificates() {
    log "Rotating HAProxy certificates"

    local cert_files=$(find "$CERT_PATH" -name "*.pem" -type f)

    for cert_file in $cert_files; do
        local days_until_expiry=$(check_certificate_expiry "$cert_file")

        if [[ $days_until_expiry -le $EXPIRY_THRESHOLD ]]; then
            log "Certificate expiring in $days_until_expiry days: $cert_file"

            local cert_name=$(basename "$cert_file" .pem)
            local domain=$(openssl x509 -in "$cert_file" -noout -subject | sed 's/.*CN = //')

            generate_new_certificate "$cert_name" "$domain"

            if [[ "$DRY_RUN" == "false" ]]; then
                cat "${CERT_PATH}/${cert_name}.crt.new" \
                    "${CERT_PATH}/${cert_name}.key.new" \
                    > "${cert_file}.new"

                mv "${cert_file}.new" "$cert_file"

                systemctl reload haproxy
                log "HAProxy reloaded with new certificate"
            fi
        fi
    done
}

function rotate_apache_certificates() {
    log "Rotating Apache certificates"

    rotate_nginx_certificates

    if [[ "$DRY_RUN" == "false" ]]; then
        apachectl configtest || {
            error "Apache configuration test failed"
        }
        systemctl reload apache2
        log "Apache reloaded"
    fi
}

function rotate_docker_certificates() {
    log "Rotating Docker daemon certificates"

    local docker_cert_path="/etc/docker/certs"
    CERT_PATH="$docker_cert_path"

    rotate_nginx_certificates

    if [[ "$DRY_RUN" == "false" ]]; then
        systemctl reload docker
        log "Docker daemon reloaded"
    fi
}

function rotate_kubernetes_certificates() {
    log "Rotating Kubernetes certificates"

    if command -v kubeadm &> /dev/null; then
        if [[ "$DRY_RUN" == "false" ]]; then
            kubeadm certs renew all 2>> "$LOG_FILE"
            log "Kubernetes certificates renewed"
        else
            log "[DRY RUN] Would run: kubeadm certs renew all"
        fi
    else
        log "Warning: kubeadm not found, manual rotation required"
    fi
}

function rollback_certificates() {
    log "Rolling back certificates"

    local state=$(load_state)
    if [[ $? -ne 0 ]]; then
        error "No state found for rollback"
    fi

    local backup_path=$(echo "$state" | jq -r '.backup_path')

    if [[ ! -d "$backup_path" ]]; then
        error "Backup not found: $backup_path"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore from: $backup_path"
        return
    fi

    cp -r "$backup_path"/* "$CERT_PATH/"
    log "Certificates restored from: $backup_path"

    systemctl reload "$SERVICE"
    log "Service reloaded: $SERVICE"
}

function send_notification() {
    local subject="$1"
    local body="$2"

    if [[ -z "$NOTIFY_EMAIL" ]]; then
        log "No notification email configured"
        return
    fi

    log "Sending notification to: $NOTIFY_EMAIL"

    echo "$body" | mail -s "$subject" "$NOTIFY_EMAIL" 2>> "$LOG_FILE" || {
        log "Warning: Failed to send email notification"
    }
}

function main() {
    parse_args "$@"

    log "=== Certificate Rotation Started ==="
    log "Service: $SERVICE"
    log "Certificate Path: $CERT_PATH"
    log "Expiry Threshold: $EXPIRY_THRESHOLD days"
    log "Dry Run: $DRY_RUN"
    log "Rollback: $ROLLBACK"

    check_dependencies

    if [[ "$ROLLBACK" == "true" ]]; then
        rollback_certificates
        log "=== Rollback Complete ==="
        return 0
    fi

    local backup_path=$(backup_certificates)

    local rotation_count=0
    rotate_service_certificates "$SERVICE"

    if [[ "$DRY_RUN" == "false" ]]; then
        save_state "$backup_path" "$rotation_count"
    fi

    log "=== Certificate Rotation Complete ==="

    send_notification \
        "Certificate Rotation: $SERVICE" \
        "Certificate rotation completed for $SERVICE at $(date)"
}

main "$@"
