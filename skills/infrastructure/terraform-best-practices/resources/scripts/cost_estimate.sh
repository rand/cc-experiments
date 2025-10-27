#!/usr/bin/env bash
#
# Terraform Cost Estimator
#
# Estimates infrastructure costs from Terraform plan using Infracost or manual estimation.
# Provides cost breakdown by resource type and environment comparison.
#
# Usage:
#     ./cost_estimate.sh [OPTIONS]
#
# Examples:
#     ./cost_estimate.sh
#     ./cost_estimate.sh --json
#     ./cost_estimate.sh --format table --output costs.txt
#     ./cost_estimate.sh --compare-with production.json
#     ./cost_estimate.sh --budget 1000 --alert-threshold 80
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
OUTPUT_FORMAT="table"
OUTPUT_FILE=""
JSON_OUTPUT=false
COMPARE_FILE=""
BUDGET=0
ALERT_THRESHOLD=80
PLAN_FILE=""
USE_INFRACOST=true
CURRENCY="USD"

# Function to print usage
usage() {
    cat << EOF
Terraform Cost Estimator

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -j, --json              Output in JSON format
    -f, --format FORMAT     Output format: table, json, csv (default: table)
    -o, --output FILE       Write output to file
    -p, --plan FILE         Terraform plan file (default: generate new plan)
    -c, --compare FILE      Compare with previous cost estimate
    -b, --budget AMOUNT     Set budget limit for alerts
    -t, --threshold PCT     Alert threshold percentage (default: 80)
    --no-infracost          Use manual estimation instead of Infracost
    --currency CURRENCY     Currency code (default: USD)

Examples:
    $0
    $0 --json --output costs.json
    $0 --compare production-costs.json --budget 5000
    $0 --format csv --output monthly-costs.csv

Requirements:
    - terraform
    - jq
    - infracost (optional but recommended)
EOF
    exit 0
}

# Function to check dependencies
check_dependencies() {
    local deps=("terraform" "jq")

    if [ "$USE_INFRACOST" = true ]; then
        deps+=("infracost")
    fi

    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo -e "${RED}Error: $cmd is not installed${NC}" >&2
            if [ "$cmd" = "infracost" ]; then
                echo "Install from: https://www.infracost.io/docs/" >&2
                echo "Or use --no-infracost for manual estimation" >&2
            fi
            exit 1
        fi
    done
}

# Function to generate terraform plan
generate_plan() {
    echo -e "${BLUE}Generating Terraform plan...${NC}"

    if [ -z "$PLAN_FILE" ]; then
        PLAN_FILE="tfplan-$(date +%s)"
        terraform plan -out="$PLAN_FILE" > /dev/null 2>&1
    fi

    if [ ! -f "$PLAN_FILE" ]; then
        echo -e "${RED}Error: Plan file not found${NC}" >&2
        exit 1
    fi

    echo -e "${GREEN}Plan generated: $PLAN_FILE${NC}"
}

# Function to estimate costs with Infracost
estimate_with_infracost() {
    echo -e "${BLUE}Estimating costs with Infracost...${NC}"

    # Generate plan JSON
    terraform show -json "$PLAN_FILE" > tfplan.json

    # Run Infracost
    infracost breakdown \
        --path tfplan.json \
        --format json \
        --out infracost.json \
        --currency "$CURRENCY"

    if [ ! -f infracost.json ]; then
        echo -e "${RED}Error: Infracost failed to generate estimate${NC}" >&2
        exit 1
    fi

    echo -e "${GREEN}Cost estimate generated${NC}"
}

