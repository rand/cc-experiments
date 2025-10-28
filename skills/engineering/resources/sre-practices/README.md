# SRE Practices - Level 3 Resources

Comprehensive resources for Site Reliability Engineering practices, including SLOs, error budgets, toil reduction, incident management, and chaos engineering.

## Contents

### REFERENCE.md (3,705 lines)

Comprehensive reference covering:
- SRE fundamentals and principles
- Service Level Objectives (SLO) design
- Error budget management
- Toil reduction strategies
- Monitoring and observability
- Incident management
- Change management (progressive rollouts)
- Capacity planning
- On-call practices
- Chaos engineering
- Automation strategies
- Performance engineering
- Reliability patterns
- Documentation and runbooks
- Team organization

### Scripts (3 executable tools)

#### 1. calculate_slo_budget.py (891 lines)
Calculate and analyze SLO error budgets with burn rate tracking.

Features:
- Time-based and request-based budget calculation
- Latency budget analysis
- Multi-window burn rate calculation
- Budget exhaustion prediction
- Multi-SLI composite budgets
- Alert threshold recommendations

Usage:
```bash
# Calculate basic error budget
./calculate_slo_budget.py --slo 99.9 --window 30

# Calculate with current availability
./calculate_slo_budget.py --slo 99.95 --window 30 --current-availability 99.85

# Calculate burn rate
./calculate_slo_budget.py --calculate-burn-rate \
  --current-consumption 0.15 \
  --elapsed-hours 360 \
  --window-hours 720

# Predict exhaustion
./calculate_slo_budget.py --predict-exhaustion \
  --consumption 0.35 \
  --elapsed-hours 360 \
  --window-hours 720

# Load from config
./calculate_slo_budget.py --config slo-config.yaml --json
```

#### 2. analyze_toil.py (838 lines)
Identify and analyze toil, calculate automation ROI, and track reduction.

Features:
- Toil percentage calculation
- Toil categorization (deployment, remediation, scaling, etc.)
- Automation candidate identification
- ROI calculation (payback period, 3-year ROI)
- Toil trend tracking over time
- Sample data generation for testing

Usage:
```bash
# Analyze toil from logs
./analyze_toil.py --work-logs work.jsonl --analyze --days 30

# Find automation candidates
./analyze_toil.py --work-logs work.jsonl --automation-candidates --top 10

# Calculate ROI for specific task
./analyze_toil.py --calculate-roi \
  --task "Manual deployments" \
  --frequency 50 \
  --duration 0.5 \
  --effort 40

# Track toil trend
./analyze_toil.py --work-logs work.jsonl --track-toil --period 7 --json

# Generate sample data
./analyze_toil.py --generate-sample --output work.jsonl
```

#### 3. test_resilience.py (895 lines)
Chaos engineering experiments to validate system resilience.

Features:
- Predefined chaos experiments (network, latency, CPU, memory, etc.)
- Circuit breaker testing
- Graceful degradation validation
- Steady-state hypothesis validation
- Automatic rollback on failure
- Multi-phase experiment execution

Usage:
```bash
# List available experiments
./test_resilience.py --list-experiments

# Run network partition test
./test_resilience.py --experiment network-partition --target api --duration 300

# Test circuit breaker
./test_resilience.py --test-circuit-breaker --service api --dependency auth

# Test graceful degradation
./test_resilience.py --test-degradation --service api --dependency cache

# Dry run (no actual chaos)
./test_resilience.py --experiment pod-failure --dry-run
```

### Examples (9 production-ready files)

#### 1. slo-definition.yaml
Complete SLO definition with error budget policy, multi-window monitoring, and dependency SLOs.

#### 2. error-budget-policy.md
Comprehensive error budget policy with 4 consumption zones, consequences, and attribution tracking.

#### 3. chaos-scenario.py
Full chaos engineering scenario testing dependency failure with circuit breaker validation.

#### 4. toil-tracking-dashboard.json
Grafana dashboard for tracking toil percentage, categories, and automation ROI.

#### 5. blameless-postmortem.md
Production incident postmortem following blameless culture principles with detailed timeline and action items.

#### 6. on-call-runbook.md
Quick reference runbook for on-call engineers with common alerts and troubleshooting steps.

#### 7. prometheus-sli-queries.promql
Collection of Prometheus queries for SLI measurement, error budget calculation, and burn rate alerts.

#### 8. grafana-slo-dashboard.json
Grafana dashboard configuration for SLO monitoring with availability, error budget, and burn rate panels.

#### 9. capacity-planning.csv
Capacity planning tracking spreadsheet with resource utilization and headroom calculations.

## Quality Standards

All resources meet the following criteria:
- ✅ No TODO, stub, or mock comments
- ✅ Production-ready code with proper error handling
- ✅ Comprehensive docstrings and type hints
- ✅ Scripts include --help and --json support
- ✅ All scripts are executable with proper shebang
- ✅ Examples are based on real-world practices

## Dependencies

Scripts require Python 3.8+ with the following packages:
```bash
pip install pyyaml  # For YAML config support (optional)
```

Core functionality works with Python standard library only.

## Usage Patterns

### SLO Monitoring Workflow
1. Define SLOs in `slo-definition.yaml`
2. Deploy Prometheus queries from `prometheus-sli-queries.promql`
3. Create Grafana dashboard using `grafana-slo-dashboard.json`
4. Calculate budgets with `calculate_slo_budget.py`
5. Track burn rate and set up alerts
6. Follow error budget policy when thresholds exceeded

### Toil Reduction Workflow
1. Log work activities in JSONL format
2. Analyze with `analyze_toil.py --analyze`
3. Identify automation candidates
4. Calculate ROI for top candidates
5. Prioritize based on payback period
6. Track progress with toil dashboard
7. Measure reduction over time

### Chaos Engineering Workflow
1. Define steady-state hypotheses
2. Start with low blast radius (10%)
3. Run experiments with `test_resilience.py`
4. Validate circuit breakers and fallbacks
5. Increase blast radius gradually
6. Automate experiments in CI/CD
7. Track resilience improvements

## Integration Examples

### CI/CD Integration
```yaml
# .github/workflows/slo-check.yml
name: SLO Budget Check
on: [pull_request]
jobs:
  slo-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: |
          python scripts/calculate_slo_budget.py \
            --config slo-config.yaml \
            --json > budget.json
      - run: |
          CONSUMPTION=$(jq '.consumption_percent' budget.json)
          if (( $(echo "$CONSUMPTION > 75" | bc -l) )); then
            echo "ERROR: Error budget > 75% consumed"
            exit 1
          fi
```

### Automated Chaos Testing
```yaml
# Run chaos experiments nightly
schedule:
  - cron: '0 2 * * *'  # 2 AM daily
jobs:
  chaos:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python scripts/test_resilience.py \
            --experiment dependency-failure \
            --target production \
            --json > results.json
```

### Toil Tracking Dashboard
```yaml
# Export toil data to Prometheus
metrics:
  - name: work_hours_total
    type: counter
    labels: [type, category, engineer, automatable]
```

## References

- Google SRE Book: https://sre.google/sre-book/table-of-contents/
- SLO Workshop: https://sre.google/workbook/table-of-contents/
- Multi-window burn rate alerting: https://sre.google/workbook/alerting-on-slos/
- Chaos Engineering Principles: https://principlesofchaos.org/

## License

These resources are provided as educational materials for SRE best practices.

## Maintainer

SRE Team - For questions or improvements, open an issue or pull request.
