# Example Log Output Samples

This document shows real-world log output from the structured logging examples in different formats.

## Pretty Console Format

### Request Correlation Demo

```
2024-01-15T10:30:45.123456Z  INFO structured_logging: === Request Correlation Demo ===
    at src/main.rs:15
    in demo_request_correlation

2024-01-15T10:30:45.124123Z  INFO structured_logging: Root request created
    at src/main.rs:23
    in demo_request_correlation
    request_id: 550e8400-e29b-41d4-a716-446655440000
    user_id: "user_123"

2024-01-15T10:30:45.124567Z  INFO structured_logging: Child request 1 created
    at src/main.rs:28
    in demo_request_correlation
    request_id: 660f9511-f39c-52e5-b827-557766551111
    parent_id: 550e8400-e29b-41d4-a716-446655440000

2024-01-15T10:30:45.124789Z  INFO structured_logging: Child request 2 created
    at src/main.rs:34
    in demo_request_correlation
    request_id: 770fa622-043d-63f6-c938-668877662222
    parent_id: 550e8400-e29b-41d4-a716-446655440000

2024-01-15T10:30:45.125012Z  INFO structured_logging: Processing operation
    at src/main.rs:51
    in process_with_context with request_id: 660f9511-f39c-52e5-b827-557766551111
    operation: "Operation 1"

2024-01-15T10:30:45.175234Z DEBUG structured_logging: Operation completed
    at src/main.rs:57
    in process_with_context with request_id: 660f9511-f39c-52e5-b827-557766551111
    operation: "Operation 1"
```

### DSPy Event Logging Demo

```
2024-01-15T10:30:46.123456Z  INFO structured_logging: === DSPy Event Logging Demo ===
    at src/main.rs:62
    in demo_dspy_events

2024-01-15T10:30:46.124123Z  INFO structured_logging: DSPy prediction completed
    at src/lib.rs:245
    in DSpyEvent::log with request_id: 880fb733-154e-74g7-d049-779988773333
    model: "gpt-4"
    prompt_tokens: 150
    completion_tokens: 75
    latency_ms: 1250
    total_tokens: 225

2024-01-15T10:30:46.124567Z  INFO structured_logging: DSPy optimization step
    at src/lib.rs:261
    in DSpyEvent::log with request_id: 880fb733-154e-74g7-d049-779988773333
    optimizer: "MIPROv2"
    iteration: 5
    score: 0.87
    improvement: 0.12

2024-01-15T10:30:46.124789Z DEBUG structured_logging: DSPy pipeline stage
    at src/lib.rs:275
    in DSpyEvent::log with request_id: 880fb733-154e-74g7-d049-779988773333
    pipeline: "qa_pipeline"
    stage: "retrieval"
    status: "completed"

2024-01-15T10:30:46.125012Z TRACE structured_logging: DSPy cache operation
    at src/lib.rs:287
    in DSpyEvent::log with request_id: 880fb733-154e-74g7-d049-779988773333
    operation: "get"
    hit: true
    key: "prompt:abc123"
```

### Error Handling with Full Context

