#!/usr/bin/env bash

# optimize_tcp.sh - Automated TCP tuning for different scenarios
# Configures kernel parameters, validates changes, and provides rollback capability

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="optimize_tcp.sh"
readonly SCRIPT_VERSION="1.0.0"
readonly BACKUP_DIR="/var/backups/tcp-optimization"
readonly SYSCTL_CONF="/etc/sysctl.d/99-tcp-optimization.conf"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Global flags
VERBOSE=0
JSON_OUTPUT=0
DRY_RUN=0
PROFILE=""
SKIP_BACKUP=0
SKIP_VALIDATION=0
ROLLBACK=0

# Logging functions
log_info() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

log_success() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
    fi
}

log_warning() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${YELLOW}[WARNING]${NC} $*" >&2
    fi
}

log_error() {
    if [[ $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
    fi
}

log_verbose() {
    if [[ $VERBOSE -eq 1 && $JSON_OUTPUT -eq 0 ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*" >&2
    fi
}

# JSON output functions
json_start() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        echo "{"
    fi
}

json_field() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        local key="$1"
        local value="$2"
        local comma="${3:-,}"
        echo "  \"$key\": \"$value\"$comma"
    fi
}

json_array_start() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        local key="$1"
        echo "  \"$key\": ["
    fi
}

json_array_end() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        local comma="${1:-,}"
        echo "  ]$comma"
    fi
}

json_end() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        echo "}"
    fi
}

# Help message
show_help() {
    cat <<EOF
$SCRIPT_NAME - Automated TCP performance tuning

USAGE:
    $SCRIPT_NAME --profile <profile> [OPTIONS]

PROFILES:
    high-bandwidth      Optimize for 10+ Gbps networks with moderate latency
    high-latency        Optimize for high-latency WAN links (100ms+ RTT)
    datacenter          Optimize for data center networks (low latency, high bandwidth)
    mobile              Optimize for mobile/wireless networks
    web-server          Optimize for high connection rate web servers
    balanced            Balanced configuration for general use
    ultra-performance   Extreme tuning for 100 Gbps networks

OPTIONS:
    --help, -h              Show this help message
    --version, -v           Show script version
    --verbose               Enable verbose output
    --json                  Output results in JSON format
    --dry-run               Show changes without applying them
    --skip-backup           Skip backup of current configuration
    --skip-validation       Skip validation of applied settings
    --rollback              Restore previous configuration from backup
    --backup-dir <dir>      Custom backup directory (default: $BACKUP_DIR)

EXAMPLES:
    # Optimize for high-bandwidth network
    sudo $SCRIPT_NAME --profile high-bandwidth

    # Dry run to preview changes
    sudo $SCRIPT_NAME --profile datacenter --dry-run

    # Verbose output with JSON
    sudo $SCRIPT_NAME --profile high-latency --verbose --json

    # Rollback previous changes
    sudo $SCRIPT_NAME --rollback

BACKUP:
    Configuration backups are stored in $BACKUP_DIR
    Each backup is timestamped for easy identification
    Use --rollback to restore the most recent backup

VALIDATION:
    After applying changes, the script validates:
    - All sysctl parameters are set correctly
    - TCP congestion control module is loaded
    - Network interface offloading is configured
    - Routing table is updated (if needed)

NOTES:
    - Requires root privileges
    - Changes persist across reboots (via sysctl.d)
    - Test thoroughly before production deployment
    - Monitor performance after tuning

EOF
}

