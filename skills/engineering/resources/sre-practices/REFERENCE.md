# SRE Practices Reference

Comprehensive reference for Site Reliability Engineering practices, covering reliability principles, error budgets, toil reduction, incident management, observability, and operational excellence.

## Table of Contents

1. [SRE Fundamentals](#sre-fundamentals)
2. [Service Level Objectives](#service-level-objectives)
3. [Error Budgets](#error-budgets)
4. [Toil Reduction](#toil-reduction)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Incident Management](#incident-management)
7. [Change Management](#change-management)
8. [Capacity Planning](#capacity-planning)
9. [On-Call Practices](#on-call-practices)
10. [Chaos Engineering](#chaos-engineering)
11. [Automation Strategies](#automation-strategies)
12. [Performance Engineering](#performance-engineering)
13. [Reliability Patterns](#reliability-patterns)
14. [Documentation and Runbooks](#documentation-and-runbooks)
15. [Team Organization](#team-organization)

---

## SRE Fundamentals

### Core Principles

**1. Embrace Risk**
```yaml
risk_management:
  principle: "100% reliability is wrong target"
  approach:
    - identify_acceptable_risk: "Based on user expectations"
    - balance_reliability_velocity: "Trade-offs explicit"
    - quantify_risk: "Error budgets make risk concrete"
    - iterate_safely: "Progressive rollouts"

  risk_levels:
    critical_service:
      target_availability: "99.99%"
      allowed_downtime: "52.56 minutes/year"
      rationale: "Revenue-critical, high visibility"

    standard_service:
      target_availability: "99.9%"
      allowed_downtime: "8.76 hours/year"
      rationale: "Important but not critical"

    experimental_service:
      target_availability: "99%"
      allowed_downtime: "3.65 days/year"
      rationale: "New feature, learning phase"
```

**2. Service Level Indicators (SLIs)**
```yaml
sli_design:
  definition: "Quantitative measure of service level"

  characteristics:
    - measurable: "Objective, not subjective"
    - meaningful: "Reflects user experience"
    - actionable: "Can be improved"
    - timely: "Real-time or near-real-time"

  common_slis:
    availability:
      formula: "successful_requests / total_requests"
      measurement: "HTTP 200-299, 400-499 vs 500-599"
      window: "Rolling 30 days"

    latency:
      formula: "requests_below_threshold / total_requests"
      percentiles: [50, 90, 95, 99]
      threshold: "500ms for p95"

    throughput:
      formula: "requests_processed / time_window"
      measurement: "Requests per second"
      capacity: "Compare to baseline"

    correctness:
      formula: "correct_responses / total_responses"
      validation: "Check data integrity"
      sampling: "May need sampling for performance"

    freshness:
      formula: "records_within_age / total_records"
      threshold: "Data < 5 minutes old"
      use_case: "Real-time pipelines"
```

**3. Service Level Objectives (SLOs)**
```yaml
slo_structure:
  definition: "Target value or range for SLI"

  components:
    indicator: "Which SLI to measure"
    target: "Desired performance level"
    window: "Time period for evaluation"
    consequences: "What happens if missed"

  examples:
    api_availability:
      sli: "HTTP success rate"
      target: "99.9%"
      window: "30 days rolling"
      measurement: "status < 500 / total"

    api_latency:
      sli: "p95 response time"
      target: "< 200ms"
      window: "30 days rolling"
      measurement: "95th percentile latency"

    data_freshness:
      sli: "Records processed within SLA"
      target: "99.5%"
      window: "24 hours"
      measurement: "age < 5min / total"
```

**4. Service Level Agreements (SLAs)**
```yaml
sla_structure:
  definition: "Business agreement with consequences"

  relationship_to_slo:
    rule: "SLO must be stricter than SLA"
    buffer: "Typically 1-2 nines stricter"
    example:
      sla: "99.9% uptime"
      slo: "99.95% uptime"
      buffer: "0.05% = 21.6 minutes/month"

  consequences:
    financial:
      - credits: "% of monthly bill"
      - refunds: "Full or partial"
      - penalties: "Contractual penalties"

    operational:
      - escalation: "Executive involvement"
      - postmortem: "Required analysis"
      - remediation: "Mandatory fixes"

    reputational:
      - communication: "Customer notification"
      - transparency: "Public status page"
      - trust: "Long-term impact"
```

### SRE vs Traditional Ops

```yaml
comparison:
  staffing:
    traditional_ops:
      model: "Manual scaling with headcount"
      ratio: "~1000:1 (servers:admins)"
      scaling: "Linear cost increase"

    sre:
      model: "Automation-first approach"
      ratio: "Software engineering team"
      scaling: "Sublinear through code"

  availability:
    traditional_ops:
      approach: "Maximize uptime at all costs"
      change_control: "Heavy gates, slow deploys"
      incidents: "Hero culture"

    sre:
      approach: "Balance reliability and velocity"
      change_control: "Progressive rollouts"
      incidents: "Systematic learning"

  work_allocation:
    traditional_ops:
      reactive: "60-80% time on tickets"
      proactive: "20-40% on projects"
      toil: "Undefined, untracked"

    sre:
      reactive: "< 50% time on toil"
      proactive: "> 50% on engineering"
      toil: "Measured, reduced systematically"
```

---

## Service Level Objectives

### SLO Design Process

**1. Identify User Journeys**
```python
# User journey mapping
user_journeys = {
    "search_product": {
        "steps": [
            {"action": "load_homepage", "latency_target": "500ms"},
            {"action": "search_query", "latency_target": "300ms"},
            {"action": "view_results", "latency_target": "200ms"},
        ],
        "success_criteria": "All steps complete",
        "total_budget": "1000ms",
    },

    "checkout": {
        "steps": [
            {"action": "add_to_cart", "latency_target": "200ms"},
            {"action": "view_cart", "latency_target": "300ms"},
            {"action": "enter_payment", "latency_target": "500ms"},
            {"action": "submit_order", "latency_target": "1000ms"},
        ],
        "success_criteria": "Order confirmed",
        "total_budget": "2000ms",
    },
}

# Calculate composite SLO
def calculate_composite_slo(journey, step_slos):
    """
    Composite SLO for multi-step journey.

    If each step has 99.9% SLO:
    Total journey = 0.999^4 = 99.6%
    """
    composite = 1.0
    for step in journey["steps"]:
        step_slo = step_slos.get(step["action"], 0.999)
        composite *= step_slo
    return composite
```

**2. Choose Appropriate SLIs**
```yaml
sli_selection_guide:
  request_response:
    primary:
      - availability: "Success rate"
      - latency: "Response time"
    secondary:
      - throughput: "Requests/second"
      - quality: "Error types"

  data_processing:
    primary:
      - freshness: "Data age"
      - coverage: "% data processed"
    secondary:
      - accuracy: "Data quality"
      - throughput: "Records/second"

  storage:
    primary:
      - durability: "Data loss rate"
      - availability: "Read/write success"
    secondary:
      - consistency: "Replication lag"
      - latency: "Operation time"
```

**3. Set Initial Targets**
```yaml
target_setting:
  data_driven_approach:
    step1: "Measure current performance"
    step2: "Analyze historical data (90 days)"
    step3: "Identify baseline performance"
    step4: "Set aspirational target"
    step5: "Validate with stakeholders"

  starting_points:
    high_reliability:
      availability: "99.95%"
      latency_p95: "100ms"
      latency_p99: "500ms"

    standard_reliability:
      availability: "99.9%"
      latency_p95: "200ms"
      latency_p99: "1000ms"

    experimental:
      availability: "99%"
      latency_p95: "1000ms"
      latency_p99: "5000ms"

  avoid:
    - "Arbitrary numbers (99.99% because it sounds good)"
    - "Matching competitors without analysis"
    - "Setting targets you can't measure"
    - "Promises without cost analysis"
```

**4. Define Measurement Windows**
```yaml
window_strategies:
  rolling_window:
    description: "Continuous sliding window"
    duration: "30 days (typical)"
    advantages:
      - smooth_trends: "No cliff edges"
      - recent_focus: "Emphasizes current state"
    disadvantages:
      - complex_calculation: "More processing"
      - slower_recovery: "Past incidents linger"

    implementation: |
      SELECT
        COUNT(*) FILTER (WHERE status < 500) / COUNT(*) as success_rate
      FROM requests
      WHERE timestamp > NOW() - INTERVAL '30 days'

  calendar_window:
    description: "Fixed periods (month, quarter)"
    duration: "1 month (typical)"
    advantages:
      - simple_calculation: "Clear boundaries"
      - fast_reset: "Fresh start each period"
    disadvantages:
      - cliff_edges: "Sudden resets"
      - gaming: "End-of-period behavior"

    implementation: |
      SELECT
        COUNT(*) FILTER (WHERE status < 500) / COUNT(*) as success_rate
      FROM requests
      WHERE timestamp >= DATE_TRUNC('month', NOW())

  request_based:
    description: "Per N requests instead of time"
    duration: "Last 1M requests"
    advantages:
      - traffic_proportional: "Fair for variable load"
      - deterministic: "Not time-dependent"
    disadvantages:
      - complex_tracking: "Need request counter"
      - low_traffic_issues: "Long windows for quiet services"
```

### Multi-Window SLOs

```python
# Multi-window SLO specification
multi_window_slo = {
    "service": "api",
    "sli": "availability",

    "windows": [
        {
            "duration": "5m",
            "target": 0.99,
            "alert": "page",
            "rationale": "Detect outages quickly",
        },
        {
            "duration": "1h",
            "target": 0.995,
            "alert": "ticket",
            "rationale": "Short-term reliability",
        },
        {
            "duration": "30d",
            "target": 0.999,
            "alert": "report",
            "rationale": "Long-term commitment",
        },
    ],

    "burn_rate": {
        "fast_burn": {
            "window": "1h",
            "threshold": "14.4x",  # Burn 5% budget in 1 hour
            "alert": "page",
        },
        "slow_burn": {
            "window": "6h",
            "threshold": "6x",     # Burn 5% budget in 6 hours
            "alert": "ticket",
        },
    },
}

# Implementation
def check_multi_window_slo(slo_config, metrics):
    """Check SLO across multiple windows."""
    results = {}

    for window in slo_config["windows"]:
        duration = window["duration"]
        target = window["target"]

        # Calculate current performance
        current = calculate_slo_for_window(metrics, duration)

        # Compare to target
        met = current >= target
        budget_remaining = (current - target) / (1 - target)

        results[duration] = {
            "current": current,
            "target": target,
            "met": met,
            "budget_remaining": budget_remaining,
            "alert_level": window["alert"] if not met else "none",
        }

    return results
```

### SLO Documentation Template

```yaml
slo_document:
  metadata:
    service: "payment-api"
    owner: "payments-team"
    version: "2.0"
    last_updated: "2025-10-15"
    review_frequency: "Quarterly"

  objectives:
    - name: "API Availability"
      sli:
        metric: "HTTP success rate"
        definition: "status_code < 500"
        exclusions:
          - "4xx client errors"
          - "Rate limit 429s"
      target: "99.95%"
      window: "30 days rolling"
      rationale: "Critical payment path"

    - name: "API Latency (p95)"
      sli:
        metric: "Response time 95th percentile"
        definition: "Time from request to response"
        exclusions:
          - "Client-side timeouts"
          - "Retries"
      target: "< 300ms"
      window: "30 days rolling"
      rationale: "User experience threshold"

    - name: "Transaction Correctness"
      sli:
        metric: "Transaction integrity rate"
        definition: "Successful vs failed settlements"
        exclusions:
          - "Declined transactions"
          - "Fraud blocks"
      target: "99.99%"
      window: "30 days rolling"
      rationale: "Financial accuracy critical"

  error_budget_policy:
    current_budget: "0.05% = 21.6 minutes/month"

    consumption_50:
      action: "Continue normal operations"
      cadence: "Standard releases"

    consumption_75:
      action: "Freeze non-critical changes"
      notification: "Team and management"
      focus: "Reliability improvements"

    consumption_90:
      action: "Feature freeze"
      notification: "Executive escalation"
      requirements: "Postmortem and remediation plan"

    consumption_100:
      action: "Full freeze, incident mode"
      notification: "All stakeholders"
      requirements: "Emergency response, SLA breach protocol"

  measurement:
    data_source: "Prometheus"
    queries:
      availability: |
        sum(rate(http_requests_total{status!~"5.."}[30d]))
        /
        sum(rate(http_requests_total[30d]))

      latency: |
        histogram_quantile(0.95,
          rate(http_request_duration_seconds_bucket[30d])
        )

    dashboard: "https://grafana.example.com/d/payment-api-slo"
    alerting: "PagerDuty: payment-api-team"

  dependencies:
    - service: "auth-service"
      slo_dependency: "99.99%"
      impact: "Direct availability impact"

    - service: "database"
      slo_dependency: "99.95%"
      impact: "Latency and availability"

  review_schedule:
    quarterly_review:
      participants: ["SRE", "Engineering", "Product"]
      agenda:
        - "Review SLO achievement"
        - "Assess appropriateness"
        - "Update targets if needed"
        - "Review error budget policy"
```

---

## Error Budgets

### Error Budget Fundamentals

```yaml
error_budget_concept:
  definition: "Amount of unreliability permitted"

  calculation:
    formula: "1 - SLO"
    example:
      slo: "99.9%"
      error_budget: "0.1%"
      monthly_downtime: "43.2 minutes"

  purpose:
    - balance_velocity_reliability: "Explicit trade-offs"
    - quantify_risk: "Make risk concrete"
    - align_incentives: "Shared responsibility"
    - enable_innovation: "Safe to experiment"
```

**Error Budget Policies**

```yaml
budget_policy:
  zones:
    healthy:
      threshold: "< 25% consumed"
      actions:
        - "Normal velocity"
        - "Experiment freely"
        - "Take calculated risks"
      meeting_frequency: "Monthly review"

    concerning:
      threshold: "25-50% consumed"
      actions:
        - "Increased monitoring"
        - "Risk assessment for changes"
        - "Defer non-critical features"
      meeting_frequency: "Bi-weekly review"

    critical:
      threshold: "50-75% consumed"
      actions:
        - "Reliability focus"
        - "Freeze low-priority features"
        - "Mandatory postmortems"
      meeting_frequency: "Weekly review"

    exhausted:
      threshold: "> 75% consumed"
      actions:
        - "Feature freeze"
        - "Emergency response"
        - "Executive escalation"
      meeting_frequency: "Daily standup"

  consequences:
    development:
      healthy: "Normal sprint planning"
      concerning: "Add reliability tasks"
      critical: "50% sprint on reliability"
      exhausted: "100% focus on reliability"

    releases:
      healthy: "Continuous deployment"
      concerning: "Staged rollouts"
      critical: "Manual approval required"
      exhausted: "Emergency fixes only"
```

### Error Budget Calculation Methods

```python
# Basic error budget
def calculate_error_budget_basic(slo_target: float, window_days: int = 30):
    """
    Calculate error budget for time-based SLO.

    Args:
        slo_target: Target SLO (e.g., 0.999 for 99.9%)
        window_days: Window size in days

    Returns:
        Error budget in minutes
    """
    total_minutes = window_days * 24 * 60
    allowed_downtime = total_minutes * (1 - slo_target)
    return allowed_downtime


# Request-based error budget
def calculate_error_budget_requests(
    total_requests: int,
    failed_requests: int,
    slo_target: float
):
    """
    Calculate error budget for request-based SLO.

    Args:
        total_requests: Total requests in window
        failed_requests: Failed requests so far
        slo_target: Target success rate

    Returns:
        Error budget consumption percentage
    """
    allowed_failures = total_requests * (1 - slo_target)
    budget_consumed = failed_requests / allowed_failures
    return budget_consumed


# Multi-SLI error budget
def calculate_composite_error_budget(slis: dict):
    """
    Calculate error budget across multiple SLIs.

    Example:
        slis = {
            "availability": {"current": 0.9995, "target": 0.999, "weight": 0.6},
            "latency": {"current": 0.998, "target": 0.995, "target": 0.4},
        }
    """
    total_budget_consumed = 0

    for sli_name, sli_data in slis.items():
        current = sli_data["current"]
        target = sli_data["target"]
        weight = sli_data["weight"]

        # Calculate consumption for this SLI
        if current >= target:
            consumption = 0  # Within budget
        else:
            budget = 1 - target
            used = target - current
            consumption = used / budget

        # Weight the consumption
        total_budget_consumed += consumption * weight

    return min(total_budget_consumed, 1.0)  # Cap at 100%


# Burn rate calculation
def calculate_burn_rate(
    error_budget_consumed: float,
    time_elapsed: float,
    window_duration: float
):
    """
    Calculate current error budget burn rate.

    Args:
        error_budget_consumed: % of budget consumed (0-1)
        time_elapsed: Time elapsed in window (e.g., hours)
        window_duration: Total window duration (same units)

    Returns:
        Burn rate multiplier (1.0 = normal, > 1.0 = burning fast)
    """
    expected_consumption = time_elapsed / window_duration
    if expected_consumption == 0:
        return 0
    return error_budget_consumed / expected_consumption


# Predictive error budget
def predict_budget_exhaustion(
    current_consumption: float,
    time_elapsed_hours: float,
    window_hours: float
):
    """
    Predict when error budget will be exhausted.

    Returns:
        Hours until budget exhaustion (None if not exhausting)
    """
    if time_elapsed_hours == 0:
        return None

    burn_rate = current_consumption / time_elapsed_hours
    remaining_budget = 1.0 - current_consumption

    if burn_rate <= 0:
        return None  # Not consuming budget

    hours_until_exhaustion = remaining_budget / burn_rate

    if hours_until_exhaustion > window_hours:
        return None  # Won't exhaust in window

    return hours_until_exhaustion
```

### Error Budget Alerting

```yaml
alerting_rules:
  fast_burn:
    condition: "Burn rate > 14.4x"
    window: "1 hour"
    impact: "5% budget in 1 hour"
    action: "Page on-call"
    severity: "critical"

  medium_burn:
    condition: "Burn rate > 6x"
    window: "6 hours"
    impact: "5% budget in 6 hours"
    action: "Page on-call"
    severity: "warning"

  slow_burn:
    condition: "Burn rate > 3x"
    window: "24 hours"
    impact: "5% budget in 24 hours"
    action: "Create ticket"
    severity: "info"

  budget_threshold:
    condition: "Budget consumed > 75%"
    window: "any"
    action: "Escalate to management"
    severity: "warning"
```

**Prometheus Alerting Rules**

```yaml
# error-budget-alerts.yml
groups:
  - name: error_budget
    interval: 1m
    rules:
      # Fast burn: page immediately
      - alert: ErrorBudgetFastBurn
        expr: |
          (
            1 - (sum(rate(http_requests_total{status!~"5.."}[1h]))
                 / sum(rate(http_requests_total[1h])))
          ) / (1 - 0.999) > 14.4
        for: 2m
        labels:
          severity: critical
          component: slo
        annotations:
          summary: "Error budget burning at 14.4x rate"
          description: "At current rate, 5% budget will be consumed in 1 hour"
          runbook: "https://wiki/runbooks/error-budget-fast-burn"

      # Medium burn: page after confirmation
      - alert: ErrorBudgetMediumBurn
        expr: |
          (
            1 - (sum(rate(http_requests_total{status!~"5.."}[6h]))
                 / sum(rate(http_requests_total[6h])))
          ) / (1 - 0.999) > 6
        for: 15m
        labels:
          severity: warning
          component: slo
        annotations:
          summary: "Error budget burning at 6x rate"
          description: "At current rate, 5% budget will be consumed in 6 hours"

      # Budget threshold: escalate
      - alert: ErrorBudgetExhausted75Percent
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[30d]))
            / sum(rate(http_requests_total[30d]))
          ) / (1 - 0.999) > 0.75
        for: 5m
        labels:
          severity: warning
          component: slo
        annotations:
          summary: "75% of error budget consumed"
          description: "Implement error budget policy: feature freeze"
          dashboard: "https://grafana/error-budget"
```

### Error Budget Attribution

```python
# Attribute error budget consumption to causes
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta


@dataclass
class ErrorBudgetEvent:
    """Single error budget consumption event."""
    timestamp: datetime
    duration_minutes: float
    impact: float  # 0-1, fraction of total budget
    category: str
    subcategory: str
    incident_id: str
    description: str


class ErrorBudgetTracker:
    """Track and attribute error budget consumption."""

    def __init__(self, slo_target: float, window_days: int = 30):
        self.slo_target = slo_target
        self.window_days = window_days
        self.total_budget = window_days * 24 * 60 * (1 - slo_target)
        self.events: List[ErrorBudgetEvent] = []

    def add_event(self, event: ErrorBudgetEvent):
        """Add error budget consumption event."""
        self.events.append(event)

    def categorize_consumption(self) -> Dict[str, float]:
        """Categorize budget consumption by type."""
        categories = {}

        for event in self.events:
            if event.category not in categories:
                categories[event.category] = 0
            categories[event.category] += event.impact

        return categories

    def top_consumers(self, n: int = 5) -> List[ErrorBudgetEvent]:
        """Get top N error budget consumers."""
        return sorted(self.events, key=lambda e: e.impact, reverse=True)[:n]

    def consumption_by_subcategory(self) -> Dict[str, Dict[str, float]]:
        """Break down consumption by category and subcategory."""
        breakdown = {}

        for event in self.events:
            if event.category not in breakdown:
                breakdown[event.category] = {}

            if event.subcategory not in breakdown[event.category]:
                breakdown[event.category][event.subcategory] = 0

            breakdown[event.category][event.subcategory] += event.impact

        return breakdown

    def generate_report(self) -> dict:
        """Generate error budget consumption report."""
        total_consumed = sum(e.impact for e in self.events)

        return {
            "window": f"{self.window_days} days",
            "total_budget": f"{self.total_budget:.2f} minutes",
            "budget_consumed": f"{total_consumed * 100:.2f}%",
            "budget_remaining": f"{(1 - total_consumed) * 100:.2f}%",
            "event_count": len(self.events),
            "by_category": self.categorize_consumption(),
            "by_subcategory": self.consumption_by_subcategory(),
            "top_consumers": [
                {
                    "incident_id": e.incident_id,
                    "impact": f"{e.impact * 100:.2f}%",
                    "category": e.category,
                    "description": e.description,
                }
                for e in self.top_consumers()
            ],
        }


# Example usage
tracker = ErrorBudgetTracker(slo_target=0.999, window_days=30)

# Add events
tracker.add_event(ErrorBudgetEvent(
    timestamp=datetime.now() - timedelta(days=5),
    duration_minutes=45,
    impact=0.15,  # 15% of budget
    category="infrastructure",
    subcategory="database_outage",
    incident_id="INC-12345",
    description="Primary database failover",
))

tracker.add_event(ErrorBudgetEvent(
    timestamp=datetime.now() - timedelta(days=2),
    duration_minutes=10,
    impact=0.03,
    category="deployment",
    subcategory="bad_release",
    incident_id="INC-12350",
    description="Failed deployment rolled back",
))

# Generate report
report = tracker.generate_report()
```

---

## Toil Reduction

### Toil Definition and Measurement

```yaml
toil_definition:
  characteristics:
    manual: "Done by human, not automated"
    repetitive: "Same task repeatedly"
    automatable: "Could be automated"
    tactical: "Interrupt-driven, reactive"
    no_enduring_value: "Doesn't improve service"
    scales_linearly: "Grows with service/traffic"

  examples:
    clear_toil:
      - "Manually resetting failed batch jobs"
      - "Running deployment scripts by hand"
      - "Acknowledging recurring alerts"
      - "Manual database failovers"
      - "Copying files between servers"
      - "Restarting hung processes"

    not_toil:
      - "Incident response (unique each time)"
      - "Writing new automation (engineering)"
      - "Code reviews (value-adding)"
      - "Architecture design (strategic)"
      - "Capacity planning (enduring value)"

  target: "< 50% of SRE time on toil"
```

**Toil Measurement**

```python
from enum import Enum
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta


class WorkType(Enum):
    """Categories of work."""
    TOIL = "toil"
    ENGINEERING = "engineering"
    INCIDENT = "incident"
    MEETING = "meeting"
    ONCALL = "oncall"


@dataclass
class WorkLog:
    """Single work log entry."""
    date: datetime
    duration_hours: float
    work_type: WorkType
    description: str
    automatable: bool = False
    automated_yet: bool = False


class ToilTracker:
    """Track and analyze toil."""

    def __init__(self):
        self.work_logs: List[WorkLog] = []

    def add_work(self, log: WorkLog):
        """Add work log entry."""
        self.work_logs.append(log)

    def calculate_toil_percentage(self, days: int = 30) -> float:
        """Calculate % of time spent on toil."""
        cutoff = datetime.now() - timedelta(days=days)
        recent_logs = [l for l in self.work_logs if l.date >= cutoff]

        total_hours = sum(l.duration_hours for l in recent_logs)
        toil_hours = sum(
            l.duration_hours for l in recent_logs
            if l.work_type == WorkType.TOIL
        )

        if total_hours == 0:
            return 0
        return (toil_hours / total_hours) * 100

    def identify_automation_candidates(self) -> List[dict]:
        """Identify high-impact automation opportunities."""
        toil_logs = [l for l in self.work_logs if l.work_type == WorkType.TOIL]

        # Group by description
        task_frequency = {}
        for log in toil_logs:
            if log.description not in task_frequency:
                task_frequency[log.description] = {
                    "count": 0,
                    "total_hours": 0,
                    "automatable": log.automatable,
                    "automated": log.automated_yet,
                }
            task_frequency[log.description]["count"] += 1
            task_frequency[log.description]["total_hours"] += log.duration_hours

        # Calculate ROI
        candidates = []
        for task, stats in task_frequency.items():
            if stats["automatable"] and not stats["automated"]:
                # Assume 40 hours to automate, 12 month payback period
                monthly_hours = stats["total_hours"] / (len(self.work_logs) / 30)
                annual_hours = monthly_hours * 12
                automation_cost = 40  # hours
                payback_months = automation_cost / monthly_hours if monthly_hours > 0 else float('inf')

                candidates.append({
                    "task": task,
                    "occurrences": stats["count"],
                    "total_hours": stats["total_hours"],
                    "monthly_hours": monthly_hours,
                    "annual_hours": annual_hours,
                    "automation_cost_hours": automation_cost,
                    "payback_months": payback_months,
                    "roi": annual_hours / automation_cost if automation_cost > 0 else 0,
                })

        # Sort by ROI
        return sorted(candidates, key=lambda x: x["roi"], reverse=True)
```

### Toil Reduction Strategies

```yaml
automation_strategies:
  quick_wins:
    - category: "Script repetitive tasks"
      examples:
        - "Deployment scripts"
        - "Database queries"
        - "Log analysis"
      effort: "Low"
      impact: "Medium"

    - category: "Self-service tools"
      examples:
        - "Password resets"
        - "Feature flags"
        - "Environment provisioning"
      effort: "Medium"
      impact: "High"

  medium_term:
    - category: "Eliminate manual steps"
      examples:
        - "Automated deployments"
        - "Self-healing systems"
        - "Auto-scaling"
      effort: "Medium"
      impact: "High"

    - category: "Improve observability"
      examples:
        - "Better alerts (reduce noise)"
        - "Auto-remediation"
        - "Predictive alerts"
      effort: "Medium"
      impact: "Medium"

  long_term:
    - category: "Architectural improvements"
      examples:
        - "Stateless services"
        - "Chaos engineering"
        - "Zero-downtime deploys"
      effort: "High"
      impact: "Very High"

    - category: "Platform building"
      examples:
        - "Internal PaaS"
        - "Service mesh"
        - "Unified observability"
      effort: "Very High"
      impact: "Very High"
```

**Automation Decision Framework**

```python
def should_automate(task: dict) -> dict:
    """
    Decide whether to automate a task.

    Args:
        task: {
            "frequency_per_month": int,
            "duration_hours": float,
            "automation_effort_hours": float,
            "complexity": str,  # "simple", "medium", "complex"
            "error_prone": bool,
            "blocks_other_work": bool,
        }

    Returns:
        Decision with reasoning
    """
    monthly_cost = task["frequency_per_month"] * task["duration_hours"]
    annual_cost = monthly_cost * 12
    automation_cost = task["automation_effort_hours"]

    # Calculate payback period
    if monthly_cost == 0:
        payback_months = float('inf')
    else:
        payback_months = automation_cost / monthly_cost

    # Decision factors
    factors = {
        "roi": annual_cost / automation_cost if automation_cost > 0 else 0,
        "payback_months": payback_months,
        "annual_hours_saved": annual_cost,
        "high_frequency": task["frequency_per_month"] > 10,
        "error_prone": task["error_prone"],
        "blocks_work": task["blocks_other_work"],
        "quick_payback": payback_months < 6,
    }

    # Decision logic
    if factors["payback_months"] < 3:
        decision = "AUTOMATE_NOW"
        reason = "Quick payback (<3 months)"
    elif factors["high_frequency"] and factors["error_prone"]:
        decision = "AUTOMATE_NOW"
        reason = "High frequency and error prone"
    elif factors["blocks_work"]:
        decision = "AUTOMATE_SOON"
        reason = "Blocks other work"
    elif factors["payback_months"] < 12:
        decision = "AUTOMATE_SOON"
        reason = "Reasonable payback (<12 months)"
    elif factors["roi"] > 2.0:
        decision = "CONSIDER"
        reason = "Good ROI but longer payback"
    else:
        decision = "DONT_AUTOMATE"
        reason = "Low ROI or high complexity"

    return {
        "decision": decision,
        "reason": reason,
        "factors": factors,
        "recommendation": _get_recommendation(decision, task),
    }


def _get_recommendation(decision: str, task: dict) -> str:
    """Generate automation recommendation."""
    if decision == "AUTOMATE_NOW":
        return "Schedule automation work in current sprint"
    elif decision == "AUTOMATE_SOON":
        return "Add to backlog, prioritize in next quarter"
    elif decision == "CONSIDER":
        return "Evaluate during quarterly planning"
    else:
        return "Focus on higher-impact automation opportunities"
```

### Self-Service Platforms

```yaml
self_service_benefits:
  for_developers:
    - "Faster delivery (no waiting)"
    - "More autonomy"
    - "Reduced context switching"
    - "Better ownership"

  for_sre:
    - "Reduced toil"
    - "More engineering time"
    - "Scale without headcount"
    - "Focus on reliability"

  examples:
    deployment:
      tool: "CI/CD platform"
      features:
        - "Automated testing"
        - "Progressive rollouts"
        - "Automatic rollback"
        - "Deployment approval flows"
      toil_eliminated: "Manual deployments"

    infrastructure:
      tool: "Internal PaaS / Terraform"
      features:
        - "Self-service provisioning"
        - "Standard configurations"
        - "Cost controls"
        - "Automatic scaling"
      toil_eliminated: "Manual provisioning"

    debugging:
      tool: "Observability platform"
      features:
        - "Distributed tracing"
        - "Log aggregation"
        - "Metrics dashboard"
        - "Correlation"
      toil_eliminated: "Manual log diving"

    operations:
      tool: "Runbook automation"
      features:
        - "Guided troubleshooting"
        - "Automated remediation"
        - "Approval workflows"
        - "Audit logs"
      toil_eliminated: "Manual operations"
```

---

## Monitoring and Observability

### Observability Pillars

```yaml
three_pillars:
  metrics:
    description: "Numeric measurements over time"
    characteristics:
      - "Low cardinality"
      - "Cheap to store"
      - "Good for trends"
      - "Aggregatable"
    use_cases:
      - "Alerting (SLO violations)"
      - "Dashboards (trends)"
      - "Capacity planning"
      - "Performance tracking"
    examples:
      - "Request rate"
      - "Error rate"
      - "Latency percentiles"
      - "Resource utilization"

  logs:
    description: "Discrete event records"
    characteristics:
      - "High cardinality"
      - "Expensive to store"
      - "Good for debugging"
      - "Contextual"
    use_cases:
      - "Debugging (root cause)"
      - "Auditing (compliance)"
      - "Security (forensics)"
      - "Troubleshooting"
    examples:
      - "Application logs"
      - "Access logs"
      - "Audit logs"
      - "Error traces"

  traces:
    description: "Request flow through system"
    characteristics:
      - "Very high cardinality"
      - "Most expensive"
      - "Shows dependencies"
      - "End-to-end view"
    use_cases:
      - "Performance analysis"
      - "Dependency mapping"
      - "Bottleneck identification"
      - "Latency debugging"
    examples:
      - "Distributed traces"
      - "Span relationships"
      - "Service dependencies"
      - "Critical path"
```

### Metric Design

```yaml
metric_design_principles:
  use_labels_not_names:
    bad: "api_v1_requests_total, api_v2_requests_total"
    good: "api_requests_total{version='v1'}"
    reason: "Labels enable aggregation and filtering"

  measure_work_not_state:
    bad: "current_active_connections"
    good: "connections_total (counter)"
    reason: "Counters are more reliable (no sampling issues)"

  keep_cardinality_low:
    bad: "requests_total{user_id='12345'}"
    good: "requests_total{endpoint='/api'}"
    reason: "High cardinality metrics expensive"

  use_standard_names:
    pattern: "{namespace}_{subsystem}_{name}_{unit}"
    examples:
      - "http_requests_total"
      - "http_request_duration_seconds"
      - "process_cpu_seconds_total"

  use_appropriate_types:
    counter:
      description: "Monotonically increasing"
      examples: ["requests_total", "errors_total"]
      operations: ["rate()", "increase()"]

    gauge:
      description: "Can go up or down"
      examples: ["memory_bytes", "queue_length"]
      operations: ["avg()", "min()", "max()"]

    histogram:
      description: "Distribution of values"
      examples: ["request_duration_seconds"]
      operations: ["histogram_quantile()"]

    summary:
      description: "Pre-calculated quantiles"
      examples: ["api_latency_summary"]
      note: "Prefer histogram (more flexible)"
```

**Prometheus Metric Examples**

```python
# Prometheus client library
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import start_http_server
import time
import random


# Counter: monotonically increasing
request_counter = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histogram: distribution (preferred for latency)
request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

# Gauge: current value
active_connections = Gauge(
    'http_active_connections',
    'Active HTTP connections'
)

# Summary: pre-calculated percentiles
request_summary = Summary(
    'http_request_duration_summary',
    'HTTP request latency summary',
    ['method', 'endpoint']
)


# Usage
def handle_request(method: str, endpoint: str):
    """Handle HTTP request with metrics."""
    active_connections.inc()

    start = time.time()
    try:
        # Simulate request processing
        time.sleep(random.uniform(0.01, 0.5))
        status = 200

    except Exception:
        status = 500

    finally:
        duration = time.time() - start

        # Record metrics
        request_counter.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        active_connections.dec()


# Start metrics server
if __name__ == '__main__':
    start_http_server(8000)

    # Simulate requests
    while True:
        handle_request('GET', '/api/users')
        time.sleep(0.1)
```

### Alerting Best Practices

```yaml
alerting_principles:
  alert_on_symptoms:
    principle: "Alert on user-facing impact"
    examples:
      good:
        - "Error rate > 1%"
        - "Latency p95 > 500ms"
        - "Availability < 99.9%"
      bad:
        - "CPU > 80%"
        - "Memory > 70%"
        - "Disk space < 20%"
    rationale: "Symptom-based alerts reduce false positives"

  actionable_alerts:
    principle: "Every alert needs clear action"
    requirements:
      - runbook: "Link to troubleshooting steps"
      - context: "Relevant dashboards and logs"
      - severity: "Critical, Warning, Info"
      - ownership: "Clear responsible team"

    bad_alert: |
      "Database connections high"
      (What should I do?)

    good_alert: |
      "API error rate > 1%: Check recent deployments,
       review error logs, consider rollback.
       Runbook: https://wiki/runbooks/api-errors"

  reduce_noise:
    strategies:
      - silence_during_maintenance: "Scheduled maintenance windows"
      - group_related_alerts: "Single alert for related issues"
      - use_inhibition: "Suppress downstream alerts"
      - require_duration: "Alert after N minutes, not instantly"
      - adjust_thresholds: "Based on historical data"

  alert_routing:
    critical:
      destination: "Page on-call"
      response_time: "Immediate"
      examples:
        - "SLO burn rate > 14.4x"
        - "Complete service outage"
        - "Data loss risk"

    warning:
      destination: "Slack + ticket"
      response_time: "Next business day"
      examples:
        - "SLO burn rate > 3x"
        - "Degraded performance"
        - "Resource trending high"

    info:
      destination: "Ticket only"
      response_time: "Weekly review"
      examples:
        - "Deployment completed"
        - "Scaling event"
        - "Certificate expiring (30 days)"
```

**Alert Rule Template**

```yaml
# Prometheus alerting rule
groups:
  - name: slo_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m]))
          ) > 0.01
        for: 5m
        labels:
          severity: critical
          component: api
          team: backend
        annotations:
          summary: "High error rate detected"
          description: |
            Error rate is {{ $value | humanizePercentage }}.
            This exceeds our 1% threshold.
          impact: "Users experiencing errors"
          action: |
            1. Check recent deployments
            2. Review error logs: https://logs/errors
            3. Consider rollback if from deployment
          runbook: "https://wiki/runbooks/high-error-rate"
          dashboard: "https://grafana/d/api-health"
          logs: "https://logs/query?q=status:5xx"
```

### Dashboard Design

```yaml
dashboard_hierarchy:
  level1_overview:
    purpose: "System health at a glance"
    audience: "Everyone"
    metrics:
      - "Overall availability (SLO)"
      - "Request rate"
      - "Error rate"
      - "Latency percentiles"
    refresh: "10 seconds"

  level2_service:
    purpose: "Individual service health"
    audience: "Service owners"
    metrics:
      - "Service-specific SLIs"
      - "Resource utilization"
      - "Dependency health"
      - "Recent deployments"
    refresh: "30 seconds"

  level3_debugging:
    purpose: "Deep dive troubleshooting"
    audience: "On-call engineers"
    metrics:
      - "Detailed error breakdowns"
      - "Request traces"
      - "Database queries"
      - "Resource metrics"
    refresh: "5 seconds"

dashboard_design_principles:
  above_the_fold:
    - "Most important metrics visible immediately"
    - "No scrolling for critical information"
    - "Use status indicators (green/yellow/red)"

  context:
    - "Time range selector prominent"
    - "Show recent events (deploys, incidents)"
    - "Link to related dashboards"
    - "Embed runbook links"

  visualization:
    - use_graphs_for: ["Trends over time"]
    - use_numbers_for: ["Current state, SLO status"]
    - use_heatmaps_for: ["Latency distribution"]
    - use_tables_for: ["Top N errors, slow queries"]

  avoid:
    - "Too many metrics (cognitive overload)"
    - "Vanity metrics (no actionable insight)"
    - "Stale data (clearly mark refresh time)"
    - "Metrics without context (add baselines)"
```

---

## Incident Management

### Incident Response Framework

```yaml
incident_roles:
  incident_commander:
    responsibilities:
      - "Overall incident coordination"
      - "Delegate tasks"
      - "Communication with stakeholders"
      - "Make high-level decisions"
      - "Track incident timeline"
    should_not:
      - "Do hands-on debugging (delegate)"
      - "Write code (too risky)"

  operations_lead:
    responsibilities:
      - "Hands-on troubleshooting"
      - "Execute mitigation steps"
      - "Coordinate technical team"
      - "Implement fixes"

  communications_lead:
    responsibilities:
      - "Internal updates (Slack, email)"
      - "External updates (status page)"
      - "Stakeholder management"
      - "Customer communication"

  scribe:
    responsibilities:
      - "Document timeline"
      - "Record decisions"
      - "Track action items"
      - "Prepare postmortem draft"

incident_severity:
  sev1_critical:
    definition: "Complete outage or data loss"
    examples:
      - "Service completely down"
      - "Data corruption or loss"
      - "Security breach"
    response_time: "Immediate"
    notification: "Page on-call, escalate management"
    communication_frequency: "Every 15 minutes"

  sev2_major:
    definition: "Significant degradation"
    examples:
      - "High error rate (> 5%)"
      - "Severe performance degradation"
      - "Critical feature unavailable"
    response_time: "Within 15 minutes"
    notification: "Page on-call"
    communication_frequency: "Every 30 minutes"

  sev3_minor:
    definition: "Limited impact"
    examples:
      - "Non-critical feature down"
      - "Minor performance issues"
      - "Isolated errors"
    response_time: "Within 1 hour"
    notification: "Slack notification"
    communication_frequency: "Hourly"
```

**Incident Response Workflow**

```yaml
incident_phases:
  detection:
    triggers:
      - "Automated alert"
      - "Customer report"
      - "Team member notice"
    actions:
      - "Acknowledge alert"
      - "Assess severity"
      - "Page appropriate team"

  triage:
    duration: "5-15 minutes"
    goals:
      - "Assess impact"
      - "Assign severity"
      - "Establish roles"
      - "Start war room"
    outputs:
      - "Severity classification"
      - "Incident commander assigned"
      - "Communication channel created"

  mitigation:
    priority: "Stop the bleeding first"
    strategies:
      - rollback: "Revert to last known good"
      - failover: "Switch to backup"
      - disable_feature: "Turn off problematic code"
      - scale_resources: "Add capacity"
      - traffic_shift: "Route around problem"

    avoid:
      - "Debugging in production"
      - "Deploying fixes without testing"
      - "Multiple changes simultaneously"

  resolution:
    goals:
      - "Confirm service restored"
      - "Validate SLOs met"
      - "Monitor stability"
      - "Customer communication"

    validation:
      - "Check SLIs: availability, latency, errors"
      - "Monitor for 2x incident duration"
      - "Confirm no new alerts"

  postmortem:
    timeline: "Within 48 hours"
    participants: "All incident responders"
    outputs:
      - "Timeline of events"
      - "Root cause analysis"
      - "Action items (with owners)"
      - "Process improvements"
```

### Blameless Postmortems

```yaml
blameless_culture:
  principles:
    - "Focus on systems, not individuals"
    - "Assume good intentions"
    - "Learn from failures"
    - "Encourage transparency"

  bad_questions:
    - "Who caused this?"
    - "Why didn't you catch this?"
    - "Who should we blame?"

  good_questions:
    - "What systemic issues led to this?"
    - "What processes failed?"
    - "How can we prevent recurrence?"
    - "What went well during response?"

postmortem_structure:
  summary:
    - "One paragraph incident description"
    - "Impact: duration, affected users, business impact"
    - "Root cause (brief)"

  timeline:
    format: |
      HH:MM - Event description
      HH:MM - Action taken
      HH:MM - Outcome observed

    example: |
      14:23 - Alert fired: high error rate
      14:25 - On-call acknowledged, began investigation
      14:30 - Identified recent deployment as cause
      14:35 - Initiated rollback
      14:42 - Rollback complete, errors declining
      14:50 - Confirmed service recovered

  root_cause:
    five_whys:
      problem: "API returned 500 errors"
      why1: "Database connections exhausted"
      why2: "Connection pool too small for load"
      why3: "Recent traffic increase not anticipated"
      why4: "No capacity planning for growth"
      why5: "Capacity planning process not defined"
      root_cause: "Lack of systematic capacity planning"

  contributing_factors:
    - "No automated rollback on error spike"
    - "Monitoring delay (5-minute window)"
    - "No staging environment for load testing"
    - "Manual deployment process (slow rollback)"

  action_items:
    template: |
      - [Priority] Action item
        Owner: @person
        Due: YYYY-MM-DD
        Track: JIRA-123

    example:
      - "[P0] Implement automated rollback on error threshold"
        "Owner: @alice"
        "Due: 2025-11-15"
        "Track: ENG-1234"

      - "[P1] Define capacity planning process"
        "Owner: @bob"
        "Due: 2025-11-30"
        "Track: ENG-1235"

  lessons_learned:
    what_went_well:
      - "Quick detection (2 minutes)"
      - "Clear incident command"
      - "Effective communication"

    what_went_poorly:
      - "Slow rollback (manual process)"
      - "Lacked load testing"
      - "No capacity alerts"

    where_we_got_lucky:
      - "Incident during business hours"
      - "Team available for quick response"
      - "Simple rollback available"
```

**Postmortem Template**

```markdown
# Postmortem: [Incident Title]

**Date**: 2025-10-27
**Incident Commander**: Alice Smith
**Severity**: Sev2
**Duration**: 45 minutes (14:23 - 15:08 UTC)
**Impact**: ~15,000 users experienced elevated error rates (5-10%)

## Summary

The API experienced elevated error rates (5-10%) due to database connection pool exhaustion following a 3x traffic spike. Service was restored by rolling back a recent deployment that included inefficient database queries. No data was lost, and normal service resumed within 45 minutes.

## Timeline (all times UTC)

14:20 - Deployment v2.3.4 completed
14:23 - Alert fired: error rate > 1%
14:25 - On-call engineer @alice acknowledged alert
14:27 - @alice determined errors related to database timeouts
14:30 - Traffic analysis showed 3x normal load
14:33 - Database pool at 100% utilization
14:35 - Incident commander role assigned to @alice
14:37 - Decision to rollback deployment
14:40 - Rollback initiated (v2.3.3)
14:45 - Rollback complete, errors declining
14:50 - Error rate back to baseline (< 0.1%)
14:55 - Monitoring for stability
15:08 - Incident declared resolved

## Root Cause

A recent code change (v2.3.4) introduced an N+1 query pattern in a high-traffic endpoint. Under normal load, the inefficiency was not noticeable. However, a marketing campaign drove 3x traffic, causing:

1. Increased query load per request
2. Database connection pool exhaustion
3. New requests timing out waiting for connections
4. Elevated error rates

**Five Whys:**
- Why did errors occur? Database connection timeouts
- Why timeouts? Connection pool exhausted
- Why exhausted? Too many concurrent queries
- Why too many? N+1 query pattern + high traffic
- Why not caught? No load testing before deploy

## Contributing Factors

1. **No load testing**: Changes not tested under realistic load
2. **Manual deployment**: Slow rollback process (10 minutes)
3. **Insufficient monitoring**: No query performance tracking
4. **Missing alerts**: No connection pool utilization alert
5. **Coordination gap**: Marketing campaign not communicated to engineering

## Impact

- **Duration**: 45 minutes
- **Users affected**: ~15,000 (10% of active users)
- **Error rate**: 5-10% (baseline < 0.1%)
- **Business impact**: ~150 failed transactions, estimated $3,000 revenue
- **SLO impact**: Consumed 15% of monthly error budget

## Resolution

Rolled back to v2.3.3, which restored service. Fix for v2.3.4 prepared offline with proper query optimization and will be deployed with load testing.

## Action Items

### Prevention
- [P0] Add load testing to CI/CD pipeline - @bob - 2025-11-10 - ENG-1234
- [P1] Implement query performance monitoring - @charlie - 2025-11-15 - ENG-1235
- [P1] Add database connection pool alerts - @alice - 2025-11-08 - ENG-1236
- [P2] Establish marketing-engineering communication process - @diana - 2025-11-20 - ENG-1237

### Detection
- [P0] Add query execution time to traces - @charlie - 2025-11-12 - ENG-1238
- [P1] Reduce alert evaluation window (5m → 1m) - @alice - 2025-11-05 - ENG-1239

### Response
- [P0] Implement automated rollback on error threshold - @bob - 2025-11-18 - ENG-1240
- [P1] Document connection pool troubleshooting - @alice - 2025-11-08 - ENG-1241

## Lessons Learned

### What Went Well
- Quick detection (3 minutes from incident start)
- Clear incident command and communication
- Decisive rollback decision (no prolonged debugging)
- No data loss or corruption

### What Went Poorly
- No load testing caught the issue
- Manual rollback took 10 minutes
- Marketing campaign not communicated
- Missing database performance monitoring

### Where We Got Lucky
- Incident during business hours (team available)
- Simple rollback path available
- Database connections recovered quickly (no restart needed)
- No cascading failures to dependent services

## Supporting Information

- **Incident Slack thread**: #incidents-2025-10-27
- **Grafana dashboard**: https://grafana/d/incident-20251027
- **Code change**: https://github/pull/1234
- **Related tickets**: ENG-1200 (original feature)
```

---

## Change Management

### Progressive Rollout Strategies

```yaml
deployment_strategies:
  blue_green:
    description: "Two production environments, swap traffic"
    steps:
      - "Deploy to green (idle environment)"
      - "Test green environment"
      - "Switch traffic from blue to green"
      - "Keep blue for quick rollback"
    pros:
      - "Instant rollback (switch back)"
      - "Test in production environment"
      - "Zero downtime"
    cons:
      - "2x infrastructure cost"
      - "Database migrations tricky"
      - "Session state issues"

  canary:
    description: "Gradual rollout to subset of traffic"
    steps:
      - "Deploy to canary (5% traffic)"
      - "Monitor metrics for 30 minutes"
      - "Increase to 25% if healthy"
      - "Increase to 50% if healthy"
      - "Full rollout if healthy"
    pros:
      - "Limited blast radius"
      - "Real production validation"
      - "Gradual confidence building"
    cons:
      - "Slower rollout"
      - "Complex routing logic"
      - "Need sufficient traffic"

  rolling:
    description: "Update instances gradually"
    steps:
      - "Update 1 instance, test"
      - "Update next batch (25%)"
      - "Update next batch (50%)"
      - "Complete rollout"
    pros:
      - "Simple implementation"
      - "No extra infrastructure"
      - "Easy to automate"
    cons:
      - "Mixed versions running"
      - "Slower rollback"
      - "Potential compatibility issues"

  feature_flags:
    description: "Deploy code, enable features gradually"
    steps:
      - "Deploy code with feature disabled"
      - "Enable for internal users"
      - "Enable for 5% of users"
      - "Monitor and increase"
      - "Full rollout"
    pros:
      - "Decouple deploy from release"
      - "Instant rollback (flip flag)"
      - "A/B testing capability"
    cons:
      - "Code complexity"
      - "Technical debt (old flags)"
      - "Need flag management system"
```

**Canary Deployment Example**

```python
from dataclasses import dataclass
from typing import List
import time


@dataclass
class CanaryStage:
    """Single stage of canary deployment."""
    percentage: int
    duration_minutes: int
    health_checks: List[str]
    auto_promote: bool


class CanaryDeployment:
    """Manage canary deployment process."""

    def __init__(self, service: str, version: str):
        self.service = service
        self.version = version
        self.current_stage = 0

        self.stages = [
            CanaryStage(
                percentage=5,
                duration_minutes=30,
                health_checks=["error_rate", "latency_p95"],
                auto_promote=False,
            ),
            CanaryStage(
                percentage=25,
                duration_minutes=30,
                health_checks=["error_rate", "latency_p95", "cpu"],
                auto_promote=True,
            ),
            CanaryStage(
                percentage=50,
                duration_minutes=20,
                health_checks=["error_rate", "latency_p95"],
                auto_promote=True,
            ),
            CanaryStage(
                percentage=100,
                duration_minutes=0,
                health_checks=[],
                auto_promote=True,
            ),
        ]

    def deploy_stage(self, stage: CanaryStage) -> bool:
        """Deploy a canary stage."""
        print(f"Deploying {stage.percentage}% of traffic to {self.version}")

        # Update traffic routing
        self._update_traffic(stage.percentage)

        # Wait for stabilization
        time.sleep(60)  # 1 minute stabilization

        # Monitor for duration
        start = time.time()
        while time.time() - start < stage.duration_minutes * 60:
            if not self._check_health(stage.health_checks):
                print(f"Health check failed, rolling back")
                self._rollback()
                return False

            time.sleep(60)  # Check every minute

        print(f"Stage {stage.percentage}% healthy")
        return True

    def _update_traffic(self, percentage: int):
        """Update traffic routing to canary."""
        # In reality, this would update load balancer rules
        # Example: AWS ALB target group weights, Istio VirtualService
        pass

    def _check_health(self, checks: List[str]) -> bool:
        """Check health metrics."""
        for check in checks:
            if not self._evaluate_metric(check):
                return False
        return True

    def _evaluate_metric(self, metric: str) -> bool:
        """Evaluate a single health metric."""
        # Query Prometheus/CloudWatch/etc
        # Compare canary vs baseline
        thresholds = {
            "error_rate": 0.01,      # < 1%
            "latency_p95": 500,      # < 500ms
            "cpu": 80,               # < 80%
        }

        canary_value = self._get_metric_value(metric, "canary")
        baseline_value = self._get_metric_value(metric, "baseline")

        # Canary should be similar to baseline
        if metric == "error_rate":
            return canary_value < thresholds[metric]
        elif metric == "latency_p95":
            return canary_value < thresholds[metric]
        elif metric == "cpu":
            # Allow canary to be slightly higher
            return canary_value < baseline_value * 1.2

        return True

    def _get_metric_value(self, metric: str, target: str) -> float:
        """Get current metric value."""
        # Query monitoring system
        # This is a placeholder
        return 0.005 if target == "canary" else 0.003

    def _rollback(self):
        """Rollback canary deployment."""
        print(f"Rolling back {self.version}")
        self._update_traffic(0)  # Send no traffic to canary

    def execute(self) -> bool:
        """Execute full canary deployment."""
        for i, stage in enumerate(self.stages):
            self.current_stage = i
            print(f"\n=== Stage {i + 1}/{len(self.stages)} ===")

            if not self.deploy_stage(stage):
                return False

            if not stage.auto_promote and i < len(self.stages) - 1:
                # Manual approval required
                response = input("Continue to next stage? (y/n): ")
                if response.lower() != 'y':
                    print("Deployment paused")
                    return False

        print(f"\n✓ Deployment complete: {self.version}")
        return True


# Usage
deployment = CanaryDeployment(service="api", version="v2.5.0")
success = deployment.execute()
```

### Feature Flags

```python
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import random


class RolloutStrategy(Enum):
    """Feature flag rollout strategies."""
    BOOLEAN = "boolean"           # On/off
    PERCENTAGE = "percentage"     # % of users
    USER_LIST = "user_list"       # Specific users
    ATTRIBUTE = "attribute"       # Based on user attributes


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    enabled: bool
    strategy: RolloutStrategy
    config: Dict[str, Any]
    description: str


class FeatureFlagManager:
    """Manage feature flags."""

    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag):
        """Register a feature flag."""
        self.flags[flag.name] = flag

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if feature is enabled for user."""
        flag = self.flags.get(flag_name)
        if not flag:
            return False  # Unknown flags default to off

        if not flag.enabled:
            return False  # Flag globally disabled

        # Apply rollout strategy
        if flag.strategy == RolloutStrategy.BOOLEAN:
            return True

        elif flag.strategy == RolloutStrategy.PERCENTAGE:
            percentage = flag.config.get("percentage", 0)
            # Consistent hashing based on user_id
            if user_id:
                hash_val = hash(user_id + flag_name) % 100
                return hash_val < percentage
            else:
                # Random for anonymous users
                return random.random() < (percentage / 100)

        elif flag.strategy == RolloutStrategy.USER_LIST:
            allowed_users = flag.config.get("users", [])
            return user_id in allowed_users

        elif flag.strategy == RolloutStrategy.ATTRIBUTE:
            if not attributes:
                return False

            conditions = flag.config.get("conditions", {})
            for attr, expected_value in conditions.items():
                if attributes.get(attr) != expected_value:
                    return False
            return True

        return False


# Usage
flag_manager = FeatureFlagManager()

# Boolean flag (on/off)
flag_manager.register(FeatureFlag(
    name="new_ui",
    enabled=True,
    strategy=RolloutStrategy.BOOLEAN,
    config={},
    description="New UI redesign",
))

# Percentage rollout
flag_manager.register(FeatureFlag(
    name="ml_recommendations",
    enabled=True,
    strategy=RolloutStrategy.PERCENTAGE,
    config={"percentage": 25},  # 25% of users
    description="ML-powered recommendations",
))

# User list (internal testing)
flag_manager.register(FeatureFlag(
    name="experimental_search",
    enabled=True,
    strategy=RolloutStrategy.USER_LIST,
    config={"users": ["alice@company.com", "bob@company.com"]},
    description="Experimental search algorithm",
))

# Attribute-based (premium users only)
flag_manager.register(FeatureFlag(
    name="premium_features",
    enabled=True,
    strategy=RolloutStrategy.ATTRIBUTE,
    config={"conditions": {"tier": "premium"}},
    description="Premium-only features",
))


# Check flags
user_id = "user123"
attributes = {"tier": "premium", "country": "US"}

if flag_manager.is_enabled("new_ui", user_id):
    print("Show new UI")

if flag_manager.is_enabled("ml_recommendations", user_id):
    print("Use ML recommendations")

if flag_manager.is_enabled("premium_features", user_id, attributes):
    print("Show premium features")
```

---

## Capacity Planning

### Capacity Planning Process

```yaml
capacity_planning:
  frequency: "Quarterly (or after major growth)"

  steps:
    1_measure_current:
      metrics:
        - "Resource utilization (CPU, memory, disk, network)"
        - "Request rate and growth trend"
        - "Database connections, queries/sec"
        - "Storage usage and growth rate"
      tools:
        - "Prometheus/CloudWatch metrics"
        - "Capacity dashboard"
        - "Historical data (6-12 months)"

    2_forecast_demand:
      factors:
        - "Historical growth rate"
        - "Planned features/launches"
        - "Seasonal patterns"
        - "Business projections"
      methods:
        - "Linear regression (steady growth)"
        - "Seasonal decomposition (periodic patterns)"
        - "Business-driven (launches, campaigns)"

    3_analyze_bottlenecks:
      techniques:
        - "Load testing (identify limits)"
        - "Resource profiling (find constraints)"
        - "Dependency analysis (upstream/downstream)"
        - "Queueing theory (model saturation)"

    4_plan_scaling:
      dimensions:
        - "Vertical: Larger instances"
        - "Horizontal: More instances"
        - "Architectural: Sharding, caching, CDN"
      timing:
        - "Lead time for procurement/setup"
        - "Buffer for unexpected growth"
        - "Target 30-50% headroom"

    5_cost_optimization:
      strategies:
        - "Right-sizing (eliminate waste)"
        - "Reserved instances (long-term savings)"
        - "Spot instances (batch workloads)"
        - "Auto-scaling (match demand)"
```

**Capacity Model Example**

```python
from dataclasses import dataclass
from typing import List
import numpy as np
from datetime import datetime, timedelta


@dataclass
class CapacityMetric:
    """Capacity measurement."""
    timestamp: datetime
    request_rate: float      # requests/second
    cpu_percent: float       # 0-100
    memory_percent: float    # 0-100
    latency_p95: float       # milliseconds


class CapacityPlanner:
    """Capacity planning and forecasting."""

    def __init__(self):
        self.metrics: List[CapacityMetric] = []

    def add_metric(self, metric: CapacityMetric):
        """Add capacity measurement."""
        self.metrics.append(metric)

    def forecast_demand(self, months_ahead: int = 6) -> dict:
        """Forecast future demand using linear regression."""
        if len(self.metrics) < 30:
            raise ValueError("Need at least 30 days of data")

        # Extract time series data
        timestamps = np.array([
            (m.timestamp - self.metrics[0].timestamp).days
            for m in self.metrics
        ])
        request_rates = np.array([m.request_rate for m in self.metrics])

        # Fit linear model
        coefficients = np.polyfit(timestamps, request_rates, deg=1)
        growth_rate = coefficients[0]  # requests/sec per day

        # Project forward
        current_rate = request_rates[-1]
        days_ahead = months_ahead * 30
        projected_rate = current_rate + (growth_rate * days_ahead)

        # Calculate growth percentage
        growth_percent = ((projected_rate - current_rate) / current_rate) * 100

        return {
            "current_rate": current_rate,
            "projected_rate": projected_rate,
            "growth_rate_per_day": growth_rate,
            "growth_percent": growth_percent,
            "months_ahead": months_ahead,
        }

    def identify_bottleneck(self) -> dict:
        """Identify current resource bottleneck."""
        if not self.metrics:
            return {}

        # Calculate average utilization (recent 7 days)
        recent = self.metrics[-7*24*4:]  # Assuming 15-min intervals
        avg_cpu = np.mean([m.cpu_percent for m in recent])
        avg_memory = np.mean([m.memory_percent for m in recent])
        avg_latency = np.mean([m.latency_p95 for m in recent])

        # Identify bottleneck
        bottleneck = "none"
        if avg_cpu > 70:
            bottleneck = "cpu"
        elif avg_memory > 70:
            bottleneck = "memory"
        elif avg_latency > 500:
            bottleneck = "latency"

        return {
            "bottleneck": bottleneck,
            "cpu_utilization": avg_cpu,
            "memory_utilization": avg_memory,
            "latency_p95": avg_latency,
        }

    def calculate_runway(self, threshold: float = 80.0) -> dict:
        """Calculate time until resource exhaustion."""
        forecast = self.forecast_demand(months_ahead=12)
        bottleneck = self.identify_bottleneck()

        # Simple linear model: assume utilization grows with traffic
        current_rate = forecast["current_rate"]
        growth_rate = forecast["growth_rate_per_day"]

        if growth_rate <= 0:
            return {"runway_days": float('inf'), "status": "stable"}

        # Current utilization and headroom
        current_util = max(
            bottleneck["cpu_utilization"],
            bottleneck["memory_utilization"]
        )
        headroom = threshold - current_util

        if headroom <= 0:
            return {"runway_days": 0, "status": "critical"}

        # Calculate days until threshold
        # Assume linear relationship: util = base + (growth_rate * rate)
        util_per_rate = current_util / current_rate if current_rate > 0 else 0
        rate_increase_to_threshold = headroom / util_per_rate
        days_to_threshold = rate_increase_to_threshold / growth_rate

        status = "healthy" if days_to_threshold > 90 else "warning"
        if days_to_threshold < 30:
            status = "critical"

        return {
            "runway_days": int(days_to_threshold),
            "status": status,
            "current_utilization": current_util,
            "threshold": threshold,
        }

    def generate_scaling_plan(self) -> dict:
        """Generate capacity scaling recommendations."""
        forecast = self.forecast_demand(months_ahead=6)
        runway = self.calculate_runway()
        bottleneck = self.identify_bottleneck()

        recommendations = []

        # Check runway
        if runway["status"] == "critical":
            recommendations.append({
                "priority": "P0",
                "action": "Immediate scaling required",
                "detail": f"Only {runway['runway_days']} days until capacity",
            })
        elif runway["status"] == "warning":
            recommendations.append({
                "priority": "P1",
                "action": "Plan scaling within 30 days",
                "detail": f"{runway['runway_days']} days runway remaining",
            })

        # Address bottleneck
        if bottleneck["bottleneck"] == "cpu":
            recommendations.append({
                "priority": "P1",
                "action": "Scale compute capacity",
                "detail": "CPU utilization high, consider horizontal scaling",
            })
        elif bottleneck["bottleneck"] == "memory":
            recommendations.append({
                "priority": "P1",
                "action": "Increase memory allocation",
                "detail": "Memory utilization high, vertical scaling recommended",
            })
        elif bottleneck["bottleneck"] == "latency":
            recommendations.append({
                "priority": "P1",
                "action": "Optimize performance or add caching",
                "detail": "High latency despite adequate resources",
            })

        # Growth planning
        if forecast["growth_percent"] > 50:
            recommendations.append({
                "priority": "P2",
                "action": "Architectural review",
                "detail": f"High growth projected ({forecast['growth_percent']:.1f}%)",
            })

        return {
            "forecast": forecast,
            "runway": runway,
            "bottleneck": bottleneck,
            "recommendations": recommendations,
        }
```

---

## On-Call Practices

### On-Call Rotation

```yaml
on_call_principles:
  rotation_size: "5-8 engineers (sustainable)"
  rotation_length: "1 week (balance load)"
  shift_handoff: "Monday morning (document weekend)"

  responsibilities:
    primary:
      - "Respond to pages immediately"
      - "Triage and resolve incidents"
      - "Escalate if needed"
      - "Document actions"

    secondary:
      - "Backup for primary"
      - "Respond if primary unavailable (15 min)"
      - "Assist with complex incidents"

  compensation:
    - "Time off in lieu (1 day per week)"
    - "On-call pay (flat rate or per-page)"
    - "Rotation bonus"
    - "Weekend premium"

  health:
    - "Max 2 pages per night (escalate if more)"
    - "Mandatory breaks after major incidents"
    - "Mental health support"
    - "Rotation opt-out for personal reasons"
```

**On-Call Runbook Structure**

```yaml
runbook_template:
  title: "Service Name - Common Issue"
  severity: "Sev2"

  symptoms:
    - "High error rate alert"
    - "Latency > 1s"
    - "Users reporting timeouts"

  triage:
    step1: "Check dashboard: https://grafana/service"
    step2: "Review recent deployments: Last 2 hours"
    step3: "Check dependency health: Upstream/downstream"
    step4: "Assess severity: How many users affected?"

  diagnosis:
    common_causes:
      - cause: "Recent deployment"
        check: "git log --since='2 hours ago'"
        action: "Consider rollback"

      - cause: "Traffic spike"
        check: "Request rate vs baseline"
        action: "Scale up or rate limit"

      - cause: "Dependency failure"
        check: "Downstream service health"
        action: "Enable circuit breaker or fallback"

  resolution:
    immediate:
      - "Rollback deployment if recent"
      - "Scale up resources if capacity issue"
      - "Enable circuit breaker if dependency down"

    investigation:
      - "Review logs: https://logs/query"
      - "Check traces: https://jaeger/search"
      - "Analyze metrics: https://grafana/debug"

  escalation:
    when: "Unable to resolve in 30 minutes"
    who: "@tech-lead, @manager"
    how: "Slack: #incidents, PagerDuty: escalate"

  communication:
    internal: "Update #incidents channel every 15 min"
    external: "Update status page if customer-facing"

  postmortem:
    required: "Yes for Sev1/Sev2"
    timeline: "Within 48 hours"
    owner: "Incident commander"
```

### Alert Fatigue Prevention

```yaml
alert_fatigue:
  symptoms:
    - "Ignoring pages"
    - "High alert volume (> 5/day)"
    - "Low signal-to-noise ratio"
    - "Repeated false positives"

  causes:
    - "Overly sensitive thresholds"
    - "Alerting on symptoms AND causes"
    - "Lack of alert grouping"
    - "No alert maintenance"

  solutions:
    tune_thresholds:
      - "Use historical data (P95, not P50)"
      - "Require duration (5min, not instant)"
      - "Add hysteresis (recover > trigger)"

    reduce_noise:
      - "Alert on SLO burn rate, not raw metrics"
      - "Group related alerts"
      - "Inhibit downstream alerts"
      - "Silence during maintenance"

    improve_actionability:
      - "Every alert needs runbook"
      - "Include context (logs, dashboard links)"
      - "Clear severity (page vs ticket)"
      - "Ownership (which team)"

    regular_review:
      - "Monthly alert audit"
      - "Track alert volume and resolution time"
      - "Delete low-value alerts"
      - "Update thresholds based on data"
```

---

## Chaos Engineering

### Chaos Engineering Principles

```yaml
chaos_engineering:
  definition: "Discipline of experimenting on distributed systems to build confidence in capability to withstand turbulence"

  principles:
    1_build_hypothesis:
      - "Define steady state (SLIs within bounds)"
      - "Hypothesize steady state continues"

    2_vary_real_world:
      - "Hardware failures"
      - "Network issues"
      - "Dependency failures"
      - "Resource exhaustion"

    3_run_in_production:
      - "Production is the truth"
      - "Staging != production"
      - "Real traffic, real dependencies"

    4_automate_experiments:
      - "Continuous chaos"
      - "Automated validation"
      - "Self-healing verification"

    5_minimize_blast_radius:
      - "Start small (1% traffic)"
      - "Expand gradually"
      - "Automatic abort"
      - "Business hours only (initially)"
```

**Chaos Experiment Types**

```yaml
experiment_types:
  resource_failure:
    cpu:
      - "Saturate CPU (stress test)"
      - "CPU throttling"
    memory:
      - "Memory leak simulation"
      - "OOM conditions"
    disk:
      - "Fill disk space"
      - "Slow disk I/O"

  network_failure:
    latency:
      - "Add 100ms delay"
      - "Variable jitter"
    packet_loss:
      - "Drop 5% of packets"
      - "Asymmetric loss"
    partition:
      - "Network split"
      - "Isolate service"

  dependency_failure:
    service_down:
      - "Terminate downstream service"
      - "Block traffic to dependency"
    degraded:
      - "Slow responses (timeouts)"
      - "Increased error rate"

  state_failure:
    data_corruption:
      - "Invalid data format"
      - "Schema mismatch"
    clock_skew:
      - "Time jumps forward/back"
      - "Clock drift"
```

**Chaos Experiment Example**

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
import time
import requests


class ExperimentStatus(Enum):
    """Chaos experiment status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class SteadyStateHypothesis:
    """Define steady state for system."""
    name: str
    measurement: Callable[[], float]
    operator: str  # ">", "<", "=="
    threshold: float


@dataclass
class ChaosExperiment:
    """Chaos engineering experiment."""
    name: str
    description: str
    blast_radius: float  # 0-1, % of traffic affected
    steady_state: SteadyStateHypothesis
    chaos_action: Callable[[], None]
    rollback_action: Callable[[], None]
    duration_seconds: int


class ChaosOrchestrator:
    """Orchestrate chaos experiments."""

    def __init__(self):
        self.status = ExperimentStatus.PENDING

    def run_experiment(self, experiment: ChaosExperiment) -> dict:
        """Execute chaos experiment."""
        results = {
            "experiment": experiment.name,
            "status": None,
            "steady_state_before": None,
            "steady_state_during": None,
            "steady_state_after": None,
            "passed": False,
        }

        try:
            # 1. Validate steady state
            print(f"[1/5] Validating steady state: {experiment.steady_state.name}")
            baseline = self._measure_steady_state(experiment.steady_state)
            results["steady_state_before"] = baseline

            if not self._is_steady_state_valid(experiment.steady_state, baseline):
                print("❌ Baseline not healthy, aborting")
                self.status = ExperimentStatus.ABORTED
                return results

            # 2. Inject chaos
            print(f"[2/5] Injecting chaos: {experiment.description}")
            self.status = ExperimentStatus.RUNNING
            experiment.chaos_action()

            # 3. Monitor during chaos
            print(f"[3/5] Monitoring for {experiment.duration_seconds}s")
            time.sleep(experiment.duration_seconds)

            during = self._measure_steady_state(experiment.steady_state)
            results["steady_state_during"] = during

            # 4. Rollback chaos
            print(f"[4/5] Rolling back chaos")
            experiment.rollback_action()

            # 5. Validate recovery
            print(f"[5/5] Validating recovery")
            time.sleep(30)  # Wait for stabilization
            after = self._measure_steady_state(experiment.steady_state)
            results["steady_state_after"] = after

            # Evaluate results
            passed = self._is_steady_state_valid(experiment.steady_state, during)
            results["passed"] = passed

            if passed:
                print("✓ Experiment passed: System resilient to chaos")
                self.status = ExperimentStatus.PASSED
            else:
                print("✗ Experiment failed: System degraded under chaos")
                self.status = ExperimentStatus.FAILED

        except Exception as e:
            print(f"❌ Experiment error: {e}")
            self.status = ExperimentStatus.ABORTED
            # Emergency rollback
            try:
                experiment.rollback_action()
            except:
                pass

        results["status"] = self.status.value
        return results

    def _measure_steady_state(self, hypothesis: SteadyStateHypothesis) -> float:
        """Measure steady state metric."""
        return hypothesis.measurement()

    def _is_steady_state_valid(
        self,
        hypothesis: SteadyStateHypothesis,
        value: float
    ) -> bool:
        """Check if steady state is valid."""
        if hypothesis.operator == ">":
            return value > hypothesis.threshold
        elif hypothesis.operator == "<":
            return value < hypothesis.threshold
        elif hypothesis.operator == "==":
            return abs(value - hypothesis.threshold) < 0.01
        return False


# Example: Test resilience to downstream failure
def measure_availability():
    """Measure API availability."""
    try:
        response = requests.get("https://api.example.com/health", timeout=5)
        return 1.0 if response.status_code == 200 else 0.0
    except:
        return 0.0


def inject_downstream_failure():
    """Simulate downstream service failure."""
    # In practice, this might:
    # - Block network traffic to dependency
    # - Terminate downstream pods
    # - Inject errors via proxy
    print("  → Blocking traffic to downstream service")


def rollback_downstream_failure():
    """Restore downstream service."""
    print("  → Restoring traffic to downstream service")


# Create experiment
experiment = ChaosExperiment(
    name="downstream-service-failure",
    description="Verify circuit breaker works when downstream fails",
    blast_radius=0.1,  # 10% of traffic
    steady_state=SteadyStateHypothesis(
        name="API Availability",
        measurement=measure_availability,
        operator=">",
        threshold=0.99,
    ),
    chaos_action=inject_downstream_failure,
    rollback_action=rollback_downstream_failure,
    duration_seconds=300,  # 5 minutes
)

# Run experiment
orchestrator = ChaosOrchestrator()
results = orchestrator.run_experiment(experiment)
print(f"\nResults: {results}")
```

---

## Automation Strategies

### Automation Pyramid

```yaml
automation_levels:
  level1_no_automation:
    - "Manual execution"
    - "Documented procedure"
    - "Human performs all steps"
    example: "DBA manually runs database migration"

  level2_script:
    - "Script automates task"
    - "Human triggers script"
    - "Some error handling"
    example: "Deployment script run by engineer"

  level3_self_service:
    - "UI/API for users"
    - "Automated execution"
    - "Good error handling"
    example: "Developers deploy via CI/CD"

  level4_automatic:
    - "Fully automated"
    - "Triggered by event"
    - "Self-healing"
    example: "Auto-scaling, auto-remediation"

  level5_self_optimizing:
    - "ML-driven optimization"
    - "Adapts to patterns"
    - "Continuous improvement"
    example: "Predictive auto-scaling"
```

**Runbook Automation**

```python
from dataclasses import dataclass
from typing import List, Callable, Optional
from enum import Enum


class StepStatus(Enum):
    """Runbook step status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RunbookStep:
    """Single step in automated runbook."""
    name: str
    description: str
    action: Callable[[], bool]  # Returns True if successful
    required: bool = True
    timeout_seconds: int = 300
    rollback: Optional[Callable[[], None]] = None


class AutomatedRunbook:
    """Automated troubleshooting runbook."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[RunbookStep] = []
        self.completed_steps: List[str] = []

    def add_step(self, step: RunbookStep):
        """Add step to runbook."""
        self.steps.append(step)

    def execute(self) -> dict:
        """Execute runbook steps."""
        results = {
            "runbook": self.name,
            "success": False,
            "steps": [],
        }

        print(f"Executing runbook: {self.name}")
        print(f"Description: {self.description}\n")

        for i, step in enumerate(self.steps):
            print(f"[Step {i+1}/{len(self.steps)}] {step.name}")
            print(f"  {step.description}")

            step_result = {
                "name": step.name,
                "status": None,
                "error": None,
            }

            try:
                # Execute step
                success = step.action()

                if success:
                    print(f"  ✓ Success")
                    step_result["status"] = StepStatus.SUCCESS.value
                    self.completed_steps.append(step.name)
                else:
                    print(f"  ✗ Failed")
                    step_result["status"] = StepStatus.FAILED.value

                    if step.required:
                        print(f"  Required step failed, aborting runbook")
                        results["steps"].append(step_result)
                        self._rollback()
                        return results

            except Exception as e:
                print(f"  ✗ Error: {e}")
                step_result["status"] = StepStatus.FAILED.value
                step_result["error"] = str(e)

                if step.required:
                    print(f"  Required step failed, aborting runbook")
                    results["steps"].append(step_result)
                    self._rollback()
                    return results

            results["steps"].append(step_result)
            print()

        print("✓ Runbook completed successfully")
        results["success"] = True
        return results

    def _rollback(self):
        """Rollback completed steps."""
        print("\nRolling back completed steps...")

        for step_name in reversed(self.completed_steps):
            step = next((s for s in self.steps if s.name == step_name), None)
            if step and step.rollback:
                print(f"  Rolling back: {step.name}")
                try:
                    step.rollback()
                    print(f"  ✓ Rolled back")
                except Exception as e:
                    print(f"  ✗ Rollback failed: {e}")


# Example: Automated incident response runbook
def check_recent_deployments() -> bool:
    """Check if recent deployment correlates with incident."""
    # Query deployment history
    print("    Checking deployments in last 2 hours...")
    # recent_deploys = get_recent_deployments(hours=2)
    # return len(recent_deploys) > 0
    return True


def initiate_rollback() -> bool:
    """Rollback recent deployment."""
    print("    Initiating rollback to previous version...")
    # rollback_deployment()
    return True


def verify_service_health() -> bool:
    """Verify service returned to healthy state."""
    print("    Checking SLIs: availability, latency, errors...")
    # return check_slos()
    return True


def notify_team() -> bool:
    """Notify team of automated remediation."""
    print("    Sending Slack notification...")
    return True


# Create runbook
runbook = AutomatedRunbook(
    name="high-error-rate-remediation",
    description="Automated response to high error rate alerts"
)

# Add steps
runbook.add_step(RunbookStep(
    name="check_deployments",
    description="Check for recent deployments",
    action=check_recent_deployments,
    required=True,
))

runbook.add_step(RunbookStep(
    name="rollback",
    description="Rollback to previous version",
    action=initiate_rollback,
    required=True,
))

runbook.add_step(RunbookStep(
    name="verify_health",
    description="Verify service health restored",
    action=verify_service_health,
    required=True,
))

runbook.add_step(RunbookStep(
    name="notify",
    description="Notify team of actions taken",
    action=notify_team,
    required=False,
))

# Execute
results = runbook.execute()
```

---

## Performance Engineering

### Performance Budgets

```yaml
performance_budgets:
  concept: "Maximum allowed resource usage"

  types:
    time_budget:
      - "Page load time < 2s"
      - "API response < 200ms (p95)"
      - "Database query < 50ms"

    resource_budget:
      - "JavaScript bundle < 200KB"
      - "Image sizes < 500KB"
      - "Memory usage < 512MB"

    network_budget:
      - "Total page weight < 1MB"
      - "Request count < 50"
      - "Third-party scripts < 100KB"

  enforcement:
    - "CI checks fail if budget exceeded"
    - "Performance tests in pipeline"
    - "Real user monitoring (RUM)"
    - "Regular audits"
```

**Performance Optimization Checklist**

```yaml
optimization_checklist:
  backend:
    - "Database query optimization (indexes, query plans)"
    - "Caching (Redis, CDN)"
    - "Connection pooling"
    - "Async processing (queues)"
    - "Compression (gzip, brotli)"
    - "Load balancing"

  frontend:
    - "Code splitting (lazy loading)"
    - "Image optimization (compression, responsive)"
    - "Minimize JavaScript"
    - "Critical CSS inline"
    - "Prefetch/preload"
    - "Service workers (offline)"

  database:
    - "Indexes on common queries"
    - "Denormalization where needed"
    - "Read replicas"
    - "Query caching"
    - "Batch operations"
    - "Avoid N+1 queries"

  network:
    - "CDN for static assets"
    - "HTTP/2 or HTTP/3"
    - "Connection keep-alive"
    - "Minimize redirects"
    - "DNS prefetch"
```

---

## Reliability Patterns

### Circuit Breaker

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timedelta(seconds=timeout_seconds)

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if datetime.now() - self.last_failure_time > self.timeout:
                print("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker OPEN: Request rejected")

        try:
            # Execute function
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.success_threshold:
                print("Circuit breaker: Recovered (CLOSED)")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            print(f"Circuit breaker: OPEN after {self.failure_count} failures")
            self.state = CircuitState.OPEN

        if self.state == CircuitState.HALF_OPEN:
            print("Circuit breaker: Recovery failed, back to OPEN")
            self.state = CircuitState.OPEN
            self.success_count = 0


# Usage
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout_seconds=60,
)

def call_external_service():
    """Call unreliable external service."""
    import random
    if random.random() < 0.3:  # 30% failure rate
        raise Exception("Service unavailable")
    return "Success"

# Call through circuit breaker
for i in range(20):
    try:
        result = circuit_breaker.call(call_external_service)
        print(f"Request {i}: {result}")
    except Exception as e:
        print(f"Request {i}: {e}")
```

### Retry with Exponential Backoff

```python
import time
import random
from typing import Callable, Any, Optional


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Any:
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Function result

    Raises:
        Exception from last attempt if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()

        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # Final attempt failed
                raise e

            # Calculate delay
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter (randomize ±25%)
            if jitter:
                delay = delay * (0.75 + random.random() * 0.5)

            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)

    raise last_exception


# Usage
def unreliable_api_call():
    """Simulate unreliable API."""
    import random
    if random.random() < 0.7:  # 70% failure rate
        raise Exception("API Error")
    return "Success"

try:
    result = retry_with_backoff(
        unreliable_api_call,
        max_retries=5,
        base_delay=1.0,
        exponential_base=2.0,
    )
    print(f"Final result: {result}")
except Exception as e:
    print(f"All retries failed: {e}")
```

---

## Documentation and Runbooks

### Runbook Template

```markdown
# Service Name - Runbook

## Service Overview
- **Purpose**: What this service does
- **Architecture**: How it's built (diagram link)
- **Dependencies**: Upstream/downstream services
- **Owner**: Team name and contacts
- **On-call**: Rotation and escalation

## Common Operations

### Deployment
- **Process**: Link to deployment guide
- **Frequency**: Continuous / Weekly
- **Rollback**: How to rollback (commands)
- **Validation**: How to verify deployment

### Scaling
- **Horizontal**: Add/remove instances
- **Vertical**: Resize instances
- **Auto-scaling**: Configured thresholds
- **Manual override**: Emergency scaling commands

### Maintenance
- **Database migrations**: Process and rollback
- **Certificate renewal**: Expiry dates and renewal process
- **Dependency updates**: Schedule and testing
- **Log rotation**: Retention and cleanup

## Troubleshooting

### High Error Rate
**Symptoms**: Error rate > 1%, alerts firing

**Triage**:
1. Check dashboard: [link]
2. Review recent deployments (last 2 hours)
3. Check dependency health
4. Review error logs: [link]

**Common Causes**:
- Recent deployment: Consider rollback
- Dependency failure: Enable circuit breaker
- Database issues: Check connections

**Resolution**:
```bash
# Rollback deployment
kubectl rollout undo deployment/service-name

# Check status
kubectl rollout status deployment/service-name

# Verify health
curl https://service/health
```

**Escalation**: If unresolved in 30min, page @tech-lead

### High Latency
**Symptoms**: p95 latency > 500ms

**Triage**:
1. Check traces: [link]
2. Identify slow endpoints
3. Review database queries
4. Check resource utilization

**Common Causes**:
- Database slow queries: Check query plans
- External API latency: Check circuit breakers
- Resource contention: Scale up

**Resolution**:
- Short term: Scale resources, enable caching
- Long term: Optimize queries, add indexes

### Service Down
**Symptoms**: Service unreachable, 100% errors

**Immediate Actions**:
1. Page on-call immediately
2. Start incident war room
3. Check infrastructure: Pods, nodes, load balancer
4. Review recent changes

**Recovery**:
- Rollback recent deployment
- Restart pods if hanging
- Failover to backup region (if available)

## Metrics and Dashboards

### Key Metrics
- **Availability**: [Grafana link]
- **Latency**: [Grafana link]
- **Error Rate**: [Grafana link]
- **Throughput**: [Grafana link]

### SLOs
- Availability: 99.9% (30-day rolling)
- Latency p95: < 200ms
- Latency p99: < 500ms

### Alerts
- Error rate > 1%: Page on-call
- Latency p95 > 500ms: Page on-call
- Error budget > 75%: Create ticket

## Configuration

### Environment Variables
```yaml
DATABASE_URL: "postgresql://..."
API_KEY: "Secret (in vault)"
LOG_LEVEL: "info"
TIMEOUT_MS: "5000"
```

### Feature Flags
- `new_algorithm`: 50% rollout
- `experimental_cache`: Internal only

## Disaster Recovery

### Backup and Restore
- **Frequency**: Hourly automated backups
- **Retention**: 30 days
- **Restore process**: [link to DR runbook]

### Region Failover
- **Primary**: us-east-1
- **Secondary**: us-west-2
- **Failover process**: [link to failover runbook]
- **RPO**: 5 minutes
- **RTO**: 15 minutes

## Contacts

- **Team**: Backend Engineering
- **Slack**: #backend-team
- **On-call**: PagerDuty rotation
- **Escalation**: @tech-lead, @engineering-manager
- **Stakeholders**: Product, Support
```

---

## Team Organization

### SRE Team Structure

```yaml
team_models:
  embedded_sre:
    description: "SREs embedded in product teams"
    pros:
      - "Close collaboration"
      - "Deep product knowledge"
      - "Fast decision making"
    cons:
      - "Limited knowledge sharing"
      - "Inconsistent practices"
      - "Harder to scale"
    best_for: "Small to medium organizations"

  centralized_sre:
    description: "Central SRE team supporting multiple services"
    pros:
      - "Shared knowledge"
      - "Consistent practices"
      - "Efficient resource use"
    cons:
      - "Distance from product teams"
      - "Potential bottleneck"
      - "Context switching"
    best_for: "Large organizations with many services"

  hybrid:
    description: "Mix of embedded and central SRE"
    structure:
      platform_sre: "Build shared tools and platforms"
      embedded_sre: "Service-specific reliability"
      consulting_sre: "Advise product teams"
    best_for: "Large organizations needing both models"
```

### Skills and Career Growth

```yaml
sre_skills:
  technical:
    - "Systems programming (Python, Go, Rust)"
    - "Distributed systems"
    - "Linux/Unix administration"
    - "Networking (TCP/IP, DNS, load balancing)"
    - "Monitoring and observability"
    - "Cloud platforms (AWS, GCP, Azure)"
    - "Container orchestration (Kubernetes)"
    - "CI/CD pipelines"

  operational:
    - "Incident response"
    - "On-call practices"
    - "Troubleshooting"
    - "Capacity planning"
    - "Performance optimization"
    - "Disaster recovery"

  soft_skills:
    - "Communication (technical writing, documentation)"
    - "Collaboration (cross-team work)"
    - "Prioritization (toil vs projects)"
    - "Teaching (knowledge sharing)"
    - "Leadership (incident command)"

career_progression:
  sre_engineer:
    responsibilities:
      - "On-call rotation"
      - "Respond to incidents"
      - "Write automation"
      - "Maintain services"
    growth_focus:
      - "Master tools and systems"
      - "Learn debugging techniques"
      - "Improve automation skills"

  senior_sre:
    responsibilities:
      - "Lead incidents"
      - "Mentor junior SREs"
      - "Design reliability improvements"
      - "Cross-team collaboration"
    growth_focus:
      - "System design"
      - "Incident leadership"
      - "Strategic thinking"

  staff_sre:
    responsibilities:
      - "Set technical direction"
      - "Define SRE practices"
      - "Multi-team impact"
      - "Architecture decisions"
    growth_focus:
      - "Organizational impact"
      - "Technical leadership"
      - "Long-term planning"
```

---

## Appendix: Tools and Resources

### Monitoring Tools
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Metrics visualization and dashboards
- **Jaeger / Zipkin**: Distributed tracing
- **ELK Stack**: Log aggregation and search
- **Datadog**: All-in-one observability platform

### SRE Tools
- **PagerDuty / Opsgenie**: Incident management and on-call
- **Terraform**: Infrastructure as code
- **Ansible**: Configuration management
- **Kubernetes**: Container orchestration
- **Chaos Mesh / Gremlin**: Chaos engineering

### Resources
- **Books**:
  - "Site Reliability Engineering" (Google)
  - "The Site Reliability Workbook" (Google)
  - "Seeking SRE" (Collection of essays)
- **Websites**:
  - SRE Weekly Newsletter
  - Google SRE Book (free online)
  - srecon.org (Conference talks)
- **Communities**:
  - Reddit: r/sre
  - Slack: hangops, devopsish
  - Conference: SREcon

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Maintainer**: SRE Team
