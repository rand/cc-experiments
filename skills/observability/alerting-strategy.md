---
name: observability-alerting-strategy
description: Setting up production monitoring and on-call rotation
---



# Alerting Strategy

**Scope**: Alert conditions, severity levels, on-call rotation, alert fatigue, SLO-based alerts

**Lines**: 368

**Last Updated**: 2025-10-18

---

## When to Use This Skill

Use this skill when:
- Setting up production monitoring and on-call rotation
- Designing alert rules for critical systems
- Reducing alert fatigue and false positives
- Implementing SLO-based alerting
- Configuring PagerDuty, Opsgenie, or similar on-call tools
- Defining incident severity levels and escalation policies
- Troubleshooting alerting issues (too many/too few alerts)
- Building runbooks for common alerts

**Don't use** for:
- Development environments (logs are sufficient)
- Non-critical systems (monitoring dashboards are sufficient)
- Metrics that don't require human intervention

---

## Core Concepts

### Alert Philosophy

**Golden Rule**: Every alert must be actionable
- **Actionable**: Requires human intervention
- **Not actionable**: FYI, nice-to-know (use dashboards instead)

**Example**:
```
❌ Bad alert: "CPU usage is 60%" (so what?)
✅ Good alert: "CPU usage >90% for 5 minutes" (take action)

❌ Bad alert: "Request latency is 200ms" (within SLO)
✅ Good alert: "Request latency >1s, SLO budget exhausted"
```

### Severity Levels

**P0 (Critical)**: Immediate response, page on-call
- Service completely down
- Data loss occurring
- Security breach
- SLO budget exhausted (user-facing impact)
- **Response**: <5 minutes

**P1 (High)**: Urgent, page on-call during business hours
- Service degraded (partial outage)
- SLO at risk (warning threshold)
- Critical dependency failing
- **Response**: <15 minutes

**P2 (Medium)**: Important, ticket to team
- Non-critical service degraded
- Elevated error rates (below SLO)
- Resource constraints (disk, memory)
- **Response**: <1 hour

**P3 (Low)**: Informational, check next day
- Non-production issues
- Optimization opportunities
- **Response**: Next business day

### Alert Types

**1. Symptom-based** (prefer): Alert on user-facing symptoms
- High latency
- High error rate
- Service unavailable
- **Why**: Direct user impact

**2. Cause-based**: Alert on underlying causes
- High CPU usage
- Memory leak
- Database connection pool exhausted
- **Why**: Useful for diagnosis, but risk false positives

### SLO-Based Alerting

**SLO (Service Level Objective)**: Target reliability (e.g., 99.9% uptime)

**SLI (Service Level Indicator)**: Measurement (e.g., success rate)

**Error Budget**: Allowed downtime (e.g., 0.1% = 43 minutes/month)

**Alerting Strategy**:
1. **Burn rate**: How fast error budget is consumed
2. **Multi-window**: Short window (fast burn) + long window (slow burn)
3. **Budget exhaustion**: Alert when budget is near zero

---

## Patterns

### Pattern 1: SLO-Based Alert (Prometheus)

```yaml
# SLO: 99.9% success rate (error budget: 0.1%)
# Alert if burning budget 10x faster (1% error rate)

groups:
  - name: slo_alerts
    interval: 30s
    rules:
      # Fast burn (1 hour window)
      - alert: ErrorBudgetBurnFast
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) > 0.01  # 1% error rate (10x SLO)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Fast error budget burn detected"
          description: "Error rate is {{ $value | humanizePercentage }}, burning error budget 10x faster than allowed"

      # Slow burn (6 hour window)
      - alert: ErrorBudgetBurnSlow
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > 0.002  # 0.2% error rate (2x SLO)
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Slow error budget burn detected"
          description: "Error rate is {{ $value | humanizePercentage }}, burning error budget 2x faster than allowed"

      # Budget exhaustion
      - alert: ErrorBudgetExhausted
        expr: |
          (
            1 - (
              sum(rate(http_requests_total{status!~"5.."}[30d]))
              /
              sum(rate(http_requests_total[30d]))
            )
          ) > 0.001  # Exceeded 0.1% error budget
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error budget exhausted"
          description: "Monthly error budget has been exhausted"
```