# Function to manually estimate costs (fallback)
estimate_manually() {
    echo -e "${YELLOW}Using manual cost estimation (less accurate)${NC}"

    terraform show -json "$PLAN_FILE" > tfplan.json

    # Create manual estimate JSON
    cat > infracost.json << 'EOF'
{
  "version": "0.2",
  "currency": "USD",
  "projects": [{
    "name": "manual-estimate",
    "metadata": {
      "path": ".",
      "type": "terraform_plan_json"
    },
    "pastBreakdown": {
      "resources": [],
      "totalHourlyCost": "0",
      "totalMonthlyCost": "0"
    },
    "breakdown": {
      "resources": [],
      "totalHourlyCost": "0",
      "totalMonthlyCost": "0"
    },
    "diff": {
      "resources": [],
      "totalHourlyCost": "0",
      "totalMonthlyCost": "0"
    }
  }],
  "totalHourlyCost": "0",
  "totalMonthlyCost": "0",
  "pastTotalHourlyCost": "0",
  "pastTotalMonthlyCost": "0",
  "diffTotalHourlyCost": "0",
  "diffTotalMonthlyCost": "0",
  "timeGenerated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "summary": {
    "totalDetectedResources": 0,
    "totalSupportedResources": 0,
    "totalUnsupportedResources": 0,
    "totalUsageBasedResources": 0,
    "totalNoPriceResources": 0
  }
}
EOF

    # Parse resources from plan
    local total_monthly=0
    local resources=()

    # Basic AWS pricing (very rough estimates)
    declare -A pricing
    pricing["aws_instance.t3.micro"]="7.50"
    pricing["aws_instance.t3.small"]="15.00"
    pricing["aws_instance.t3.medium"]="30.00"
    pricing["aws_instance.t3.large"]="60.00"
    pricing["aws_db_instance.db.t3.micro"]="15.00"
    pricing["aws_db_instance.db.t3.small"]="30.00"
    pricing["aws_db_instance.db.t3.medium"]="60.00"
    pricing["aws_s3_bucket"]="1.00"
    pricing["aws_lb"]="16.00"
    pricing["aws_nat_gateway"]="32.00"

    # Extract resource changes
    while IFS= read -r resource; do
        local type=$(echo "$resource" | jq -r '.type')
        local name=$(echo "$resource" | jq -r '.name')
        local instance_type=$(echo "$resource" | jq -r '.change.after.instance_type // empty')

        local cost=0
        local key="${type}"
        if [ -n "$instance_type" ]; then
            key="${type}.${instance_type}"
        fi

        cost=${pricing[$key]:-5.00}  # Default $5/month for unknown resources
        total_monthly=$(echo "$total_monthly + $cost" | bc)

        resources+=("{\"name\":\"$name\",\"type\":\"$type\",\"monthlyCost\":\"$cost\"}")
    done < <(jq -c '.resource_changes[]? | select(.change.actions[] | contains("create") or contains("update"))' tfplan.json)

    # Update estimate JSON
    jq --arg monthly "$total_monthly" \
       --arg resources "$(printf '%s,' "${resources[@]}" | sed 's/,$//')" \
       '.totalMonthlyCost = $monthly | .diffTotalMonthlyCost = $monthly' \
       infracost.json > infracost.tmp.json && mv infracost.tmp.json infracost.json

    echo -e "${YELLOW}Warning: Manual estimation is rough and may not be accurate${NC}"
    echo -e "${YELLOW}Install Infracost for accurate cost estimates${NC}"
}

# Function to format output as table
format_table() {
    local monthly_cost=$(jq -r '.totalMonthlyCost' infracost.json)
    local monthly_diff=$(jq -r '.diffTotalMonthlyCost // "0"' infracost.json)
    local hourly_cost=$(jq -r '.totalHourlyCost' infracost.json)

    echo ""
    echo "=========================================="
    echo "  TERRAFORM COST ESTIMATE"
    echo "=========================================="
    echo ""
    echo "Currency: $CURRENCY"
    echo "Generated: $(date)"
    echo ""
    echo "Total Monthly Cost: \$$monthly_cost"
    echo "Total Hourly Cost:  \$$hourly_cost"

    if [ "$monthly_diff" != "0" ]; then
        if (( $(echo "$monthly_diff > 0" | bc -l) )); then
            echo -e "Monthly Change:     ${RED}+\$$monthly_diff${NC}"
        else
            echo -e "Monthly Change:     ${GREEN}\$$monthly_diff${NC}"
        fi
    fi

    echo ""
    echo "=========================================="
    echo "  COST BREAKDOWN BY RESOURCE"
    echo "=========================================="
    echo ""

    # Resources
    jq -r '.projects[0].breakdown.resources[]? |
           "\(.name)\t\(.resourceType)\t$\(.monthlyCost // "0")"' infracost.json |
        column -t -s $'\t' -N "Resource,Type,Monthly Cost"

    echo ""

    # Summary
    local detected=$(jq -r '.summary.totalDetectedResources // 0' infracost.json)
    local supported=$(jq -r '.summary.totalSupportedResources // 0' infracost.json)
    local unsupported=$(jq -r '.summary.totalUnsupportedResources // 0' infracost.json)

    echo "Summary:"
    echo "  Detected Resources:    $detected"
    echo "  Supported Resources:   $supported"
    echo "  Unsupported Resources: $unsupported"

    # Budget check
    if [ "$BUDGET" -gt 0 ]; then
        local threshold_amount=$(echo "$BUDGET * $ALERT_THRESHOLD / 100" | bc)
        local monthly_int=$(echo "$monthly_cost" | cut -d. -f1)

        echo ""
        echo "Budget Analysis:"
        echo "  Budget Limit:     \$$BUDGET"
        echo "  Alert Threshold:  $ALERT_THRESHOLD% (\$$threshold_amount)"
        echo "  Current Cost:     \$$monthly_cost"

        if [ "$monthly_int" -gt "$BUDGET" ]; then
            echo -e "  Status:           ${RED}OVER BUDGET${NC}"
        elif [ "$monthly_int" -gt "$threshold_amount" ]; then
            echo -e "  Status:           ${YELLOW}WARNING - Near threshold${NC}"
        else
            echo -e "  Status:           ${GREEN}Within budget${NC}"
        fi
    fi

    echo ""
}

