---
name: observability-dashboard-design
description: Building Grafana dashboards for service monitoring
---



# Dashboard Design

**Scope**: Grafana, visualization types, SLO dashboards, troubleshooting views, panel best practices

**Lines**: 376

**Last Updated**: 2025-10-18

---

## When to Use This Skill

Use this skill when:
- Building Grafana dashboards for service monitoring
- Designing SLO/SLI dashboards for stakeholders
- Creating troubleshooting views for on-call engineers
- Visualizing metrics from Prometheus, Loki, or other data sources
- Implementing RED (Rate, Errors, Duration) dashboards
- Building executive dashboards showing business metrics
- Designing real-time operational dashboards
- Creating custom alerting views

**Don't use** for:
- Static reports (use BI tools like Tableau, Looker)
- Ad-hoc data exploration (use Jupyter notebooks)
- Long-term trend analysis (use dedicated analytics platforms)

---

## Core Concepts

### Dashboard Types

**1. Service Dashboard** (Operational)
- Target audience: Engineers, on-call
- Focus: System health, errors, latency
- Update frequency: Real-time (5s-30s)
- Metrics: RED (Rate, Errors, Duration)

**2. SLO Dashboard** (Business)
- Target audience: Managers, stakeholders
- Focus: Reliability targets, error budgets
- Update frequency: Hourly/daily
- Metrics: Availability, latency percentiles, error budget burn

**3. Troubleshooting Dashboard** (Diagnostic)
- Target audience: On-call engineers
- Focus: Detailed system state, dependencies
- Update frequency: Real-time (1s-5s)
- Metrics: Resource usage, request flow, errors by endpoint

**4. Executive Dashboard** (Strategic)
- Target audience: Leadership
- Focus: High-level KPIs, trends
- Update frequency: Daily/weekly
- Metrics: Uptime, revenue, active users

### Visualization Types

**Time Series Graph**: Trends over time
- Use for: Latency, throughput, error rate
- Best for: Spotting patterns, anomalies

**Gauge**: Single value with thresholds
- Use for: Current status (CPU, memory, disk)
- Best for: At-a-glance health checks

**Stat Panel**: Single metric value
- Use for: Totals, percentages, counts
- Best for: KPIs, summary metrics

**Heatmap**: Distribution over time
- Use for: Latency distribution, bucket histograms
- Best for: Identifying percentile outliers

**Table**: Multi-dimensional data
- Use for: Service list, error breakdown
- Best for: Detailed comparisons

**Bar Chart**: Compare categories
- Use for: Error counts by endpoint, requests by region
- Best for: Top-N comparisons

### RED Method

**Rate**: Requests per second
```promql
rate(http_requests_total[5m])
```

**Errors**: Error percentage
```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
* 100
```

**Duration**: Latency percentiles
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### USE Method (Resources)

**Utilization**: % time resource busy
```promql
cpu_usage_percent
memory_usage_percent
```

**Saturation**: Degree of queuing/waiting
```promql
queue_depth
connection_pool_waiting
```

**Errors**: Error count/rate
```promql
rate(disk_errors_total[5m])
rate(network_errors_total[5m])
```

---

## Patterns

### Pattern 1: Service Overview Dashboard (Grafana JSON)

```json
{
  "dashboard": {
    "title": "API Service Overview",
    "tags": ["service", "api"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service=\"api\"}[5m]))",
            "legendFormat": "Total Requests/sec"
          }
        ],
        "yaxes": [
          {"format": "reqps", "label": "Requests/sec"}
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service=\"api\",status=~\"5..\"}[5m])) / sum(rate(http_requests_total{service=\"api\"}[5m])) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [1]},
              "operator": {"type": "and"},
              "query": {"params": ["A", "5m", "now"]},
              "type": "query"
            }
          ]
        }
      },
      {
        "title": "Latency (P50, P95, P99)",
        "type": "graph",
        "gridPos": {"x": 0, "y": 8, "w": 24, "h": 8},
        "targets": [
          {
            "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{service=\"api\"}[5m])) by (le))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service=\"api\"}[5m])) by (le))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=\"api\"}[5m])) by (le))",
            "legendFormat": "P99"
          }
        ],
        "yaxes": [
          {"format": "s", "label": "Latency"}
        ]
      }
    ]
  }
}
```