```
2024-01-15T10:30:47.123456Z  INFO structured_logging: === Error Handling Demo ===
    at src/main.rs:95
    in demo_error_handling

2024-01-15T10:30:47.124123Z  INFO structured_logging: Executing operation
    at src/main.rs:142
    in execute_operation with request_id: 990fc844-265f-85h8-e15a-88aa99884444
    succeed: true

2024-01-15T10:30:47.124567Z  INFO structured_logging: Operation succeeded
    at src/main.rs:101
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    result: "Operation completed successfully"

2024-01-15T10:30:47.124789Z  INFO structured_logging: Executing operation
    at src/main.rs:142
    in execute_operation with request_id: 990fc844-265f-85h8-e15a-88aa99884444
    succeed: false

2024-01-15T10:30:47.125012Z ERROR structured_logging: Operation failed with full error context
    at src/main.rs:118
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    error: Failed to execute operation
    error_chain: [
        "Failed to execute operation",
        "Operation failed: simulated error"
    ]

2024-01-15T10:30:47.125234Z ERROR structured_logging: Nested operation failed
    at src/main.rs:124
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    error: Failed at top level

2024-01-15T10:30:47.125456Z ERROR structured_logging: Error chain
    at src/main.rs:127
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    level: 0
    cause: "Failed at top level"

2024-01-15T10:30:47.125678Z ERROR structured_logging: Error chain
    at src/main.rs:127
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    level: 1
    cause: "Failed at level 1"

2024-01-15T10:30:47.125890Z ERROR structured_logging: Error chain
    at src/main.rs:127
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    level: 2
    cause: "Failed at level 2"

2024-01-15T10:30:47.126012Z ERROR structured_logging: Error chain
    at src/main.rs:127
    in demo_error_handling
    request_id: 990fc844-265f-85h8-e15a-88aa99884444
    level: 3
    cause: "Deep nested error at level 3"
```

### Performance Metrics Demo

```
2024-01-15T10:30:48.123456Z  INFO structured_logging: === Performance Metrics Demo ===
    at src/main.rs:176
    in demo_performance_metrics

2024-01-15T10:30:48.173567Z  INFO structured_logging: Performance metric
    at src/lib.rs:315
    in PerformanceMetric::log with request_id: aa0fd955-376g-96i9-f26b-99bb00995555
    operation: "operation_0"
    duration_ms: 50
    success: false

2024-01-15T10:30:48.224789Z  INFO structured_logging: Performance metric
    at src/lib.rs:315
    in PerformanceMetric::log with request_id: bb1fe066-487h-07ja-037c-00cc11aa6666
    operation: "operation_1"
    duration_ms: 60
    success: true

[... more metrics ...]

2024-01-15T10:30:49.125012Z  INFO structured_logging: Performance metrics summary
    at src/main.rs:201
    in demo_performance_metrics
    total: 10
    successful: 7
    mean_ms: 95.5
    p50_ms: 90
    p95_ms: 140
    p99_ms: 140
    max_ms: 140

Metrics Summary:
  Total Operations: 10
  Successful: 7
  Mean Duration: 95.50ms
  P50: 90ms
  P95: 140ms
  P99: 140ms
  Max: 140ms
```

### Instrumented Service Demo

```
2024-01-15T10:30:50.123456Z  INFO structured_logging: === Instrumented Service Demo ===
    at src/main.rs:213
    in demo_instrumented_service

2024-01-15T10:30:50.124123Z  INFO structured_logging: Executing predictions...
    at src/main.rs:233
    in demo_instrumented_service

2024-01-15T10:30:50.124567Z  INFO structured_logging: Starting prediction
    at src/lib.rs:456
    in InstrumentedDSpyService::predict with request_id: cc2ff177-598i-18kb-148d-11dd22bb7777
    model: "gpt-4"
    prompt_len: 38

2024-01-15T10:30:50.224789Z  INFO structured_logging: DSPy prediction completed
    at src/lib.rs:245
    in DSpyEvent::log with request_id: cc2ff177-598i-18kb-148d-11dd22bb7777
    model: "gpt-4"
    prompt_tokens: 9
    completion_tokens: 14
    latency_ms: 100
    total_tokens: 23

2024-01-15T10:30:50.225012Z  INFO structured_logging: Performance metric
    at src/lib.rs:315
    in PerformanceMetric::log with request_id: cc2ff177-598i-18kb-148d-11dd22bb7777
    operation: "predict:gpt-4"
    duration_ms: 100
    success: true

2024-01-15T10:30:50.225234Z  INFO structured_logging: Prediction completed successfully
    at src/lib.rs:479
    in InstrumentedDSpyService::predict with request_id: cc2ff177-598i-18kb-148d-11dd22bb7777
    duration_ms: 100
    response_len: 54
```

## JSON Format

