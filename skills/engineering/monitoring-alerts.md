---
name: engineering-monitoring-alerts
description: Production-ready monitoring and alerting strategies
---

# Monitoring and Alerts

**Scope**: Alert design, SLO-based alerting, alert fatigue prevention, Prometheus Alertmanager, PagerDuty, Opsgenie, escalation policies, oncall rotation, runbooks

**Lines**: 862

**Last Updated**: 2025-10-27

---

## When to Use This Skill

Use this skill when:
- Designing alerting strategy for services
- Implementing SLO-based alerts with error budgets
- Setting up Prometheus Alertmanager
- Configuring PagerDuty or Opsgenie integration
- Creating runbooks for alerts
- Reducing alert fatigue and notification noise
- Implementing escalation policies
- Managing oncall rotations
- Testing alert routing and delivery

**Don't use** for:
- Metrics collection (use metrics-instrumentation.md)
- Prometheus query language (use prometheus-monitoring.md)
- Log-based alerting (use structured-logging.md)

---

## Core Concepts

### Alert Design Principles

**1. Alert on symptoms, not causes**
```yaml
# GOOD: User-facing symptom
- alert: APIUnavailable
  expr: probe_success{job="api"} == 0
  annotations:
    impact: "API is completely unavailable to customers"

# BAD: Internal cause
- alert: HighCPU
  expr: cpu_usage > 80
  # May not affect users
```

**2. Every alert must be actionable**
- If no human action is needed → Don't alert
- If it's informational → Send to dashboard/ticket, not page
- If it's not urgent → Adjust severity

**3. Provide context**
```yaml
annotations:
  summary: "{{ $labels.service }} error rate high"
  description: "Error rate {{ $value }}% (threshold: 5%)"
  impact: "5% of customer requests failing"
  runbook_url: "https://runbooks.example.com/high-error-rate"
  dashboard_url: "https://grafana.example.com/d/service"
```

### The Four Golden Signals

From Google SRE:

1. **Latency**: Time to service requests
2. **Traffic**: Demand on the system
3. **Errors**: Rate of failed requests
4. **Saturation**: Resource utilization

```yaml
groups:
  - name: golden_signals
    rules:
      # Latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
        for: 10m

      # Traffic anomaly
      - alert: TrafficDrop
        expr: sum(rate(http_requests_total[5m])) < avg_over_time(rate(http_requests_total[5m])[1h:5m]) * 0.5
        for: 10m

      # Errors
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m

      # Saturation
      - alert: HighMemoryUsage
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
        for: 5m
```

---

## Patterns

### Pattern 1: SLO-Based Alerting

**Multi-Window Multi-Burn Rate** alerts:

```yaml
groups:
  - name: slo_alerts
    interval: 30s
    rules:
      # Fast burn: 2% error budget in 1 hour (critical)
      - alert: ErrorBudgetBurnRateFast
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) > 0.0144  # 14.4x burn rate
        for: 2m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Fast error budget burn"
          description: "Burning 2% error budget per hour (14.4x rate)"
          impact: "Monthly error budget exhausted in 2 days at this rate"
          runbook_url: "https://runbooks.example.com/error-budget-burn"

      # Slow burn: 10% error budget in 6 hours (warning)
      - alert: ErrorBudgetBurnRateSlow
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > 0.006  # 6x burn rate
        for: 15m
        labels:
          severity: warning
          slo: availability
```

**Why this works**:
- Catches both sudden outages (fast burn) and gradual degradation (slow burn)
- Different severities and response times
- Tied to error budget, not arbitrary thresholds

### Pattern 2: Alertmanager Configuration

```yaml
global:
  resolve_timeout: 5m
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s        # Wait 30s before sending first notification
  group_interval: 5m     # Wait 5m before sending new alerts in group
  repeat_interval: 4h    # Repeat every 4h if still firing

  routes:
    # Critical → PagerDuty + Slack
    - match:
        severity: critical
      receiver: 'pagerduty'
      group_wait: 10s
      repeat_interval: 1h
      continue: true      # Also send to next route

    - match:
        severity: critical
      receiver: 'slack-incidents'

    # Warnings → Slack only
    - match:
        severity: warning
      receiver: 'slack-warnings'
      group_wait: 5m
      repeat_interval: 12h

# Suppress cascading alerts
inhibit_rules:
  # If node down, suppress resource alerts from that node
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: '(HighCPU|HighMemory|DiskFull)'
    equal: ['instance']

  # If critical firing, suppress warnings
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service']

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          runbook: '{{ .CommonAnnotations.runbook_url }}'

  - name: 'slack-incidents'
    slack_configs:
      - channel: '#incidents'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'
        color: 'danger'
```

