---
name: engineering-error-tracking
description: Production error tracking, grouping, and alerting with Sentry, Rollbar, and alternatives
---

# Error Tracking

**Scope**: Error capture, grouping strategies, Sentry/Rollbar/Bugsnag, stack trace analysis, source maps, release tracking, alert rules, PII scrubbing, error prioritization

**Lines**: 384

**Last Updated**: 2025-10-29

---

## When to Use This Skill

Use this skill when:
- Setting up error tracking for production applications
- Implementing Sentry, Rollbar, or Bugsnag
- Configuring error grouping and fingerprinting
- Analyzing production errors and stack traces
- Setting up error-based alerting
- Tracking errors across releases (regression detection)
- Configuring source map support for JavaScript/TypeScript
- Implementing PII scrubbing and privacy controls
- Prioritizing errors by frequency and user impact
- Integrating error tracking with incident management

**Don't use** for:
- Application logging (use structured-logging.md)
- Monitoring and metrics (use monitoring-alerts.md)
- APM and tracing (use observability-distributed-tracing.md)

---

## Core Concepts

### Error Tracking Architecture

**Capture → Group → Alert → Resolve**

```python
# 1. Capture: Application sends error to tracking service
try:
    process_payment(order)
except Exception as e:
    sentry_sdk.capture_exception(e)  # Sent to Sentry
    raise

# 2. Group: Errors with similar stack traces grouped
# Same issue across 100 users = 1 grouped issue

# 3. Alert: Rules determine when to notify
# New issue, high frequency, user impact threshold

# 4. Resolve: Track resolution, detect regressions
# Mark resolved in release v1.2.3
# Alert if same error appears in v1.2.4
```

**Benefits**:
- Deduplicate similar errors across users
- Identify high-impact issues quickly
- Track error trends over time
- Detect regressions between releases

### Error Context Enrichment

**Always include**:
```python
import sentry_sdk

# User context
sentry_sdk.set_user({
    "id": user.id,
    "email": user.email,  # Scrub if PII sensitive
    "username": user.username,
    "ip_address": request.remote_addr
})

# Tags for filtering and grouping
sentry_sdk.set_tag("environment", "production")
sentry_sdk.set_tag("release", "v1.2.3")
sentry_sdk.set_tag("server", socket.gethostname())
sentry_sdk.set_tag("feature_flag", "new_checkout")

# Breadcrumbs for debugging
sentry_sdk.add_breadcrumb(
    category="user_action",
    message="User clicked checkout button",
    level="info"
)

# Custom context
sentry_sdk.set_context("order", {
    "order_id": order.id,
    "total": order.total,
    "items_count": len(order.items)
})
```

**Why this matters**:
- `user` → Identify affected users, count unique users
- `tags` → Filter errors by environment, release, server
- `breadcrumbs` → Understand user journey before error
- `context` → Domain-specific debugging info

### Error Grouping Strategies

**1. Default: Stack trace similarity**
```python
# These errors grouped together
def process_order(order):
    order.total()  # AttributeError: NoneType has no attribute 'total'

# Same stack trace = same group (even if order IDs differ)
```

**2. Custom fingerprinting**
```python
# Group by error message pattern, not stack
sentry_sdk.set_tag("fingerprint", ["database-connection-error"])

# Or by exception type + critical context
def custom_fingerprint(event):
    if "DatabaseError" in str(event.get("exception")):
        # Group all DB errors together
        return ["database-error"]

    # Default grouping
    return event.get("fingerprint", ["{{ default }}"])
```

**3. Ignore noisy errors**
```python
import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

# Ignore specific exception types
sentry_sdk.init(
    dsn="...",
    ignore_errors=[
        KeyboardInterrupt,
        BrokenPipeError,
        "MyCustomNonCriticalError"
    ]
)

# Ignore by error message pattern
def before_send(event, hint):
    if "connection reset by peer" in str(event):
        return None  # Don't send to Sentry
    return event

sentry_sdk.init(dsn="...", before_send=before_send)
```

---

## Patterns