### Single Event

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "fields": {
    "message": "DSPy prediction completed",
    "request_id": "880fb733-154e-74g7-d049-779988773333",
    "model": "gpt-4",
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "latency_ms": 1250,
    "total_tokens": 225
  },
  "target": "structured_logging",
  "span": {
    "name": "log",
    "request_id": "880fb733-154e-74g7-d049-779988773333"
  },
  "spans": [
    {
      "name": "demo_dspy_events"
    },
    {
      "name": "log",
      "request_id": "880fb733-154e-74g7-d049-779988773333"
    }
  ],
  "file": "src/lib.rs",
  "line": 245
}
```

### Error Event with Chain

```json
{
  "timestamp": "2024-01-15T10:30:47.125012Z",
  "level": "ERROR",
  "fields": {
    "message": "Operation failed with full error context",
    "request_id": "990fc844-265f-85h8-e15a-88aa99884444",
    "error": "Failed to execute operation",
    "error_chain": [
      "Failed to execute operation",
      "Operation failed: simulated error"
    ]
  },
  "target": "structured_logging",
  "span": {
    "name": "demo_error_handling"
  },
  "file": "src/main.rs",
  "line": 118
}
```

### Performance Metric Event

```json
{
  "timestamp": "2024-01-15T10:30:48.173567Z",
  "level": "INFO",
  "fields": {
    "message": "Performance metric",
    "request_id": "aa0fd955-376g-96i9-f26b-99bb00995555",
    "operation": "operation_0",
    "duration_ms": 50,
    "success": false
  },
  "target": "structured_logging",
  "span": {
    "name": "log",
    "request_id": "aa0fd955-376g-96i9-f26b-99bb00995555"
  },
  "spans": [
    {
      "name": "demo_performance_metrics"
    },
    {
      "name": "record"
    },
    {
      "name": "log",
      "request_id": "aa0fd955-376g-96i9-f26b-99bb00995555"
    }
  ],
  "file": "src/lib.rs",
  "line": 315
}
```

## Compact Format

```
2024-01-15T10:30:45.123456Z INFO demo_request_correlation: structured_logging: === Request Correlation Demo ===
2024-01-15T10:30:45.124123Z INFO demo_request_correlation: structured_logging: Root request created request_id=550e8400-e29b-41d4-a716-446655440000 user_id="user_123"
2024-01-15T10:30:45.124567Z INFO demo_request_correlation: structured_logging: Child request 1 created request_id=660f9511-f39c-52e5-b827-557766551111 parent_id=550e8400-e29b-41d4-a716-446655440000
2024-01-15T10:30:45.125012Z INFO process_with_context{request_id=660f9511-f39c-52e5-b827-557766551111}: structured_logging: Processing operation operation="Operation 1"
2024-01-15T10:30:45.175234Z DEBUG process_with_context{request_id=660f9511-f39c-52e5-b827-557766551111}: structured_logging: Operation completed operation="Operation 1"
```

## Concurrent Operations with Correlation

```
2024-01-15T10:30:51.123456Z  INFO structured_logging: === Concurrent Operations Demo ===
    at src/main.rs:308
    in demo_concurrent_operations

2024-01-15T10:30:51.124123Z  INFO structured_logging: Worker started
    at src/main.rs:339
    in concurrent_worker with request_id: dd3gg288-6a9j-29lc-259e-22ee33cc8888
    worker_id: 0

2024-01-15T10:30:51.124567Z  INFO structured_logging: Worker started
    at src/main.rs:339
    in concurrent_worker with request_id: ee4hh399-7b0k-30md-360f-33ff44dd9999
    worker_id: 1

2024-01-15T10:30:51.124789Z  INFO structured_logging: Worker started
    at src/main.rs:339
    in concurrent_worker with request_id: ff5ii400-8c1l-41ne-471g-44gg55ee0000
    worker_id: 2

2024-01-15T10:30:51.125012Z  INFO structured_logging: Worker started
    at src/main.rs:339
    in concurrent_worker with request_id: 006jj511-9d2m-52of-582h-55hh66ff1111
    worker_id: 3

