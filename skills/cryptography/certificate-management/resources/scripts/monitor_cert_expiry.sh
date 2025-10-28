#!/usr/bin/env bash
#
# Certificate Expiry Monitoring Tool
#
# Monitors SSL/TLS certificates across infrastructure and sends alerts for
# certificates expiring soon.
#
# Features:
# - Monitor multiple hosts/domains
# - File-based certificate monitoring
# - Configurable expiry thresholds
# - Multiple output formats (text, JSON, Prometheus)
# - Email/webhook alerts
# - Certificate inventory export
# - Integration with monitoring systems
#
# Usage:
#   ./monitor_cert_expiry.sh --host example.com
#   ./monitor_cert_expiry.sh --hosts-file hosts.txt --threshold 30
#   ./monitor_cert_expiry.sh --cert-dir /etc/ssl/certs --json
#   ./monitor_cert_expiry.sh --hosts-file hosts.txt --format prometheus
#   ./monitor_cert_expiry.sh --host example.com --alert-email admin@example.com
#
# Author: Generated with Claude Code
# License: MIT

set -euo pipefail

# Default values
THRESHOLD_WARNING=30
THRESHOLD_CRITICAL=7
OUTPUT_FORMAT="text"
TIMEOUT=10
PORT=443
VERBOSE=false
CHECK_REVOCATION=false

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Usage function
usage() {
    cat << EOF
Certificate Expiry Monitoring Tool

Usage: $0 [OPTIONS]

Monitoring Options:
  --host HOST              Monitor single host
  --port PORT              Port to check (default: 443)
  --hosts-file FILE        File with hosts to monitor (one per line)
  --cert-dir DIR           Directory with certificate files to monitor
  --cert-file FILE         Single certificate file to check

Threshold Options:
  --threshold-warning N    Warning threshold in days (default: 30)
  --threshold-critical N   Critical threshold in days (default: 7)

Output Options:
  --format FORMAT          Output format: text, json, prometheus, csv (default: text)
  --json                   JSON output (shorthand for --format json)
  --verbose                Verbose output
  --quiet                  Only output errors

Alert Options:
  --alert-email EMAIL      Send email alerts to this address
  --alert-webhook URL      Send webhook alerts to this URL
  --alert-slack URL        Send Slack alerts to webhook URL

Additional Options:
  --timeout SECONDS        Connection timeout (default: 10)
  --check-revocation       Check OCSP revocation status
  --inventory-file FILE    Export certificate inventory to file
  --help                   Show this help message

Examples:
  # Monitor single host
  $0 --host example.com

  # Monitor multiple hosts
  $0 --hosts-file hosts.txt --threshold-warning 30

  # Monitor with JSON output
  $0 --host example.com --json

  # Monitor and alert
  $0 --hosts-file hosts.txt --alert-email admin@example.com

  # Prometheus metrics
  $0 --hosts-file hosts.txt --format prometheus > /var/lib/prometheus/cert_metrics.prom

  # Certificate inventory
  $0 --hosts-file hosts.txt --inventory-file certs.json

  # Monitor local certificate files
  $0 --cert-dir /etc/ssl/certs --json

Hosts File Format:
  example.com
  api.example.com:8443
  internal.example.com

Exit Codes:
  0 - All certificates valid
  1 - One or more certificates expiring soon (warning)
  2 - One or more certificates expiring critically soon or expired
  3 - Error during monitoring
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --hosts-file)
            HOSTS_FILE="$2"
            shift 2
            ;;
        --cert-dir)
            CERT_DIR="$2"
            shift 2
            ;;
        --cert-file)
            CERT_FILE="$2"
            shift 2
            ;;
        --threshold-warning)
            THRESHOLD_WARNING="$2"
            shift 2
            ;;
        --threshold-critical)
            THRESHOLD_CRITICAL="$2"
            shift 2
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --json)
            OUTPUT_FORMAT="json"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --alert-email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        --alert-webhook)
            ALERT_WEBHOOK="$2"
            shift 2
            ;;
        --alert-slack)
            ALERT_SLACK="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --check-revocation)
            CHECK_REVOCATION=true
            shift
            ;;
        --inventory-file)
            INVENTORY_FILE="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ ! -v HOST && ! -v HOSTS_FILE && ! -v CERT_DIR && ! -v CERT_FILE ]]; then
    echo "Error: Must specify --host, --hosts-file, --cert-dir, or --cert-file" >&2
    usage
    exit 1
fi

# Check required commands
for cmd in openssl date; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Error: $cmd not found" >&2
        exit 3
    fi
done

# Global arrays for results
declare -a RESULTS
declare -a ALERTS

