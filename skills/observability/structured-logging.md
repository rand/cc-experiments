---
name: observability-structured-logging
description: Setting up application logging infrastructure
---



# Structured Logging

**Scope**: JSON logging, log levels, correlation IDs, log aggregation, structured formats

**Lines**: 387

**Last Updated**: 2025-10-18

---

## When to Use This Skill

Use this skill when:
- Setting up application logging infrastructure
- Migrating from unstructured (text) logs to structured (JSON) logs
- Implementing correlation IDs for request tracing
- Configuring log aggregation systems (ELK, Loki, CloudWatch)
- Designing log levels and filtering strategies
- Building multi-service systems requiring log correlation
- Debugging production issues requiring searchable, queryable logs
- Implementing compliance/audit logging requirements

**Don't use** for:
- Simple scripts with minimal logging needs
- Local development without aggregation needs (plain text is fine)

---

## Core Concepts

### Structured vs Unstructured Logging

**Unstructured (Text)**:
```
2025-10-18 10:23:45 INFO User john@example.com logged in from 192.168.1.1
```

**Structured (JSON)**:
```json
{
  "timestamp": "2025-10-18T10:23:45.123Z",
  "level": "info",
  "message": "user_login",
  "user_email": "john@example.com",
  "ip_address": "192.168.1.1",
  "service": "auth",
  "trace_id": "a1b2c3d4e5f6"
}
```

**Benefits of Structured Logging**:
- Machine-parseable without regex
- Queryable by field (WHERE user_email = "john@example.com")
- Consistent format across services
- Easy to index and aggregate
- Type-safe fields

### Log Levels

Standard hierarchy (least to most severe):
1. **TRACE**: Very detailed debugging (function entry/exit)
2. **DEBUG**: Detailed debugging information
3. **INFO**: General informational messages
4. **WARN**: Warning messages (degraded state, retries)
5. **ERROR**: Error messages (handled exceptions)
6. **FATAL/CRITICAL**: Unrecoverable errors (process crashes)

### Correlation IDs

**Purpose**: Track requests across multiple services

**Types**:
- **Trace ID**: Unique identifier for entire request flow
- **Span ID**: Unique identifier for single operation within trace
- **Request ID**: HTTP request identifier
- **Session ID**: User session identifier
- **User ID**: User identifier

### Log Aggregation

**Common Stacks**:
- **ELK**: Elasticsearch + Logstash + Kibana
- **Loki**: Grafana Loki (labels-based, cost-efficient)
- **CloudWatch Logs**: AWS native
- **Datadog**: Commercial SaaS
- **Splunk**: Enterprise log management

---

## Patterns

### Pattern 1: Structured Logger Setup (Python)

```python
import logging
import json
import uuid
from datetime import datetime
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, service_name: str, environment: str):
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
            "service": self.service_name,
            "environment": self.environment,
        }

        # Add correlation ID if present
        trace_id = correlation_id.get()
        if trace_id:
            log_data["trace_id"] = trace_id

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_data)

def setup_logging(service_name: str, environment: str, level: str = "INFO"):
    """Configure structured logging."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Add JSON handler
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(service_name, environment))
    logger.addHandler(handler)

    return logger

# Usage
logger = setup_logging("api-service", "production", "INFO")

def log_with_context(level: str, message: str, **kwargs):
    """Log with additional context fields."""
    log_method = getattr(logger, level)

    # Create log record with extra fields
    extra_record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    extra_record.extra_fields = kwargs

    logger.handle(extra_record)

# Example usage
correlation_id.set(str(uuid.uuid4()))

log_with_context("info", "user_login",
    user_id="user_123",
    email="john@example.com",
    ip_address="192.168.1.1"
)

log_with_context("error", "payment_failed",
    user_id="user_123",
    amount=99.99,
    currency="USD",
    error_code="card_declined"
)
```

### Pattern 2: Structured Logger Setup (Go)