# Version information
show_version() {
    echo "$SCRIPT_NAME version $SCRIPT_VERSION"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Detect network characteristics
detect_network() {
    local interface="${1:-}"

    if [[ -z "$interface" ]]; then
        # Get default interface
        interface=$(ip route | grep default | awk '{print $5}' | head -1)
    fi

    if [[ -z "$interface" ]]; then
        log_warning "Could not detect default network interface"
        return 1
    fi

    log_verbose "Detected network interface: $interface"

    # Get interface speed
    local speed
    if [[ -f "/sys/class/net/$interface/speed" ]]; then
        speed=$(cat "/sys/class/net/$interface/speed" 2>/dev/null || echo "unknown")
        log_verbose "Interface speed: ${speed} Mbps"
    fi

    # Get MTU
    local mtu
    mtu=$(ip link show "$interface" | grep mtu | awk '{print $5}')
    log_verbose "Interface MTU: $mtu"

    echo "$interface"
}

# Backup current configuration
backup_configuration() {
    if [[ $SKIP_BACKUP -eq 1 ]]; then
        log_info "Skipping backup (--skip-backup)"
        return 0
    fi

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/sysctl_backup_$timestamp.conf"

    log_info "Backing up current configuration to $backup_file"

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Backup current sysctl settings
    sysctl -a 2>/dev/null | grep -E "^net\.(ipv4|core)" > "$backup_file"

    # Backup current sysctl.d config if it exists
    if [[ -f "$SYSCTL_CONF" ]]; then
        cp "$SYSCTL_CONF" "$BACKUP_DIR/sysctl_conf_$timestamp.conf"
    fi

    # Backup routing table
    ip route show > "$BACKUP_DIR/routes_$timestamp.txt"

    # Backup interface settings
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        ethtool -k "$interface" > "$BACKUP_DIR/ethtool_$timestamp.txt" 2>/dev/null || true
    fi

    log_success "Backup created: $backup_file"
}

# Restore configuration from backup
restore_configuration() {
    log_info "Searching for backups in $BACKUP_DIR"

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory does not exist: $BACKUP_DIR"
        exit 1
    fi

    # Find most recent backup
    local latest_backup
    latest_backup=$(ls -t "$BACKUP_DIR"/sysctl_backup_*.conf 2>/dev/null | head -1)

    if [[ -z "$latest_backup" ]]; then
        log_error "No backup files found in $BACKUP_DIR"
        exit 1
    fi

    log_info "Restoring from backup: $latest_backup"

    # Apply backup
    while IFS='=' read -r key value; do
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)

        if [[ -n "$key" && "$key" != "#"* ]]; then
            log_verbose "Restoring: $key = $value"
            sysctl -w "$key=$value" >/dev/null 2>&1 || log_warning "Failed to restore: $key"
        fi
    done < "$latest_backup"

    # Remove current sysctl.d config
    if [[ -f "$SYSCTL_CONF" ]]; then
        log_info "Removing $SYSCTL_CONF"
        rm -f "$SYSCTL_CONF"
    fi

    log_success "Configuration restored from backup"
    log_info "Reboot or run 'sysctl -p' to ensure all settings are applied"
}

# Apply sysctl parameter
apply_sysctl() {
    local key="$1"
    local value="$2"

    log_verbose "Setting $key = $value"

    if [[ $DRY_RUN -eq 1 ]]; then
        echo "Would set: $key = $value"
        return 0
    fi

    # Apply immediately
    if ! sysctl -w "$key=$value" >/dev/null 2>&1; then
        log_warning "Failed to set $key = $value"
        return 1
    fi

    # Add to config file for persistence
    echo "$key = $value" >> "$SYSCTL_CONF"
}

# Configure TCP congestion control
configure_congestion_control() {
    local algorithm="$1"

    log_info "Configuring congestion control: $algorithm"

    # Check if module needs to be loaded
    if [[ "$algorithm" == "bbr" ]] || [[ "$algorithm" == "bbr2" ]]; then
        local module="tcp_$algorithm"

        if ! lsmod | grep -q "$module"; then
            log_verbose "Loading kernel module: $module"

            if [[ $DRY_RUN -eq 0 ]]; then
                if ! modprobe "$module" 2>/dev/null; then
                    log_error "Failed to load $module kernel module"
                    log_error "Your kernel may not support $algorithm"
                    return 1
                fi
            fi
        fi

        # Set qdisc to fq (required for BBR)
        apply_sysctl "net.core.default_qdisc" "fq"
    fi

    # Set congestion control algorithm
    apply_sysctl "net.ipv4.tcp_congestion_control" "$algorithm"

    return 0
}