### Pattern 2: SLO Dashboard

```json
{
  "dashboard": {
    "title": "SLO Dashboard - 99.9% Availability",
    "panels": [
      {
        "title": "Availability (30d)",
        "type": "stat",
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status!~\"5..\"}[30d])) / sum(rate(http_requests_total[30d])) * 100"
          }
        ],
        "options": {
          "colorMode": "background",
          "graphMode": "none",
          "textMode": "value_and_name"
        },
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 99, "color": "yellow"},
                {"value": 99.9, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "title": "Error Budget Remaining (30d)",
        "type": "gauge",
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "(0.001 - (1 - sum(rate(http_requests_total{status!~\"5..\"}[30d])) / sum(rate(http_requests_total[30d])))) / 0.001 * 100"
          }
        ],
        "options": {
          "showThresholdLabels": true,
          "showThresholdMarkers": true
        },
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 25, "color": "yellow"},
                {"value": 50, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "title": "Error Budget Burn Rate",
        "type": "graph",
        "gridPos": {"x": 0, "y": 4, "w": 24, "h": 8},
        "targets": [
          {
            "expr": "(sum(rate(http_requests_total{status=~\"5..\"}[1h])) / sum(rate(http_requests_total[1h]))) / 0.001",
            "legendFormat": "1h burn rate (1.0 = on track)"
          },
          {
            "expr": "(sum(rate(http_requests_total{status=~\"5..\"}[6h])) / sum(rate(http_requests_total[6h]))) / 0.001",
            "legendFormat": "6h burn rate"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"type": "gt", "params": [10]},
              "query": {"params": ["A", "5m", "now"]}
            }
          ],
          "name": "Error budget burning 10x faster"
        }
      }
    ]
  }
}
```

### Pattern 3: Troubleshooting Dashboard

```json
{
  "dashboard": {
    "title": "Troubleshooting - API Service",
    "panels": [
      {
        "title": "Requests by Endpoint (Top 10)",
        "type": "table",
        "targets": [
          {
            "expr": "topk(10, sum by (endpoint) (rate(http_requests_total{service=\"api\"}[5m])))",
            "format": "table",
            "instant": true
          }
        ]
      },
      {
        "title": "Errors by Endpoint",
        "type": "bargauge",
        "targets": [
          {
            "expr": "sum by (endpoint) (rate(http_requests_total{service=\"api\",status=~\"5..\"}[5m]))"
          }
        ],
        "options": {
          "orientation": "horizontal",
          "displayMode": "gradient"
        }
      },
      {
        "title": "Latency Heatmap",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum(rate(http_request_duration_seconds_bucket{service=\"api\"}[5m])) by (le)",
            "format": "heatmap"
          }
        ],
        "heatmap": {
          "yAxis": {"format": "s", "decimals": 2}
        }
      },
      {
        "title": "Database Connection Pool",
        "type": "graph",
        "targets": [
          {
            "expr": "database_connections{state=\"active\"}",
            "legendFormat": "Active"
          },
          {
            "expr": "database_connections{state=\"idle\"}",
            "legendFormat": "Idle"
          },
          {
            "expr": "database_connections_max",
            "legendFormat": "Max"
          }
        ]
      }
    ]
  }
}
```

### Pattern 4: Resource Usage Dashboard

```json
{
  "dashboard": {
    "title": "Resource Usage",
    "panels": [
      {
        "title": "CPU Usage by Instance",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{ instance }}"
          }
        ],
        "yaxes": [
          {"format": "percent", "max": 100}
        ]
      },
      {
        "title": "Memory Usage by Instance",
        "type": "graph",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "{{ instance }}"
          }
        ],
        "yaxes": [
          {"format": "percent", "max": 100}
        ]
      },
      {
        "title": "Disk I/O",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_disk_read_bytes_total[5m])",
            "legendFormat": "Read - {{ device }}"
          },
          {
            "expr": "rate(node_disk_written_bytes_total[5m])",
            "legendFormat": "Write - {{ device }}"
          }
        ],
        "yaxes": [
          {"format": "Bps"}
        ]
      }
    ]
  }
}
```

### Pattern 5: Business Metrics Dashboard