```go
package logger

import (
    "context"
    "encoding/json"
    "os"
    "time"

    "github.com/google/uuid"
)

type Level string

const (
    LevelTrace Level = "trace"
    LevelDebug Level = "debug"
    LevelInfo  Level = "info"
    LevelWarn  Level = "warn"
    LevelError Level = "error"
    LevelFatal Level = "fatal"
)

type Logger struct {
    serviceName string
    environment string
    minLevel    Level
}

type LogEntry struct {
    Timestamp   string                 `json:"timestamp"`
    Level       Level                  `json:"level"`
    Message     string                 `json:"message"`
    Service     string                 `json:"service"`
    Environment string                 `json:"environment"`
    TraceID     string                 `json:"trace_id,omitempty"`
    SpanID      string                 `json:"span_id,omitempty"`
    Fields      map[string]interface{} `json:"fields,omitempty"`
}

func New(serviceName, environment string, minLevel Level) *Logger {
    return &Logger{
        serviceName: serviceName,
        environment: environment,
        minLevel:    minLevel,
    }
}

func (l *Logger) log(ctx context.Context, level Level, message string, fields map[string]interface{}) {
    entry := LogEntry{
        Timestamp:   time.Now().UTC().Format(time.RFC3339Nano),
        Level:       level,
        Message:     message,
        Service:     l.serviceName,
        Environment: l.environment,
        Fields:      fields,
    }

    // Extract trace ID from context
    if traceID := ctx.Value("trace_id"); traceID != nil {
        entry.TraceID = traceID.(string)
    }

    if spanID := ctx.Value("span_id"); spanID != nil {
        entry.SpanID = spanID.(string)
    }

    jsonData, _ := json.Marshal(entry)
    os.Stdout.Write(append(jsonData, '\n'))
}

func (l *Logger) Info(ctx context.Context, message string, fields map[string]interface{}) {
    l.log(ctx, LevelInfo, message, fields)
}

func (l *Logger) Error(ctx context.Context, message string, fields map[string]interface{}) {
    l.log(ctx, LevelError, message, fields)
}

// Usage
func main() {
    log := logger.New("api-service", "production", logger.LevelInfo)

    ctx := context.Background()
    ctx = context.WithValue(ctx, "trace_id", uuid.New().String())

    log.Info(ctx, "user_login", map[string]interface{}{
        "user_id": "user_123",
        "email":   "john@example.com",
        "ip":      "192.168.1.1",
    })
}
```

### Pattern 3: Correlation ID Middleware (FastAPI)

```python
from fastapi import FastAPI, Request
from uuid import uuid4
from contextvars import ContextVar
import logging

app = FastAPI()
correlation_id_var: ContextVar[str] = ContextVar('correlation_id')

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to request context."""
    # Check for existing trace ID from upstream
    trace_id = request.headers.get("X-Trace-ID") or str(uuid4())

    # Set in context
    correlation_id_var.set(trace_id)

    # Add to response headers
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id

    return response

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    trace_id = correlation_id_var.get()

    logging.info(
        "Fetching user",
        extra={
            "trace_id": trace_id,
            "user_id": user_id,
            "endpoint": "/api/users"
        }
    )

    # ... fetch user logic

    return {"user_id": user_id, "trace_id": trace_id}
```

### Pattern 4: Log Aggregation with Loki Labels

```python
import logging
from pythonjsonlogger import jsonlogger

class LokiFormatter(jsonlogger.JsonFormatter):
    """Formatter optimized for Grafana Loki."""

    def add_fields(self, log_record, record, message_dict):
        super(LokiFormatter, self).add_fields(log_record, record, message_dict)

        # Loki uses labels for indexing (keep cardinality low)
        log_record['service'] = 'api-service'
        log_record['environment'] = 'production'
        log_record['level'] = record.levelname.lower()

        # High-cardinality fields go in message (not labels)
        log_record['message'] = record.getMessage()
        log_record['timestamp'] = record.created

# Configure handler
handler = logging.StreamHandler()
handler.setFormatter(LokiFormatter())

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Example log
logger.info(
    "Payment processed",
    extra={
        'user_id': 'user_123',  # High cardinality - not a label
        'amount': 99.99,
        'transaction_id': 'txn_abc123'
    }
)
```

### Pattern 5: Contextual Logger (Rust)