# Function to format output as CSV
format_csv() {
    echo "Resource,Type,Monthly Cost,Hourly Cost"
    jq -r '.projects[0].breakdown.resources[]? |
           "\(.name),\(.resourceType),\(.monthlyCost // "0"),\(.hourlyCost // "0")"' \
           infracost.json
    echo ""
    echo "Total,,$( jq -r '.totalMonthlyCost' infracost.json),$( jq -r '.totalHourlyCost' infracost.json)"
}

# Function to compare with previous estimate
compare_estimates() {
    if [ ! -f "$COMPARE_FILE" ]; then
        echo -e "${RED}Error: Comparison file not found: $COMPARE_FILE${NC}" >&2
        return 1
    fi

    local prev_cost=$(jq -r '.totalMonthlyCost' "$COMPARE_FILE")
    local curr_cost=$(jq -r '.totalMonthlyCost' infracost.json)
    local diff=$(echo "$curr_cost - $prev_cost" | bc)
    local pct_change=$(echo "scale=2; ($diff / $prev_cost) * 100" | bc)

    echo ""
    echo "=========================================="
    echo "  COST COMPARISON"
    echo "=========================================="
    echo ""
    echo "Previous Monthly Cost: \$$prev_cost"
    echo "Current Monthly Cost:  \$$curr_cost"

    if (( $(echo "$diff > 0" | bc -l) )); then
        echo -e "Change:                ${RED}+\$$diff (+${pct_change}%)${NC}"
    elif (( $(echo "$diff < 0" | bc -l) )); then
        echo -e "Change:                ${GREEN}\$$diff (${pct_change}%)${NC}"
    else
        echo "Change:                \$0.00 (0%)"
    fi
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -j|--json)
            JSON_OUTPUT=true
            OUTPUT_FORMAT="json"
            shift
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -p|--plan)
            PLAN_FILE="$2"
            shift 2
            ;;
        -c|--compare)
            COMPARE_FILE="$2"
            shift 2
            ;;
        -b|--budget)
            BUDGET="$2"
            shift 2
            ;;
        -t|--threshold)
            ALERT_THRESHOLD="$2"
            shift 2
            ;;
        --no-infracost)
            USE_INFRACOST=false
            shift
            ;;
        --currency)
            CURRENCY="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage
            ;;
    esac
done

# Main execution
main() {
    check_dependencies
    generate_plan

    if [ "$USE_INFRACOST" = true ]; then
        estimate_with_infracost
    else
        estimate_manually
    fi

    # Generate output
    local output=""

    case "$OUTPUT_FORMAT" in
        json)
            output=$(cat infracost.json)
            ;;
        csv)
            output=$(format_csv)
            ;;
        table|*)
            output=$(format_table)

            if [ -n "$COMPARE_FILE" ]; then
                output="$output$(echo)$(compare_estimates)"
            fi
            ;;
    esac

    # Write to file or stdout
    if [ -n "$OUTPUT_FILE" ]; then
        echo "$output" > "$OUTPUT_FILE"
        echo -e "${GREEN}Cost estimate written to $OUTPUT_FILE${NC}"
    else
        echo "$output"
    fi

    # Cleanup temp files
    rm -f tfplan.json

    # Exit code based on budget
    if [ "$BUDGET" -gt 0 ]; then
        local monthly_cost=$(jq -r '.totalMonthlyCost' infracost.json | cut -d. -f1)
        if [ "$monthly_cost" -gt "$BUDGET" ]; then
            exit 2
        fi
    fi

    exit 0
}

# Run main
main