2024-01-15T10:30:51.125234Z  INFO structured_logging: Worker started
    at src/main.rs:339
    in concurrent_worker with request_id: 117kk622-0e3n-63pg-693i-66ii77gg2222
    worker_id: 4

2024-01-15T10:30:51.174567Z WARN structured_logging: Worker encountered non-fatal issue
    at src/main.rs:347
    in concurrent_worker with request_id: dd3gg288-6a9j-29lc-259e-22ee33cc8888
    worker_id: 0

2024-01-15T10:30:51.174789Z  INFO structured_logging: Worker completed
    at src/main.rs:350
    in concurrent_worker with request_id: dd3gg288-6a9j-29lc-259e-22ee33cc8888
    worker_id: 0
    duration_ms: 50

2024-01-15T10:30:51.194123Z  INFO structured_logging: Worker completed
    at src/main.rs:350
    in concurrent_worker with request_id: ee4hh399-7b0k-30md-360f-33ff44dd9999
    worker_id: 1
    duration_ms: 70
```

## Log Levels Demonstration

```
2024-01-15T10:30:52.123456Z  INFO structured_logging: === Log Levels Demo ===
    at src/main.rs:360
    in demo_log_levels

2024-01-15T10:30:52.124123Z TRACE structured_logging: This is a TRACE message
    at src/main.rs:365
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333

2024-01-15T10:30:52.124567Z DEBUG structured_logging: This is a DEBUG message
    at src/main.rs:366
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333

2024-01-15T10:30:52.124789Z  INFO structured_logging: This is an INFO message
    at src/main.rs:367
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333

2024-01-15T10:30:52.125012Z  WARN structured_logging: This is a WARN message
    at src/main.rs:368
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333

2024-01-15T10:30:52.125234Z ERROR structured_logging: This is an ERROR message
    at src/main.rs:369
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333

2024-01-15T10:30:52.125456Z DEBUG structured_logging: Debug with structured fields
    at src/main.rs:371
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333
    field1: "value1"
    field2: 42
    field3: true

2024-01-15T10:30:52.125678Z  INFO structured_logging: User action logged
    at src/main.rs:379
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333
    user: "john_doe"
    action: "login"
    duration_ms: 125

2024-01-15T10:30:52.125890Z  WARN structured_logging: Threshold exceeded
    at src/main.rs:387
    in demo_log_levels
    request_id: 228ll733-1f4o-74qh-7a4j-77jj88hh3333
    threshold: 1000
    actual: 1250
```

## Integration with Log Aggregation Systems

### Elasticsearch Query Examples

```json
// Find all errors for a specific request
{
  "query": {
    "bool": {
      "must": [
        { "term": { "level": "ERROR" } },
        { "term": { "fields.request_id": "550e8400-e29b-41d4-a716-446655440000" } }
      ]
    }
  }
}

// Find slow predictions (> 1000ms)
{
  "query": {
    "bool": {
      "must": [
        { "match": { "fields.message": "DSPy prediction completed" } },
        { "range": { "fields.latency_ms": { "gt": 1000 } } }
      ]
    }
  },
  "sort": [
    { "fields.latency_ms": "desc" }
  ]
}

// Aggregate by operation type
{
  "aggs": {
    "operations": {
      "terms": {
        "field": "fields.operation.keyword"
      },
      "aggs": {
        "avg_duration": {
          "avg": { "field": "fields.duration_ms" }
        }
      }
    }
  }
}
```

### Splunk Search Examples

```spl
# Find request chain
index=app_logs request_id="550e8400-e29b-41d4-a716-446655440000" OR parent_id="550e8400-e29b-41d4-a716-446655440000"
| table _time request_id parent_id message
| sort _time

# Calculate p95 latency by model
index=app_logs "DSPy prediction completed"
| stats perc95(latency_ms) as p95_latency by model

# Error rate over time
index=app_logs level=ERROR
| timechart count span=5m
```