### Pattern 1: Sentry Initialization (Python)

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn="https://examplePublicKey@o0.ingest.sentry.io/0",

    # Environment
    environment="production",
    release="myapp@1.2.3",

    # Sampling
    traces_sample_rate=0.1,  # 10% transaction sampling for performance
    profiles_sample_rate=0.1,

    # Integrations
    integrations=[
        FlaskIntegration(),
        SqlalchemyIntegration(),
    ],

    # Privacy
    send_default_pii=False,  # Don't send cookies, headers by default

    # Filtering
    before_send=scrub_sensitive_data,
    ignore_errors=[KeyboardInterrupt, SystemExit],

    # Performance
    _experiments={
        "profiles_sample_rate": 0.1,
    }
)

def scrub_sensitive_data(event, hint):
    # Remove PII from error data
    if "request" in event:
        if "headers" in event["request"]:
            # Remove auth tokens
            event["request"]["headers"].pop("Authorization", None)
            event["request"]["headers"].pop("Cookie", None)
    return event
```

### Pattern 2: Node.js/Express Integration

```javascript
const Sentry = require("@sentry/node");
const { ProfilingIntegration } = require("@sentry/profiling-node");
const express = require("express");

const app = express();

// Initialize BEFORE any other middleware
Sentry.init({
  dsn: "https://examplePublicKey@o0.ingest.sentry.io/0",
  environment: process.env.NODE_ENV,
  release: process.env.RELEASE_VERSION,

  // Performance monitoring
  tracesSampleRate: 0.1,
  profilesSampleRate: 0.1,

  integrations: [
    new Sentry.Integrations.Http({ tracing: true }),
    new Sentry.Integrations.Express({ app }),
    new ProfilingIntegration(),
  ],

  // Filter sensitive data
  beforeSend(event) {
    // Remove query parameters with tokens
    if (event.request?.url) {
      event.request.url = event.request.url.split('?')[0];
    }
    return event;
  },
});

// Request handler MUST be first middleware
app.use(Sentry.Handlers.requestHandler());
app.use(Sentry.Handlers.tracingHandler());

// App routes here
app.get("/", (req, res) => {
  res.send("Hello");
});

// Error handler MUST be last middleware
app.use(Sentry.Handlers.errorHandler());

app.listen(3000);
```

### Pattern 3: Source Map Configuration

```javascript
// Next.js with Sentry
// next.config.js
const { withSentryConfig } = require("@sentry/nextjs");

module.exports = withSentryConfig(
  {
    // Next.js config
  },
  {
    // Sentry webpack plugin options
    silent: true,
    org: "my-org",
    project: "my-project",

    // Upload source maps to Sentry
    widenClientFileUpload: true,

    // Hide source maps from public
    hideSourceMaps: true,

    // Automatically create releases
    autoInstrumentServerFunctions: true,
  }
);

// Webpack manual configuration
const SentryWebpackPlugin = require("@sentry/webpack-plugin");

module.exports = {
  devtool: "hidden-source-map",
  plugins: [
    new SentryWebpackPlugin({
      authToken: process.env.SENTRY_AUTH_TOKEN,
      org: "my-org",
      project: "my-project",
      include: "./dist",
      ignore: ["node_modules"],
    }),
  ],
};
```

### Pattern 4: Release Tracking

```bash
# Create release in Sentry
sentry-cli releases new "myapp@1.2.3"

# Associate commits (for regression detection)
sentry-cli releases set-commits "myapp@1.2.3" --auto

# Upload source maps
sentry-cli releases files "myapp@1.2.3" upload-sourcemaps ./dist

# Finalize release
sentry-cli releases finalize "myapp@1.2.3"

# Deploy notification
sentry-cli releases deploys "myapp@1.2.3" new -e production
```

**In CI/CD**:
```yaml
# .github/workflows/deploy.yml
- name: Create Sentry release
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: my-org
    SENTRY_PROJECT: my-project
  run: |
    VERSION=$(git describe --tags --always)
    sentry-cli releases new "$VERSION"
    sentry-cli releases set-commits "$VERSION" --auto
    sentry-cli releases files "$VERSION" upload-sourcemaps ./dist
    sentry-cli releases finalize "$VERSION"
    sentry-cli releases deploys "$VERSION" new -e production