### Pattern 2: Latency Alert (Prometheus)

```yaml
groups:
  - name: latency_alerts
    rules:
      # P95 latency above SLO
      - alert: HighLatencyP95
        expr: |
          histogram_quantile(0.95,
            sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
          ) > 1.0  # 1 second SLO
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above SLO"
          description: "P95 latency is {{ $value }}s (SLO: 1s)"

      # P99 latency critical
      - alert: HighLatencyP99Critical
        expr: |
          histogram_quantile(0.99,
            sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
          ) > 5.0  # 5 second critical threshold
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "P99 latency critically high"
          description: "P99 latency is {{ $value }}s (threshold: 5s)"
```

### Pattern 3: Resource Alert (Prometheus)

```yaml
groups:
  - name: resource_alerts
    rules:
      # CPU usage high
      - alert: HighCPUUsage
        expr: |
          100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value | humanize }}%"

      # Memory usage critical
      - alert: HighMemoryUsage
        expr: |
          (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value | humanize }}%"

      # Disk space low
      - alert: DiskSpaceLow
        expr: |
          (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk space available: {{ $value | humanize }}%"
```

### Pattern 4: Error Rate Alert (Python)

```python
from prometheus_client import Counter, generate_latest
from flask import Flask, jsonify

app = Flask(__name__)

errors_total = Counter(
    'api_errors_total',
    'Total API errors',
    ['endpoint', 'error_type']
)

# Prometheus alert rule (configured in Prometheus)
# alert: HighErrorRate
# expr: rate(api_errors_total[5m]) > 1  # More than 1 error/sec
# for: 5m
# labels:
#   severity: critical
# annotations:
#   summary: "High error rate detected"

@app.route('/api/data')
def get_data():
    try:
        data = fetch_data()
        return jsonify(data)
    except Exception as e:
        errors_total.labels(
            endpoint='/api/data',
            error_type=type(e).__name__
        ).inc()
        raise

@app.route('/metrics')
def metrics():
    return generate_latest()
```

### Pattern 5: Alert Routing (Alertmanager)

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  # Default receiver
  receiver: team-slack

  # Group alerts by cluster and alertname
  group_by: ['cluster', 'alertname']

  # Wait before sending notification
  group_wait: 10s

  # Wait before sending notification for new alerts in group
  group_interval: 10s

  # Wait before resending notification
  repeat_interval: 12h

  routes:
    # Critical alerts to PagerDuty
    - match:
        severity: critical
      receiver: pagerduty-critical
      continue: true  # Also send to Slack

    # Database alerts to DBA team
    - match_re:
        service: database
      receiver: dba-team-slack

    # Business hours only
    - match:
        severity: warning
      receiver: team-slack
      active_time_intervals:
        - business-hours

receivers:
  - name: team-slack
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX'
        channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
        severity: 'critical'

  - name: dba-team-slack
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YYY'
        channel: '#dba-alerts'

time_intervals:
  - name: business-hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '17:00'
        location: 'America/New_York'