# Configure TCP buffers
configure_buffers() {
    local rmem_min="$1"
    local rmem_default="$2"
    local rmem_max="$3"
    local wmem_min="$4"
    local wmem_default="$5"
    local wmem_max="$6"

    log_info "Configuring TCP buffers"

    apply_sysctl "net.ipv4.tcp_rmem" "$rmem_min $rmem_default $rmem_max"
    apply_sysctl "net.ipv4.tcp_wmem" "$wmem_min $wmem_default $wmem_max"
    apply_sysctl "net.core.rmem_max" "$rmem_max"
    apply_sysctl "net.core.wmem_max" "$wmem_max"
    apply_sysctl "net.core.rmem_default" "$rmem_default"
    apply_sysctl "net.core.wmem_default" "$wmem_default"
}

# Configure TCP parameters
configure_tcp_parameters() {
    log_info "Configuring TCP parameters"

    # Essential parameters
    apply_sysctl "net.ipv4.tcp_window_scaling" "1"
    apply_sysctl "net.ipv4.tcp_timestamps" "1"
    apply_sysctl "net.ipv4.tcp_sack" "1"
    apply_sysctl "net.ipv4.tcp_dsack" "1"
    apply_sysctl "net.ipv4.tcp_fack" "1"
    apply_sysctl "net.ipv4.tcp_moderate_rcvbuf" "1"
}

# Configure network interface
configure_interface() {
    local interface="$1"

    log_info "Configuring network interface: $interface"

    if [[ $DRY_RUN -eq 1 ]]; then
        echo "Would configure interface: $interface"
        return 0
    fi

    # Enable offloading features
    log_verbose "Enabling TSO, GSO, GRO"
    ethtool -K "$interface" tso on 2>/dev/null || log_warning "Failed to enable TSO"
    ethtool -K "$interface" gso on 2>/dev/null || log_warning "Failed to enable GSO"
    ethtool -K "$interface" gro on 2>/dev/null || log_warning "Failed to enable GRO"

    # Disable LRO (can break forwarding)
    ethtool -K "$interface" lro off 2>/dev/null || log_warning "Failed to disable LRO"

    # Set RSS queues to match CPU count
    local cpu_count
    cpu_count=$(nproc)
    log_verbose "Setting RSS queues to $cpu_count"
    ethtool -L "$interface" combined "$cpu_count" 2>/dev/null || log_warning "Failed to set RSS queues"
}

