#!/usr/bin/env bash
#
# Analyze core dumps to diagnose crashes.
#
# This script provides comprehensive core dump analysis including:
# - Automatic debugger detection (gdb, lldb, delve)
# - Stack trace extraction for all threads
# - Symbol resolution and source mapping
# - Crash pattern detection
# - Automated report generation
#

set -euo pipefail

# Script configuration
SCRIPT_NAME="$(basename "$0")"
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
VERBOSE=0
JSON_OUTPUT=0
OUTPUT_FILE=""
BINARY_PATH=""
CORE_PATH=""
SYMBOL_PATH=""
DEBUGGER=""
TEMP_DIR=""

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------

log_info() {
    if [[ $VERBOSE -eq 1 ]]; then
        echo -e "${BLUE}[INFO]${NC} $*" >&2
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

cleanup() {
    if [[ -n "${TEMP_DIR:-}" ]] && [[ -d "$TEMP_DIR" ]]; then
        # Safety check: only delete if it's in /tmp
        if [[ "$TEMP_DIR" == /tmp/* ]]; then
            log_info "Cleaning up temporary directory: $TEMP_DIR"
            # Safe in this context: path is verified to be in /tmp
            rm -rf "$TEMP_DIR"
        fi
    fi
}

trap cleanup EXIT INT TERM

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <core_file>

Analyze core dumps to diagnose application crashes.

Arguments:
  <core_file>           Path to core dump file

Options:
  -b, --binary PATH     Path to binary executable
  -s, --symbols PATH    Path to debug symbols directory
  -o, --output FILE     Write output to file
  -d, --debugger CMD    Debugger to use (gdb, lldb, dlv)
  --json                Output in JSON format
  -v, --verbose         Verbose output
  -h, --help            Show this help message
  --version             Show version information

Examples:
  # Analyze core dump
  $SCRIPT_NAME core.12345

  # With specific binary
  $SCRIPT_NAME --binary /usr/bin/myapp core.12345

  # With debug symbols
  $SCRIPT_NAME --binary /usr/bin/myapp --symbols /usr/lib/debug core.12345

  # JSON output
  $SCRIPT_NAME --json --output report.json core.12345

  # Verbose analysis
  $SCRIPT_NAME --verbose --binary /usr/bin/myapp core.12345

Exit Codes:
  0    Success
  1    General error
  2    Invalid arguments
  3    Core dump not found
  4    Binary not found
  5    Debugger not found

EOF
    exit 0
}

show_version() {
    echo "$SCRIPT_NAME version $VERSION"
    exit 0
}

#------------------------------------------------------------------------------
# Core Dump Analysis Functions
#------------------------------------------------------------------------------

detect_debugger() {
    log_info "Detecting available debugger..."

    if command -v gdb &>/dev/null; then
        echo "gdb"
        return 0
    elif command -v lldb &>/dev/null; then
        echo "lldb"
        return 0
    elif command -v dlv &>/dev/null; then
        echo "dlv"
        return 0
    else
        log_error "No supported debugger found (gdb, lldb, dlv)"
        return 1
    fi
}

detect_binary_from_core() {
    local core_file="$1"

    log_info "Attempting to detect binary from core dump..."

    # Try using 'file' command
    if command -v file &>/dev/null; then
        local file_output
        file_output=$(file "$core_file")

        # Extract binary path from file output
        if [[ $file_output =~ execfn:\ \'([^\']+)\' ]]; then
            echo "${BASH_REMATCH[1]}"
            return 0
        fi

        # Try alternate format
        if [[ $file_output =~ from\ \'([^\']+)\' ]]; then
            echo "${BASH_REMATCH[1]}"
            return 0
        fi
    fi

    # Try using eu-unstrip (from elfutils)
    if command -v eu-unstrip &>/dev/null; then
        local binary
        binary=$(eu-unstrip -n --core="$core_file" 2>/dev/null | awk '{print $3}' | head -1)
        if [[ -n "$binary" ]] && [[ -f "$binary" ]]; then
            echo "$binary"
            return 0
        fi
    fi

    return 1
}

get_core_info() {
    local core_file="$1"
    local binary="${2:-}"

    log_info "Extracting core dump information..."

    local result="{"

    # File size
    local size
    size=$(stat -f%z "$core_file" 2>/dev/null || stat -c%s "$core_file" 2>/dev/null || echo "0")
    result+="\"file_size_bytes\": $size,"

    # File modified time
    local mtime
    mtime=$(stat -f%m "$core_file" 2>/dev/null || stat -c%Y "$core_file" 2>/dev/null || echo "0")
    result+="\"timestamp\": $mtime,"

    # Use 'file' command to get details
    if command -v file &>/dev/null; then
        local file_output
        file_output=$(file "$core_file")
        result+="\"file_info\": \"$(echo "$file_output" | sed 's/"/\\"/g')\","
    fi

    # Binary path
    if [[ -n "$binary" ]]; then
        result+="\"binary\": \"$binary\","
    fi

    result="${result%,}}"  # Remove trailing comma
    echo "$result"
}

analyze_with_gdb() {
    local binary="$1"
    local core_file="$2"
    local symbols="${3:-}"

    log_info "Analyzing with GDB..."

    # Create GDB command file
    local gdb_commands="$TEMP_DIR/gdb_commands.txt"

    cat > "$gdb_commands" <<'GDB_EOF'
set pagination off
set print pretty on

printf "\n=== CORE DUMP ANALYSIS ===\n\n"

printf "Binary: "
info file

printf "\n=== CRASH INFORMATION ===\n"
info program

printf "\n=== SIGNAL INFORMATION ===\n"
if $_siginfo
  printf "Signal: %d (%s)\n", $_siginfo.si_signo, $_siginfo
  printf "Fault Address: %p\n", $_siginfo.si_addr
  printf "Error Code: %d\n", $_siginfo.si_errno
end

printf "\n=== BACKTRACE (Crashing Thread) ===\n"
bt full

printf "\n=== REGISTERS ===\n"
info registers

printf "\n=== THREAD INFORMATION ===\n"
info threads

printf "\n=== ALL THREAD BACKTRACES ===\n"
thread apply all bt

printf "\n=== LOCAL VARIABLES (Frame 0) ===\n"
frame 0
info locals

printf "\n=== ARGUMENTS (Frame 0) ===\n"
info args

printf "\n=== SHARED LIBRARIES ===\n"
info sharedlibrary

printf "\n=== CRASH PATTERN ANALYSIS ===\n"

# Check for null pointer dereference
if $_siginfo
  if $_siginfo.si_addr < 0x1000
    printf "PATTERN: Likely null pointer dereference (address: %p)\n", $_siginfo.si_addr
  end
end

# Check for stack overflow
set $frame_count = 0
bt
# Note: Stack overflow detection would need frame counting logic

printf "\n=== END OF ANALYSIS ===\n"
quit
GDB_EOF

    # Run GDB
    local gdb_output
    local gdb_cmd="gdb -batch -x \"$gdb_commands\""

    if [[ -n "$symbols" ]]; then
        gdb_cmd+=" -d \"$symbols\""
    fi

    gdb_cmd+=" \"$binary\" \"$core_file\""

    log_info "Running: $gdb_cmd"
    gdb_output=$(eval "$gdb_cmd" 2>&1) || {
        log_error "GDB analysis failed"
        return 1
    }

    echo "$gdb_output"
}

analyze_with_lldb() {
    local binary="$1"
    local core_file="$2"
    local symbols="${3:-}"

    log_info "Analyzing with LLDB..."

    # Create LLDB command file
    local lldb_commands="$TEMP_DIR/lldb_commands.txt"

    cat > "$lldb_commands" <<'LLDB_EOF'
settings set auto-confirm true

script print("\n=== CORE DUMP ANALYSIS ===\n")

target create --core core_file_placeholder binary_placeholder

script print("\n=== CRASH INFORMATION ===")
script print(f"Process: {lldb.process}")
script print(f"State: {lldb.process.GetState()}")

script print("\n=== THREAD INFORMATION ===")
thread list

script print("\n=== BACKTRACE (Crashing Thread) ===")
bt all

script print("\n=== REGISTERS ===")
register read

script print("\n=== FRAME VARIABLES ===")
frame variable

script print("\n=== ALL THREADS BACKTRACE ===")
thread backtrace all

script print("\n=== LIBRARIES ===")
image list

script print("\n=== END OF ANALYSIS ===")
quit
LLDB_EOF

    # Replace placeholders
    sed -i.bak "s|core_file_placeholder|$core_file|g" "$lldb_commands"
    sed -i.bak "s|binary_placeholder|$binary|g" "$lldb_commands"

    # Run LLDB
    local lldb_output
    lldb_output=$(lldb -s "$lldb_commands" 2>&1) || {
        log_error "LLDB analysis failed"
        return 1
    }

    echo "$lldb_output"
}

analyze_with_delve() {
    local binary="$1"
    local core_file="$2"

    log_info "Analyzing with Delve (Go debugger)..."

    # Delve core analysis
    local dlv_output
    dlv_output=$(dlv core "$binary" "$core_file" <<'DLV_EOF'
goroutines
goroutine 1
bt
locals
exit
DLV_EOF
) || {
        log_error "Delve analysis failed"
        return 1
    }

    echo "$dlv_output"
}

detect_crash_patterns() {
    local analysis_output="$1"

    log_info "Detecting crash patterns..."

    local patterns=()

    # Null pointer dereference
    if echo "$analysis_output" | grep -qi "null pointer\|address.*0x0\|0x00000000"; then
        patterns+=("null_pointer_dereference")
    fi

    # Segmentation fault
    if echo "$analysis_output" | grep -qi "SIGSEGV\|segmentation fault"; then
        patterns+=("segmentation_fault")
    fi

    # Abort signal
    if echo "$analysis_output" | grep -qi "SIGABRT\|abort"; then
        patterns+=("abort_signal")
    fi

    # Stack overflow
    if echo "$analysis_output" | grep -qi "stack overflow"; then
        patterns+=("stack_overflow")
    fi

    # Assertion failure
    if echo "$analysis_output" | grep -qi "assertion\|assert"; then
        patterns+=("assertion_failure")
    fi

    # Double free
    if echo "$analysis_output" | grep -qi "double free\|invalid pointer"; then
        patterns+=("double_free")
    fi

    # Deadlock
    if echo "$analysis_output" | grep -qi "deadlock"; then
        patterns+=("deadlock")
    fi

    # Print patterns as JSON array
    if [[ ${#patterns[@]} -gt 0 ]]; then
        printf '['
        printf '"%s",' "${patterns[@]}"
        printf ']'
    else
        echo '[]'
    fi | sed 's/,]/]/'
}

extract_backtrace() {
    local analysis_output="$1"

    log_info "Extracting backtrace..."

    # Extract lines between backtrace markers
    echo "$analysis_output" | \
        sed -n '/=== BACKTRACE/,/===/p' | \
        grep -E '^#[0-9]+' || echo "[]"
}

generate_recommendations() {
    local patterns="$1"

    log_info "Generating recommendations..."

    local recommendations='['

    if echo "$patterns" | grep -q "null_pointer_dereference"; then
        recommendations+='{"pattern":"null_pointer_dereference","recommendation":"Check for null pointer checks before dereferencing. Review recent changes to pointer handling."},'
    fi

    if echo "$patterns" | grep -q "segmentation_fault"; then
        recommendations+='{"pattern":"segmentation_fault","recommendation":"Review memory access patterns. Check array bounds and pointer arithmetic."},'
    fi

    if echo "$patterns" | grep -q "abort_signal"; then
        recommendations+='{"pattern":"abort_signal","recommendation":"Check for assertion failures. Review invariant violations and error handling."},'
    fi

    if echo "$patterns" | grep -q "stack_overflow"; then
        recommendations+='{"pattern":"stack_overflow","recommendation":"Look for infinite recursion or large stack allocations. Consider increasing stack size."},'
    fi

    if echo "$patterns" | grep -q "assertion_failure"; then
        recommendations+='{"pattern":"assertion_failure","recommendation":"Review the failed assertion condition. Check if invariant assumption is correct."},'
    fi

    if echo "$patterns" | grep -q "double_free"; then
        recommendations+='{"pattern":"double_free","recommendation":"Review memory management. Check for double frees or use-after-free bugs."},'
    fi

    recommendations="${recommendations%,}]"  # Remove trailing comma

    echo "$recommendations"
}

generate_json_report() {
    local core_info="$1"
    local analysis_output="$2"

    log_info "Generating JSON report..."

    local patterns
    patterns=$(detect_crash_patterns "$analysis_output")

    local backtrace
    backtrace=$(extract_backtrace "$analysis_output" | head -20)

    local recommendations
    recommendations=$(generate_recommendations "$patterns")

    cat <<JSON_REPORT
{
  "core_dump_analysis": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "core_info": $core_info,
    "debugger": "$DEBUGGER",
    "crash_patterns": $patterns,
    "recommendations": $recommendations,
    "backtrace_preview": $(echo "$backtrace" | jq -Rs .),
    "full_analysis": $(echo "$analysis_output" | jq -Rs .)
  }
}
JSON_REPORT
}

generate_text_report() {
    local core_info="$1"
    local analysis_output="$2"

    log_info "Generating text report..."

    local patterns
    patterns=$(detect_crash_patterns "$analysis_output")

    local recommendations
    recommendations=$(generate_recommendations "$patterns")

    cat <<TEXT_REPORT
================================================================================
                         CORE DUMP ANALYSIS REPORT
================================================================================

Generated: $(date)
Debugger: $DEBUGGER

Core Information:
-----------------
$core_info

Detected Patterns:
------------------
$patterns

Recommendations:
----------------
$recommendations

Full Analysis:
--------------
$analysis_output

================================================================================
TEXT_REPORT
}

#------------------------------------------------------------------------------
# Main Analysis Function
#------------------------------------------------------------------------------

perform_analysis() {
    local binary="$1"
    local core_file="$2"
    local symbols="${3:-}"

    log_info "Starting core dump analysis..."
    log_info "Binary: $binary"
    log_info "Core: $core_file"
    log_info "Debugger: $DEBUGGER"

    # Get core info
    local core_info
    core_info=$(get_core_info "$core_file" "$binary")

    # Perform analysis based on debugger
    local analysis_output
    case "$DEBUGGER" in
        gdb)
            analysis_output=$(analyze_with_gdb "$binary" "$core_file" "$symbols")
            ;;
        lldb)
            analysis_output=$(analyze_with_lldb "$binary" "$core_file" "$symbols")
            ;;
        dlv)
            analysis_output=$(analyze_with_delve "$binary" "$core_file")
            ;;
        *)
            log_error "Unknown debugger: $DEBUGGER"
            return 1
            ;;
    esac

    # Generate report
    local report
    if [[ $JSON_OUTPUT -eq 1 ]]; then
        report=$(generate_json_report "$core_info" "$analysis_output")
    else
        report=$(generate_text_report "$core_info" "$analysis_output")
    fi

    # Output report
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "$report" > "$OUTPUT_FILE"
        log_success "Analysis report written to: $OUTPUT_FILE"
    else
        echo "$report"
    fi
}

#------------------------------------------------------------------------------
# Argument Parsing
#------------------------------------------------------------------------------

parse_arguments() {
    if [[ $# -eq 0 ]]; then
        usage
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                ;;
            --version)
                show_version
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            --json)
                JSON_OUTPUT=1
                shift
                ;;
            -b|--binary)
                if [[ -z "${2:-}" ]]; then
                    log_error "Missing argument for --binary"
                    exit 2
                fi
                BINARY_PATH="$2"
                shift 2
                ;;
            -s|--symbols)
                if [[ -z "${2:-}" ]]; then
                    log_error "Missing argument for --symbols"
                    exit 2
                fi
                SYMBOL_PATH="$2"
                shift 2
                ;;
            -o|--output)
                if [[ -z "${2:-}" ]]; then
                    log_error "Missing argument for --output"
                    exit 2
                fi
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -d|--debugger)
                if [[ -z "${2:-}" ]]; then
                    log_error "Missing argument for --debugger"
                    exit 2
                fi
                DEBUGGER="$2"
                shift 2
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 2
                ;;
            *)
                if [[ -z "$CORE_PATH" ]]; then
                    CORE_PATH="$1"
                else
                    log_error "Unexpected argument: $1"
                    exit 2
                fi
                shift
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$CORE_PATH" ]]; then
        log_error "Core dump file required"
        usage
        exit 2
    fi

    if [[ ! -f "$CORE_PATH" ]]; then
        log_error "Core dump file not found: $CORE_PATH"
        exit 3
    fi

    # Detect debugger if not specified
    if [[ -z "$DEBUGGER" ]]; then
        DEBUGGER=$(detect_debugger) || {
            log_error "No debugger found"
            exit 5
        }
        log_info "Auto-detected debugger: $DEBUGGER"
    fi

    # Detect binary if not specified
    if [[ -z "$BINARY_PATH" ]]; then
        BINARY_PATH=$(detect_binary_from_core "$CORE_PATH") || {
            log_error "Could not detect binary from core dump. Please specify with --binary"
            exit 4
        }
        log_info "Auto-detected binary: $BINARY_PATH"
    fi

    if [[ ! -f "$BINARY_PATH" ]]; then
        log_error "Binary file not found: $BINARY_PATH"
        exit 4
    fi
}

#------------------------------------------------------------------------------
# Main Entry Point
#------------------------------------------------------------------------------

main() {
    # Create temporary directory
    TEMP_DIR=$(mktemp -d -t "coredump_analysis.XXXXXX")
    log_info "Created temporary directory: $TEMP_DIR"

    # Parse arguments
    parse_arguments "$@"

    # Perform analysis
    perform_analysis "$BINARY_PATH" "$CORE_PATH" "$SYMBOL_PATH"

    log_success "Analysis complete"
}

# Run main function
main "$@"