```

### Pattern 6: Runbook Annotation

```yaml
groups:
  - name: service_alerts
    rules:
      - alert: ServiceDown
        expr: up{job="api-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "Service has been down for more than 1 minute"
          runbook_url: "https://wiki.example.com/runbooks/service-down"
          dashboard_url: "https://grafana.example.com/d/service-overview"

          # Inline runbook
          runbook: |
            1. Check service logs: kubectl logs -l app=api-service --tail=100
            2. Check recent deployments: kubectl rollout history deployment/api-service
            3. Check resource usage: kubectl top pods -l app=api-service
            4. Restart service: kubectl rollout restart deployment/api-service
            5. Escalate to team lead if issue persists >10 minutes
```

---

## Quick Reference

### Alert Design Checklist

```
[ ] Alert is actionable (requires human intervention)
[ ] Alert has clear severity level (P0/P1/P2/P3)
[ ] Alert includes context (service, endpoint, instance)
[ ] Alert includes runbook link
[ ] Alert threshold avoids false positives
[ ] Alert uses appropriate time window (for: duration)
[ ] Alert routes to correct team/channel
[ ] Alert has tested escalation policy
```

### Severity Guidelines

```
P0 (Critical): Page immediately, 24/7
- Service down
- Data loss
- SLO exhausted

P1 (High): Page during business hours
- Service degraded
- SLO at risk
- Critical dependency down

P2 (Medium): Ticket to team
- Non-critical degradation
- Resource warnings

P3 (Low): Informational
- Non-prod issues
- Optimization opportunities
```

### Common Alert Thresholds

```yaml
# Error rate
rate(errors_total[5m]) / rate(requests_total[5m]) > 0.01  # 1%

# Latency (P95)
histogram_quantile(0.95, rate(latency_bucket[5m])) > 1.0  # 1s

# Availability
up == 0  # Service down

# CPU
cpu_usage > 90  # 90%

# Memory
memory_usage > 95  # 95%

# Disk
disk_usage > 90  # 90%

# Queue size
queue_size > 1000  # 1000 messages
```

### Alert Routing Strategies

```
By Severity:
  Critical → PagerDuty → SMS + Call
  Warning → Slack → #alerts channel
  Info → Dashboard → No notification

By Service:
  API → API team
  Database → DBA team
  Frontend → Frontend team

By Time:
  Business hours → Slack
  After hours → PagerDuty (critical only)
```

---

## Anti-Patterns

### ❌ Alert Fatigue

```yaml
# WRONG: Too many alerts, too sensitive
- alert: CPUHigh
  expr: cpu_usage > 50  # Fires constantly!
  for: 1m

# CORRECT: Reasonable threshold, longer window
- alert: CPUCritical
  expr: cpu_usage > 90
  for: 15m
```

### ❌ Non-Actionable Alerts

```yaml
# WRONG: FYI alert (not actionable)
- alert: RequestsIncreased
  expr: rate(requests_total[5m]) > 100
  annotations:
    summary: "Requests increased"

# CORRECT: Actionable alert with impact
- alert: ErrorRateHigh
  expr: rate(errors_total[5m]) / rate(requests_total[5m]) > 0.05
  annotations:
    summary: "Error rate exceeds 5%, users impacted"
```

### ❌ Missing Context

```yaml
# WRONG: Vague alert
- alert: Error
  expr: errors_total > 0
  annotations:
    summary: "Error occurred"

# CORRECT: Context-rich alert
- alert: PaymentServiceErrors
  expr: rate(errors_total{service="payment"}[5m]) > 1
  annotations:
    summary: "Payment service error rate high"
    description: "{{ $value }} errors/sec on {{ $labels.instance }}"
    runbook_url: "https://wiki.example.com/payment-errors"
```

### ❌ No Grouping or Throttling

```yaml
# WRONG: Individual alert per instance
- alert: HighMemory
  expr: memory_usage > 90
  # Fires 100x for 100 instances!

# CORRECT: Grouped alert
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
```

### ❌ Alerting on Causes, Not Symptoms

```yaml
# WRONG: Alert on CPU (cause)
- alert: HighCPU
  expr: cpu_usage > 80
  # So what? Is service degraded?

# CORRECT: Alert on latency (symptom)
- alert: HighLatency
  expr: p95_latency > 1.0
  # Clear user impact
```

### ❌ No Escalation Policy

```yaml
# WRONG: Single notification channel
receiver: team-slack

# CORRECT: Escalation chain
routes:
  - match:
      severity: critical
    receiver: pagerduty-primary
    routes:
      - match:
          acknowledged: false
        receiver: pagerduty-secondary
        continue: true
        repeat_interval: 15m
```

---

## Related Skills

- **metrics-instrumentation.md** - Define metrics for alerts
- **structured-logging.md** - Correlate logs with alerts
- **distributed-tracing.md** - Trace context for debugging alerts
- **dashboard-design.md** - Visualize alert status

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