# Check certificate from host
check_host_certificate() {
    local host="$1"
    local port="${2:-443}"
    local result=""

    # Extract hostname if contains port
    if [[ "$host" == *:* ]]; then
        port="${host#*:}"
        host="${host%:*}"
    fi

    [[ "$VERBOSE" == true ]] && echo "Checking $host:$port..." >&2

    # Get certificate
    local cert_info
    if ! cert_info=$(timeout "$TIMEOUT" openssl s_client -connect "$host:$port" \
                    -servername "$host" </dev/null 2>/dev/null | \
                    openssl x509 -noout -dates -subject -issuer 2>/dev/null); then
        result=$(printf '{"host":"%s","port":%d,"status":"error","error":"Connection failed"}' "$host" "$port")
        RESULTS+=("$result")
        return 1
    fi

    # Extract dates
    local not_before not_after subject issuer
    not_before=$(echo "$cert_info" | grep "notBefore=" | cut -d= -f2)
    not_after=$(echo "$cert_info" | grep "notAfter=" | cut -d= -f2)
    subject=$(echo "$cert_info" | grep "subject=" | cut -d= -f2-)
    issuer=$(echo "$cert_info" | grep "issuer=" | cut -d= -f2-)

    # Calculate days remaining
    local expiry_epoch now_epoch days_remaining
    expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$not_after" +%s 2>/dev/null)
    now_epoch=$(date +%s)
    days_remaining=$(( (expiry_epoch - now_epoch) / 86400 ))

    # Determine status
    local status severity
    if (( days_remaining < 0 )); then
        status="expired"
        severity="critical"
    elif (( days_remaining <= THRESHOLD_CRITICAL )); then
        status="critical"
        severity="critical"
    elif (( days_remaining <= THRESHOLD_WARNING )); then
        status="warning"
        severity="warning"
    else
        status="ok"
        severity="info"
    fi

    # Check revocation if requested
    local revocation_status=""
    if [[ "$CHECK_REVOCATION" == true ]]; then
        if timeout "$TIMEOUT" openssl s_client -connect "$host:$port" \
            -servername "$host" -status </dev/null 2>/dev/null | \
            grep -q "OCSP Response Status: successful"; then
            revocation_status="valid"
        else
            revocation_status="unknown"
        fi
    fi

    # Build result
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        result=$(cat <<EOF
{
  "host": "$host",
  "port": $port,
  "status": "$status",
  "severity": "$severity",
  "days_remaining": $days_remaining,
  "not_before": "$not_before",
  "not_after": "$not_after",
  "subject": "$subject",
  "issuer": "$issuer"$([ -n "$revocation_status" ] && echo ",
  \"revocation_status\": \"$revocation_status\"" || echo "")
}
EOF
        )
    else
        result="$host:$port|$status|$days_remaining|$not_after|$subject"
    fi

    RESULTS+=("$result")

    # Add to alerts if needed
    if [[ "$status" == "critical" || "$status" == "expired" || "$status" == "warning" ]]; then
        local alert_msg="Certificate for $host:$port expires in $days_remaining days (status: $status)"
        ALERTS+=("$alert_msg")
    fi

    return 0
}

