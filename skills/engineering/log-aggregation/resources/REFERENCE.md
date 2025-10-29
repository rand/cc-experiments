# Log Aggregation - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: 3,687

This comprehensive reference covers log aggregation architectures, tools, patterns, and best practices for production centralized logging systems.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture](#architecture)
3. [Log Aggregation Tools](#log-aggregation-tools)
4. [ELK Stack](#elk-stack)
5. [EFK Stack](#efk-stack)
6. [Loki + Grafana](#loki--grafana)
7. [Vector](#vector)
8. [Structured Logging](#structured-logging)
9. [Log Parsing and Enrichment](#log-parsing-and-enrichment)
10. [Log Retention and Rotation](#log-retention-and-rotation)
11. [Search and Query Patterns](#search-and-query-patterns)
12. [Log-Based Alerting](#log-based-alerting)
13. [Cost Optimization](#cost-optimization)
14. [Kubernetes Logging](#kubernetes-logging)
15. [Cloud Logging](#cloud-logging)
16. [Security and Compliance](#security-and-compliance)
17. [Performance Considerations](#performance-considerations)
18. [Anti-Patterns](#anti-patterns)
19. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is Log Aggregation?

Log aggregation is the process of collecting, centralizing, parsing, and analyzing log data from multiple sources into a single, searchable repository. This enables:

- **Centralized visibility**: All logs in one place
- **Troubleshooting**: Search across services to diagnose issues
- **Monitoring**: Detect patterns and anomalies
- **Compliance**: Audit trails and retention policies
- **Analytics**: Business intelligence from log data

### Why Log Aggregation Matters

**Without log aggregation**:
- SSH to each server to view logs
- No correlation across services
- Hard to debug distributed systems
- Manual log searches
- No historical analysis

**With log aggregation**:
- Search all logs from single UI
- Correlate logs across services
- Debug distributed systems with trace IDs
- Powerful query languages
- Historical analysis and trends

### Key Metrics

**Log Volume**:
- Small: < 1 GB/day
- Medium: 1-100 GB/day
- Large: 100 GB - 1 TB/day
- Very Large: > 1 TB/day

**Retention**:
- Short-term: 7-30 days (hot storage)
- Medium-term: 30-90 days (warm storage)
- Long-term: 90+ days (cold/archive storage)

---

## Architecture

### Four-Layer Model

```
┌────────────────────────────────────────────────┐
│              Application Layer                 │
│  (Services generating logs)                    │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│              Collection Layer                  │
│  (Agents: Filebeat, Fluentd, Promtail)        │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│              Transport Layer                   │
│  (Buffering: Kafka, Redis, Queue)             │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│              Storage Layer                     │
│  (Backend: Elasticsearch, Loki, S3)           │
└────────────────────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────┐
│              Analysis Layer                    │
│  (UI: Kibana, Grafana, Custom)                │
└────────────────────────────────────────────────┘
```

### Collection Layer

**Responsibilities**:
- Tail log files
- Parse log formats
- Add metadata (hostname, tags)
- Buffer logs locally
- Ship to transport or storage

**Common Agents**:
- **Filebeat**: Lightweight shipper for log files (Elastic)
- **Fluentd**: Unified logging layer (CNCF)
- **Promtail**: Log collector for Loki (Grafana)
- **Vector**: High-performance observability pipeline (Datadog)
- **Logstash**: Server-side data processing (Elastic)

**Deployment Patterns**:
- **Sidecar**: Agent container per pod (Kubernetes)
- **DaemonSet**: Agent per node (Kubernetes)
- **Host Agent**: Agent per VM/server
- **Centralized**: Application logs to central agent

### Transport Layer

**Purpose**: Decouple collection from storage

**Benefits**:
- Buffer spikes in log volume
- Prevent log loss during backend outages
- Enable multiple consumers
- Replay logs if needed

**Common Transports**:
- **Kafka**: High-throughput message queue
- **Redis**: In-memory buffer (Redis Streams)
- **RabbitMQ**: Message broker
- **AWS Kinesis**: Managed streaming
- **None**: Direct shipping (small scale)

**When to Use Transport**:
- Log volume > 10 GB/day
- Multiple log consumers
- Need replay capability
- Backend may go down

**When to Skip Transport**:
- Small log volume (< 1 GB/day)
- Single consumer
- Simple architecture preferred

### Storage Layer

**Responsibilities**:
- Index logs for search
- Store log data
- Manage retention
- Provide query API

**Storage Types**:

1. **Search-Optimized** (Elasticsearch, Splunk):
   - Full-text search
   - Complex aggregations
   - High indexing cost
   - Best for: Interactive queries, analytics

2. **Label-Indexed** (Loki):
   - Index only metadata/labels
   - Lower cost
   - Limited query power
   - Best for: Cost-sensitive, simple queries

3. **Object Storage** (S3, GCS):
   - Cheapest storage
   - No search (must scan)
   - Long-term archive
   - Best for: Compliance, cold storage

### Analysis Layer

**Responsibilities**:
- Visualize logs
- Search and filter
- Create dashboards
- Configure alerts

**Common UIs**:
- **Kibana**: For Elasticsearch
- **Grafana**: For Loki, Elasticsearch
- **AWS CloudWatch Insights**: For CloudWatch Logs
- **Custom**: API-based tools

---

## Log Aggregation Tools

### Tool Comparison

| Tool | Collection | Processing | Storage | Query | Best For |
|------|-----------|-----------|---------|-------|----------|
| **ELK** | Filebeat, Logstash | Logstash | Elasticsearch | Kibana/DSL | Full-text search, analytics |
| **EFK** | Fluentd | Fluentd | Elasticsearch | Kibana/DSL | Kubernetes, flexibility |
| **Loki** | Promtail | Promtail | Loki | LogQL | Cost-effective, Grafana users |
| **Vector** | Vector | Vector | Multiple | N/A | High-performance pipelines |
| **Splunk** | Universal Forwarder | Indexers | Splunk | SPL | Enterprise, all-in-one |
| **CloudWatch** | Agent | CloudWatch | CloudWatch | Insights | AWS-native |

### Selection Criteria

**Choose ELK when**:
- Need powerful full-text search
- Complex aggregations required
- Large team familiar with Elastic ecosystem
- Budget for licensing (production features)

**Choose EFK when**:
- Running on Kubernetes
- Need flexible log routing
- Want unified logging layer (Fluentd)
- Open-source preferred

**Choose Loki when**:
- Cost is primary concern
- Already using Grafana
- Simple label-based queries sufficient
- Log volume is high

**Choose Vector when**:
- Maximum performance needed
- Complex transformations required
- Multiple output destinations
- Want unified observability pipeline

**Choose Cloud-Native when**:
- Fully managed solution preferred
- Small team, don't want ops burden
- Already on AWS/GCP/Azure
- Cost acceptable for convenience

---

## ELK Stack

### Overview

**ELK** = Elasticsearch + Logstash + Kibana

**Components**:
- **Elasticsearch**: Search and analytics engine
- **Logstash**: Server-side data processing pipeline
- **Kibana**: Visualization and exploration UI
- **Beats**: Lightweight data shippers (Filebeat, Metricbeat)

### Architecture

```
┌─────────────┐
│   Filebeat  │ → Tail log files
└─────────────┘
       ↓
┌─────────────┐
│  Logstash   │ → Parse, filter, enrich
└─────────────┘
       ↓
┌─────────────┐
│Elasticsearch│ → Index and store
└─────────────┘
       ↓
┌─────────────┐
│   Kibana    │ → Visualize and search
└─────────────┘
```

### Elasticsearch

**What it is**: Distributed search and analytics engine built on Apache Lucene

**Key Concepts**:

1. **Index**: Collection of documents (like database table)
2. **Document**: JSON object (like database row)
3. **Shard**: Subdivision of index for horizontal scaling
4. **Replica**: Copy of shard for redundancy

**Index Structure**:
```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "index.lifecycle.name": "logs-policy"
  },
  "mappings": {
    "properties": {
      "@timestamp": {"type": "date"},
      "level": {"type": "keyword"},
      "message": {"type": "text"},
      "service": {"type": "keyword"},
      "trace_id": {"type": "keyword"},
      "user_id": {"type": "keyword"},
      "duration_ms": {"type": "integer"}
    }
  }
}
```

**Data Types**:
- `keyword`: Exact match, aggregations (tags, IDs)
- `text`: Full-text search (log messages)
- `date`: Timestamps
- `integer`/`long`: Numbers
- `boolean`: True/false
- `object`: Nested JSON
- `geo_point`: Lat/long coordinates

**Index Templates**:
```json
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "message": {"type": "text"}
      }
    }
  }
}
```

**Index Lifecycle Management (ILM)**:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": {
            "max_num_segments": 1
          },
          "shrink": {
            "number_of_shards": 1
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {},
          "set_priority": {
            "priority": 0
          }
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

**Phases**:
- **Hot**: Actively indexing, fast hardware (SSD)
- **Warm**: No longer indexing, queries only
- **Cold**: Rarely accessed, frozen
- **Delete**: Remove old data

### Logstash

**What it is**: Server-side data processing pipeline (input → filter → output)

**Pipeline Structure**:
```ruby
input {
  # Where logs come from
}

filter {
  # Transform and enrich logs
}

output {
  # Where logs go
}
```

**Common Inputs**:

```ruby
# Beats input
input {
  beats {
    port => 5044
  }
}

# TCP input
input {
  tcp {
    port => 5000
    codec => json_lines
  }
}

# HTTP input
input {
  http {
    port => 8080
  }
}

# Kafka input
input {
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["logs"]
    codec => "json"
  }
}
```

**Common Filters**:

```ruby
# Parse JSON
filter {
  json {
    source => "message"
  }
}

# Grok pattern matching
filter {
  grok {
    match => {
      "message" => "%{COMBINEDAPACHELOG}"
    }
  }
}

# Parse date
filter {
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
}

# Add fields
filter {
  mutate {
    add_field => {
      "environment" => "production"
    }
  }
}

# GeoIP lookup
filter {
  geoip {
    source => "client_ip"
  }
}

# Drop logs
filter {
  if [level] == "DEBUG" {
    drop {}
  }
}

# Conditional logic
filter {
  if [service] == "api" {
    mutate {
      add_tag => ["api-service"]
    }
  }
}
```

**Common Outputs**:

```ruby
# Elasticsearch output
output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
    user => "elastic"
    password => "${ES_PASSWORD}"
  }
}

# S3 output (archive)
output {
  s3 {
    bucket => "log-archive"
    region => "us-east-1"
    codec => "json_lines"
    time_file => 15
  }
}

# Kafka output
output {
  kafka {
    bootstrap_servers => "kafka:9092"
    topic_id => "logs-processed"
    codec => "json"
  }
}

# Multiple outputs
output {
  # Primary: Elasticsearch
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }

  # Archive: S3
  s3 {
    bucket => "log-archive"
    region => "us-east-1"
  }
}
```

**Performance Tuning**:

```ruby
# Pipeline settings in logstash.yml
pipeline.workers: 4              # Number of workers
pipeline.batch.size: 125         # Events per batch
pipeline.batch.delay: 50         # Max wait time (ms)

# JVM heap
## config/jvm.options
-Xms2g
-Xmx2g
```

### Filebeat

**What it is**: Lightweight log shipper

**Configuration**:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    fields:
      service: api-gateway
      environment: production
    fields_under_root: true
    multiline.pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    multiline.negate: true
    multiline.match: after

  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log

processors:
  - add_host_metadata: ~
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - drop_fields:
      fields: ["agent.ephemeral_id", "agent.id"]

output.logstash:
  hosts: ["logstash:5044"]
  loadbalance: true

# OR direct to Elasticsearch
output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "filebeat-%{[agent.version]}-%{+yyyy.MM.dd}"

setup.kibana:
  host: "kibana:5601"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
```

**Modules**:
```bash
# Enable modules for common formats
filebeat modules enable nginx
filebeat modules enable apache
filebeat modules enable mysql

# Configure module
filebeat modules list
filebeat -c /etc/filebeat/filebeat.yml -e
```

### Kibana

**What it is**: Visualization and exploration UI for Elasticsearch

**Key Features**:

1. **Discover**: Search and filter logs
2. **Visualize**: Create charts and graphs
3. **Dashboard**: Combine visualizations
4. **Alerts**: Notify on conditions
5. **Canvas**: Pixel-perfect presentations

**Discover Tab**:
```
Search bar: service:"api" AND level:"ERROR"
Time picker: Last 15 minutes
Field filters: service, level, user_id
Document table: Individual log entries
```

**KQL (Kibana Query Language)**:
```
# Simple search
service:api

# AND/OR
service:api AND level:ERROR

# Wildcards
service:api* AND message:*timeout*

# Range
duration_ms >= 1000

# Exists
user_id:*

# Not
NOT level:DEBUG
```

**Creating Visualizations**:

1. **Line Chart**: Error rate over time
```
Y-axis: Count
X-axis: @timestamp
Split series: level
Filters: level:(ERROR OR WARN)
```

2. **Pie Chart**: Errors by service
```
Slice size: Count
Split slices: service.keyword
Filters: level:ERROR
```

3. **Data Table**: Top errors
```
Rows: error.type.keyword
Metrics: Count, Top hit (message)
```

4. **Metric**: Total errors
```
Metric: Count
Filters: level:ERROR
```

**Dashboard Creation**:
```
1. Create visualizations
2. Dashboard → Create dashboard
3. Add visualizations
4. Arrange and resize
5. Save dashboard
6. Share with team
```

**Alerting**:

```yaml
# Watcher (Elasticsearch alerting)
{
  "trigger": {
    "schedule": {
      "interval": "5m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {"range": {"@timestamp": {"gte": "now-5m"}}},
                {"term": {"level": "ERROR"}}
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total": {
        "gte": 10
      }
    }
  },
  "actions": {
    "send_email": {
      "email": {
        "to": "oncall@example.com",
        "subject": "High error rate detected",
        "body": "Found {{ctx.payload.hits.total}} errors in last 5 minutes"
      }
    }
  }
}
```

### ELK Production Setup

**Docker Compose** (single-node, development):

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - node.name=es01
      - cluster.name=logs-cluster
      - discovery.type=single-node
      - bootstrap.memory_lock=true
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=false
      - xpack.monitoring.collection.enabled=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - elk

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml:ro
    ports:
      - "5044:5044"
      - "9600:9600"
    environment:
      - "LS_JAVA_OPTS=-Xms1g -Xmx1g"
    networks:
      - elk
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - SERVER_NAME=kibana
    ports:
      - "5601:5601"
    networks:
      - elk
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    container_name: filebeat
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - filebeat_data:/usr/share/filebeat/data
    command: filebeat -e -strict.perms=false
    networks:
      - elk
    depends_on:
      - logstash

volumes:
  es_data:
  filebeat_data:

networks:
  elk:
    driver: bridge
```

**Kubernetes** (production cluster):

```yaml
# elasticsearch-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: logging
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      initContainers:
      - name: increase-vm-max-map
        image: busybox
        command: ["sysctl", "-w", "vm.max_map_count=262144"]
        securityContext:
          privileged: true
      - name: increase-fd-ulimit
        image: busybox
        command: ["sh", "-c", "ulimit -n 65536"]
        securityContext:
          privileged: true
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
        resources:
          requests:
            memory: 4Gi
            cpu: 1000m
          limits:
            memory: 8Gi
            cpu: 2000m
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        env:
        - name: cluster.name
          value: k8s-logs
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch"
        - name: cluster.initial_master_nodes
          value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
        - name: ES_JAVA_OPTS
          value: "-Xms4g -Xmx4g"
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 100Gi
```

### ELK Sizing Guidelines

**Small deployment** (< 1 GB/day):
- Elasticsearch: 1 node, 4 GB RAM, 2 CPU
- Logstash: 1 instance, 2 GB RAM, 1 CPU
- Kibana: 1 instance, 1 GB RAM, 0.5 CPU

**Medium deployment** (1-50 GB/day):
- Elasticsearch: 3 nodes, 16 GB RAM each, 4 CPU
- Logstash: 2-3 instances, 4 GB RAM, 2 CPU
- Kibana: 1-2 instances, 2 GB RAM, 1 CPU

**Large deployment** (50-500 GB/day):
- Elasticsearch: 5+ data nodes, 32 GB RAM, 8 CPU
- Elasticsearch: 3 dedicated master nodes
- Logstash: 5+ instances, 8 GB RAM, 4 CPU
- Kibana: 2+ instances, 4 GB RAM, 2 CPU

**Storage**:
- Raw log data × 1.1 (10% overhead)
- Replicas: × 2 for redundancy
- ILM: Reduce by 50-70% with compression/forcemerge

---

## EFK Stack

### Overview

**EFK** = Elasticsearch + Fluentd + Kibana

**Difference from ELK**:
- **Fluentd** instead of Logstash + Filebeat
- More flexible log routing
- Lower memory footprint
- Better Kubernetes integration

### Fluentd

**What it is**: Unified logging layer, collects and routes logs

**Architecture**:
```
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Source  │ → │ Filter  │ → │ Output  │
└─────────┘    └─────────┘    └─────────┘
```

**Configuration**:

```xml
# fluentd.conf

## Source: Read logs
<source>
  @type tail
  path /var/log/app/*.log
  pos_file /var/log/fluentd/app.log.pos
  tag app.logs
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

## Filter: Transform logs
<filter app.logs>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    environment "#{ENV['ENVIRONMENT']}"
  </record>
</filter>

<filter app.logs>
  @type grep
  <exclude>
    key level
    pattern /^DEBUG$/
  </exclude>
</filter>

## Output: Send to Elasticsearch
<match app.logs>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  logstash_format true
  logstash_prefix app
  <buffer>
    @type file
    path /var/log/fluentd-buffers/app.buffer
    flush_mode interval
    flush_interval 5s
    retry_type exponential_backoff
    retry_forever false
    retry_max_interval 30
    chunk_limit_size 2M
    queue_limit_length 8
    overflow_action block
  </buffer>
</match>
```

**Plugins**:

```bash
# Install plugins
fluent-gem install fluent-plugin-elasticsearch
fluent-gem install fluent-plugin-s3
fluent-gem install fluent-plugin-kafka
fluent-gem install fluent-plugin-prometheus
fluent-gem install fluent-plugin-rewrite-tag-filter
```

**Common Plugins**:
- `fluent-plugin-elasticsearch`: Output to Elasticsearch
- `fluent-plugin-kafka`: Input/output to Kafka
- `fluent-plugin-s3`: Output to S3
- `fluent-plugin-prometheus`: Expose metrics
- `fluent-plugin-kubernetes_metadata_filter`: Enrich with K8s metadata

### Fluentd for Kubernetes

**DaemonSet Deployment**:

```yaml
# fluentd-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: logging
  labels:
    app: fluentd
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
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
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
        - name: FLUENT_UID
          value: "0"
        - name: FLUENTD_SYSTEMD_CONF
          value: "disable"
        resources:
          limits:
            memory: 512Mi
          requests:
            cpu: 100m
            memory: 256Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: config
          mountPath: /fluentd/etc/fluent.conf
          subPath: fluent.conf
      terminationGracePeriodSeconds: 30
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
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluentd
  namespace: logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: fluentd
rules:
- apiGroups: [""]
  resources:
  - pods
  - namespaces
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: fluentd
roleRef:
  kind: ClusterRole
  name: fluentd
  apiGroup: rbac.authorization.k8s.io
subjects:
- kind: ServiceAccount
  name: fluentd
  namespace: logging
```

**Fluentd Configuration for Kubernetes**:

```xml
# kubernetes.conf (ConfigMap)
<source>
  @type tail
  @id in_tail_container_logs
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
  kubernetes_url "#{ENV['FLUENT_FILTER_KUBERNETES_URL'] || 'https://' + ENV.fetch('KUBERNETES_SERVICE_HOST') + ':' + ENV.fetch('KUBERNETES_SERVICE_PORT') + '/api'}"
  verify_ssl "#{ENV['KUBERNETES_VERIFY_SSL'] || true}"
  ca_file "#{ENV['KUBERNETES_CA_FILE']}"
  skip_labels "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_LABELS'] || 'false'}"
  skip_container_metadata "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_CONTAINER_METADATA'] || 'false'}"
  skip_master_url "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_MASTER_URL'] || 'false'}"
  skip_namespace_metadata "#{ENV['FLUENT_KUBERNETES_METADATA_SKIP_NAMESPACE_METADATA'] || 'false'}"
</filter>

<filter kubernetes.var.log.containers.**>
  @type parser
  key_name log
  reserve_data true
  remove_key_name_field true
  <parse>
    @type json
  </parse>
</filter>

<filter kubernetes.**>
  @type record_transformer
  <record>
    cluster_name "#{ENV['CLUSTER_NAME']}"
    cluster_region "#{ENV['CLUSTER_REGION']}"
  </record>
</filter>

<match kubernetes.**>
  @type elasticsearch
  @id out_es
  @log_level info
  include_tag_key true
  host "#{ENV['FLUENT_ELASTICSEARCH_HOST']}"
  port "#{ENV['FLUENT_ELASTICSEARCH_PORT']}"
  scheme "#{ENV['FLUENT_ELASTICSEARCH_SCHEME'] || 'http'}"
  ssl_verify "#{ENV['FLUENT_ELASTICSEARCH_SSL_VERIFY'] || 'true'}"
  logstash_format true
  logstash_prefix "#{ENV['FLUENT_ELASTICSEARCH_LOGSTASH_PREFIX'] || 'logstash'}"
  logstash_dateformat %Y.%m.%d
  <buffer>
    @type file
    path /var/log/fluentd-buffers/kubernetes.system.buffer
    flush_mode interval
    retry_type exponential_backoff
    flush_thread_count 2
    flush_interval 5s
    retry_forever false
    retry_max_interval 30
    chunk_limit_size 2M
    total_limit_size 512M
    overflow_action block
  </buffer>
</match>
```

### Fluentd vs Logstash

| Feature | Fluentd | Logstash |
|---------|---------|----------|
| **Language** | Ruby/C | JRuby (Java) |
| **Memory** | Lower (~40 MB) | Higher (~200 MB base) |
| **Config** | Ruby DSL | Custom DSL |
| **Plugins** | 1000+ | 200+ |
| **Performance** | High (C core) | High (JVM) |
| **Ecosystem** | CNCF, K8s native | Elastic ecosystem |
| **Best for** | Kubernetes, unified layer | Complex transformations |

---

## Loki + Grafana

### Overview

**Loki**: Log aggregation system inspired by Prometheus

**Key Difference**: Indexes only metadata (labels), not log content

**Benefits**:
- **Lower cost**: 10x cheaper storage than Elasticsearch
- **Simpler**: No complex indexing
- **Grafana integration**: Native support in Grafana

**Trade-offs**:
- No full-text search on log content
- Query language less powerful than Elasticsearch
- Best for label-based filtering

### Architecture

```
┌─────────────┐
│  Promtail   │ → Collect logs, add labels
└─────────────┘
       ↓
┌─────────────┐
│    Loki     │ → Index labels, store logs
└─────────────┘
       ↓
┌─────────────┐
│   Grafana   │ → Query and visualize
└─────────────┘
```

### Loki

**Configuration**:

```yaml
# loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  max_streams_per_user: 10000
  max_global_streams_per_user: 0

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: true
  retention_period: 336h
```

**S3 Backend** (production):

```yaml
# loki-s3.yml
storage_config:
  aws:
    s3: s3://us-east-1/my-loki-bucket
    s3forcepathstyle: false
  boltdb_shipper:
    active_index_directory: /loki/index
    shared_store: s3
    cache_location: /loki/cache
```

### Promtail

**What it is**: Agent to collect logs and send to Loki

**Configuration**:

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Local files
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          host: myhost
          __path__: /var/log/*.log

  # Docker containers
  - job_name: containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'

  # Kubernetes pods
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_node_name]
        target_label: node
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod

pipeline_stages:
  # Parse JSON logs
  - json:
      expressions:
        level: level
        timestamp: timestamp
        message: message

  # Extract labels
  - labels:
      level:

  # Parse timestamp
  - timestamp:
      source: timestamp
      format: RFC3339

  # Drop debug logs
  - match:
      selector: '{level="DEBUG"}'
      action: drop
```

### LogQL (Loki Query Language)

**Similar to PromQL**, but for logs

**Log Stream Selector**:
```logql
# All logs from service
{service="api"}

# Multiple labels
{service="api", environment="production"}

# Regex match
{service=~"api.*"}

# Multiple values
{service=~"api|web"}
```

**Line Filter**:
```logql
# Contains
{service="api"} |= "error"

# Doesn't contain
{service="api"} != "debug"

# Regex match
{service="api"} |~ "error|timeout"

# Regex doesn't match
{service="api"} !~ "debug|trace"
```

**Parser**:
```logql
# JSON
{service="api"} | json

# Logfmt
{service="api"} | logfmt

# Regex
{service="api"} | regexp "(?P<method>\\w+) (?P<path>/\\w+)"
```

**Label Filter**:
```logql
# After parsing JSON
{service="api"} | json | level="ERROR"

# Numeric comparison
{service="api"} | json | duration_ms > 1000
```

**Line Format**:
```logql
# Custom output
{service="api"} | json | line_format "{{.level}}: {{.message}}"
```

**Aggregation**:
```logql
# Count logs
count_over_time({service="api"}[5m])

# Rate (logs per second)
rate({service="api"}[5m])

# Sum of parsed field
sum(count_over_time({service="api"} | json | level="ERROR" [5m]))

# Average
avg(avg_over_time({service="api"} | json | unwrap duration_ms [5m]))

# Top N
topk(5, sum by (endpoint) (rate({service="api"}[5m])))
```

**Examples**:

```logql
# Error rate by service
sum by (service) (rate({environment="production"} |= "ERROR" [5m]))

# P95 latency
quantile_over_time(0.95,
  {service="api"} | json | unwrap duration_ms [5m]
)

# Top 10 endpoints by request count
topk(10,
  sum by (endpoint) (count_over_time({service="api"}[1h]))
)

# Error ratio
sum(rate({service="api"} |= "ERROR" [5m]))
/
sum(rate({service="api"} [5m]))
```

### Loki Production Setup

**Docker Compose**:

```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:2.9.3
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - logging

  promtail:
    image: grafana/promtail:2.9.3
    container_name: promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - logging
    depends_on:
      - loki

  grafana:
    image: grafana/grafana:10.2.2
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
    networks:
      - logging
    depends_on:
      - loki

volumes:
  loki_data:
  grafana_data:

networks:
  logging:
    driver: bridge
```

**Kubernetes**:

```yaml
# loki-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: loki
  namespace: logging
spec:
  serviceName: loki
  replicas: 1
  selector:
    matchLabels:
      app: loki
  template:
    metadata:
      labels:
        app: loki
    spec:
      containers:
      - name: loki
        image: grafana/loki:2.9.3
        ports:
        - containerPort: 3100
          name: http
        volumeMounts:
        - name: config
          mountPath: /etc/loki
        - name: storage
          mountPath: /loki
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
      volumes:
      - name: config
        configMap:
          name: loki-config
  volumeClaimTemplates:
  - metadata:
      name: storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

---

## Vector

### Overview

**Vector**: High-performance observability data pipeline by Datadog

**Key Features**:
- **Fast**: Rust-based, minimal overhead
- **Flexible**: Route to multiple destinations
- **Reliable**: Built-in buffering and retries
- **Unified**: Logs, metrics, traces

**Use Cases**:
- High-volume log processing (> 100 GB/day)
- Complex transformations
- Multiple output destinations
- Cost optimization (filter before sending)

### Architecture

```
┌──────────┐
│  Sources │ → Collect data
└──────────┘
      ↓
┌──────────┐
│Transforms│ → Process, filter, enrich
└──────────┘
      ↓
┌──────────┐
│  Sinks   │ → Send to destinations
└──────────┘
```

### Configuration

**TOML Format**:

```toml
# vector.toml

# Data directory for buffers
data_dir = "/var/lib/vector"

# Sources: Where data comes from
[sources.docker_logs]
type = "docker_logs"

[sources.kubernetes_logs]
type = "kubernetes_logs"

[sources.syslog]
type = "syslog"
address = "0.0.0.0:514"
mode = "tcp"

[sources.http]
type = "http"
address = "0.0.0.0:8080"
encoding = "json"

# Transforms: Process data
[transforms.parse_json]
type = "remap"
inputs = ["docker_logs", "kubernetes_logs"]
source = '''
  . = parse_json!(.message)
  .timestamp = to_timestamp!(.timestamp)
  .level = upcase!(.level)
'''

[transforms.add_host]
type = "remap"
inputs = ["parse_json"]
source = '''
  .host = get_hostname!()
  .environment = get_env_var!("ENVIRONMENT")
'''

[transforms.filter_debug]
type = "filter"
inputs = ["add_host"]
condition = '.level != "DEBUG"'

[transforms.sample_info]
type = "sample"
inputs = ["filter_debug"]
rate = 10  # Keep 1 in 10 INFO logs
key_field = "level"
exclude = ["ERROR", "WARN"]  # Don't sample errors/warnings

[transforms.redact_pii]
type = "remap"
inputs = ["sample_info"]
source = '''
  # Redact email addresses
  .message = replace(.message, r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL]")

  # Redact credit card numbers
  .message = replace(.message, r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "[CC]")

  # Redact SSN
  .message = replace(.message, r'\b\d{3}-\d{2}-\d{4}\b', "[SSN]")
'''

# Sinks: Where data goes
[sinks.elasticsearch]
type = "elasticsearch"
inputs = ["redact_pii"]
endpoint = "http://elasticsearch:9200"
index = "logs-%Y.%m.%d"
compression = "gzip"

[sinks.s3_archive]
type = "aws_s3"
inputs = ["redact_pii"]
bucket = "log-archive"
region = "us-east-1"
compression = "gzip"
encoding.codec = "json"
key_prefix = "logs/year=%Y/month=%m/day=%d/"

[sinks.prometheus_metrics]
type = "prometheus_exporter"
inputs = ["redact_pii"]
address = "0.0.0.0:9090"

[sinks.loki]
type = "loki"
inputs = ["redact_pii"]
endpoint = "http://loki:3100"
encoding.codec = "json"
labels.service = "{{ service }}"
labels.environment = "{{ environment }}"

# Healthcheck
[api]
enabled = true
address = "0.0.0.0:8686"
```

### Vector Remap Language (VRL)

**Powerful transformation language**:

```toml
[transforms.complex_parsing]
type = "remap"
inputs = ["source"]
source = '''
  # Parse JSON
  . = parse_json!(.message)

  # Type conversion
  .duration_ms = to_int!(.duration)
  .timestamp = to_timestamp!(.timestamp)

  # String manipulation
  .level = upcase(.level)
  .service = downcase(.service)

  # Conditional logic
  if .status_code >= 500 {
    .severity = "error"
  } else if .status_code >= 400 {
    .severity = "warn"
  } else {
    .severity = "info"
  }

  # Array operations
  .tags = split(.tags_string, ",")
  .tag_count = length(.tags)

  # Remove fields
  del(.internal_field)
  del(.password)

  # Add fields
  .processed_at = now()
  .pipeline_version = "1.0"

  # Regex
  .is_api_request = match(.path, r'^/api/')

  # Error handling
  .user_id = to_int(.user_id) ?? 0  # Default to 0 if parse fails
'''
```

### Vector Performance

**Benchmarks** (compared to alternatives):

| Metric | Vector | Fluentd | Logstash |
|--------|--------|---------|----------|
| **Throughput** | 1M events/s | 200K events/s | 300K events/s |
| **CPU Usage** | Low | Medium | High |
| **Memory** | 10 MB | 50 MB | 200 MB |
| **Latency** | < 1ms | ~5ms | ~10ms |

**Why Vector is Fast**:
- Written in Rust (zero-cost abstractions)
- Async I/O (Tokio runtime)
- Efficient memory management
- Optimized buffering

### Vector Deployment

**Docker**:

```yaml
version: '3.8'
services:
  vector:
    image: timberio/vector:0.35.0-alpine
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - vector_data:/var/lib/vector
    ports:
      - "8686:8686"  # API
      - "9090:9090"  # Prometheus metrics
    command: ["--config", "/etc/vector/vector.toml"]

volumes:
  vector_data:
```

**Kubernetes**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: vector
  namespace: logging
spec:
  selector:
    matchLabels:
      app: vector
  template:
    metadata:
      labels:
        app: vector
    spec:
      containers:
      - name: vector
        image: timberio/vector:0.35.0-alpine
        volumeMounts:
        - name: config
          mountPath: /etc/vector
        - name: data
          mountPath: /var/lib/vector
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: vector-config
      - name: data
        hostPath:
          path: /var/lib/vector
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
```

---

## Structured Logging

### Why Structured Logging?

**Unstructured** (bad):
```
2025-10-29 10:30:45 INFO User alice performed login from 192.168.1.1
```

**Structured** (good):
```json
{
  "timestamp": "2025-10-29T10:30:45.123Z",
  "level": "INFO",
  "message": "User login",
  "user": "alice",
  "action": "login",
  "ip": "192.168.1.1"
}
```

**Benefits**:
- **Machine-parseable**: No regex needed
- **Queryable**: Filter by fields
- **Consistent**: Same structure across services
- **Aggregatable**: Easy to count, group, average

### Log Structure Best Practices

**Core Fields** (always include):
```json
{
  "timestamp": "2025-10-29T10:30:45.123Z",  // ISO 8601
  "level": "INFO",                           // DEBUG/INFO/WARN/ERROR/FATAL
  "message": "Short human-readable message",
  "service": "api-gateway",                  // Service name
  "version": "1.2.3",                        // Service version
  "environment": "production"                // prod/staging/dev
}
```

**Tracing Fields** (for distributed tracing):
```json
{
  "trace_id": "abc123def456",     // Trace ID (from OpenTelemetry/Jaeger)
  "span_id": "span789",            // Span ID
  "parent_span_id": "span456"     // Parent span
}
```

**Request Fields** (for HTTP logs):
```json
{
  "request": {
    "method": "GET",
    "path": "/api/users/123",
    "query": {"filter": "active"},
    "headers": {
      "user-agent": "Mozilla/5.0...",
      "x-request-id": "req-123"
    },
    "ip": "192.168.1.1",
    "user_id": "user_456"
  },
  "response": {
    "status_code": 200,
    "duration_ms": 45,
    "size_bytes": 1024
  }
}
```

**Error Fields** (for error logs):
```json
{
  "error": {
    "type": "DatabaseConnectionError",
    "message": "Failed to connect to database",
    "stack_trace": "...",
    "code": "DB_CONN_TIMEOUT"
  }
}
```

**Context Fields** (application-specific):
```json
{
  "context": {
    "user_id": "user_123",
    "tenant_id": "tenant_456",
    "session_id": "session_789"
  }
}
```

### Structured Logging Libraries

#### Python (structlog)

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Log with structured data
logger.info(
    "user_login",
    user_id="alice",
    ip="192.168.1.1",
    action="login"
)

# Bind context (added to all subsequent logs)
logger = logger.bind(
    service="api-gateway",
    version="1.2.3",
    environment="production"
)

# Error logging
try:
    connect_to_database()
except Exception as e:
    logger.error(
        "database_connection_failed",
        error_type=type(e).__name__,
        error_message=str(e),
        exc_info=True
    )
```

#### Node.js (Winston)

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp({
      format: 'YYYY-MM-DDTHH:mm:ss.SSSZ'
    }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'api-gateway',
    version: '1.2.3',
    environment: 'production'
  },
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// Log with structured data
logger.info('User login', {
  user_id: 'alice',
  ip: '192.168.1.1',
  action: 'login'
});

// Error logging
try {
  connectToDatabase();
} catch (error) {
  logger.error('Database connection failed', {
    error_type: error.name,
    error_message: error.message,
    stack: error.stack
  });
}
```

#### Go (zap)

```go
package main

import (
    "go.uber.org/zap"
    "go.uber.org/zap/zapcore"
)

func main() {
    // Production config (JSON output)
    config := zap.NewProductionConfig()
    config.EncoderConfig.TimeKey = "timestamp"
    config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

    logger, _ := config.Build()
    defer logger.Sync()

    // Add default fields
    logger = logger.With(
        zap.String("service", "api-gateway"),
        zap.String("version", "1.2.3"),
        zap.String("environment", "production"),
    )

    // Structured logging
    logger.Info("User login",
        zap.String("user_id", "alice"),
        zap.String("ip", "192.168.1.1"),
        zap.String("action", "login"),
    )

    // Error logging
    err := connectToDatabase()
    if err != nil {
        logger.Error("Database connection failed",
            zap.Error(err),
            zap.String("error_type", "DatabaseError"),
        )
    }
}
```

---

## Log Parsing and Enrichment

### Why Parse Logs?

**Raw log**:
```
192.168.1.1 - alice [29/Oct/2025:10:30:45 +0000] "GET /api/users HTTP/1.1" 200 1024
```

**Parsed log**:
```json
{
  "ip": "192.168.1.1",
  "user": "alice",
  "timestamp": "2025-10-29T10:30:45Z",
  "method": "GET",
  "path": "/api/users",
  "protocol": "HTTP/1.1",
  "status_code": 200,
  "size_bytes": 1024
}
```

### Grok Patterns (Logstash)

**Common Log Format**:
```ruby
filter {
  grok {
    match => {
      "message" => "%{COMMONAPACHELOG}"
    }
  }
}
```

**Custom Pattern**:
```ruby
filter {
  grok {
    match => {
      "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{GREEDYDATA:message}"
    }
  }
}
```

**Multiline Logs** (stack traces):
```ruby
filter {
  multiline {
    pattern => "^%{TIMESTAMP_ISO8601}"
    negate => true
    what => "previous"
  }
}
```

### Enrichment

**Add GeoIP Data**:
```ruby
filter {
  geoip {
    source => "ip"
    target => "geoip"
    fields => ["city_name", "country_name", "location"]
  }
}
```

**Add Hostname**:
```ruby
filter {
  mutate {
    add_field => {
      "hostname" => "%{HOSTNAME}"
    }
  }
}
```

**Lookup from Database**:
```ruby
filter {
  jdbc_streaming {
    jdbc_driver_library => "/path/to/mysql-connector.jar"
    jdbc_driver_class => "com.mysql.jdbc.Driver"
    jdbc_connection_string => "jdbc:mysql://localhost:3306/db"
    jdbc_user => "user"
    jdbc_password => "password"
    statement => "SELECT name FROM users WHERE id = :user_id"
    parameters => { "user_id" => "user_id" }
    target => "user_info"
  }
}
```

---

## Log Retention and Rotation

### Retention Strategy

**Hot Storage** (0-7 days):
- Fast SSDs
- Full indexing
- Immediate search
- Expensive ($$$$)

**Warm Storage** (7-30 days):
- Standard disks
- Read-only
- Slower queries
- Moderate cost ($$$)

**Cold Storage** (30-90 days):
- Compressed
- Infrequent access
- Slow queries
- Cheap ($$)

**Archive** (90+ days):
- Object storage (S3, GCS)
- No search (must restore)
- Compliance/audit
- Very cheap ($)

### Elasticsearch ILM

**Index Lifecycle**:

```json
PUT _ilm/policy/logs-policy
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d",
            "max_docs": 10000000
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "readonly": {},
          "forcemerge": {
            "max_num_segments": 1
          },
          "shrink": {
            "number_of_shards": 1
          },
          "allocate": {
            "require": {
              "data": "warm"
            }
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {},
          "allocate": {
            "require": {
              "data": "cold"
            }
          },
          "set_priority": {
            "priority": 0
          }
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

**Apply to Index Template**:

```json
PUT _index_template/logs-template
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.lifecycle.name": "logs-policy",
      "index.lifecycle.rollover_alias": "logs"
    }
  }
}
```

### Loki Retention

```yaml
# loki-config.yml
limits_config:
  retention_period: 336h  # 14 days

table_manager:
  retention_deletes_enabled: true
  retention_period: 336h

chunk_store_config:
  max_look_back_period: 336h
```

---

## Search and Query Patterns

### Elasticsearch Queries

**Match Query** (full-text):
```json
GET logs-*/_search
{
  "query": {
    "match": {
      "message": "error timeout"
    }
  }
}
```

**Term Query** (exact):
```json
GET logs-*/_search
{
  "query": {
    "term": {
      "level": "ERROR"
    }
  }
}
```

**Bool Query** (AND/OR/NOT):
```json
GET logs-*/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"service": "api"}},
        {"term": {"level": "ERROR"}}
      ],
      "filter": [
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ],
      "must_not": [
        {"term": {"user_id": "test_user"}}
      ]
    }
  }
}
```

**Aggregations** (count, avg, etc.):
```json
GET logs-*/_search
{
  "size": 0,
  "aggs": {
    "errors_by_service": {
      "terms": {
        "field": "service.keyword",
        "size": 10
      },
      "aggs": {
        "error_count": {
          "value_count": {
            "field": "level"
          }
        }
      }
    },
    "avg_duration": {
      "avg": {
        "field": "duration_ms"
      }
    },
    "error_rate_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "fixed_interval": "5m"
      },
      "aggs": {
        "error_count": {
          "filter": {
            "term": {"level": "ERROR"}
          }
        }
      }
    }
  }
}
```

### Loki Queries (LogQL)

**Basic Search**:
```logql
{service="api"} |= "error"
```

**Time Range**:
```logql
{service="api"}[5m]
```

**Aggregations**:
```logql
# Count
count_over_time({service="api"}[5m])

# Rate (per second)
rate({service="api"}[5m])

# Sum by label
sum by (level) (count_over_time({service="api"}[1h]))
```

**Percentiles**:
```logql
quantile_over_time(0.95, {service="api"} | json | unwrap duration_ms [5m])
```

---

## Log-Based Alerting

### When to Alert on Logs

**Good use cases**:
- Error rate spike
- Specific error pattern (e.g., "DatabaseConnectionError")
- Absence of expected logs (e.g., no health checks)
- Security events (e.g., failed logins)

**Bad use cases**:
- Individual log entries (alert fatigue)
- Already covered by metrics (redundant)

### Elasticsearch Watcher

```json
PUT _watcher/watch/high-error-rate
{
  "trigger": {
    "schedule": {
      "interval": "5m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {"range": {"@timestamp": {"gte": "now-5m"}}},
                {"term": {"level": "ERROR"}},
                {"term": {"service": "api"}}
              ]
            }
          },
          "size": 0
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total.value": {
        "gte": 10
      }
    }
  },
  "actions": {
    "send_slack": {
      "webhook": {
        "scheme": "https",
        "host": "hooks.slack.com",
        "port": 443,
        "method": "post",
        "path": "/services/YOUR/SLACK/WEBHOOK",
        "body": "{\"text\": \"High error rate: {{ctx.payload.hits.total.value}} errors in last 5min\"}"
      }
    }
  }
}
```

### Loki Alerting (with Prometheus Alertmanager)

```yaml
# loki-rules.yml
groups:
  - name: logs
    interval: 1m
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate({service="api"} |= "ERROR" [5m])) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on API service"
          description: "API error rate is {{ $value }} errors/second"

      - alert: DatabaseErrors
        expr: |
          count_over_time({service="api"} |= "DatabaseConnectionError" [5m]) > 0
        labels:
          severity: warning
        annotations:
          summary: "Database connection errors detected"
```

---

## Cost Optimization

### Log Volume Reduction

**1. Sampling**:

```python
import random

# Sample 10% of INFO logs, keep all errors
if level == "INFO" and random.random() > 0.1:
    return  # Drop log

logger.info("Request processed", extra=context)
```

**2. Filtering**:

```ruby
# Logstash: Drop debug logs
filter {
  if [level] == "DEBUG" {
    drop {}
  }
}
```

**3. Rate Limiting**:

```python
from time import time

error_log_cache = {}

def should_log_error(error_type):
    now = time()
    last_log = error_log_cache.get(error_type, 0)

    # Log max once per minute per error type
    if now - last_log > 60:
        error_log_cache[error_type] = now
        return True
    return False

if should_log_error(error.type):
    logger.error("Error occurred", extra={"error": error})
```

### Storage Cost Reduction

**1. Compression**:
- Elasticsearch: Use `best_compression` codec
- Loki: Built-in compression
- S3: Use gzip compression

**2. ILM (Index Lifecycle Management)**:
- Move old data to cheaper storage
- Delete after retention period

**3. Use Loki Instead of Elasticsearch**:
- 10x cheaper for same volume
- Trade-off: Less query power

**4. Archive to Object Storage**:
```ruby
# Logstash: Dual output
output {
  # Hot: Elasticsearch (7 days)
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }

  # Cold: S3 archive
  s3 {
    bucket => "log-archive"
    region => "us-east-1"
    codec => "json_lines"
    time_file => 60  # New file every hour
  }
}
```

### Cost Examples

**Elasticsearch** (100 GB/day):
- Storage: 100 GB × 30 days × $0.10/GB = $300/month
- Compute: $500/month (3-node cluster)
- **Total: ~$800/month**

**Loki** (100 GB/day):
- Storage: 100 GB × 30 days × $0.02/GB = $60/month
- Compute: $200/month (simpler setup)
- **Total: ~$260/month**

**Savings**: 67% cheaper with Loki

---

## Kubernetes Logging

### Logging Architecture

**Three patterns**:

1. **Node-level logging** (DaemonSet):
   - Agent on each node
   - Collects logs from all pods
   - Example: Fluentd, Promtail

2. **Sidecar logging**:
   - Agent container per pod
   - Collects logs from app container
   - Higher resource usage

3. **Application-level logging**:
   - App sends logs directly
   - No agent needed
   - Network dependency

**Best Practice**: Node-level logging (DaemonSet)

### Fluentd DaemonSet

```yaml
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
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        resources:
          limits:
            memory: 512Mi
          requests:
            cpu: 100m
            memory: 256Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

### Log Format in Kubernetes

**Container logs** (Docker/containerd):
```json
{
  "log": "2025-10-29T10:30:45Z [INFO] User login\n",
  "stream": "stdout",
  "time": "2025-10-29T10:30:45.123456789Z"
}
```

**Fluentd adds Kubernetes metadata**:
```json
{
  "log": "User login",
  "stream": "stdout",
  "time": "2025-10-29T10:30:45.123456789Z",
  "kubernetes": {
    "pod_name": "api-gateway-5d7f8c9b-xyz",
    "namespace_name": "production",
    "pod_id": "abc123...",
    "labels": {
      "app": "api-gateway",
      "version": "1.2.3"
    },
    "host": "node-1",
    "container_name": "api",
    "docker_id": "def456..."
  }
}
```

---

## Cloud Logging

### AWS CloudWatch Logs

**Agent Configuration**:

```json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/app/*.log",
            "log_group_name": "/aws/ec2/app",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 7
          }
        ]
      }
    }
  }
}
```

**CloudWatch Insights Queries**:

```sql
-- Error rate
fields @timestamp, level, message
| filter level = "ERROR"
| stats count() by bin(5m)

-- Top error types
fields @timestamp, error.type
| filter level = "ERROR"
| stats count() by error.type
| sort count desc
| limit 10

-- P95 latency
fields @timestamp, duration_ms
| stats pct(duration_ms, 95) as p95_latency by bin(5m)
```

### GCP Cloud Logging

**Log Router**:

```yaml
# Log sink to BigQuery
apiVersion: logging.cnrm.cloud.google.com/v1beta1
kind: LoggingLogSink
metadata:
  name: bigquery-sink
spec:
  destination: bigquery.googleapis.com/projects/PROJECT/datasets/logs
  filter: |
    resource.type="k8s_container"
    severity>="ERROR"
```

**Query in Log Explorer**:
```
resource.type="k8s_container"
severity="ERROR"
resource.labels.container_name="api-gateway"
timestamp>="2025-10-29T00:00:00Z"
```

### Azure Monitor Logs

**Kusto Query Language (KQL)**:

```kql
// Error rate
ContainerLog
| where TimeGenerated > ago(1h)
| where LogLevel == "ERROR"
| summarize ErrorCount = count() by bin(TimeGenerated, 5m)
| render timechart

// Top error types
ContainerLog
| where LogLevel == "ERROR"
| extend ErrorType = tostring(parse_json(Message).error.type)
| summarize Count = count() by ErrorType
| top 10 by Count desc
```

---

## Security and Compliance

### PII Redaction

**Logstash**:

```ruby
filter {
  mutate {
    gsub => [
      # Redact email
      "message", "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]",

      # Redact credit card
      "message", "\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CC]",

      # Redact SSN
      "message", "\b\d{3}-\d{2}-\d{4}\b", "[SSN]",

      # Redact phone
      "message", "\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"
    ]
  }
}
```

**Vector**:

```toml
[transforms.redact_pii]
type = "remap"
inputs = ["source"]
source = '''
  .message = replace(.message, r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL]")
  .message = replace(.message, r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "[CC]")
  .message = replace(.message, r'\b\d{3}-\d{2}-\d{4}\b', "[SSN]")
'''
```

### Access Control

**Elasticsearch**:

```yaml
# elasticsearch.yml
xpack.security.enabled: true

# Role: read-only logs
POST /_security/role/logs_reader
{
  "indices": [
    {
      "names": ["logs-*"],
      "privileges": ["read"]
    }
  ]
}

# User
POST /_security/user/log_viewer
{
  "password": "password",
  "roles": ["logs_reader"]
}
```

### Audit Logging

**Track who accessed what**:

```yaml
# Elasticsearch audit log
xpack.security.audit.enabled: true
xpack.security.audit.logfile.events.include:
  - access_granted
  - access_denied
  - authentication_failed
```

### Compliance (GDPR, HIPAA)

**Requirements**:
1. **Data minimization**: Only log necessary data
2. **Encryption**: At rest and in transit
3. **Access control**: Role-based access
4. **Retention**: Delete after retention period
5. **Audit trail**: Track who accessed logs

**Implementation**:

```yaml
# Encrypted transport
elasticsearch:
  xpack.security.transport.ssl.enabled: true
  xpack.security.http.ssl.enabled: true

# Encryption at rest
elasticsearch:
  xpack.security.encryption_keys:
    - encryption_key_1

# Retention
ILM policy:
  delete_phase: 90 days
```

---

## Performance Considerations

### Elasticsearch Performance

**Indexing Performance**:

1. **Bulk Indexing**:
```python
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch(['http://localhost:9200'])

actions = [
    {
        "_index": "logs",
        "_source": log
    }
    for log in logs
]

helpers.bulk(es, actions, chunk_size=500)
```

2. **Refresh Interval**:
```json
PUT logs-*/_settings
{
  "index": {
    "refresh_interval": "30s"  # Default: 1s
  }
}
```

3. **Disable Replicas During Bulk Load**:
```json
PUT logs-*/_settings
{
  "index": {
    "number_of_replicas": 0
  }
}
```

**Query Performance**:

1. **Use Filters (Cached)**:
```json
{
  "query": {
    "bool": {
      "filter": [
        {"term": {"service": "api"}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

2. **Limit Field Data**:
```json
PUT logs/_mapping
{
  "properties": {
    "message": {
      "type": "text",
      "index": false  # Don't index, only store
    }
  }
}
```

3. **Use Index Patterns**:
```
# Query only today's index
GET logs-2025.10.29/_search

# NOT
GET logs-*/_search
```

### Loki Performance

**Label Cardinality**:

```yaml
# GOOD: Low cardinality labels
{service="api", environment="prod"}  # ~10 combinations

# BAD: High cardinality labels
{service="api", user_id="123"}  # Millions of combinations
```

**Query Optimization**:

```logql
# GOOD: Specific time range
{service="api"}[5m]

# BAD: Large time range
{service="api"}[24h]
```

---

## Anti-Patterns

### 1. Logging Sensitive Data

```python
# WRONG
logger.info("User login", extra={
    "password": password,
    "ssn": ssn,
    "credit_card": cc
})

# CORRECT
logger.info("User login", extra={
    "user_id": user_id,
    "ip": ip
})
```

### 2. Unstructured Logs

```python
# WRONG
logger.info(f"User {user_id} performed {action}")

# CORRECT
logger.info("User action", extra={
    "user_id": user_id,
    "action": action
})
```

### 3. Logging in Tight Loops

```python
# WRONG
for item in items:
    logger.info(f"Processing {item}")

# CORRECT
logger.info("Processing batch", extra={
    "count": len(items)
})
```

### 4. No Sampling for High-Volume Logs

```python
# WRONG
for request in requests:
    logger.info("Request", extra=request)

# CORRECT
if random.random() < 0.01:  # 1% sampling
    logger.info("Request", extra=request)
```

### 5. Ignoring Log Levels

```python
# WRONG
logger.info("Database connection failed")

# CORRECT
logger.error("Database connection failed")
```

---

## Troubleshooting

### Elasticsearch Issues

**1. Cluster Health Yellow**:
```bash
# Check health
GET _cluster/health

# Cause: Unassigned replica shards
# Fix: Add more nodes or reduce replicas
PUT logs-*/_settings
{
  "number_of_replicas": 0
}
```

**2. High CPU Usage**:
```bash
# Check hot threads
GET _nodes/hot_threads

# Common causes:
# - Heavy queries (optimize)
# - High indexing rate (increase refresh_interval)
# - Merge operations (tune merge settings)
```

**3. Out of Memory**:
```bash
# Check heap usage
GET _nodes/stats/jvm

# Fix: Increase heap size (max 50% of RAM, max 32GB)
ES_JAVA_OPTS="-Xms16g -Xmx16g"
```

### Loki Issues

**1. "maximum of series (50000) reached"**:
```yaml
# Fix: Increase limit
limits_config:
  max_streams_per_user: 100000
```

**2. High Memory Usage**:
```yaml
# Fix: Reduce ingestion rate
limits_config:
  ingestion_rate_mb: 4
  ingestion_burst_size_mb: 6
```

### Fluentd Issues

**1. Buffer Overflow**:
```xml
# Fix: Increase buffer size
<buffer>
  chunk_limit_size 8M
  queue_limit_length 32
  overflow_action block
</buffer>
```

**2. High Memory Usage**:
```xml
# Fix: Reduce buffer
<buffer>
  total_limit_size 256M
</buffer>
```

---

## Conclusion

This comprehensive reference covers:

- **Architecture**: Four-layer model (collection, transport, storage, analysis)
- **Tools**: ELK, EFK, Loki, Vector comparison
- **ELK Stack**: Elasticsearch, Logstash, Kibana setup
- **EFK Stack**: Fluentd for Kubernetes
- **Loki**: Cost-effective alternative
- **Vector**: High-performance pipelines
- **Structured Logging**: JSON format, libraries
- **Parsing**: Grok patterns, enrichment
- **Retention**: ILM, hot/warm/cold storage
- **Querying**: Elasticsearch DSL, LogQL
- **Alerting**: Log-based alerts
- **Cost**: Optimization strategies
- **Kubernetes**: DaemonSet patterns
- **Cloud**: AWS, GCP, Azure logging
- **Security**: PII redaction, access control
- **Performance**: Tuning tips
- **Anti-Patterns**: Common mistakes

**Key Takeaways**:

1. **Use structured logging** (JSON) from the start
2. **Choose the right tool** for your scale and budget
3. **Implement retention policies** to manage costs
4. **Redact sensitive data** before ingestion
5. **Monitor log pipeline health** (buffer size, lag)
6. **Sample high-volume logs** to reduce costs
7. **Use labels wisely** (low cardinality)
8. **Correlate logs with traces** (trace_id)

**Next Steps**:

- Set up logging stack (start with Loki for cost)
- Instrument applications with structured logging
- Configure retention policies
- Create dashboards and alerts
- Monitor costs and optimize

---

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: 3,687