```

### Pattern 5: Alert Rules

```python
# Alert on new issues
{
    "name": "New Error in Production",
    "conditions": [
        {"id": "sentry.rules.conditions.first_seen_event.FirstSeenEventCondition"}
    ],
    "filters": [
        {"id": "sentry.rules.filters.tagged_event.TaggedEventFilter",
         "key": "environment", "match": "eq", "value": "production"}
    ],
    "actions": [
        {"id": "sentry.integrations.slack.notify_action.SlackNotifyServiceAction",
         "workspace": "123", "channel": "#alerts"}
    ]
}

# Alert on high frequency
{
    "name": "High Error Frequency",
    "conditions": [
        {"id": "sentry.rules.conditions.event_frequency.EventFrequencyCondition",
         "value": 100, "interval": "1h"}  # 100 events in 1 hour
    ],
    "actions": [
        {"id": "sentry.integrations.pagerduty.notify_action.PagerDutyNotifyServiceAction",
         "service": "P1234"}
    ]
}

# Alert on regression
{
    "name": "Regression Detected",
    "conditions": [
        {"id": "sentry.rules.conditions.regression_event.RegressionEventCondition"}
    ],
    "actions": [
        {"id": "sentry.mail.actions.NotifyEmailAction",
         "targetType": "Team", "targetIdentifier": "engineering"}
    ]
}
```

### Pattern 6: Error Prioritization

```python
# Prioritization factors
def calculate_priority(issue):
    score = 0

    # Frequency (events in last 24h)
    if issue.count_24h > 1000:
        score += 10
    elif issue.count_24h > 100:
        score += 5
    elif issue.count_24h > 10:
        score += 2

    # User impact (unique users affected)
    if issue.unique_users_24h > 100:
        score += 10
    elif issue.unique_users_24h > 10:
        score += 5

    # Environment
    if "production" in issue.tags.get("environment"):
        score += 5

    # Status
    if issue.status == "regression":
        score += 8  # Regressions are high priority

    # First seen
    if issue.first_seen_within_hours(24):
        score += 3  # New issues need attention

    return score

# Priority levels
# 20+: P0 - Critical, page on-call
# 15-19: P1 - High, notify team
# 10-14: P2 - Medium, create ticket
# <10: P3 - Low, review in triage
```

---

## Quick Reference

### Sentry CLI Commands

```bash
# Authentication
sentry-cli login

# Releases
sentry-cli releases new <version>
sentry-cli releases set-commits <version> --auto
sentry-cli releases finalize <version>
sentry-cli releases list

# Source maps
sentry-cli releases files <version> upload-sourcemaps <path>
sentry-cli releases files <version> list

# Debug
sentry-cli send-event -m "Test message"
```

### Error Tracking Best Practices

```
✅ DO: Include rich context (user, tags, breadcrumbs)
✅ DO: Set up release tracking for regression detection
✅ DO: Configure source maps for JavaScript/TypeScript
✅ DO: Scrub PII and sensitive data before sending
✅ DO: Use custom fingerprinting for better grouping
✅ DO: Set sample rates to control volume and cost
✅ DO: Alert on high-impact errors (frequency + user count)
✅ DO: Integrate with incident management workflow

❌ DON'T: Send every error (use sampling for high volume)
❌ DON'T: Forget to upload source maps (stack traces useless without)
❌ DON'T: Alert on every error (causes alert fatigue)
❌ DON'T: Include passwords, tokens, or PII in context
❌ DON'T: Use default grouping for all errors (customize when needed)
```

---

## Anti-Patterns

### Sending All Errors Without Sampling

```python
# ❌ WRONG: No sampling, high volume can overwhelm
sentry_sdk.init(
    dsn="...",
    traces_sample_rate=1.0  # 100% of transactions
)

# ✅ CORRECT: Sample high-volume apps
sentry_sdk.init(
    dsn="...",
    traces_sample_rate=0.1,  # 10% sampling

    # Higher sampling for errors than transactions
    before_send=lambda event, hint: event if random.random() < 0.5 else None
)
```

### Missing Source Maps

```javascript
// ❌ WRONG: Minified stack traces are useless
// build.js
output: {
    filename: 'bundle.min.js'
}
// No source maps uploaded