### Pattern 3: Alert Fatigue Prevention

**Strategies**:

1. **Increase "for" duration**:
   ```yaml
   # Before: Fires on transient spikes
   - alert: HighErrorRate
     expr: error_rate > 0.01
     for: 1m

   # After: Filters transient issues
   - alert: HighErrorRate
     expr: error_rate > 0.05  # Higher threshold
     for: 10m                  # Longer duration
   ```

2. **Use recording rules**:
   ```yaml
   # Pre-compute complex queries
   - record: service:error_rate:5m
     expr: |
       sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
       /
       sum(rate(http_requests_total[5m])) by (service)

   # Alert on recorded metric (faster, more stable)
   - alert: HighErrorRate
     expr: service:error_rate:5m > 0.05
     for: 5m
   ```

3. **Group related alerts**:
   ```yaml
   route:
     group_by: ['alertname', 'service', 'datacenter']
     group_wait: 30s
     group_interval: 5m
   ```
   - 10 pods crash → 1 grouped notification (not 10)

4. **Remove non-actionable alerts**:
   - Monthly review: Which alerts fired but required no action?
   - Archive or adjust those alerts

### Pattern 4: Runbook Structure

```markdown
# Alert: [AlertName]

## Overview
What this alert means and why it exists.

## Impact
- User impact: [Service down | Performance degraded | No user impact]
- Business impact: [Revenue/SLA impact]

## Diagnosis
### 1. Verify the alert
\`\`\`bash
# Check metric
curl 'http://prometheus:9090/api/v1/query?query=...'
\`\`\`

### 2. Check related systems
\`\`\`bash
kubectl get pods -n production
kubectl logs [pod] --tail=100
\`\`\`

### 3. Identify root cause
Common causes:
1. Recent deployment
2. Upstream dependency failure
3. Resource exhaustion

## Remediation

### Immediate (< 5 min)
1. **Rollback deployment**:
   \`\`\`bash
   kubectl rollout undo deployment/api
   \`\`\`

2. **Scale horizontally**:
   \`\`\`bash
   kubectl scale deployment/api --replicas=10
   \`\`\`

### Short-term (< 1 hour)
- Investigate root cause
- Apply workaround

### Long-term
- Permanent fix
- Prevent recurrence

## Validation
\`\`\`bash
# Verify service healthy
curl https://api.example.com/health

# Check metrics recovered
# [Dashboard URL]
\`\`\`

## Related
- Dashboards: [URLs]
- Previous incidents: [INC-123, INC-456]
- Team: #platform-team
```

### Pattern 5: Escalation Policies

```yaml
# PagerDuty escalation policy
escalation_policy:
  name: "Platform Team 24/7"
  num_loops: 2  # Repeat entire chain twice
  escalation_rules:
    # Level 1: Primary oncall (immediate)
    - escalation_delay_minutes: 0
      targets:
        - type: schedule
          id: "SCHEDULE_PRIMARY"

    # Level 2: Secondary oncall (after 15 min)
    - escalation_delay_minutes: 15
      targets:
        - type: schedule
          id: "SCHEDULE_SECONDARY"

    # Level 3: Team lead (after 30 min total)
    - escalation_delay_minutes: 15
      targets:
        - type: user
          id: "USER_TEAM_LEAD"

    # Level 4: Engineering manager (after 60 min)
    - escalation_delay_minutes: 30
      targets:
        - type: user
          id: "USER_MANAGER"
```

### Pattern 6: Testing Alert Routing

```python
#!/usr/bin/env python3
"""Send test alert to Alertmanager."""
import requests
from datetime import datetime, timedelta

def send_test_alert():
    alert = {
        "labels": {
            "alertname": "TestAlert",
            "severity": "warning",
            "service": "test",
            "test": "true"  # Mark as test
        },
        "annotations": {
            "summary": "This is a test alert",
            "description": "Testing alert routing"
        },
        "startsAt": datetime.utcnow().isoformat() + 'Z',
        "endsAt": (datetime.utcnow() + timedelta(minutes=5)).isoformat() + 'Z'
    }

    response = requests.post(
        "http://alertmanager:9093/api/v1/alerts",
        json=[alert]
    )
    return response.status_code == 200

if __name__ == "__main__":
    if send_test_alert():
        print("✓ Test alert sent")
    else:
        print("✗ Failed to send test alert")
```