```json
{
  "dashboard": {
    "title": "Business Metrics",
    "panels": [
      {
        "title": "Revenue (Last 24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(revenue_total_dollars[24h]))"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD",
            "decimals": 2
          }
        }
      },
      {
        "title": "Orders by Product Category",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (product_category) (increase(orders_total[24h]))"
          }
        ]
      },
      {
        "title": "Active Users (Last 30 days)",
        "type": "graph",
        "targets": [
          {
            "expr": "count(count by (user_id) (increase(user_activity_total[24h])))"
          }
        ]
      },
      {
        "title": "Cart Abandonment Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(increase(cart_abandonment_total[24h])) / sum(increase(cart_created_total[24h])) * 100"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 50, "color": "yellow"},
                {"value": 70, "color": "red"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

---

## Quick Reference

### Dashboard Design Principles

1. **Most important metrics first** (top-left)
2. **Logical grouping** (related panels together)
3. **Consistent time ranges** (use dashboard-level variable)
4. **Clear titles** (action-oriented: "Check latency" not "Latency")
5. **Appropriate colors** (red for errors, green for success)
6. **Thresholds** (visual indicators for good/bad states)
7. **Legends** (concise, meaningful labels)

### Panel Layout Guidelines

```
+------------------------------------------+
|  Critical KPIs (Stats/Gauges)            |  ← Row 1: 4 panels
+------------------------------------------+
|  Trends (Time Series)                    |  ← Row 2: 2-3 panels
+------------------------------------------+
|  Detailed Breakdown (Tables/Bar Charts)  |  ← Row 3: 1-2 panels
+------------------------------------------+
|  Resource Usage (Graphs)                 |  ← Row 4: 2-3 panels
+------------------------------------------+
```

### Common PromQL Patterns

```promql
# Rate (requests/sec)
rate(metric_total[5m])

# Error rate (%)
sum(rate(errors[5m])) / sum(rate(requests[5m])) * 100

# Percentiles
histogram_quantile(0.95, rate(metric_bucket[5m]))

# Top N
topk(10, sum by (label) (rate(metric[5m])))

# Aggregation
sum by (service) (rate(metric[5m]))
avg by (instance) (metric)
max by (region) (metric)

# Math
metric1 / metric2  # Ratio
metric1 - metric2  # Difference
metric1 > 100      # Filter
```

### Grafana Variables

```
# Service selector
Name: service
Query: label_values(http_requests_total, service)
Usage: {service="$service"}

# Time range
Name: range
Type: Interval
Values: 5m,15m,1h,6h,24h
Usage: rate(metric[$range])

# Instance selector
Name: instance
Query: label_values(up{service="$service"}, instance)
Usage: {instance=~"$instance"}
```

---

## Anti-Patterns

### ❌ Too Many Panels

```
# WRONG: 50 panels on one dashboard (overwhelming)
# CORRECT: 8-12 panels max, use drill-down links
```

### ❌ No Thresholds

```json
// WRONG: Plain graph with no visual indicators
{"type": "graph"}

// CORRECT: Color-coded thresholds
{
  "type": "graph",
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          {"value": 0, "color": "green"},
          {"value": 80, "color": "yellow"},
          {"value": 90, "color": "red"}
        ]
      }
    }
  }
}
```

### ❌ Inconsistent Time Ranges

```
# WRONG: Panel 1 uses [5m], Panel 2 uses [1h]
# CORRECT: Use dashboard variable $range
```

### ❌ Raw Counters Instead of Rates

```promql
# WRONG: Counter value (meaningless)
http_requests_total

# CORRECT: Rate (requests/sec)
rate(http_requests_total[5m])
```

### ❌ Missing Context in Titles

```
# WRONG: "Requests"
# CORRECT: "API Requests per Second (5m avg)"
```

### ❌ Too Much Data in Tables

```
# WRONG: 1000 rows in table
topk(1000, metric)

# CORRECT: Top 10
topk(10, metric)
```

---

## Related Skills

- **metrics-instrumentation.md** - Define metrics for dashboards
- **structured-logging.md** - Link logs from dashboard panels
- **distributed-tracing.md** - Drill down to traces
- **alerting-strategy.md** - Dashboard-based alert status

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