# Check certificate from file
check_file_certificate() {
    local cert_file="$1"
    local result=""

    [[ "$VERBOSE" == true ]] && echo "Checking $cert_file..." >&2

    if [[ ! -f "$cert_file" ]]; then
        result=$(printf '{"file":"%s","status":"error","error":"File not found"}' "$cert_file")
        RESULTS+=("$result")
        return 1
    fi

    # Get certificate info
    local cert_info
    if ! cert_info=$(openssl x509 -in "$cert_file" -noout -dates -subject -issuer 2>/dev/null); then
        result=$(printf '{"file":"%s","status":"error","error":"Invalid certificate"}' "$cert_file")
        RESULTS+=("$result")
        return 1
    fi

    # Extract dates
    local not_before not_after subject issuer
    not_before=$(echo "$cert_info" | grep "notBefore=" | cut -d= -f2)
    not_after=$(echo "$cert_info" | grep "notAfter=" | cut -d= -f2)
    subject=$(echo "$cert_info" | grep "subject=" | cut -d= -f2-)
    issuer=$(echo "$cert_info" | grep "issuer=" | cut -d= -f2-)

    # Calculate days remaining
    local expiry_epoch now_epoch days_remaining
    expiry_epoch=$(date -d "$not_after" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$not_after" +%s 2>/dev/null)
    now_epoch=$(date +%s)
    days_remaining=$(( (expiry_epoch - now_epoch) / 86400 ))

    # Determine status
    local status severity
    if (( days_remaining < 0 )); then
        status="expired"
        severity="critical"
    elif (( days_remaining <= THRESHOLD_CRITICAL )); then
        status="critical"
        severity="critical"
    elif (( days_remaining <= THRESHOLD_WARNING )); then
        status="warning"
        severity="warning"
    else
        status="ok"
        severity="info"
    fi

    # Build result
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        result=$(cat <<EOF
{
  "file": "$cert_file",
  "status": "$status",
  "severity": "$severity",
  "days_remaining": $days_remaining,
  "not_before": "$not_before",
  "not_after": "$not_after",
  "subject": "$subject",
  "issuer": "$issuer"
}
EOF
        )
    else
        result="$cert_file|$status|$days_remaining|$not_after|$subject"
    fi

    RESULTS+=("$result")

    # Add to alerts if needed
    if [[ "$status" == "critical" || "$status" == "expired" || "$status" == "warning" ]]; then
        local alert_msg="Certificate $cert_file expires in $days_remaining days (status: $status)"
        ALERTS+=("$alert_msg")
    fi

    return 0
}

# Send email alert
send_email_alert() {
    local email="$1"
    local subject="Certificate Expiry Alert"
    local body=""

    if [[ ${#ALERTS[@]} -eq 0 ]]; then
        return 0
    fi

    body+="The following certificates require attention:\n\n"
    for alert in "${ALERTS[@]}"; do
        body+="- $alert\n"
    done

    echo -e "$body" | mail -s "$subject" "$email" 2>/dev/null || {
        echo "Warning: Failed to send email alert" >&2
        return 1
    }
}

# Send webhook alert
send_webhook_alert() {
    local webhook_url="$1"
    local payload=""

    if [[ ${#ALERTS[@]} -eq 0 ]]; then
        return 0
    fi

    payload=$(cat <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "alerts": [
$(for i in "${!ALERTS[@]}"; do
    echo "    \"${ALERTS[$i]}\""
    [[ $i -lt $((${#ALERTS[@]} - 1)) ]] && echo ","
done)
  ]
}
EOF
    )

    curl -X POST -H "Content-Type: application/json" -d "$payload" "$webhook_url" 2>/dev/null || {
        echo "Warning: Failed to send webhook alert" >&2
        return 1
    }
}

# Send Slack alert
send_slack_alert() {
    local slack_url="$1"
    local text=""

    if [[ ${#ALERTS[@]} -eq 0 ]]; then
        return 0
    fi

    text="*Certificate Expiry Alert*\n\n"
    for alert in "${ALERTS[@]}"; do
        text+="• $alert\n"
    done

    local payload
    payload=$(cat <<EOF
{
  "text": "$text",
  "username": "Certificate Monitor",
  "icon_emoji": ":warning:"
}
EOF
    )

    curl -X POST -H "Content-Type: application/json" -d "$payload" "$slack_url" 2>/dev/null || {
        echo "Warning: Failed to send Slack alert" >&2
        return 1
    }
}

# Output results
output_results() {
    case "$OUTPUT_FORMAT" in
        json)
            echo "["
            for i in "${!RESULTS[@]}"; do
                echo "  ${RESULTS[$i]}"
                [[ $i -lt $((${#RESULTS[@]} - 1)) ]] && echo ","
            done
            echo "]"
            ;;

        prometheus)
            echo "# HELP ssl_certificate_expiry_days Days until SSL certificate expires"
            echo "# TYPE ssl_certificate_expiry_days gauge"
            for result in "${RESULTS[@]}"; do
                if [[ "$result" == *"host"* ]]; then
                    # Parse JSON (basic extraction)
                    local host port days status
                    host=$(echo "$result" | grep -o '"host":"[^"]*"' | cut -d'"' -f4)
                    port=$(echo "$result" | grep -o '"port":[0-9]*' | grep -o '[0-9]*')
                    days=$(echo "$result" | grep -o '"days_remaining":[0-9-]*' | grep -o '[0-9-]*$')
                    status=$(echo "$result" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

                    echo "ssl_certificate_expiry_days{host=\"$host\",port=\"$port\",status=\"$status\"} $days"
                fi
            done
            ;;

        csv)
            echo "Host,Port,Status,Days Remaining,Expiry Date,Subject"
            for result in "${RESULTS[@]}"; do
                echo "$result" | tr '|' ','
            done
            ;;

        text|*)
            printf "${GREEN}=== Certificate Expiry Report ===${NC}\n"
            printf "Timestamp: %s\n" "$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
            printf "Warning threshold: %d days\n" "$THRESHOLD_WARNING"
            printf "Critical threshold: %d days\n\n" "$THRESHOLD_CRITICAL"

            printf "%-40s %-10s %-15s %-25s\n" "Host/File" "Status" "Days Remaining" "Expiry Date"
            printf "%-40s %-10s %-15s %-25s\n" "$(printf '%0.s-' {1..40})" "$(printf '%0.s-' {1..10})" "$(printf '%0.s-' {1..15})" "$(printf '%0.s-' {1..25})"

            for result in "${RESULTS[@]}"; do
                if [[ "$result" == *"|"* ]]; then
                    IFS='|' read -r host_file status days expiry_date subject <<< "$result"

                    local color=$NC
                    case "$status" in
                        expired|critical)
                            color=$RED
                            ;;
                        warning)
                            color=$YELLOW
                            ;;
                        ok)
                            color=$GREEN
                            ;;
                    esac

                    printf "${color}%-40s %-10s %-15s %-25s${NC}\n" \
                        "${host_file:0:40}" "$status" "$days" "$expiry_date"
                fi
            done

            # Summary
            local count_ok=0 count_warning=0 count_critical=0 count_error=0
            for result in "${RESULTS[@]}"; do
                [[ "$result" == *"\"ok\""* || "$result" == *"|ok|"* ]] && ((count_ok++))
                [[ "$result" == *"\"warning\""* || "$result" == *"|warning|"* ]] && ((count_warning++))
                [[ "$result" == *"\"critical\""* || "$result" == *"|critical|"* || "$result" == *"\"expired\""* || "$result" == *"|expired|"* ]] && ((count_critical++))
                [[ "$result" == *"\"error\""* ]] && ((count_error++))
            done

            printf "\n${GREEN}=== Summary ===${NC}\n"
            printf "${GREEN}OK: %d${NC}\n" "$count_ok"
            printf "${YELLOW}Warning: %d${NC}\n" "$count_warning"
            printf "${RED}Critical/Expired: %d${NC}\n" "$count_critical"
            [[ $count_error -gt 0 ]] && printf "Errors: %d\n" "$count_error"
            ;;
    esac
}

# Main execution
main() {
    # Monitor single host
    if [[ -v HOST ]]; then
        check_host_certificate "$HOST" "$PORT"
    fi

    # Monitor hosts from file
    if [[ -v HOSTS_FILE ]]; then
        if [[ ! -f "$HOSTS_FILE" ]]; then
            echo "Error: Hosts file not found: $HOSTS_FILE" >&2
            exit 3
        fi

        while IFS= read -r host; do
            # Skip empty lines and comments
            [[ -z "$host" || "$host" =~ ^# ]] && continue
            check_host_certificate "$host"
        done < "$HOSTS_FILE"
    fi

    # Monitor certificate directory
    if [[ -v CERT_DIR ]]; then
        if [[ ! -d "$CERT_DIR" ]]; then
            echo "Error: Certificate directory not found: $CERT_DIR" >&2
            exit 3
        fi

        while IFS= read -r cert_file; do
            check_file_certificate "$cert_file"
        done < <(find "$CERT_DIR" -type f \( -name "*.pem" -o -name "*.crt" -o -name "*.cer" \))
    fi

    # Monitor single certificate file
    if [[ -v CERT_FILE ]]; then
        check_file_certificate "$CERT_FILE"
    fi

    # Output results
    if [[ ! -v QUIET || "$QUIET" != true ]]; then
        output_results
    fi

    # Export inventory if requested
    if [[ -v INVENTORY_FILE ]]; then
        if [[ "$OUTPUT_FORMAT" == "json" ]]; then
            output_results > "$INVENTORY_FILE"
        else
            # Temporarily switch to JSON
            local original_format="$OUTPUT_FORMAT"
            OUTPUT_FORMAT="json"
            output_results > "$INVENTORY_FILE"
            OUTPUT_FORMAT="$original_format"
        fi
        [[ "$VERBOSE" == true ]] && echo "Inventory exported to $INVENTORY_FILE" >&2
    fi

    # Send alerts
    if [[ -v ALERT_EMAIL ]]; then
        send_email_alert "$ALERT_EMAIL"
    fi

    if [[ -v ALERT_WEBHOOK ]]; then
        send_webhook_alert "$ALERT_WEBHOOK"
    fi

    if [[ -v ALERT_SLACK ]]; then
        send_slack_alert "$ALERT_SLACK"
    fi

    # Exit code based on status
    local has_critical=false has_warning=false
    for result in "${RESULTS[@]}"; do
        [[ "$result" == *"\"critical\""* || "$result" == *"|critical|"* || "$result" == *"\"expired\""* || "$result" == *"|expired|"* ]] && has_critical=true
        [[ "$result" == *"\"warning\""* || "$result" == *"|warning|"* ]] && has_warning=true
    done

    if [[ "$has_critical" == true ]]; then
        exit 2
    elif [[ "$has_warning" == true ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run main
main