---

## Quick Reference

### Alert Severity Levels

```yaml
# Critical/P1: Page immediately, 24/7
severity: critical
# - Service down
# - Data loss risk
# - Security breach
# - SLA breach

# Warning/P2: Page during business hours, ticket after hours
severity: warning
# - Performance degraded
# - Approaching limits
# - Non-critical failure

# Info/P3: Ticket only
severity: info
# - Anomaly detected
# - Maintenance reminder
```

### Alertmanager CLI (amtool)

```bash
# Check config
amtool check-config alertmanager.yml

# List active alerts
amtool alert query

# Create silence
amtool silence add \
  alertname=DiskFull \
  instance=db-01 \
  --duration=2h \
  --author="alice@example.com" \
  --comment="Disk expansion in progress"

# List silences
amtool silence query

# Expire silence
amtool silence expire <silence-id>
```

### PagerDuty Event API

```bash
# Send event
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H 'Content-Type: application/json' \
  -d '{
    "routing_key": "YOUR_KEY",
    "event_action": "trigger",
    "payload": {
      "summary": "Test incident",
      "severity": "critical",
      "source": "alertmanager"
    }
  }'
```

---

## Anti-Patterns

### Alert on Everything

```yaml
# WRONG: Too many alerts
- alert: CPUUsageAbove50Percent
  expr: cpu_usage > 50
  # Will fire constantly, causes alert fatigue

# CORRECT: Alert on actionable thresholds
- alert: CPUUsageCritical
  expr: cpu_usage > 90
  for: 15m
  # Only alerts when action needed
```

### Cause-Based Instead of Symptom-Based

```yaml
# WRONG: Alert on cause
- alert: DatabaseConnectionPoolHigh
  expr: db_connections > 80

# CORRECT: Alert on user-facing symptom
- alert: DatabaseConnectionsExhausted
  expr: db_connection_errors > 0
  annotations:
    impact: "Users unable to connect to service"
```

### Missing Runbooks

```yaml
# WRONG: No guidance
annotations:
  summary: "High error rate"

# CORRECT: Link to runbook
annotations:
  summary: "High error rate on {{ $labels.service }}"
  description: "Error rate {{ $value }}%"
  runbook_url: "https://runbooks.example.com/high-error-rate"
  dashboard_url: "https://grafana.example.com/d/errors"
```

### Alert Flapping

```yaml
# WRONG: Fires on every transient spike
- alert: HighLatency
  expr: latency > 500ms
  for: 0s  # No duration

# CORRECT: Filter transient issues
- alert: HighLatency
  expr: latency > 500ms
  for: 10m  # Sustained high latency
```

### Not Grouping Related Alerts

```yaml
# WRONG: 10 pods crash = 10 separate pages
route:
  group_by: []

# CORRECT: Group by alertname
route:
  group_by: ['alertname', 'service']
  # 10 pods crash = 1 grouped notification
```

---

## Level 3: Resources

This skill has **Level 3 Resources** available with comprehensive reference material, production-ready scripts, and runnable examples.

### Resource Structure

```
monitoring-alerts/resources/
├── REFERENCE.md                        # Comprehensive reference (3,842 lines)
│   ├── Alert design principles and methodologies
│   ├── SLO-based alerting with error budgets
│   ├── Symptom-based vs cause-based alerts
│   ├── Alert fatigue prevention strategies
│   ├── Complete Alertmanager configuration
│   ├── PagerDuty and Opsgenie integration
│   ├── Alert routing, grouping, and inhibition
│   ├── Escalation policies and oncall rotation
│   ├── Runbook structure and examples
│   ├── Notification channels (Slack, email, webhooks)
│   ├── Silencing and muting strategies
│   ├── Testing alerting systems
│   ├── Metrics for alert health
│   └── Production troubleshooting guide
│
├── scripts/                            # Production-ready tools
│   ├── validate_alert_rules.py         # Validate Prometheus alert rules
│   ├── analyze_alert_fatigue.py        # Analyze alert frequency and flapping
│   └── test_alert_routing.py           # Test alert routing and escalation
│
└── examples/                           # Runnable examples
    ├── prometheus/
    │   └── alert-rules.yml             # Complete alert rules (SLO, symptoms, resources)
    ├── alertmanager/
    │   └── alertmanager.yml            # Full Alertmanager config with routing
    ├── pagerduty/
    │   └── integration-config.json     # PagerDuty services and schedules
    ├── runbooks/
    │   ├── template.md                 # Runbook template
    │   └── high-memory-usage.md        # Complete runbook example
    ├── escalation/
    │   └── escalation-policies.yml     # Escalation and oncall schedules
    └── dashboards/
        └── alert-overview-dashboard.json  # Grafana alert dashboard
```