// ✅ CORRECT: Generate and upload source maps
output: {
    filename: 'bundle.min.js',
    sourceMapFilename: '[file].map'
}

// In CI: Upload to Sentry
// sentry-cli releases files <version> upload-sourcemaps ./dist
```

### Leaking PII in Errors

```python
# ❌ WRONG: Sensitive data in error message
raise ValueError(f"Invalid credit card: {user.credit_card_number}")

# ✅ CORRECT: Generic message, PII in scrubbed context
raise ValueError("Invalid credit card")
# Context automatically scrubbed by before_send hook
```

### Poor Error Grouping

```python
# ❌ WRONG: Dynamic data in exception message
raise Exception(f"Order {order_id} failed at {timestamp}")
# Creates separate issue for every order/time

# ✅ CORRECT: Static message, dynamic data in context
sentry_sdk.set_context("order", {"id": order_id, "timestamp": timestamp})
raise Exception("Order processing failed")
# All grouped under single issue
```

---

## Level 3: Resources

This skill has **Level 3 Resources** available with comprehensive reference material, production-ready scripts, and runnable examples.

### Resource Structure

```
error-tracking/resources/
├── REFERENCE.md                           # Comprehensive reference (3,200+ lines)
│   ├── Error tracking architecture
│   ├── Sentry setup and configuration
│   ├── Rollbar, Bugsnag, Airbrake comparison
│   ├── Error grouping and fingerprinting
│   ├── Stack trace analysis
│   ├── Source map support (JS/TS)
│   ├── Release tracking and regression detection
│   ├── Alert rules and thresholds
│   ├── Error prioritization strategies
│   ├── PII scrubbing and privacy
│   ├── Multi-language integration
│   ├── Distributed systems error correlation
│   └── Production troubleshooting
│
├── scripts/                               # Production-ready tools
│   ├── setup_error_tracking.py            # Automated Sentry deployment
│   ├── analyze_errors.py                  # Error pattern analysis
│   └── test_error_tracking.py             # Error capture testing
│
└── examples/                              # Runnable examples
    ├── sentry-self-hosted/
    │   └── docker-compose.yml             # Self-hosted Sentry setup
    ├── python-integration/
    │   ├── flask-sentry.py                # Flask integration
    │   ├── django-sentry.py               # Django integration
    │   └── fastapi-sentry.py              # FastAPI integration
    ├── nodejs-integration/
    │   ├── express-sentry.js              # Express integration
    │   └── nextjs-sentry.js               # Next.js integration
    ├── go-integration/
    │   └── sentry-middleware.go           # Go custom middleware
    ├── source-maps/
    │   └── webpack-sourcemap-config.js    # Source map setup
    ├── fingerprinting/
    │   └── custom-grouping.py             # Custom error grouping
    ├── release-tracking/
    │   └── ci-release-automation.yml      # Release tracking in CI
    ├── alerts/
    │   └── alert-rules.json               # Sentry alert configurations
    └── error-budget/
        └── error-budget-tracker.py        # Error budget tracking
```

### Key Resources

**REFERENCE.md**: Comprehensive 3,200+ line guide covering error tracking architecture, tool comparison, integration patterns, and production best practices.

**setup_error_tracking.py**: Automated deployment tool (700+ lines) for Sentry projects with multi-project setup, integration configuration, and alert rule generation.

**analyze_errors.py**: Error analysis tool (700+ lines) for pattern detection, regression analysis, impact assessment, and triage recommendations.

**test_error_tracking.py**: Testing tool (600+ lines) for validating error capture, grouping, alerts, and performance impact.

---

## Related Skills

- **monitoring-alerts.md** - Alert design and escalation policies
- **structured-logging.md** - Application logging and log aggregation
- **observability-distributed-tracing.md** - Request tracing and APM
- **incident-response.md** - Handling production incidents
- **ci-cd-pipelines.md** - Integrating error tracking in CI/CD

---

**Last Updated**: 2025-10-29
**Format Version**: 1.0 (Atomic)
**Level 3 Resources**: Available