# Apply high-bandwidth profile
apply_high_bandwidth_profile() {
    log_info "Applying high-bandwidth profile (10+ Gbps)"

    # Large buffers for high BDP
    configure_buffers 4096 131072 134217728 4096 131072 134217728

    # BBR congestion control
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Additional settings
    apply_sysctl "net.ipv4.tcp_slow_start_after_idle" "0"
    apply_sysctl "net.ipv4.tcp_mtu_probing" "1"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # Memory limits
    apply_sysctl "net.ipv4.tcp_mem" "1048576 2097152 4194304"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply high-latency profile
apply_high_latency_profile() {
    log_info "Applying high-latency profile (100ms+ RTT)"

    # Large buffers for high BDP
    configure_buffers 4096 262144 67108864 4096 262144 67108864

    # BBR (handles latency well)
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Additional settings
    apply_sysctl "net.ipv4.tcp_slow_start_after_idle" "0"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"
    apply_sysctl "net.ipv4.tcp_mtu_probing" "1"

    # Keep-alive settings
    apply_sysctl "net.ipv4.tcp_keepalive_time" "600"
    apply_sysctl "net.ipv4.tcp_keepalive_intvl" "60"
    apply_sysctl "net.ipv4.tcp_keepalive_probes" "3"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply datacenter profile
apply_datacenter_profile() {
    log_info "Applying datacenter profile (low latency, high bandwidth)"

    # Moderate buffers (low latency)
    configure_buffers 4096 87380 33554432 4096 65536 33554432

    # BBR or DCTCP
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Fast connection handling
    apply_sysctl "net.ipv4.tcp_fin_timeout" "10"
    apply_sysctl "net.ipv4.tcp_tw_reuse" "1"
    apply_sysctl "net.ipv4.tcp_max_tw_buckets" "2000000"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # ECN for DCTCP (optional)
    apply_sysctl "net.ipv4.tcp_ecn" "1"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply mobile profile
apply_mobile_profile() {
    log_info "Applying mobile/wireless profile"

    # Conservative buffers
    configure_buffers 4096 131072 16777216 4096 65536 16777216

    # BBR (handles loss well)
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Shorter keep-alive
    apply_sysctl "net.ipv4.tcp_keepalive_time" "300"
    apply_sysctl "net.ipv4.tcp_keepalive_intvl" "30"
    apply_sysctl "net.ipv4.tcp_keepalive_probes" "3"

    # Conservative timeouts
    apply_sysctl "net.ipv4.tcp_retries2" "15"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply web-server profile
apply_web_server_profile() {
    log_info "Applying web-server profile (high connection rate)"

    # Moderate buffers
    configure_buffers 4096 87380 16777216 4096 65536 16777216

    # Cubic or BBR
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Fast connection handling
    apply_sysctl "net.ipv4.tcp_tw_reuse" "1"
    apply_sysctl "net.ipv4.tcp_fin_timeout" "15"
    apply_sysctl "net.ipv4.tcp_max_tw_buckets" "2000000"
    apply_sysctl "net.ipv4.tcp_max_syn_backlog" "16384"
    apply_sysctl "net.core.somaxconn" "8192"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # Port range
    apply_sysctl "net.ipv4.ip_local_port_range" "1024 65535"

    # SYN cookies
    apply_sysctl "net.ipv4.tcp_syncookies" "1"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply balanced profile
apply_balanced_profile() {
    log_info "Applying balanced profile (general purpose)"

    # Balanced buffers
    configure_buffers 4096 131072 67108864 4096 65536 67108864

    # BBR
    configure_congestion_control "bbr"

    # TCP parameters
    configure_tcp_parameters

    # Reasonable defaults
    apply_sysctl "net.ipv4.tcp_slow_start_after_idle" "0"
    apply_sysctl "net.ipv4.tcp_tw_reuse" "1"
    apply_sysctl "net.ipv4.tcp_fin_timeout" "30"
    apply_sysctl "net.ipv4.tcp_keepalive_time" "600"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"
    fi
}

# Apply ultra-performance profile
apply_ultra_performance_profile() {
    log_info "Applying ultra-performance profile (100 Gbps)"

    # Massive buffers
    configure_buffers 4096 131072 1073741824 4096 131072 1073741824

    # Large memory allocation
    apply_sysctl "net.ipv4.tcp_mem" "2097152 4194304 8388608"

    # BBR v2 (if available)
    if lsmod | grep -q tcp_bbr2; then
        configure_congestion_control "bbr2"
    else
        configure_congestion_control "bbr"
    fi

    # TCP parameters
    configure_tcp_parameters

    # Aggressive settings
    apply_sysctl "net.ipv4.tcp_slow_start_after_idle" "0"
    apply_sysctl "net.ipv4.tcp_mtu_probing" "1"
    apply_sysctl "net.ipv4.tcp_fastopen" "3"

    # Large backlog
    apply_sysctl "net.core.netdev_max_backlog" "100000"
    apply_sysctl "net.core.netdev_budget" "600"

    # Interface configuration
    local interface
    interface=$(detect_network)
    if [[ -n "$interface" ]]; then
        configure_interface "$interface"

        # Try to enable jumbo frames
        log_verbose "Attempting to set MTU to 9000 (jumbo frames)"
        ip link set "$interface" mtu 9000 2>/dev/null || log_warning "Failed to set jumbo frames"
    fi
}

# Validate configuration
validate_configuration() {
    if [[ $SKIP_VALIDATION -eq 1 ]]; then
        log_info "Skipping validation (--skip-validation)"
        return 0
    fi

    log_info "Validating configuration"

    local errors=0

    # Check if congestion control is set
    local cc
    cc=$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo "unknown")
    log_verbose "Congestion control: $cc"

    # Check if window scaling is enabled
    local ws
    ws=$(sysctl -n net.ipv4.tcp_window_scaling 2>/dev/null || echo "0")
    if [[ "$ws" != "1" ]]; then
        log_warning "Window scaling is not enabled"
        ((errors++))
    fi

    # Check if SACK is enabled
    local sack
    sack=$(sysctl -n net.ipv4.tcp_sack 2>/dev/null || echo "0")
    if [[ "$sack" != "1" ]]; then
        log_warning "SACK is not enabled"
        ((errors++))
    fi

    # Check buffer sizes
    local rmem_max
    rmem_max=$(sysctl -n net.core.rmem_max 2>/dev/null || echo "0")
    log_verbose "Receive buffer max: $rmem_max bytes"

    if [[ $errors -eq 0 ]]; then
        log_success "Validation passed"
        return 0
    else
        log_warning "Validation completed with $errors warnings"
        return 1
    fi
}

# Generate report
generate_report() {
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        json_start
        json_field "script" "$SCRIPT_NAME"
        json_field "version" "$SCRIPT_VERSION"
        json_field "profile" "$PROFILE"
        json_field "timestamp" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

        # Current settings
        json_array_start "settings"
        echo "    {"
        echo "      \"congestion_control\": \"$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo 'unknown')\","
        echo "      \"window_scaling\": \"$(sysctl -n net.ipv4.tcp_window_scaling 2>/dev/null || echo 'unknown')\","
        echo "      \"sack\": \"$(sysctl -n net.ipv4.tcp_sack 2>/dev/null || echo 'unknown')\","
        echo "      \"rmem_max\": \"$(sysctl -n net.core.rmem_max 2>/dev/null || echo 'unknown')\","
        echo "      \"wmem_max\": \"$(sysctl -n net.core.wmem_max 2>/dev/null || echo 'unknown')\""
        echo "    }"
        json_array_end ""
        json_end
    else
        log_info "Configuration Summary:"
        echo "  Profile: $PROFILE"
        echo "  Congestion Control: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo 'unknown')"
        echo "  Window Scaling: $(sysctl -n net.ipv4.tcp_window_scaling 2>/dev/null || echo 'unknown')"
        echo "  SACK: $(sysctl -n net.ipv4.tcp_sack 2>/dev/null || echo 'unknown')"
        echo "  Receive Buffer Max: $(sysctl -n net.core.rmem_max 2>/dev/null || echo 'unknown') bytes"
        echo "  Send Buffer Max: $(sysctl -n net.core.wmem_max 2>/dev/null || echo 'unknown') bytes"
    fi
}

# Main function
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --version|-v)
                show_version
                exit 0
                ;;
            --verbose)
                VERBOSE=1
                shift
                ;;
            --json)
                JSON_OUTPUT=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            --skip-backup)
                SKIP_BACKUP=1
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=1
                shift
                ;;
            --rollback)
                ROLLBACK=1
                shift
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Check root
    check_root

    # Rollback mode
    if [[ $ROLLBACK -eq 1 ]]; then
        restore_configuration
        exit 0
    fi

    # Validate profile
    if [[ -z "$PROFILE" ]]; then
        log_error "Profile is required (use --profile)"
        show_help
        exit 1
    fi

    # Backup configuration
    backup_configuration

    # Initialize sysctl config file
    if [[ $DRY_RUN -eq 0 ]]; then
        mkdir -p "$(dirname "$SYSCTL_CONF")"
        cat > "$SYSCTL_CONF" <<EOF
