---
name: engineering-log-aggregation
description: Production-ready log aggregation and centralized logging strategies
---

# Log Aggregation

**Scope**: Centralized logging, ELK/EFK stack, Loki, Vector, structured logging, log parsing, retention, search patterns, alerting, Kubernetes logging, cloud logging, cost optimization

**Lines**: 362

**Last Updated**: 2025-10-29

---

## When to Use This Skill

Use this skill when:
- Designing centralized logging architecture
- Implementing ELK Stack (Elasticsearch, Logstash, Kibana)
- Setting up EFK Stack (Elasticsearch, Fluentd, Kibana)
- Deploying Loki + Promtail for lightweight logging
- Using Vector for high-performance log pipelines
- Implementing structured logging across services
- Parsing and enriching log data
- Setting up log retention and rotation policies
- Creating log-based alerts
- Optimizing logging costs
- Implementing Kubernetes logging patterns
- Integrating cloud logging services

**Don't use** for:
- Application instrumentation (use metrics-instrumentation.md)
- Distributed tracing (use observability-distributed-tracing.md)
- Metrics collection (use prometheus-monitoring.md)

---

## Core Concepts

### Log Aggregation Architecture

**Four-layer model**:

```
┌─────────────┐
│ Application │ → Structured logs (JSON)
└─────────────┘
       ↓
┌─────────────┐
│ Collection  │ → Agent (Filebeat, Fluentd, Promtail, Vector)
└─────────────┘
       ↓
┌─────────────┐
│ Transport   │ → Buffer/Queue (Kafka, Redis)
└─────────────┘
       ↓
┌─────────────┐
│  Storage    │ → Backend (Elasticsearch, Loki, S3)
└─────────────┘
       ↓
┌─────────────┐
│  Analysis   │ → UI (Kibana, Grafana)
└─────────────┘
```

### Structured Logging

**JSON format**:
```json
{
  "timestamp": "2025-10-29T10:30:45.123Z",
  "level": "ERROR",
  "service": "api-gateway",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "Failed to process request",
  "error": {
    "type": "TimeoutError",
    "message": "Database query timeout",
    "stack": "..."
  },
  "context": {
    "user_id": "user_123",
    "endpoint": "/api/users",
    "method": "GET",
    "duration_ms": 5000
  }
}
```

**Benefits**:
- Machine-parseable (no regex parsing)
- Queryable fields
- Consistent structure
- Easy to filter and aggregate

---

## Patterns

### Pattern 1: ELK Stack (Elasticsearch, Logstash, Kibana)

**Use when**: Need powerful search and analytics

```yaml
# docker-compose.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    user: root
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash

volumes:
  es_data:
```

**Logstash pipeline**:
```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
    }
  }

  # Parse common log format
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }

  # Add geo-location
  geoip {
    source => "client_ip"
  }

  # Add timestamp
  date {
    match => [ "timestamp", "ISO8601" ]
    target => "@timestamp"
  }

  # Drop debug logs in production
  if [level] == "DEBUG" and [environment] == "production" {
    drop {}
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
  }
}
```

### Pattern 2: EFK Stack (Elasticsearch, Fluentd, Kibana)

**Use when**: Need flexibility and Kubernetes integration

```yaml
# fluentd-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: logging
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      serviceAccountName: fluentd
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        - name: FLUENT_ELASTICSEARCH_SCHEME
          value: "http"
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: config
          mountPath: /fluentd/etc
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: config
        configMap:
          name: fluentd-config
```