### Key Resources

**REFERENCE.md** (3,842 lines): Comprehensive guide covering:
- Alert design principles (Four Golden Signals, RED, USE methods)
- SLO-based alerting with multi-window multi-burn rate
- Symptom vs cause-based alerting patterns
- Alert fatigue prevention (15+ strategies)
- Complete Alertmanager architecture and configuration
- PagerDuty integration (services, schedules, escalation)
- Opsgenie integration and routing
- Alert routing tree design
- Grouping, inhibition, and silencing
- Escalation policies (24/7, business hours, follow-the-sun)
- Oncall rotation best practices
- Runbook structure and templates
- Notification channels (Slack, email, webhooks, Teams, Discord)
- Testing alerting end-to-end
- Alert health metrics
- Production troubleshooting

**validate_alert_rules.py**: Production-ready validator (578 lines)
- Validates Prometheus alert rule syntax
- Checks best practices (naming, labels, annotations)
- Detects anti-patterns (high cardinality, missing runbooks)
- Tests expressions against Prometheus API
- Validates duration formats
- Checks for flapping alerts (too short "for" duration)
- Example: `validate_alert_rules.py --file alerts.yml --prometheus http://localhost:9090 --json`

**analyze_alert_fatigue.py**: Alert fatigue analyzer (534 lines)
- Analyzes alert frequency over time
- Detects flapping alerts (rapid state changes)
- Identifies long-running alerts (>24h)
- Analyzes notification load by channel
- Tracks notification success/failure rates
- Generates actionable recommendations
- Example: `analyze_alert_fatigue.py --prometheus http://localhost:9090 --days 7 --json`

**test_alert_routing.py**: Alert routing tester (597 lines)
- Tests alert routing through Alertmanager
- Validates routing tree matches
- Tests inhibition rules
- Checks active silences
- Sends test alerts and verifies delivery
- Comprehensive test suite for common scenarios
- Example: `test_alert_routing.py --alertmanager http://localhost:9093 --labels '{"severity":"critical"}'`

**Runnable Examples**:
- Complete Prometheus alert rules (SLO-based, symptom-based, resource saturation)
- Full Alertmanager configuration with routing, grouping, inhibition
- PagerDuty integration config (services, schedules, escalation policies)
- Runbook template and complete example (HighMemoryUsage)
- Escalation policies (24/7, business hours, follow-the-sun)
- Grafana dashboard for alert monitoring
- Test scripts for alert routing and delivery

### Usage

```bash
# Access comprehensive reference
cat monitoring-alerts/resources/REFERENCE.md

# Validate alert rules
./scripts/validate_alert_rules.py --file alerts.yml --prometheus http://localhost:9090

# Analyze alert fatigue
./scripts/analyze_alert_fatigue.py --prometheus http://localhost:9090 --days 30

# Test alert routing
./scripts/test_alert_routing.py --alertmanager http://localhost:9093

# Send test alert
./scripts/test_alert_routing.py --alertmanager http://localhost:9093 \
  --send-test --labels '{"severity":"warning","service":"test"}'

# Validate Alertmanager config
amtool check-config alertmanager/alertmanager.yml
```

### When to Use Level 3 Resources

Use these resources when:
- Designing alerting strategy for new services
- Implementing SLO-based alerting
- Setting up Alertmanager from scratch
- Integrating with PagerDuty or Opsgenie
- Creating runbooks for existing alerts
- Debugging alert fatigue issues
- Testing alert routing and escalation
- Training team on alerting best practices
- Reviewing and optimizing existing alerts
- Setting up oncall rotation and schedules

---

## Related Skills

- **prometheus-monitoring.md** - PromQL and recording rules
- **metrics-instrumentation.md** - Instrumenting applications
- **observability-distributed-tracing.md** - Request tracing
- **structured-logging.md** - Log-based alerting

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