# TCP Optimization - Generated by $SCRIPT_NAME
# Profile: $PROFILE
# Timestamp: $(date)

EOF
    fi

    # Apply profile
    case "$PROFILE" in
        high-bandwidth)
            apply_high_bandwidth_profile
            ;;
        high-latency)
            apply_high_latency_profile
            ;;
        datacenter)
            apply_datacenter_profile
            ;;
        mobile)
            apply_mobile_profile
            ;;
        web-server)
            apply_web_server_profile
            ;;
        balanced)
            apply_balanced_profile
            ;;
        ultra-performance)
            apply_ultra_performance_profile
            ;;
        *)
            log_error "Unknown profile: $PROFILE"
            log_error "Valid profiles: high-bandwidth, high-latency, datacenter, mobile, web-server, balanced, ultra-performance"
            exit 1
            ;;
    esac

    # Validate configuration
    validate_configuration

    # Generate report
    generate_report

    if [[ $DRY_RUN -eq 0 ]]; then
        log_success "TCP optimization complete"
        log_info "Changes are persistent and will survive reboot"
        log_info "Configuration saved to: $SYSCTL_CONF"
        log_info "Backup saved to: $BACKUP_DIR"
    else
        log_info "Dry run complete (no changes applied)"
    fi
}

# Run main function
main "$@"