**Fluentd configuration**:
```ruby
# fluentd.conf
<source>
  @type tail
  path /var/log/containers/*.log
  pos_file /var/log/fluentd-containers.log.pos
  tag kubernetes.*
  read_from_head true
  <parse>
    @type json
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

<filter kubernetes.**>
  @type kubernetes_metadata
  @id filter_kube_metadata
</filter>

<filter kubernetes.**>
  @type record_transformer
  <record>
    cluster_name "#{ENV['CLUSTER_NAME']}"
  </record>
</filter>

<match kubernetes.**>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  logstash_format true
  logstash_prefix k8s
  <buffer>
    @type file
    path /var/log/fluentd-buffers/kubernetes.system.buffer
    flush_mode interval
    retry_type exponential_backoff
    flush_interval 5s
    retry_forever false
    retry_max_interval 30
    chunk_limit_size 2M
    queue_limit_length 8
    overflow_action block
  </buffer>
</match>
```

### Pattern 3: Loki + Promtail (Lightweight Alternative)

**Use when**: Need cost-effective solution, already using Grafana

```yaml
# docker-compose.yml
version: '3.8'
services:
  loki:
    image: grafana/loki:2.9.3
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:2.9.3
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:10.2.2
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  loki_data:
  grafana_data:
```

**Why Loki**:
- Lower cost than Elasticsearch (indexes only metadata)
- Integrates with Grafana
- Label-based indexing
- Efficient for Kubernetes logs

### Pattern 4: Vector (High-Performance Pipeline)

**Use when**: Need maximum performance and flexibility

```toml
# vector.toml
[sources.docker]
type = "docker_logs"

[sources.kubernetes]
type = "kubernetes_logs"

[transforms.parse_json]
type = "remap"
inputs = ["docker", "kubernetes"]
source = '''
  . = parse_json!(.message)
  .timestamp = to_timestamp!(.timestamp)
'''

[transforms.filter_errors]
type = "filter"
inputs = ["parse_json"]
condition = '.level == "ERROR" || .level == "WARN"'

[transforms.enrich]
type = "remap"
inputs = ["parse_json"]
source = '''
  .environment = get_env_var!("ENVIRONMENT")
  .region = get_env_var!("AWS_REGION")
'''

[sinks.elasticsearch]
type = "elasticsearch"
inputs = ["enrich"]
endpoint = "http://elasticsearch:9200"
index = "logs-%Y.%m.%d"

[sinks.s3_archive]
type = "aws_s3"
inputs = ["enrich"]
bucket = "log-archive"
compression = "gzip"
encoding.codec = "json"
```

---

## Quick Reference

### Log Levels (Standard)

```
TRACE   - Very detailed debugging
DEBUG   - Debugging information
INFO    - Informational messages
WARN    - Warning messages
ERROR   - Error messages
FATAL   - Fatal errors (crash)
```

### Common Log Queries

**Elasticsearch DSL**:
```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"@timestamp": {"gte": "now-1h"}}},
        {"term": {"level": "ERROR"}},
        {"term": {"service": "api-gateway"}}
      ]
    }
  },
  "aggs": {
    "errors_by_type": {
      "terms": {"field": "error.type"}
    }
  }
}
```

**Loki LogQL**:
```logql
# Error logs from api-gateway in last hour
{service="api-gateway"} |= "ERROR" | json | line_format "{{.message}}"

# Error rate
rate({service="api-gateway"} |= "ERROR" [5m])

# Top error types
sum by (error_type) (count_over_time({service="api-gateway"} |= "ERROR" [1h]))
```

### Retention Policies

```yaml
# Elasticsearch ILM policy
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": {"max_num_segments": 1},
          "shrink": {"number_of_shards": 1}
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

---

## Anti-Patterns

### Unstructured Logs

```python
# WRONG: String interpolation
logger.info(f"User {user_id} performed {action}")

# CORRECT: Structured fields
logger.info("User action", extra={
    "user_id": user_id,
    "action": action
})
```

### Logging Sensitive Data

```python
# WRONG: Log PII
logger.info("User login", extra={"password": password})

# CORRECT: Redact or omit sensitive fields
logger.info("User login", extra={"user_id": user_id})
```

### No Sampling in High-Volume Scenarios

```python
# WRONG: Log every request
for request in requests:
    logger.info("Request processed", extra=request)

