# Monitoring and Alerting - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-27
**Lines**: 3,842

---

## Table of Contents

1. [Introduction](#introduction)
2. [Alert Design Principles](#alert-design-principles)
3. [SLO-Based Alerting](#slo-based-alerting)
4. [Symptom-Based vs Cause-Based Alerts](#symptom-based-vs-cause-based-alerts)
5. [Alert Fatigue Prevention](#alert-fatigue-prevention)
6. [Prometheus Alertmanager](#prometheus-alertmanager)
7. [PagerDuty Integration](#pagerduty-integration)
8. [Opsgenie Integration](#opsgenie-integration)
9. [Alert Routing and Grouping](#alert-routing-and-grouping)
10. [Escalation Policies](#escalation-policies)
11. [On-Call Rotation](#on-call-rotation)
12. [Runbooks](#runbooks)
13. [Alert Inhibition and Silencing](#alert-inhibition-and-silencing)
14. [Notification Channels](#notification-channels)
15. [Dashboards for Alerts](#dashboards-for-alerts)
16. [Testing Alerting Systems](#testing-alerting-systems)
17. [Metrics for Alert Health](#metrics-for-alert-health)
18. [Production Best Practices](#production-best-practices)
19. [Troubleshooting Guide](#troubleshooting-guide)
20. [Examples and Templates](#examples-and-templates)

---

## Introduction

### What is Effective Alerting?

Effective alerting is about notifying the right people at the right time with the right information to take corrective action. Poor alerting leads to:
- **Alert fatigue**: Too many noisy alerts causing operators to ignore them
- **Missed incidents**: Important alerts buried in noise
- **Slow response**: Unclear alerts requiring investigation before action
- **Burnout**: Constant interruptions and false alarms

### Key Principles

1. **Page only for actionable issues**: Every alert should require human intervention
2. **Prioritize by user impact**: Alert severity should reflect customer impact
3. **Provide context**: Alerts should contain enough information to start troubleshooting
4. **Avoid duplicates**: Route correlated alerts together
5. **Escalate appropriately**: Route to the right team based on severity and time
6. **Document response**: Every alert should have a runbook

### Alert Levels

- **Critical/P1**: Service down, data loss, security breach (page immediately)
- **Warning/P2**: Degraded performance, approaching limits (page during business hours or after threshold)
- **Info/P3**: Anomalies worth investigating (ticket/email)

---

## Alert Design Principles

### The Four Golden Signals (Google SRE)

**1. Latency**: Time to service requests
```promql
# Alert on p95 latency > threshold
- alert: HighLatency
  expr: |
    histogram_quantile(0.95,
      sum by (service, le) (
        rate(http_request_duration_seconds_bucket[5m])
      )
    ) > 1.0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High latency on {{ $labels.service }}"
    description: "p95 latency is {{ $value }}s (threshold: 1s)"
```

**2. Traffic**: Demand on the system
```promql
# Alert on unusual traffic patterns
- alert: TrafficSpike
  expr: |
    sum(rate(http_requests_total[5m])) by (service)
    >
    sum(avg_over_time(rate(http_requests_total[5m])[1h:5m])) by (service) * 2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Traffic spike on {{ $labels.service }}"
    description: "Request rate {{ $value }}/s is 2x normal"
```

**3. Errors**: Rate of failed requests
```promql
# Alert on error rate > 1%
- alert: HighErrorRate
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
    /
    sum(rate(http_requests_total[5m])) by (service)
    > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate on {{ $labels.service }}"
    description: "Error rate {{ $value | humanizePercentage }}"
```

**4. Saturation**: Resource utilization approaching limits
```promql
# Alert on memory saturation > 90%
- alert: HighMemoryUsage
  expr: |
    100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
    > 90
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High memory on {{ $labels.instance }}"
    description: "Memory usage {{ $value }}%"
```

### RED Method (Requests, Errors, Duration)

Similar to Golden Signals but focused on request-based services:

```yaml
groups:
  - name: red_alerts
    rules:
      # Request rate drop (traffic)
      - alert: RequestRateDrop
        expr: |
          sum(rate(http_requests_total[5m])) by (service)
          <
          sum(avg_over_time(rate(http_requests_total[5m])[1h:5m])) by (service) * 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Request rate dropped on {{ $labels.service }}"
          description: "Current: {{ $value }}/s, expected: > {{ $threshold }}/s"

      # Error rate (errors)
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          /
          sum(rate(http_requests_total[5m])) by (service)
          > 0.05
        for: 5m
        labels:
          severity: critical

      # Duration/latency (covered above)
```

### USE Method (Utilization, Saturation, Errors)

For infrastructure resources:

```yaml
groups:
  - name: use_alerts
    rules:
      # CPU utilization
      - alert: HighCPUUtilization
        expr: |
          100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
          > 80
        for: 10m
        labels:
          severity: warning

      # CPU saturation (load average)
      - alert: HighLoadAverage
        expr: |
          node_load5 / count(node_cpu_seconds_total{mode="idle"}) by (instance)
          > 2.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High load average on {{ $labels.instance }}"
          description: "Load average {{ $value }} (threshold: 2.0)"

      # Disk errors
      - alert: DiskErrors
        expr: |
          rate(node_disk_io_errors_total[5m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk errors on {{ $labels.instance }}"
          description: "Device {{ $labels.device }} has I/O errors"
```

---

## SLO-Based Alerting

### What are SLOs?

**Service Level Objectives (SLOs)**: Target values for service level indicators (SLIs)
- SLI: Measurement (e.g., 95th percentile latency, error rate)
- SLO: Target (e.g., 95th percentile latency < 500ms for 99.9% of requests)
- SLA: Customer-facing contract with consequences

### Error Budget

**Error Budget**: Allowed failure within SLO period (usually 30 days)

Example:
- SLO: 99.9% availability (43.2 minutes downtime per month)
- Error budget: 0.1% (43.2 minutes)
- If burned 50% in 3 days → alert and slow deployments
- If burned 100% → freeze deployments, focus on reliability

### Multi-Window Multi-Burn Rate Alerts

**Concept**: Alert based on how fast error budget is being consumed

```yaml
groups:
  - name: slo_alerts
    rules:
      # Fast burn: 2% error budget consumed in 1 hour (page immediately)
      - alert: ErrorBudgetBurnRateFast
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[1h]))
            /
            sum(rate(http_requests_total[1h]))
          ) > (14.4 * 0.001)  # 14.4x burn rate = 2% in 1h
        for: 2m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Fast error budget burn on {{ $labels.service }}"
          description: "Burning 2% error budget per hour (14.4x)"
          runbook: "https://runbooks.example.com/slo-fast-burn"

      # Slow burn: 10% error budget consumed in 6 hours (page during business hours)
      - alert: ErrorBudgetBurnRateSlow
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[6h]))
            /
            sum(rate(http_requests_total[6h]))
          ) > (6 * 0.001)  # 6x burn rate = 10% in 6h
        for: 15m
        labels:
          severity: warning
          slo: availability
        annotations:
          summary: "Slow error budget burn on {{ $labels.service }}"
          description: "Burning 10% error budget per 6 hours"

      # Latency SLO: 95th percentile < 500ms for 99% of requests
      - alert: LatencySLOBreach
        expr: |
          (
            sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
            /
            sum(rate(http_request_duration_seconds_count[5m]))
          ) < 0.99
        for: 10m
        labels:
          severity: warning
          slo: latency
        annotations:
          summary: "Latency SLO breach on {{ $labels.service }}"
          description: "{{ $value | humanizePercentage }} requests < 500ms (target: 99%)"
```

### SLO Tracking Metrics

```yaml
# Record error budget consumption
groups:
  - name: slo_recording
    interval: 1m
    rules:
      # Availability SLI (success rate)
      - record: slo:availability:ratio_1h
        expr: |
          sum(rate(http_requests_total{status!~"5.."}[1h]))
          /
          sum(rate(http_requests_total[1h]))

      # Error budget remaining (%)
      - record: slo:availability:error_budget_remaining
        expr: |
          (
            1 - (
              sum(increase(http_requests_total{status=~"5.."}[30d]))
              /
              sum(increase(http_requests_total[30d]))
            )
          ) / 0.001 * 100  # 0.001 = 99.9% SLO

      # Latency SLI (% requests meeting latency target)
      - record: slo:latency:ratio_5m
        expr: |
          sum(rate(http_request_duration_seconds_bucket{le="0.5"}[5m]))
          /
          sum(rate(http_request_duration_seconds_count[5m]))
```

---

## Symptom-Based vs Cause-Based Alerts

### Symptom-Based Alerts (Preferred)

**Alert on customer-facing symptoms**, not internal causes.

**Good - Symptom-based**:
```yaml
- alert: APIUnavailable
  expr: probe_success{job="api-healthcheck"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "API is unavailable"
    description: "Health check failing for {{ $labels.instance }}"
```

**Bad - Cause-based**:
```yaml
# Don't page for this - it's a cause, not a symptom
- alert: HighCPU
  expr: cpu_usage > 80
  labels:
    severity: warning
```

### When to Use Cause-Based Alerts

Use cause-based alerts for **early warning** or **tickets**, not pages:

```yaml
- alert: DiskSpaceLow
  expr: disk_usage_percent > 80
  for: 30m
  labels:
    severity: warning  # Warning, not critical
  annotations:
    summary: "Disk space low on {{ $labels.instance }}"
    description: "{{ $labels.device }} at {{ $value }}%"
    action: "Create ticket for disk expansion"
```

### Cascading Alerts

**Problem**: Internal failure causes multiple symptoms to alert

**Solution**: Use inhibition rules to suppress downstream alerts

```yaml
# alertmanager.yml
inhibit_rules:
  # If database is down, don't alert on API errors
  - source_match:
      alertname: DatabaseDown
    target_match:
      alertname: APIErrors
    equal: ['datacenter']
```

---

## Alert Fatigue Prevention

### Symptoms of Alert Fatigue

- Teams ignore alerts
- Alerts muted without investigation
- Pages go unacknowledged
- High MTTD (Mean Time To Detect) despite alerting
- Team burnout and oncall stress

### Strategies to Reduce Alert Fatigue

#### 1. Increase Alert Threshold or Duration

```yaml
# Before: Too sensitive
- alert: HighErrorRate
  expr: error_rate > 0.01
  for: 1m  # Fires on transient spikes

# After: More robust
- alert: HighErrorRate
  expr: error_rate > 0.05  # Higher threshold
  for: 10m  # Longer duration to filter noise
```

#### 2. Add "for" Duration

```yaml
# Before: Fires immediately
- alert: ServiceDown
  expr: up == 0

# After: Allows for transient failures
- alert: ServiceDown
  expr: up == 0
  for: 3m  # 3 failed scrapes (1m interval)
```

#### 3. Use Recording Rules for Complex Queries

```yaml
# Recording rule (evaluated every 30s)
- record: api:error_rate:5m
  expr: |
    sum(rate(http_requests_total{status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total[5m]))

# Alert on recorded metric
- alert: HighErrorRate
  expr: api:error_rate:5m > 0.05
  for: 5m
```

#### 4. Adjust Severity Levels

```yaml
# Not everything is critical
- alert: DiskSpaceLow
  expr: disk_free_percent < 20
  labels:
    severity: warning  # Ticket, not page

- alert: DiskSpaceCritical
  expr: disk_free_percent < 5
  labels:
    severity: critical  # Page immediately
```

#### 5. Remove Non-Actionable Alerts

**Ask**: "What action should the oncall engineer take?"

If the answer is "investigate" or "nothing urgent," it shouldn't page.

#### 6. Group Related Alerts

```yaml
# Alertmanager grouping
route:
  group_by: ['alertname', 'service', 'datacenter']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 7. Implement Alert Lifecycle Reviews

Monthly review:
- Alerts that fired but were not actionable → adjust or remove
- Alerts that never fired → validate or remove
- Incidents without alerts → create new alerts

---

## Prometheus Alertmanager

### Architecture

```
Prometheus → Alertmanager → PagerDuty/Slack/Email
             (Grouping, Deduplication, Routing, Silencing)
```

### Configuration Structure

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'
  slack_api_url: 'https://hooks.slack.com/services/XXX'

# Templates for notification formatting
templates:
  - '/etc/alertmanager/templates/*.tmpl'

# Routing tree
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # Critical alerts → PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      group_wait: 10s
      repeat_interval: 1h

    # Database alerts → DB team
    - match:
        team: database
      receiver: 'database-team'
      group_wait: 30s
      repeat_interval: 12h

    # Development environment → Slack only
    - match:
        environment: dev
      receiver: 'slack-dev'
      repeat_interval: 24h

# Inhibition rules (suppress alerts)
inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service', 'instance']

  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: '(NodeHigh.*|NodeDisk.*)'
    equal: ['instance']

# Receivers (notification destinations)
receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'

  - name: 'database-team'
    email_configs:
      - to: 'db-team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts'
        auth_password: 'password'
        headers:
          Subject: '[DB] {{ .GroupLabels.alertname }}'

  - name: 'slack-dev'
    slack_configs:
      - channel: '#dev-alerts'
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
```

### Alert States

1. **Inactive**: Alert condition not met
2. **Pending**: Alert condition met, waiting for "for" duration
3. **Firing**: Alert triggered, sent to Alertmanager
4. **Resolved**: Alert condition no longer met

### Grouping

**Purpose**: Batch related alerts into single notification

```yaml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s       # Wait 30s for more alerts before first notification
  group_interval: 5m    # Wait 5m before sending new alerts in same group
  repeat_interval: 4h   # Repeat notification every 4h if still firing
```

**Example**:
- 10 pods crash simultaneously
- Without grouping: 10 separate pages
- With grouping by `alertname`: 1 page with 10 instances listed

### Routing Tree

```yaml
route:
  receiver: default
  routes:
    # P1 alerts → PagerDuty 24/7
    - match:
        severity: critical
      receiver: pagerduty
      continue: true  # Also send to Slack

    # P2 alerts → PagerDuty business hours only
    - match:
        severity: warning
      receiver: pagerduty-business-hours
      group_wait: 5m
      repeat_interval: 12h

    # Specific service → Team channel
    - match:
        service: auth-service
      receiver: auth-team-slack

    # Default → General channel
```

### Notification Templates

```go
# templates/slack.tmpl
{{ define "slack.title" }}
[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "slack.text" }}
{{ if gt (len .Alerts.Firing) 0 }}
**Firing Alerts ({{ len .Alerts.Firing }})**:
{{ range .Alerts.Firing }}
• {{ .Labels.instance }}: {{ .Annotations.summary }}
  {{ .Annotations.description }}
  Runbook: {{ .Annotations.runbook_url }}
{{ end }}
{{ end }}

{{ if gt (len .Alerts.Resolved) 0 }}
**Resolved ({{ len .Alerts.Resolved }})**:
{{ range .Alerts.Resolved }}
• {{ .Labels.instance }}
{{ end }}
{{ end }}
{{ end }}
```

### Alertmanager HA Setup

```yaml
# alertmanager1.yml
alertmanager:
  cluster:
    listen-address: "0.0.0.0:9094"
    peers:
      - alertmanager2:9094
      - alertmanager3:9094

# Prometheus configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager1:9093
            - alertmanager2:9093
            - alertmanager3:9093
```

---

## PagerDuty Integration

### Service Configuration

```yaml
# alertmanager.yml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'  # Integration key from PagerDuty
        url: 'https://events.pagerduty.com/v2/enqueue'
        severity: '{{ .GroupLabels.severity }}'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'
          instances: '{{ range .Alerts }}{{ .Labels.instance }} {{ end }}'
          runbook: '{{ .CommonAnnotations.runbook_url }}'
        client: 'Alertmanager'
        client_url: 'https://alertmanager.example.com'
```

### Multi-Service Routing

```yaml
receivers:
  # API service
  - name: 'pagerduty-api'
    pagerduty_configs:
      - service_key: 'API_SERVICE_KEY'

  # Database service
  - name: 'pagerduty-db'
    pagerduty_configs:
      - service_key: 'DB_SERVICE_KEY'

route:
  routes:
    - match:
        service: api
      receiver: pagerduty-api
    - match:
        service: database
      receiver: pagerduty-db
```

### Event Deduplication

PagerDuty deduplicates based on `dedup_key`:

```yaml
pagerduty_configs:
  - service_key: 'YOUR_SERVICE_KEY'
    # Custom dedup key
    details:
      dedup_key: '{{ .GroupLabels.alertname }}/{{ .GroupLabels.instance }}'
```

### Severity Mapping

```yaml
# Map Prometheus severity to PagerDuty severity
pagerduty_configs:
  - service_key: 'YOUR_SERVICE_KEY'
    severity: >-
      {{ if eq .GroupLabels.severity "critical" }}critical{{
         else if eq .GroupLabels.severity "warning" }}warning{{
         else }}info{{ end }}
```

### PagerDuty Best Practices

1. **One service per team**: Don't route all alerts to one service
2. **Use integration keys**: Not API keys (different purpose)
3. **Set proper severity**: Critical for pages, Warning for notifications
4. **Include runbook URLs**: Link to troubleshooting docs
5. **Configure escalation policies**: Don't rely on single oncall

---

## Opsgenie Integration

### Configuration

```yaml
# alertmanager.yml
receivers:
  - name: 'opsgenie'
    opsgenie_configs:
      - api_key: 'YOUR_API_KEY'
        api_url: 'https://api.opsgenie.com/v2/alerts'
        message: '{{ .GroupLabels.alertname }}'
        description: '{{ .CommonAnnotations.description }}'
        priority: '{{ if eq .GroupLabels.severity "critical" }}P1{{ else }}P3{{ end }}'
        tags: 'prometheus,{{ .GroupLabels.service }},{{ .GroupLabels.environment }}'
        details:
          instance: '{{ .GroupLabels.instance }}'
          runbook: '{{ .CommonAnnotations.runbook_url }}'
        responders:
          - type: 'team'
            name: 'Platform'
          - type: 'user'
            username: 'oncall@example.com'
```

### Priority Mapping

```yaml
opsgenie_configs:
  - api_key: 'YOUR_API_KEY'
    priority: >-
      {{ if eq .GroupLabels.severity "critical" }}P1{{
         else if eq .GroupLabels.severity "warning" }}P3{{
         else }}P5{{ end }}
```

### Team Routing

```yaml
# Route to different teams
route:
  routes:
    - match:
        team: frontend
      receiver: opsgenie-frontend
    - match:
        team: backend
      receiver: opsgenie-backend

receivers:
  - name: opsgenie-frontend
    opsgenie_configs:
      - api_key: 'FRONTEND_API_KEY'
        responders:
          - type: team
            name: Frontend

  - name: opsgenie-backend
    opsgenie_configs:
      - api_key: 'BACKEND_API_KEY'
        responders:
          - type: team
            name: Backend
```

---

## Alert Routing and Grouping

### Routing Strategies

#### 1. Route by Severity

```yaml
route:
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      repeat_interval: 1h

    - match:
        severity: warning
      receiver: slack
      repeat_interval: 12h
```

#### 2. Route by Service/Team

```yaml
route:
  routes:
    - match:
        team: platform
      receiver: platform-team

    - match:
        team: data
      receiver: data-team
```

#### 3. Route by Environment

```yaml
route:
  routes:
    - match:
        environment: production
      receiver: pagerduty

    - match:
        environment: staging
      receiver: slack-staging

    - match:
        environment: dev
      receiver: dev-null  # Discard
```

#### 4. Time-Based Routing

```yaml
# Using time_intervals (Alertmanager 0.24+)
time_intervals:
  - name: business_hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '17:00'
        location: 'America/New_York'

route:
  routes:
    - match:
        severity: warning
      receiver: pagerduty
      mute_time_intervals:
        - business_hours  # Only page outside business hours
```

### Grouping Strategies

#### 1. Group by Alert Name

```yaml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 5m
```

**Result**: All instances of "HighCPU" alert grouped together

#### 2. Group by Service

```yaml
route:
  group_by: ['service', 'alertname']
```

**Result**: Alerts grouped per service (e.g., "api-service: HighCPU, HighMemory")

#### 3. Group by Cluster/Region

```yaml
route:
  group_by: ['cluster', 'alertname']
```

**Result**: Regional outages grouped together

#### 4. Don't Group (Individual Notifications)

```yaml
route:
  group_by: ['...']  # Special value: don't group
```

**Use case**: Critical alerts that need immediate individual attention

---

## Escalation Policies

### Basic Escalation

```yaml
# PagerDuty-style escalation (configured in PagerDuty UI)
Level 1: Primary oncall (immediate notification)
  ↓ (15 minutes, no ack)
Level 2: Secondary oncall
  ↓ (15 minutes, no ack)
Level 3: Manager
  ↓ (30 minutes, no ack)
Level 4: Director
```

### Alertmanager-Based Escalation

```yaml
# Use routes with increasing repeat intervals
route:
  receiver: primary
  repeat_interval: 15m
  routes:
    # After 15m, escalate to secondary
    - match:
        severity: critical
      receiver: secondary
      repeat_interval: 30m
```

### Multi-Channel Escalation

```yaml
route:
  receiver: level1
  routes:
    - match:
        severity: critical
      receiver: level1
      continue: true  # Send to multiple receivers

    - match:
        severity: critical
      receiver: level2
      group_wait: 15m  # Delay 15 minutes
```

### Follow-the-Sun Escalation

```yaml
# Route based on timezone
time_intervals:
  - name: apac_hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '17:00'
        location: 'Asia/Singapore'

  - name: emea_hours
    time_intervals:
      - weekdays: ['monday:friday']
        times:
          - start_time: '09:00'
            end_time: '17:00'
        location: 'Europe/London'

route:
  routes:
    - active_time_intervals:
        - apac_hours
      receiver: apac-team

    - active_time_intervals:
        - emea_hours
      receiver: emea-team

    - receiver: americas-team  # Default
```

---

## On-Call Rotation

### Best Practices

1. **Rotation length**: 1 week (balancing continuity and burnout)
2. **Handoff process**: Sync meeting between outgoing and incoming oncall
3. **Primary + secondary**: Always have backup
4. **Fair distribution**: Use automated scheduling tools
5. **Compensation**: Oncall pay or time off in lieu

### Rotation Patterns

#### Weekly Rotation
```
Week 1: Alice (primary), Bob (secondary)
Week 2: Bob (primary), Charlie (secondary)
Week 3: Charlie (primary), Alice (secondary)
```

#### Follow-the-Sun
```
APAC hours (SGT 9am-5pm): Singapore team
EMEA hours (GMT 9am-5pm): London team
Americas hours (EST 9am-5pm): New York team
```

#### Split Rotation
```
Weekday oncall: Senior engineers (Mon-Fri)
Weekend oncall: All engineers rotate
```

### Oncall Handoff Checklist

```markdown
## Oncall Handoff Template

**Outgoing Oncall**: Alice
**Incoming Oncall**: Bob
**Date**: 2025-10-27

### Incidents This Week
- [INC-123] API latency spike (resolved, root cause: DB query regression)
- [INC-124] Partial outage in us-west-2 (ongoing, escalated to AWS support)

### Ongoing Issues
- Disk space on db-prod-01 at 75% (monitoring, expansion scheduled for Friday)
- Elevated error rate on /api/search (engineering investigating)

### Upcoming Maintenance
- Database upgrade: Saturday 2am-4am EST
- Certificate renewal: Monday 10am EST

### Notes
- PagerDuty escalation policy updated (Level 2 now goes to Bob)
- New runbook for HighMemory alert: https://runbooks.example.com/high-memory
```

### Oncall Metrics

```promql
# Track oncall burden
- record: oncall:alerts_per_week
  expr: |
    sum(increase(ALERTS{severity="critical"}[7d])) by (service)

- record: oncall:pages_per_person
  expr: |
    sum(increase(pagerduty_incidents_total[7d])) by (oncall_user)

- record: oncall:mttr
  expr: |
    avg(pagerduty_incident_duration_seconds) by (service)
```

---

## Runbooks

### What is a Runbook?

A runbook is a step-by-step guide for responding to an alert. Every alert should have a runbook URL.

### Runbook Structure

```markdown
# Alert: HighMemoryUsage

## Overview
This alert fires when memory usage exceeds 90% for 5 minutes.

## Impact
- Service may become unresponsive
- OOM killer may terminate processes
- Customer requests may timeout

## Severity
Warning (escalate to Critical if > 95% or duration > 30m)

## Diagnosis

### 1. Check current memory usage
\`\`\`bash
ssh <instance>
free -h
top -o %MEM
\`\`\`

### 2. Identify memory-consuming processes
\`\`\`bash
ps aux --sort=-%mem | head -20
\`\`\`

### 3. Check for memory leaks
\`\`\`bash
# View process memory over time
cat /proc/<pid>/status | grep VmRSS
\`\`\`

## Remediation

### Immediate (< 5 min)
1. **Restart leaking service** (if identified):
   \`\`\`bash
   systemctl restart <service>
   \`\`\`

2. **Drop caches** (temporary relief):
   \`\`\`bash
   echo 3 > /proc/sys/vm/drop_caches
   \`\`\`

3. **Scale horizontally** (if load balancer allows):
   \`\`\`bash
   kubectl scale deployment <app> --replicas=<N+1>
   \`\`\`

### Short-term (< 1 hour)
1. Investigate memory leak in application logs
2. Review recent deployments for regressions
3. Analyze heap dumps (if Java/JVM app)

### Long-term
1. Increase instance memory (infrastructure change)
2. Optimize application memory usage
3. Implement memory limits (cgroups, Kubernetes resources)

## Escalation
- If memory > 95%: Page oncall manager
- If OOM events occur: Page service owner + oncall manager
- If affecting customers: Open incident bridge

## Related Alerts
- OOMKiller: Indicates OOM events occurred
- HighSwapUsage: Memory pressure spilling to swap

## References
- Grafana dashboard: https://grafana.example.com/d/memory
- Application docs: https://docs.example.com/memory-tuning
- Previous incidents: INC-456, INC-789

## Last Updated
2025-10-27 by Alice
```

### Runbook Best Practices

1. **Link from alerts**:
   ```yaml
   annotations:
     runbook_url: "https://runbooks.example.com/high-memory"
   ```

2. **Keep it actionable**: Focus on "what to do," not "why it happens"

3. **Include commands**: Copy-pasteable commands with placeholders

4. **Update after incidents**: Post-mortem should update runbooks

5. **Version control**: Store in Git, not Wiki

6. **Test regularly**: Oncall should practice runbooks in drills

### Runbook Repository Structure

```
runbooks/
├── README.md
├── alerts/
│   ├── high-memory.md
│   ├── high-cpu.md
│   ├── disk-full.md
│   ├── service-down.md
│   └── high-latency.md
├── services/
│   ├── api-service.md
│   ├── database.md
│   └── cache.md
├── infrastructure/
│   ├── kubernetes.md
│   ├── load-balancer.md
│   └── networking.md
└── templates/
    └── runbook-template.md
```

---

## Alert Inhibition and Silencing

### Inhibition Rules

**Purpose**: Suppress alerts when a root cause alert is firing

```yaml
# alertmanager.yml
inhibit_rules:
  # If datacenter is down, suppress all alerts from that datacenter
  - source_match:
      alertname: DatacenterDown
    target_match_re:
      alertname: '.*'
    equal: ['datacenter']

  # If node is down, suppress all alerts from that node
  - source_match:
      alertname: NodeDown
    target_match_re:
      alertname: '(HighCPU|HighMemory|DiskFull)'
    equal: ['instance']

  # If critical alert is firing, suppress warnings
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service']

  # If database is down, suppress connection errors
  - source_match:
      alertname: DatabaseDown
    target_match:
      alertname: DatabaseConnectionErrors
    equal: ['database', 'cluster']
```

### Silencing

**Purpose**: Temporarily suppress alerts (e.g., during maintenance)

#### Via UI

```
Alertmanager UI → Silences → New Silence
- Matchers: alertname=DiskFull, instance=db-01
- Duration: 2 hours
- Creator: alice@example.com
- Comment: "Disk expansion in progress"
```

#### Via CLI (amtool)

```bash
# Silence specific alert
amtool silence add \
  alertname=DiskFull \
  instance=db-01 \
  --duration=2h \
  --author="alice@example.com" \
  --comment="Disk expansion maintenance"

# Silence by regex
amtool silence add \
  alertname=~'High.*' \
  environment=staging \
  --duration=24h

# List active silences
amtool silence query

# Expire a silence
amtool silence expire <silence-id>
```

#### Silence During Deployments

```bash
# Silence all alerts for a service during deployment
deploy_with_silence() {
  SILENCE_ID=$(amtool silence add \
    service=api \
    --duration=30m \
    --comment="Deployment in progress" \
    --quiet)

  # Run deployment
  kubectl apply -f deployment.yaml
  kubectl rollout status deployment/api

  # Remove silence
  amtool silence expire $SILENCE_ID
}
```

### Maintenance Windows

```yaml
# Use time_intervals for recurring maintenance
time_intervals:
  - name: maintenance_window
    time_intervals:
      - weekdays: ['sunday']
        times:
          - start_time: '02:00'
            end_time: '04:00'

route:
  mute_time_intervals:
    - maintenance_window
```

---

## Notification Channels

### Email

```yaml
receivers:
  - name: email
    email_configs:
      - to: 'ops@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'password'
        headers:
          Subject: '[{{ .Status }}] {{ .GroupLabels.alertname }}'
        html: '{{ template "email.html" . }}'
        text: '{{ template "email.text" . }}'
```

### Slack

```yaml
receivers:
  - name: slack
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
        channel: '#alerts'
        username: 'Alertmanager'
        icon_emoji: ':fire:'
        title: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
        actions:
          - type: button
            text: 'View Runbook'
            url: '{{ .CommonAnnotations.runbook_url }}'
          - type: button
            text: 'Silence'
            url: 'https://alertmanager.example.com/#/silences/new'
```

### Microsoft Teams

```yaml
receivers:
  - name: teams
    webhook_configs:
      - url: 'https://outlook.office.com/webhook/XXX/IncomingWebhook/YYY'
        send_resolved: true
```

### Discord

```yaml
receivers:
  - name: discord
    webhook_configs:
      - url: 'https://discord.com/api/webhooks/XXX/YYY'
        send_resolved: true
```

### Custom Webhooks

```yaml
receivers:
  - name: custom-webhook
    webhook_configs:
      - url: 'https://api.example.com/alerts'
        send_resolved: true
        http_config:
          bearer_token: 'YOUR_TOKEN'
        max_alerts: 0  # Send all alerts
```

### Multi-Channel Notifications

```yaml
route:
  receiver: multi-channel
  routes:
    - match:
        severity: critical
      receiver: multi-channel
      continue: true

receivers:
  - name: multi-channel
    pagerduty_configs:
      - service_key: 'PAGERDUTY_KEY'  # Page oncall
    slack_configs:
      - channel: '#incidents'  # Also notify Slack
    email_configs:
      - to: 'ops@example.com'  # And email
```

---

## Dashboards for Alerts

### Alert Overview Dashboard

```promql
# Total active alerts
sum(ALERTS{alertstate="firing"})

# Active alerts by severity
sum(ALERTS{alertstate="firing"}) by (severity)

# Alert trends (last 24h)
sum(increase(ALERTS[24h])) by (alertname)

# Top firing alerts
topk(10, sum(ALERTS{alertstate="firing"}) by (alertname))

# Alert flapping (firing/resolved cycles)
sum(changes(ALERTS[1h])) by (alertname)
```

### Alertmanager Dashboard

```promql
# Notifications sent
sum(rate(alertmanager_notifications_total[5m])) by (integration)

# Notification failures
sum(rate(alertmanager_notifications_failed_total[5m])) by (integration)

# Silences active
alertmanager_silences

# Alerts suppressed by inhibition
alertmanager_alerts_suppressed_total
```

### SLO Dashboard

```promql
# Error budget remaining
slo:availability:error_budget_remaining

# Burn rate (1h, 6h, 24h)
slo:availability:burn_rate_1h
slo:availability:burn_rate_6h
slo:availability:burn_rate_24h

# Time to exhaust error budget
predict_linear(slo:availability:error_budget_remaining[1h], 30*24*3600)
```

### Oncall Metrics Dashboard

```promql
# Alerts per day
sum(increase(ALERTS{alertstate="firing",severity="critical"}[24h]))

# Mean time to acknowledge (MTTA)
avg(pagerduty_incident_acknowledge_time_seconds)

# Mean time to resolve (MTTR)
avg(pagerduty_incident_resolve_time_seconds)

# Alerts by service
sum(ALERTS{alertstate="firing"}) by (service)

# Oncall load (alerts per person)
sum(increase(pagerduty_incidents_total[7d])) by (user)
```

---

## Testing Alerting Systems

### Manual Testing

```bash
# Test alert rule evaluation
promtool check rules /etc/prometheus/alerts/*.yml

# Test Alertmanager config
amtool check-config /etc/alertmanager/alertmanager.yml

# Send test alert to Alertmanager
amtool alert add test \
  alertname=TestAlert \
  severity=critical \
  instance=test-instance \
  --annotation=description="This is a test alert" \
  --end=$(date -d '+5min' +%s)
```

### Automated Testing

```python
#!/usr/bin/env python3
"""Test alerting pipeline end-to-end."""
import requests
import time

def send_test_alert():
    """Send test alert to Alertmanager."""
    alert = {
        "labels": {
            "alertname": "TestAlert",
            "severity": "critical",
            "service": "test"
        },
        "annotations": {
            "summary": "Test alert",
            "description": "Automated test"
        },
        "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 300))
    }

    response = requests.post(
        "http://alertmanager:9093/api/v1/alerts",
        json=[alert]
    )
    return response.status_code == 200

def verify_notification(channel):
    """Verify notification was sent to channel."""
    # Check Slack, PagerDuty API, etc.
    pass

if __name__ == "__main__":
    assert send_test_alert(), "Failed to send test alert"
    time.sleep(60)
    assert verify_notification("slack"), "Notification not received"
    print("Alert test passed")
```

### Integration Testing

```bash
# Test Prometheus → Alertmanager → PagerDuty
# 1. Trigger alert condition
curl -X POST http://pushgateway:9091/metrics/job/test -d '
test_metric 100
'

# 2. Wait for Prometheus to evaluate (15s)
sleep 20

# 3. Check Alertmanager received alert
curl http://alertmanager:9093/api/v1/alerts | jq '.data[] | select(.labels.alertname=="TestAlert")'

# 4. Verify PagerDuty incident created
curl -H "Authorization: Token token=PAGERDUTY_API_KEY" \
  https://api.pagerduty.com/incidents | jq '.incidents[] | select(.title | contains("TestAlert"))'
```

### Chaos Testing

```bash
# Test oncall response to simulated outages
# 1. Kill service pod
kubectl delete pod -l app=api-server --grace-period=0

# 2. Verify alert fires within SLA (e.g., 2 minutes)
# 3. Verify oncall receives page
# 4. Time oncall response
# 5. Verify runbook is accurate
```

---

## Metrics for Alert Health

### Alert Quality Metrics

```promql
# Alert precision (% of alerts that were actionable)
alert_precision = actionable_alerts / total_alerts

# Alert recall (% of incidents that triggered alerts)
alert_recall = incidents_with_alerts / total_incidents

# False positive rate
false_positive_rate = false_positive_alerts / total_alerts

# Alert latency (time from issue to alert)
alert_latency = alert_timestamp - issue_start_time
```

### Recording Rules for Alert Metrics

```yaml
groups:
  - name: alert_health
    interval: 5m
    rules:
      # Total alerts fired in last 24h
      - record: alerts:fired:24h
        expr: sum(increase(ALERTS{alertstate="firing"}[24h]))

      # Alert flapping (changed state > 5 times in 1h)
        - record: alerts:flapping:1h
        expr: sum(changes(ALERTS[1h]) > 5) by (alertname)

      # Time in alert state
      - record: alerts:duration:seconds
        expr: time() - ALERTS_FOR_STATE

      # Alerts by team
      - record: alerts:by_team:24h
        expr: sum(increase(ALERTS{alertstate="firing"}[24h])) by (team)
```

### Alertmanager Metrics

```promql
# Notification success rate
sum(rate(alertmanager_notifications_total[5m])) by (integration)
/
(sum(rate(alertmanager_notifications_total[5m])) by (integration)
 + sum(rate(alertmanager_notifications_failed_total[5m])) by (integration))

# Notification latency
histogram_quantile(0.95,
  rate(alertmanager_notification_latency_seconds_bucket[5m])
) by (integration)

# Alert processing rate
rate(alertmanager_alerts_received_total[5m])

# Silences active
alertmanager_silences{state="active"}
```

---

## Production Best Practices

### Alert Design Checklist

- [ ] Alert is symptom-based (customer impact), not cause-based
- [ ] Alert has clear severity (critical = page, warning = ticket)
- [ ] Alert includes "for" duration to filter transient issues
- [ ] Alert threshold is tuned to minimize false positives
- [ ] Alert has descriptive summary and description
- [ ] Alert links to runbook
- [ ] Alert includes relevant labels (service, team, environment)
- [ ] Alert has been tested (manually or automatically)

### Runbook Checklist

- [ ] Clear overview of what the alert means
- [ ] Impact statement (what breaks if not addressed)
- [ ] Diagnosis steps with commands
- [ ] Remediation steps (immediate, short-term, long-term)
- [ ] Escalation criteria
- [ ] Links to dashboards, docs, related alerts
- [ ] Last updated date and author

### Alertmanager Best Practices

1. **Use inhibition rules** to suppress cascading alerts
2. **Group alerts** to reduce notification fatigue
3. **Route by severity and team** for appropriate response
4. **Set repeat_interval** appropriately (1h for critical, 12h for warnings)
5. **Run Alertmanager in HA mode** (3 instances minimum)
6. **Use templates** for consistent notification formatting
7. **Monitor Alertmanager itself** (meta-monitoring)

### Oncall Best Practices

1. **Rotate fairly**: Use automated scheduling, balance load
2. **Handoff properly**: Sync meeting with notes
3. **Document everything**: Runbooks, incident reports, postmortems
4. **Practice runbooks**: Oncall drills and game days
5. **Respect oncall time**: Minimize pages, compensate appropriately
6. **Learn from incidents**: Update runbooks and alerts after each incident

### Alert Lifecycle

```
1. Create alert → 2. Test alert → 3. Deploy to staging
  ↓
4. Monitor for false positives → 5. Tune threshold/duration
  ↓
6. Deploy to production → 7. Document in runbook
  ↓
8. Monthly review → 9. Adjust or remove based on data
```

---

## Troubleshooting Guide

### Alerts Not Firing

**Symptoms**: Expected alert is not firing

**Diagnosis**:
```bash
# 1. Check if metric exists
curl 'http://prometheus:9090/api/v1/query?query=my_metric'

# 2. Check alert rule evaluation
curl http://prometheus:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name=="MyAlert")'

# 3. Check alert state
curl http://prometheus:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="MyAlert")'

# 4. Test rule locally
promtool query instant http://prometheus:9090 'my_metric > 100'
```

**Solutions**:
- Verify metric is being scraped
- Check alert expression for errors
- Verify "for" duration hasn't prevented firing
- Check if alert is inhibited or silenced

### Alerts Not Reaching Alertmanager

**Symptoms**: Alert firing in Prometheus but not in Alertmanager

**Diagnosis**:
```bash
# Check Prometheus alertmanager targets
curl http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="alertmanager")'

# Check Prometheus logs
kubectl logs prometheus-0 | grep -i alertmanager
```

**Solutions**:
- Verify Alertmanager is reachable from Prometheus
- Check Prometheus configuration `alerting.alertmanagers`
- Check firewall rules

### Notifications Not Sent

**Symptoms**: Alert in Alertmanager but no notification

**Diagnosis**:
```bash
# Check Alertmanager alerts
curl http://alertmanager:9093/api/v1/alerts

# Check notification metrics
curl http://alertmanager:9093/metrics | grep notification

# Check Alertmanager logs
kubectl logs alertmanager-0 | grep -i notification
```

**Solutions**:
- Verify receiver configuration (API keys, webhooks)
- Check routing rules match alert labels
- Check if alert is silenced
- Verify notification channel is working (test manually)

### Alert Flapping

**Symptoms**: Alert repeatedly firing and resolving

**Diagnosis**:
```promql
# Check alert state changes
changes(ALERTS{alertname="MyAlert"}[1h])
```

**Solutions**:
- Increase "for" duration
- Adjust threshold (add hysteresis)
- Use recording rules for smoother metrics
- Investigate underlying cause (resource thrashing, network instability)

### Too Many Notifications

**Symptoms**: Notification fatigue, duplicate pages

**Solutions**:
- Increase `group_interval` and `repeat_interval`
- Add `group_by` labels to batch related alerts
- Use inhibition rules for cascading failures
- Review and remove noisy alerts

### Silences Not Working

**Diagnosis**:
```bash
# List active silences
amtool silence query

# Check if silence matchers are correct
amtool silence query --active | jq '.[] | select(.comment | contains("my-silence"))'
```

**Solutions**:
- Verify matchers match alert labels exactly
- Check silence hasn't expired
- Ensure label names are correct (case-sensitive)

---

## Examples and Templates

### Complete Alert Rule Example

```yaml
groups:
  - name: slo_alerts
    interval: 30s
    rules:
      # SLO-based error budget burn rate
      - alert: ErrorBudgetBurnRateFast
        expr: |
          (
            sum(rate(http_requests_total{job="api",status=~"5.."}[1h]))
            /
            sum(rate(http_requests_total{job="api"}[1h]))
          ) > 0.0144  # 14.4x burn rate (2% budget in 1h)
        for: 2m
        labels:
          severity: critical
          service: api
          team: platform
          slo: availability
        annotations:
          summary: "Fast error budget burn on API"
          description: |
            API is burning error budget at 14.4x rate
            Current error rate: {{ $value | humanizePercentage }}
            At this rate, monthly error budget will be exhausted in 2 days
          impact: "Customer requests may be failing"
          runbook_url: "https://runbooks.example.com/error-budget-burn"
          dashboard_url: "https://grafana.example.com/d/slo-api"
          playbook: |
            1. Check recent deployments: kubectl rollout history deployment/api
            2. Review error logs: kubectl logs -l app=api --tail=100
            3. Check upstream dependencies: curl -I https://database/health
            4. If deployment related: kubectl rollout undo deployment/api

      # Symptom-based alert
      - alert: APIUnavailable
        expr: probe_success{job="api-healthcheck"} == 0
        for: 2m
        labels:
          severity: critical
          service: api
          team: platform
        annotations:
          summary: "API is unavailable"
          description: "Health check failing for {{ $labels.instance }} for 2+ minutes"
          impact: "All customer API requests are failing"
          runbook_url: "https://runbooks.example.com/api-unavailable"

      # Resource saturation
      - alert: HighMemoryUsage
        expr: |
          100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
          > 90
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage {{ $value | humanize }}%"
          runbook_url: "https://runbooks.example.com/high-memory"
```

### Complete Alertmanager Config

```yaml
global:
  resolve_timeout: 5m
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'
  slack_api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # Critical alerts → PagerDuty + Slack
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      group_wait: 10s
      repeat_interval: 1h
      continue: true

    - match:
        severity: critical
      receiver: 'slack-incidents'

    # Warning alerts → Slack only
    - match:
        severity: warning
      receiver: 'slack-warnings'
      group_wait: 5m
      repeat_interval: 12h

    # Team-specific routing
    - match:
        team: database
      receiver: 'database-team'

    # Non-production → Low priority
    - match_re:
        environment: '(dev|staging)'
      receiver: 'slack-dev'
      repeat_interval: 24h

inhibit_rules:
  # If critical, suppress warnings
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service']

  # If datacenter down, suppress everything from that DC
  - source_match:
      alertname: DatacenterDown
    target_match_re:
      alertname: '.*'
    equal: ['datacenter']

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}'

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        severity: 'critical'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          instances: '{{ range .Alerts }}{{ .Labels.instance }} {{ end }}'
          runbook: '{{ .CommonAnnotations.runbook_url }}'

  - name: 'slack-incidents'
    slack_configs:
      - channel: '#incidents'
        color: 'danger'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Instance*: {{ .Labels.instance }}
          *Description*: {{ .Annotations.description }}
          *Runbook*: {{ .Annotations.runbook_url }}
          {{ end }}

  - name: 'slack-warnings'
    slack_configs:
      - channel: '#monitoring'
        color: 'warning'

  - name: 'database-team'
    email_configs:
      - to: 'db-team@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts'
        auth_password: '${SMTP_PASSWORD}'  # Environment variable - set securely before running

  - name: 'slack-dev'
    slack_configs:
      - channel: '#dev-alerts'
```

---

## Conclusion

Effective monitoring and alerting is about:
1. **Alerting on symptoms** (customer impact), not causes
2. **Preventing alert fatigue** through thoughtful design
3. **Routing alerts** to the right team with the right priority
4. **Providing context** via runbooks and dashboards
5. **Continuously improving** based on incident learnings

Key takeaways:
- Use SLO-based alerts for user-facing services
- Follow the Four Golden Signals (latency, traffic, errors, saturation)
- Every alert should be actionable and have a runbook
- Group and route alerts to minimize noise
- Monitor your monitoring (meta-monitoring)
- Review and tune alerts regularly

**Next Steps**:
1. Implement SLO-based alerting for critical services
2. Create runbooks for all existing alerts
3. Set up escalation policies and oncall rotation
4. Add meta-monitoring for Alertmanager
5. Conduct monthly alert review meetings
6. Practice incident response through chaos drills

---

**Document Version**: 1.0
**Last Updated**: 2025-10-27
**Maintained By**: Platform Team