```rust
use serde_json::json;
use tracing::{info, error, span, Level};
use tracing_subscriber::{fmt, prelude::*};
use uuid::Uuid;

fn setup_logging() {
    tracing_subscriber::registry()
        .with(fmt::layer().json())
        .init();
}

fn main() {
    setup_logging();

    let trace_id = Uuid::new_v4().to_string();

    // Create span with trace context
    let span = span!(Level::INFO, "request", trace_id = %trace_id);
    let _enter = span.enter();

    info!(
        user_id = "user_123",
        email = "john@example.com",
        "user_login"
    );

    error!(
        user_id = "user_123",
        error_code = "card_declined",
        amount = 99.99,
        "payment_failed"
    );
}
```

---

## Quick Reference

### Python Libraries
```bash
# Standard library (built-in)
import logging
import json

# JSON formatter
pip install python-json-logger

# Structured logging library
pip install structlog
```

### Go Libraries
```bash
go get -u go.uber.org/zap              # Fast structured logging
go get -u github.com/sirupsen/logrus   # Structured logging
go get -u github.com/rs/zerolog        # Zero-allocation JSON logger
```

### Rust Libraries
```bash
# Add to Cargo.toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["json"] }
serde_json = "1.0"
```

### Log Level Guidelines

```
TRACE:   Function entry/exit, variable values
DEBUG:   Detailed diagnostic information
INFO:    Business events, request/response summaries
WARN:    Degraded performance, retries, deprecated usage
ERROR:   Handled errors, failed operations
FATAL:   Unrecoverable errors, immediate shutdown
```

### Essential Fields

**Always include**:
- `timestamp` (ISO 8601 UTC)
- `level` (lowercase: info, warn, error)
- `message` (event name or description)
- `service` (service name)

**Include when available**:
- `trace_id` (request correlation)
- `span_id` (operation within trace)
- `user_id` (user context)
- `request_id` (HTTP request ID)
- `environment` (dev/staging/prod)

### Loki Label Best Practices

**Good labels** (low cardinality):
- `service`, `environment`, `level`, `host`, `region`

**Bad labels** (high cardinality):
- `user_id`, `request_id`, `trace_id`, `email`, `ip_address`

**Rule**: If it has >100 unique values, it's a field, not a label.

---

## Anti-Patterns

### ❌ Logging Sensitive Data

```python
# WRONG: PII in logs
logger.info(f"User password: {password}")
logger.info(f"Credit card: {card_number}")

# CORRECT: Redact sensitive data
logger.info(f"User authenticated", extra={"user_id": user_id})
logger.info(f"Payment processed", extra={"last4": card_number[-4:]})
```

### ❌ String Concatenation in Logs

```python
# WRONG: Loses structure
logger.info(f"User {user_id} logged in from {ip}")

# CORRECT: Structured fields
logger.info("user_login", extra={"user_id": user_id, "ip": ip})
```

### ❌ Excessive Logging

```python
# WRONG: Log spam
for item in items:  # 10,000 items
    logger.info(f"Processing {item}")

# CORRECT: Batch logging
logger.info(f"Processing batch", extra={"count": len(items)})
# ... process items
logger.info(f"Batch complete", extra={"count": len(items), "duration_ms": elapsed})
```

### ❌ Unstructured Exception Logging

```python
# WRONG: String-only exception
try:
    process()
except Exception as e:
    logger.error(f"Error: {e}")

# CORRECT: Structured with context
try:
    process()
except Exception as e:
    logger.error(
        "process_failed",
        extra={
            "error_type": type(e).__name__,
            "error_message": str(e),
            "user_id": user_id
        },
        exc_info=True  # Includes traceback
    )
```

### ❌ Logging in Hot Paths

```python
# WRONG: Logging in tight loop
for i in range(1_000_000):
    logger.debug(f"Iteration {i}")
    compute()

# CORRECT: Sample or aggregate
if i % 10_000 == 0:
    logger.debug(f"Progress: {i} iterations")
```

### ❌ High-Cardinality Loki Labels

```yaml
# WRONG: High cardinality labels
labels:
  service: api
  user_id: user_123  # Millions of unique values!
  trace_id: abc123   # Billions of unique values!

# CORRECT: Low cardinality labels
labels:
  service: api
  environment: prod
  level: info
# user_id and trace_id go in log fields
```

---

## Related Skills

- **metrics-instrumentation.md** - Complementary numeric metrics
- **distributed-tracing.md** - Deep request tracing with spans
- **alerting-strategy.md** - Log-based alerts and anomaly detection
- **dashboard-design.md** - Log visualization in Grafana

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