# CORRECT: Sample logs
if random.random() < 0.01:  # 1% sampling
    logger.info("Request processed", extra=request)
```

---

## Level 3: Resources

This skill has **Level 3 Resources** available with comprehensive reference material, production-ready scripts, and runnable examples.

### Resource Structure

```
log-aggregation/resources/
├── REFERENCE.md                        # Comprehensive reference (3,500+ lines)
│   ├── Log aggregation architecture and patterns
│   ├── ELK Stack (Elasticsearch, Logstash, Kibana) deep dive
│   ├── EFK Stack (Elasticsearch, Fluentd, Kibana) setup
│   ├── Loki + Grafana lightweight logging
│   ├── Vector high-performance pipelines
│   ├── Structured logging best practices
│   ├── Log parsing and enrichment
│   ├── Log retention and rotation strategies
│   ├── Search and query patterns
│   ├── Log-based alerting
│   ├── Cost optimization techniques
│   ├── Kubernetes logging patterns
│   ├── Cloud logging integration
│   ├── Security and compliance (PII redaction)
│   └── Performance tuning
│
├── scripts/                            # Production-ready tools
│   ├── setup_logging_stack.py          # Automated stack deployment
│   ├── analyze_logs.py                 # Log pattern analysis
│   └── optimize_log_pipeline.py        # Cost and performance optimization
│
└── examples/                           # Runnable examples
    ├── elk-stack/
    │   └── docker-compose.yml          # Complete ELK deployment
    ├── efk-stack/
    │   └── kubernetes/                 # Fluentd daemonset config
    ├── loki/
    │   └── docker-compose.yml          # Loki + Promtail setup
    ├── vector/
    │   └── vector.toml                 # Vector pipeline config
    ├── structured-logging/
    │   ├── python-logging.py           # Python integration
    │   ├── nodejs-winston.js           # Node.js integration
    │   └── go-zap.go                   # Go integration
    ├── kibana-dashboards/
    │   └── log-overview.json           # Kibana dashboard
    ├── log-alerts/
    │   └── alert-rules.yml             # Log-based alerting
    ├── pii-redaction/
    │   └── logstash-filter.conf        # PII filtering
    └── multi-cloud/
        └── terraform/                   # Multi-cloud setup
```

### Key Resources

**setup_logging_stack.py**: Automated deployment (700+ lines)
- Deploy ELK, EFK, or Loki stack
- Generate configuration files
- Validate setup and health checks
- Support for Docker Compose and Kubernetes
- Example: `setup_logging_stack.py --stack elk --environment docker --validate`

**analyze_logs.py**: Log analysis tool (700+ lines)
- Pattern detection and anomaly analysis
- Error correlation and trend analysis
- Report generation with recommendations
- Support for Elasticsearch and Loki
- Example: `analyze_logs.py --backend elasticsearch --days 7 --analyze-errors`

**optimize_log_pipeline.py**: Pipeline optimizer (600+ lines)
- Analyze log volume and costs
- Recommend sampling strategies
- Validate retention policies
- Performance tuning suggestions
- Example: `optimize_log_pipeline.py --backend elasticsearch --recommend-sampling`

### Usage

```bash
# Deploy logging stack
./scripts/setup_logging_stack.py --stack elk --environment docker

# Analyze logs for patterns
./scripts/analyze_logs.py --backend elasticsearch --days 7

# Optimize log pipeline
./scripts/optimize_log_pipeline.py --backend elasticsearch --analyze-costs

# Access comprehensive reference
cat log-aggregation/resources/REFERENCE.md
```

---

## Related Skills

- **monitoring-alerts.md** - Log-based alerting
- **observability-distributed-tracing.md** - Trace correlation
- **structured-logging.md** - Application-level logging
- **kubernetes-logging.md** - K8s logging patterns

---

**Last Updated**: 2025-10-29
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
