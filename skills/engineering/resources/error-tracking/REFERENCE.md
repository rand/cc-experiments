# Error Tracking - Comprehensive Reference

**Version**: 1.0
**Last Updated**: 2025-10-29
**Lines**: 3,200+

This comprehensive reference covers production error tracking systems, including Sentry, Rollbar, Bugsnag, and alternatives. It includes architecture patterns, integration strategies, error grouping, alerting, and operational best practices.

---

## Table of Contents

1. [Error Tracking Architecture](#error-tracking-architecture)
2. [Error Tracking Tools Landscape](#error-tracking-tools-landscape)
3. [Sentry Deep Dive](#sentry-deep-dive)
4. [Alternative Tools](#alternative-tools)
5. [Error Context Enrichment](#error-context-enrichment)
6. [Error Grouping and Fingerprinting](#error-grouping-and-fingerprinting)
7. [Stack Trace Analysis](#stack-trace-analysis)
8. [Source Map Support](#source-map-support)
9. [Release Tracking](#release-tracking)
10. [Alert Strategies](#alert-strategies)
11. [Error Prioritization](#error-prioritization)
12. [PII and Privacy](#pii-and-privacy)
13. [Multi-Language Integration](#multi-language-integration)
14. [Distributed Systems](#distributed-systems)
15. [Performance and Sampling](#performance-and-sampling)
16. [Testing Error Tracking](#testing-error-tracking)
17. [Operational Patterns](#operational-patterns)
18. [Troubleshooting](#troubleshooting)
19. [Anti-Patterns](#anti-patterns)

---

## Error Tracking Architecture

### Core Pipeline

Error tracking systems follow a standard pipeline:

```
Application → Capture → Transport → Aggregate → Group → Alert → Resolve
```

**1. Capture**: Exception intercepted in application
```python
try:
    risky_operation()
except Exception as e:
    # Capture with context
    error_tracker.capture(e, context={...})
    raise
```

**2. Transport**: Error sent to tracking service
```
HTTP POST → Error tracking API
- Compressed payload
- Asynchronous (non-blocking)
- Retry on failure
- Rate limiting
```

**3. Aggregate**: Enrich error with metadata
```
Original error + Context data
→ User info
→ Environment info
→ Breadcrumbs (recent events)
→ Stack trace
→ Request data
```

**4. Group**: Similar errors clustered
```
Stack trace similarity analysis
→ Group by exception type + stack frames
→ Custom fingerprinting rules
→ One issue per error pattern
```

**5. Alert**: Notify on threshold breach
```
New issue created → Slack notification
Frequency > 100/hour → PagerDuty alert
Regression detected → Email to team
```

**6. Resolve**: Track resolution workflow
```
Deploy fix in release v1.2.3
→ Mark issue resolved
→ Monitor for regression
→ Auto-reopen if seen again
```

### Architecture Patterns

#### Pattern 1: Client-Side Capture

```javascript
// Browser captures unhandled errors
window.addEventListener('error', (event) => {
    ErrorTracker.captureException(event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    ErrorTracker.captureException(event.reason);
});

// Manual capture
try {
    processPayment();
} catch (err) {
    ErrorTracker.captureException(err);
    throw err;
}
```

**Challenges**:
- Browser extension interference
- Ad blockers blocking tracking domains
- CORS restrictions
- Large payload size (full stack trace)
- Privacy concerns (PII in URLs, forms)

**Solutions**:
- Use first-party domain for error endpoint
- Compress and sample data
- Scrub sensitive data client-side
- Implement retry with exponential backoff

#### Pattern 2: Server-Side Capture

```python
# Python middleware captures all exceptions
from flask import Flask
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

app = Flask(__name__)

sentry_sdk.init(
    dsn="...",
    integrations=[FlaskIntegration()],
    traces_sample_rate=0.1
)

# Automatic capture - no code changes needed
@app.route('/api/payment')
def process_payment():
    # Any exception automatically captured
    result = payment_service.charge(amount)
    return result
```

**Benefits**:
- Controlled environment (no browser quirks)
- Rich context (DB queries, system metrics)
- Reliable delivery (no client-side blocking)
- Server-side source maps

**Challenges**:
- Async error handling (background jobs)
- Multi-process applications (shared state)
- High throughput (need sampling)

#### Pattern 3: Proxy Pattern

```
Application → Local Proxy → Error Tracking Service
```

```yaml
# relay.yml - Sentry Relay config
relay:
  mode: proxy
  upstream: https://sentry.io

  # Process data before forwarding
  normalization:
    enabled: true

  # PII scrubbing
  pii:
    enabled: true
    config:
      rules:
        - type: pattern
          pattern: '\d{3}-\d{2}-\d{4}'  # SSN
          redaction:
            method: replace
            text: '[Filtered]'
```

**Benefits**:
- Centralized PII scrubbing
- Network control (firewall, VPN)
- Data retention control
- Batch processing (reduced API calls)

**Use cases**:
- Compliance requirements (GDPR, HIPAA)
- Air-gapped environments
- High-volume applications

### Error Lifecycle

```
NEW → ACKNOWLEDGED → IN_PROGRESS → RESOLVED → REGRESSION
  ↓           ↓              ↓           ↓          ↓
IGNORED   ASSIGNED       MERGED    AUTO-RESOLVE  REOPEN
```

**State transitions**:

1. **NEW**: First occurrence of error
   - Alert team via configured channels
   - Assign based on ownership rules
   - High priority if production + high frequency

2. **ACKNOWLEDGED**: Team aware, investigating
   - Suppresses duplicate alerts
   - Starts SLA clock for resolution

3. **IN_PROGRESS**: Active work on fix
   - Link to PR/commit fixing issue
   - Track time to resolution

4. **RESOLVED**: Fixed in specific release
   - Associate with release version
   - Monitor for regression

5. **REGRESSION**: Reappears after resolution
   - Auto-reopen with high priority
   - Alert original assignee

6. **IGNORED**: Decided not to fix
   - Suppress all alerts
   - Document reason for ignoring

---

## Error Tracking Tools Landscape

### Tool Comparison Matrix

| Feature | Sentry | Rollbar | Bugsnag | Airbrake | New Relic | Datadog |
|---------|--------|---------|---------|----------|-----------|---------|
| **Open Source** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Self-Hosted** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Multi-Language** | ✅ 80+ | ✅ 40+ | ✅ 20+ | ✅ 15+ | ✅ Many | ✅ Many |
| **Source Maps** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Release Tracking** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Performance Monitoring** | ✅ Yes | ⚠️ Limited | ⚠️ Limited | ❌ No | ✅ Yes | ✅ Yes |
| **Session Replay** | ✅ Yes | ❌ No | ⚠️ Limited | ❌ No | ✅ Yes | ✅ Yes |
| **Distributed Tracing** | ✅ Yes | ❌ No | ⚠️ Limited | ❌ No | ✅ Yes | ✅ Yes |
| **Pricing (5M events)** | ~$100/mo | ~$150/mo | ~$200/mo | ~$150/mo | ~$500/mo | ~$400/mo |
| **Free Tier** | 5K events | 5K events | 7.5K events | Free plan | Limited | Trial only |

### When to Choose Each Tool

**Sentry**:
- Best for: Open source, self-hosted requirements
- Strengths: Feature-rich, active development, strong community
- Weaknesses: Complex self-hosted setup, pricing can scale high
- Use when: Need full control, want performance + errors + sessions

**Rollbar**:
- Best for: Simple error tracking, fast setup
- Strengths: Clean UI, good grouping, deploy tracking
- Weaknesses: No performance monitoring, limited integrations
- Use when: Just need error tracking, budget constrained

**Bugsnag**:
- Best for: Mobile apps (iOS/Android)
- Strengths: Excellent mobile SDKs, stability monitoring
- Weaknesses: Higher pricing, fewer integrations
- Use when: Mobile-first application

**Airbrake**:
- Best for: Ruby/Rails applications
- Strengths: Ruby-native, good Rails integration
- Weaknesses: Limited language support, dated UI
- Use when: Ruby shop, simple requirements

**New Relic / Datadog**:
- Best for: Full observability platform
- Strengths: Unified metrics + logs + traces + errors
- Weaknesses: High cost, complex setup
- Use when: Need complete observability, enterprise budget

### Migration Considerations

Moving between error tracking tools:

```python
# Dual-write pattern for migration
import sentry_sdk
import rollbar

def capture_exception(exc):
    # Old system (during migration)
    rollbar.report_exc_info()

    # New system
    sentry_sdk.capture_exception(exc)

# Gradually increase traffic to new system
import random
def should_send_to_new_system():
    return random.random() < 0.5  # 50% traffic
```

**Migration checklist**:
- [ ] Set up new tool in test environment
- [ ] Dual-write to both systems (1 week)
- [ ] Compare error grouping accuracy
- [ ] Migrate alert rules
- [ ] Train team on new UI
- [ ] Update runbooks
- [ ] Increase traffic gradually (10% → 50% → 100%)
- [ ] Decommission old tool

---

## Sentry Deep Dive

### Installation and Setup

#### Self-Hosted Sentry

```bash
# Requirements
# - Docker 20.10+
# - Docker Compose 2.0+
# - 4GB RAM minimum (8GB recommended)
# - 20GB disk space

# Clone and install
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted
./install.sh

# Configuration
cat > sentry/sentry.conf.py <<EOF
from sentry.conf.server import *

# System settings
SENTRY_URL_PREFIX = 'https://sentry.example.com'
ALLOWED_HOSTS = ['sentry.example.com']

# Email
SENTRY_OPTIONS['mail.backend'] = 'smtp'
SENTRY_OPTIONS['mail.host'] = 'smtp.gmail.com'
SENTRY_OPTIONS['mail.port'] = 587
SENTRY_OPTIONS['mail.username'] = 'alerts@example.com'
SENTRY_OPTIONS['mail.password'] = 'app-password'
SENTRY_OPTIONS['mail.use-tls'] = True
SENTRY_OPTIONS['mail.from'] = 'sentry@example.com'

# Auth
SENTRY_FEATURES['auth:register'] = False  # Disable public registration

# File storage (S3)
SENTRY_OPTIONS['filestore.backend'] = 's3'
SENTRY_OPTIONS['filestore.options'] = {
    'access_key': 'AWS_ACCESS_KEY',
    'secret_key': 'AWS_SECRET_KEY',
    'bucket_name': 'sentry-files',
}

# Performance
SENTRY_OPTIONS['system.event-retention-days'] = 90
EOF

# Start services
docker-compose up -d

# Create first user
docker-compose run --rm web createuser \
  --email admin@example.com \
  --password changeme \
  --superuser
```

**Services overview**:
```yaml
services:
  web:        # Web UI (port 9000)
  worker:     # Background task processor
  cron:       # Scheduled jobs

  # Data stores
  postgres:   # Main database
  redis:      # Cache and queues
  clickhouse: # Events storage (columnar)

  # Optional
  relay:      # Data ingestion proxy
  snuba:      # Query service for events
  symbolicator: # Source map processing
```

#### SaaS Sentry Setup

```bash
# 1. Create organization and project at sentry.io

# 2. Get DSN (Data Source Name)
# Format: https://<key>@<org>.ingest.sentry.io/<project-id>

# 3. Install SDK
pip install sentry-sdk

# 4. Initialize
import sentry_sdk

sentry_sdk.init(
    dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    environment="production",
    release="myapp@1.0.0",
    traces_sample_rate=0.1,
)
```

### Sentry Configuration Deep Dive

#### Organization Settings

```python
# Organization-level settings
{
    "name": "ACME Corp",
    "slug": "acme",

    # Membership
    "defaultRole": "member",  # New member role
    "requireEmailVerification": True,
    "require2FA": True,  # Enforce 2FA for all members

    # Integrations
    "integrations": {
        "github": {
            "organization": "acme-corp",
            "repositories": ["backend", "frontend"]
        },
        "slack": {
            "workspace": "acme-workspace"
        },
        "pagerduty": {
            "services": ["backend-service", "frontend-service"]
        }
    },

    # Data scrubbing (org-wide)
    "dataScrubbing": True,
    "dataScrubber": {
        "enabled": True,
        "scrubDefaults": True,  # Credit cards, SSN, passwords
        "sensitiveFields": ["api_key", "token", "secret"]
    },

    # Quota and rate limits
    "quotas": {
        "maxEventsPerMinute": 1000,
        "maxTransactionsPerMinute": 500
    }
}
```

#### Project Settings

```python
# Project-level settings
{
    "name": "Backend API",
    "platform": "python-flask",
    "dsn": "https://key@o0.ingest.sentry.io/123",

    # Environments
    "environments": ["production", "staging", "development"],

    # Alerts
    "alerts": [
        {
            "name": "New Error in Production",
            "conditions": ["first_seen_event"],
            "filters": [{"environment": "production"}],
            "actions": ["slack_notification", "pagerduty_alert"]
        }
    ],

    # Issue grouping
    "groupingConfig": "newstyle:2023-01-11",
    "fingerprintingRules": """
    # Custom fingerprinting
    error.type:DatabaseError -> database-error
    error.value:"Connection refused" -> connection-error
    """,

    # Performance monitoring
    "transactionThreshold": {
        "metric": "lcp",  # Largest Contentful Paint
        "threshold": 2.5  # seconds
    },

    # Data retention
    "retentionDays": 90,

    # Source maps
    "sourceMapsEnabled": True,
    "sourceMapsArtifacts": {
        "release": "1.0.0",
        "dist": "prod"
    }
}
```

### Sentry SDK Configuration

#### Python Advanced Configuration

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk import set_tag, set_context, add_breadcrumb

def init_sentry(app):
    """Initialize Sentry with full configuration."""

    # Logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Capture errors as events
    )

    sentry_sdk.init(
        dsn=app.config['SENTRY_DSN'],
        environment=app.config['ENVIRONMENT'],
        release=app.config['RELEASE'],

        # Integrations
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
            logging_integration,
        ],

        # Sampling
        traces_sample_rate=get_traces_sample_rate(),
        profiles_sample_rate=0.1,

        # Request data
        send_default_pii=False,
        request_bodies='never',  # Never capture request bodies

        # Hooks
        before_send=before_send_handler,
        before_breadcrumb=before_breadcrumb_handler,

        # Ignoring
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
            BrokenPipeError,
            ConnectionResetError,
            'UserWarning',
        ],

        # Performance
        _experiments={
            "profiles_sample_rate": 0.1,
        },

        # Advanced
        max_breadcrumbs=50,
        attach_stacktrace=True,
        shutdown_timeout=2,
    )

    # Global tags
    set_tag("service", "backend-api")
    set_tag("datacenter", app.config['DATACENTER'])

def get_traces_sample_rate():
    """Dynamic sampling based on environment."""
    env = os.getenv('ENVIRONMENT')
    if env == 'production':
        return 0.05  # 5% in production
    elif env == 'staging':
        return 0.5   # 50% in staging
    else:
        return 1.0   # 100% in development

def before_send_handler(event, hint):
    """Scrub sensitive data before sending."""

    # Remove cookies
    if 'request' in event:
        if 'cookies' in event['request']:
            event['request']['cookies'] = {}

        # Remove sensitive headers
        if 'headers' in event['request']:
            sensitive_headers = ['Authorization', 'Cookie', 'X-API-Key']
            for header in sensitive_headers:
                event['request']['headers'].pop(header, None)

        # Scrub sensitive query params
        if 'query_string' in event['request']:
            parsed = parse_qs(event['request']['query_string'])
            for key in ['token', 'api_key', 'password']:
                if key in parsed:
                    parsed[key] = ['[Filtered]']
            event['request']['query_string'] = urlencode(parsed, doseq=True)

    # Remove exception context with sensitive data
    if 'exception' in event:
        for exception in event['exception'].get('values', []):
            if 'stacktrace' in exception:
                for frame in exception['stacktrace'].get('frames', []):
                    # Remove local variables (might contain sensitive data)
                    if 'vars' in frame:
                        frame['vars'] = {}

    # Sample based on issue type
    if 'exception' in event:
        exc_type = event['exception']['values'][0]['type']

        # Sample common exceptions more aggressively
        if exc_type in ['ConnectionError', 'TimeoutError']:
            if random.random() > 0.1:  # Keep only 10%
                return None

    return event

def before_breadcrumb_handler(crumb, hint):
    """Filter or modify breadcrumbs."""

    # Don't log SQL queries with sensitive data
    if crumb.get('category') == 'query':
        if 'password' in crumb.get('message', '').lower():
            return None

    # Limit console breadcrumbs
    if crumb.get('category') == 'console':
        if crumb.get('level') == 'debug':
            return None

    return crumb

# Request handler to add context
@app.before_request
def before_request():
    """Add request context to Sentry."""

    # User info
    if current_user.is_authenticated:
        sentry_sdk.set_user({
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "subscription": current_user.subscription_tier,
        })

    # Request context
    set_context("request_info", {
        "url": request.url,
        "method": request.method,
        "endpoint": request.endpoint,
        "referrer": request.referrer,
        "user_agent": request.user_agent.string,
    })

    # Feature flags
    feature_flags = get_user_feature_flags(current_user)
    for flag, enabled in feature_flags.items():
        set_tag(f"feature.{flag}", enabled)

    # Breadcrumb for request start
    add_breadcrumb(
        category='request',
        message=f'{request.method} {request.path}',
        level='info'
    )
```

#### JavaScript Advanced Configuration

```javascript
import * as Sentry from "@sentry/browser";
import { BrowserTracing } from "@sentry/tracing";
import { CaptureConsole } from "@sentry/integrations";

Sentry.init({
  dsn: "https://key@o0.ingest.sentry.io/123",
  environment: process.env.NODE_ENV,
  release: process.env.RELEASE_VERSION,

  // Integrations
  integrations: [
    new BrowserTracing({
      // Tracing
      tracingOrigins: ["localhost", "api.example.com", /^\//],
      routingInstrumentation: Sentry.reactRouterV6Instrumentation(
        React.useEffect,
        useLocation,
        useNavigationType,
        createRoutesFromChildren,
        matchRoutes
      ),
    }),

    // Capture console errors
    new CaptureConsole({
      levels: ["error", "assert"]
    }),

    // Session replay
    new Sentry.Replay({
      maskAllText: true,
      blockAllMedia: true,
      maskAllInputs: true,
    }),
  ],

  // Sampling
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Hooks
  beforeSend(event, hint) {
    // Filter out browser extension errors
    if (event.exception) {
      const errorMessage = event.exception.values[0].value;
      if (errorMessage && errorMessage.includes('chrome-extension://')) {
        return null;
      }
    }

    // Scrub sensitive data from URLs
    if (event.request && event.request.url) {
      event.request.url = event.request.url.replace(
        /token=[^&]+/g,
        'token=[Filtered]'
      );
    }

    return event;
  },

  beforeBreadcrumb(breadcrumb, hint) {
    // Filter console breadcrumbs
    if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
      return null;
    }

    // Scrub sensitive data from fetch breadcrumbs
    if (breadcrumb.category === 'fetch') {
      if (breadcrumb.data && breadcrumb.data.url) {
        breadcrumb.data.url = breadcrumb.data.url.replace(
          /api_key=[^&]+/g,
          'api_key=[Filtered]'
        );
      }
    }

    return breadcrumb;
  },

  // Ignoring
  ignoreErrors: [
    // Browser extensions
    'top.GLOBALS',
    'Can\'t find variable: ZiteReader',
    'jigsaw is not defined',

    // Network errors (handled separately)
    'NetworkError',
    'Network request failed',

    // Random plugins/extensions
    'atomicFindClose',
    'conduitPage',
  ],

  denyUrls: [
    // Chrome extensions
    /extensions\//i,
    /^chrome:\/\//i,
    /^chrome-extension:\/\//i,

    // Firefox extensions
    /^moz-extension:\/\//i,
  ],

  // Advanced
  maxBreadcrumbs: 100,
  attachStacktrace: true,
});

// Set user context
export function identifyUser(user) {
  Sentry.setUser({
    id: user.id,
    email: user.email,
    username: user.username,
    subscription: user.subscription,
  });
}

// Clear user context
export function clearUser() {
  Sentry.setUser(null);
}

// Add custom context
export function setAppContext(context) {
  Sentry.setContext("app", context);
}

// Manual error capture with context
export function captureError(error, context = {}) {
  Sentry.withScope((scope) => {
    // Add custom tags
    Object.entries(context.tags || {}).forEach(([key, value]) => {
      scope.setTag(key, value);
    });

    // Add custom context
    Object.entries(context.contexts || {}).forEach(([key, value]) => {
      scope.setContext(key, value);
    });

    // Set level
    if (context.level) {
      scope.setLevel(context.level);
    }

    // Capture
    Sentry.captureException(error);
  });
}
```

---

## Alternative Tools

### Rollbar Configuration

```python
import rollbar
from flask import Flask, request

app = Flask(__name__)

rollbar.init(
    access_token='POST_SERVER_ITEM_ACCESS_TOKEN',
    environment='production',

    # Code version
    code_version='v1.2.3',

    # Root directory for stack traces
    root='/app',

    # Branch
    branch='main',

    # Enabled environments
    enabled_environments=['production', 'staging'],

    # Custom payload
    payload_handler=custom_payload_handler,
)

def custom_payload_handler(payload):
    """Add custom data to every error."""
    payload['data']['custom'] = {
        'datacenter': 'us-east-1',
        'cluster': 'prod-1',
    }
    return payload

# Flask integration
@app.before_request
def before_request():
    rollbar.report_message(
        f'Request: {request.method} {request.path}',
        'info'
    )

@app.errorhandler(Exception)
def handle_exception(e):
    rollbar.report_exc_info()
    return "Internal Server Error", 500

# Manual capture
try:
    risky_operation()
except Exception as e:
    rollbar.report_exc_info(
        extra_data={
            'user_id': user.id,
            'order_id': order.id,
        }
    )
    raise
```

### Bugsnag Configuration

```javascript
// Node.js with Bugsnag
const Bugsnag = require('@bugsnag/js');
const BugsnagPluginExpress = require('@bugsnag/plugin-express');

Bugsnag.start({
  apiKey: 'YOUR_API_KEY',
  appVersion: '1.2.3',
  releaseStage: process.env.NODE_ENV,

  // Notify release stages
  enabledReleaseStages: ['production', 'staging'],

  // Breadcrumbs
  maxBreadcrumbs: 50,
  enabledBreadcrumbTypes: ['error', 'log', 'navigation', 'request', 'state'],

  // Callbacks
  onError: function(event) {
    // Add metadata
    event.addMetadata('account', {
      id: user.id,
      plan: user.plan,
    });

    // Modify severity
    if (event.errors[0].errorClass === 'ValidationError') {
      event.severity = 'warning';
    }

    // Filter events
    if (event.request.url.includes('/health')) {
      return false;  // Don't send
    }
  },

  plugins: [BugsnagPluginExpress],
});

// Express middleware
const express = require('express');
const app = express();

const bugsnagMiddleware = Bugsnag.getPlugin('express');
app.use(bugsnagMiddleware.requestHandler);

// Routes
app.get('/', (req, res) => {
  res.send('Hello');
});

// Error handler (must be last)
app.use(bugsnagMiddleware.errorHandler);
```

### Airbrake Configuration

```ruby
# Ruby on Rails with Airbrake
# config/initializers/airbrake.rb

Airbrake.configure do |c|
  c.project_id = ENV['AIRBRAKE_PROJECT_ID']
  c.project_key = ENV['AIRBRAKE_API_KEY']

  # Environment
  c.environment = Rails.env
  c.ignore_environments = %w[development test]

  # Root directory
  c.root_directory = Rails.root

  # Filtering
  c.blocklist_keys = [
    /password/i,
    /authorization/i,
    /api_key/i,
    /access_token/i,
  ]

  # Performance monitoring
  c.performance_stats = true
  c.performance_stats_flush_period = 15

  # Query stats
  c.query_stats = true

  # Callbacks
  c.add_filter do |notice|
    # Add custom parameters
    notice[:params][:server_name] = Socket.gethostname
    notice[:params][:rails_env] = Rails.env

    # Ignore certain errors
    if notice[:errors].any? { |error| error[:type] == 'ActiveRecord::RecordNotFound' }
      notice.ignore!
    end
  end
end
```

---

## Error Context Enrichment

### User Context

```python
# Python user context
sentry_sdk.set_user({
    # Identifier
    "id": user.id,
    "email": user.email,
    "username": user.username,

    # Metadata
    "subscription": user.subscription_tier,
    "signup_date": user.created_at.isoformat(),
    "last_login": user.last_login.isoformat(),

    # Segmentation
    "segment": user.segment,  # "free", "premium", "enterprise"
    "cohort": user.cohort,    # "2023-Q4"

    # Technical
    "ip_address": request.remote_addr,
    "user_agent": request.user_agent.string,
})
```

```javascript
// JavaScript user context
Sentry.setUser({
  id: user.id,
  email: user.email,
  username: user.username,

  // Custom fields
  subscription: user.subscription,
  accountAge: daysSinceSignup(user.createdAt),
  features: user.enabledFeatures,
});
```

### Tags for Filtering

```python
# Strategic tagging
sentry_sdk.set_tag("environment", "production")
sentry_sdk.set_tag("release", "v1.2.3")
sentry_sdk.set_tag("server", socket.gethostname())
sentry_sdk.set_tag("datacenter", "us-east-1")
sentry_sdk.set_tag("cluster", "prod-cluster-1")

# Feature flags
sentry_sdk.set_tag("feature.new_checkout", user.has_feature("new_checkout"))
sentry_sdk.set_tag("feature.ai_recommendations", True)

# Business context
sentry_sdk.set_tag("payment_provider", "stripe")
sentry_sdk.set_tag("user_segment", "enterprise")
sentry_sdk.set_tag("ab_test.checkout_flow", "variant_b")

# Technical context
sentry_sdk.set_tag("python_version", sys.version)
sentry_sdk.set_tag("celery_task", "process_order")
```

**Tag best practices**:
- Keep tag values low cardinality (<100 unique values)
- Use tags for filtering, not debugging details
- Consistent naming: `category.subcategory`
- Boolean tags: `"true"/"false"` strings, not booleans

### Breadcrumbs

```python
# Navigation breadcrumb
sentry_sdk.add_breadcrumb(
    category='navigation',
    message='User navigated to checkout',
    level='info'
)

# User action breadcrumb
sentry_sdk.add_breadcrumb(
    category='user',
    message='Clicked "Complete Purchase" button',
    level='info',
    data={
        'button_id': 'complete-purchase',
        'form_valid': True,
    }
)

# HTTP request breadcrumb
sentry_sdk.add_breadcrumb(
    category='http',
    message='POST /api/payment',
    level='info',
    data={
        'url': 'https://api.stripe.com/v1/charges',
        'method': 'POST',
        'status_code': 200,
        'duration_ms': 234,
    }
)

# Database query breadcrumb
sentry_sdk.add_breadcrumb(
    category='query',
    message='SELECT * FROM orders WHERE id = %s',
    level='info',
    data={
        'duration_ms': 12,
        'rows': 1,
    }
)

# State change breadcrumb
sentry_sdk.add_breadcrumb(
    category='state',
    message='Order status changed',
    level='info',
    data={
        'from': 'pending',
        'to': 'processing',
        'order_id': order.id,
    }
)
```

**Breadcrumb best practices**:
- Max 50-100 breadcrumbs (older ones dropped)
- Chronological order (newest last)
- Include timestamps (automatic)
- Add structured data in `data` field

### Custom Context

```python
# Order context
sentry_sdk.set_context("order", {
    "id": order.id,
    "total": float(order.total),
    "items_count": len(order.items),
    "currency": order.currency,
    "status": order.status,
    "created_at": order.created_at.isoformat(),
})

# Payment context
sentry_sdk.set_context("payment", {
    "provider": "stripe",
    "method": "credit_card",
    "last4": payment.card_last4,
    "amount": float(payment.amount),
    "status": payment.status,
})

# Environment context
sentry_sdk.set_context("environment", {
    "python_version": sys.version,
    "django_version": django.VERSION,
    "celery_version": celery.__version__,
    "database": "PostgreSQL 14.2",
    "cache": "Redis 6.2",
})

# Device context (mobile)
sentry_sdk.set_context("device", {
    "model": "iPhone 13 Pro",
    "os": "iOS 16.2",
    "screen_resolution": "1170x2532",
    "memory": "6GB",
    "battery_level": 0.45,
})
```

---

## Error Grouping and Fingerprinting

### Default Grouping Algorithm

Sentry groups errors by:

1. **Exception type**: `ValueError`, `TypeError`, etc.
2. **Exception message**: Similar messages grouped
3. **Stack trace**: Top frames similarity
4. **Module context**: Source file and function

```python
# These errors are grouped together:
raise ValueError("Invalid user ID")           # User 123
raise ValueError("Invalid user ID")           # User 456
raise ValueError("Invalid user ID")           # User 789

# Different groups:
raise ValueError("Invalid user ID")           # Different exception message
raise TypeError("Invalid user ID")            # Different exception type
```

### Custom Fingerprinting

#### Rule-Based Fingerprinting

```python
# Sentry fingerprinting rules (in Project Settings → Issue Grouping)
"""
# Group all database errors together
error.type:DatabaseError -> database-error

# Group by error message pattern
error.value:"Connection timeout*" -> connection-timeout

# Group by stack trace pattern
stack.function:process_payment -> payment-processing-error

# Parameterized grouping
error.value:"User * not found" -> user-not-found
"""
```

#### Programmatic Fingerprinting

```python
from sentry_sdk import configure_scope

def custom_fingerprint_handler(event, hint):
    """Dynamically set fingerprint based on error properties."""

    # Get exception info
    if 'exception' in event:
        exc_type = event['exception']['values'][0]['type']
        exc_value = event['exception']['values'][0]['value']

        # Database errors: Group by table name
        if exc_type == 'DatabaseError':
            table_match = re.search(r'table "(.*?)"', exc_value)
            if table_match:
                table = table_match.group(1)
                return ['database-error', table]

        # API errors: Group by endpoint
        if exc_type == 'APIError':
            endpoint = extract_endpoint(event)
            status_code = extract_status_code(event)
            return ['api-error', endpoint, str(status_code)]

        # Timeout errors: Group by operation
        if 'timeout' in exc_value.lower():
            operation = extract_operation(event)
            return ['timeout', operation]

    # Default grouping
    return ['{{ default }}']

# Apply in before_send
def before_send(event, hint):
    fingerprint = custom_fingerprint_handler(event, hint)
    event['fingerprint'] = fingerprint
    return event

sentry_sdk.init(
    dsn="...",
    before_send=before_send
)
```

```javascript
// JavaScript fingerprinting
Sentry.init({
  dsn: "...",
  beforeSend(event, hint) {
    // Group React errors by component
    if (hint.originalException && hint.originalException.componentStack) {
      const component = extractComponentName(hint.originalException.componentStack);
      event.fingerprint = ['react-error', component];
    }

    // Group network errors by URL
    if (event.exception && event.exception.values) {
      const error = event.exception.values[0];
      if (error.type === 'NetworkError') {
        const url = extractURL(event);
        event.fingerprint = ['network-error', url];
      }
    }

    return event;
  }
});
```

### Advanced Fingerprinting Strategies

#### Strategy 1: Parameterize Dynamic Data

```python
# Bad: Each order ID creates separate issue
raise ValueError(f"Order {order_id} not found")
# Result: 1000 orders = 1000 separate issues

# Good: Static message, dynamic data in context
sentry_sdk.set_context("order", {"id": order_id})
raise ValueError("Order not found")
# Result: All grouped under single issue
```

#### Strategy 2: Group by Business Impact

```python
def set_fingerprint_by_impact(error, context):
    """Group by business impact, not technical details."""

    # Critical: Payment failures
    if context.get('operation') == 'payment':
        return ['critical', 'payment-failure']

    # High: User-facing API errors
    if context.get('api_type') == 'public':
        return ['high', 'public-api-error']

    # Medium: Background job failures
    if context.get('job_type') == 'background':
        return ['medium', 'background-job-error']

    # Low: Non-critical operations
    return ['low', 'non-critical-error']
```

#### Strategy 3: Group by Root Cause

```python
def set_fingerprint_by_root_cause(event):
    """Analyze stack trace to identify root cause."""

    if 'exception' in event:
        frames = event['exception']['values'][0]['stacktrace']['frames']

        # Find first frame in our codebase (skip framework frames)
        for frame in reversed(frames):
            if '/app/' in frame.get('filename', ''):
                module = frame['module']
                function = frame['function']
                return ['root-cause', module, function]

    return ['{{ default }}']
```

### Merging and Splitting Issues

```python
# Merge related issues
# Via API
import requests

requests.put(
    'https://sentry.io/api/0/projects/org/project/issues/123/',
    headers={'Authorization': 'Bearer TOKEN'},
    json={
        'merge': {
            'issues': [124, 125, 126]  # Merge these into 123
        }
    }
)

# Split issues with bad grouping
# 1. Identify bad group (multiple root causes)
# 2. Add custom fingerprinting rules
# 3. New errors will create separate issues
# 4. Resolve old mixed issue
```

---

## Stack Trace Analysis

### Reading Stack Traces

```python
# Example error
Traceback (most recent call last):
  File "/app/api/views.py", line 45, in process_order
    payment = charge_customer(order)
  File "/app/payment/stripe.py", line 23, in charge_customer
    result = stripe.Charge.create(amount=total, currency='usd')
  File "/usr/local/lib/python3.9/site-packages/stripe/api.py", line 156, in create
    response = self._request('post', url, params)
  File "/usr/local/lib/python3.9/site-packages/stripe/api.py", line 89, in _request
    raise stripe.error.CardError(message, code)
stripe.error.CardError: Your card was declined
```

**Analysis**:
1. **Error type**: `stripe.error.CardError` - Known Stripe error
2. **Error message**: "Your card was declined" - Business error, not technical
3. **Entry point**: `/app/api/views.py:45` - API endpoint
4. **Intermediate**: `/app/payment/stripe.py:23` - Payment service
5. **External**: `/stripe/api.py` - Third-party library

**Insights**:
- **Root cause**: Declined card (user issue, not bug)
- **Frequency**: If high, check fraud detection
- **Resolution**: Surface better error to user, don't alert

### Stack Trace Patterns

#### Pattern 1: Deep Framework Stacks

```python
# 50-line stack trace, mostly framework code
File "/usr/local/lib/python3.9/site-packages/django/..."  # Line 1-45
File "/app/myapp/views.py", line 23, in my_view          # Line 46 (YOUR CODE)
File "/usr/local/lib/python3.9/site-packages/django/..."  # Line 47-50

# Focus on YOUR CODE frame
# Ignore framework frames (unless framework bug)
```

**Sentry frame filtering**:
```python
# Mark frames as "in-app"
sentry_sdk.init(
    dsn="...",
    in_app_include=["myapp"],         # Include these modules
    in_app_exclude=["django", "celery"]  # Exclude frameworks
)
```

#### Pattern 2: Async/Await Stacks

```python
# Async error stack traces
Traceback (most recent call last):
  File "/app/api/views.py", line 34, in async_handler
    result = await fetch_data()
  File "/app/api/client.py", line 12, in fetch_data
    response = await aiohttp.get(url)
  File "/usr/local/lib/python3.9/site-packages/aiohttp/...", line 456
    raise ClientError("Connection timeout")
aiohttp.ClientError: Connection timeout

# Analysis: Focus on await chain
# - async_handler (entry)
# - fetch_data (your code)
# - aiohttp.get (library)
```

#### Pattern 3: Recursive Errors

```python
# Stack trace with recursion
File "/app/utils.py", line 45, in process_tree
    process_tree(node.left)
File "/app/utils.py", line 45, in process_tree  # Same line!
    process_tree(node.left)
File "/app/utils.py", line 45, in process_tree
    process_tree(node.left)
... [995 more lines] ...
RecursionError: maximum recursion depth exceeded

# Analysis: Look for repeated frames
# Fix: Add base case or increase recursion limit
```

### Source Code Context

```python
# Sentry shows source code around error
# views.py, line 45

43:     order = Order.objects.get(id=order_id)
44:     if order.total > 0:
45:  >>>     payment = charge_customer(order)  # ERROR HERE
46:         order.status = 'paid'
47:         order.save()
```

**Context improvements**:
- Upload source code to Sentry (for private repos)
- Use source maps (JavaScript/TypeScript)
- Include commit hash in release

### Local Variables

```python
# Sentry can capture local variables at error time
def charge_customer(order):
    # Local variables at time of error:
    # order = <Order: 123>
    # total = 99.99
    # customer_id = "cus_abc123"
    # stripe_token = None  ← Problem!

    result = stripe.Charge.create(
        amount=int(total * 100),
        currency='usd',
        customer=customer_id,
        source=stripe_token  # Error: source is None
    )
```

**Configuration**:
```python
# Enable local variables capture (use cautiously)
sentry_sdk.init(
    dsn="...",
    attach_stacktrace=True,
    with_locals=True,  # Capture local variables
)

# Or disable for privacy
sentry_sdk.init(
    dsn="...",
    send_default_pii=False,
    with_locals=False,
)
```

---

## Source Map Support

### Why Source Maps Matter

```javascript
// Original source (app.js)
function validateUserInput(email, password) {
    if (!email.includes('@')) {
        throw new Error('Invalid email');
    }
    return true;
}

// Minified bundle (app.min.js)
function a(b,c){if(!b.includes('@'))throw new Error('Invalid email');return!0}

// Stack trace WITHOUT source maps:
Error: Invalid email
    at a (app.min.js:1:234)  ← Useless!

// Stack trace WITH source maps:
Error: Invalid email
    at validateUserInput (app.js:3:15)  ← Useful!
```

### Generating Source Maps

#### Webpack Configuration

```javascript
// webpack.config.js
module.exports = {
    mode: 'production',

    // Source map type
    devtool: 'hidden-source-map',  // Don't expose to public

    output: {
        filename: '[name].[contenthash].js',
        sourceMapFilename: '[name].[contenthash].js.map',
        path: path.resolve(__dirname, 'dist'),
    },

    plugins: [
        // Upload source maps to Sentry
        new SentryWebpackPlugin({
            authToken: process.env.SENTRY_AUTH_TOKEN,
            org: 'my-org',
            project: 'my-project',
            include: './dist',
            ignore: ['node_modules', 'webpack.config.js'],

            // Release version
            release: process.env.RELEASE_VERSION,

            // Optionally delete source maps after upload
            // (so they're not served publicly)
            cleanArtifacts: true,
        }),
    ],
};
```

**Source map types**:
- `source-map`: Full source maps, separate files
- `hidden-source-map`: Full source maps, not referenced in bundle
- `nosources-source-map`: Source maps without original source (line numbers only)
- `cheap-source-map`: Faster build, less accurate

#### Next.js Configuration

```javascript
// next.config.js
const { withSentryConfig } = require('@sentry/nextjs');

module.exports = withSentryConfig(
    {
        // Next.js config
        productionBrowserSourceMaps: true,  // Enable source maps
    },
    {
        // Sentry config
        silent: true,
        org: 'my-org',
        project: 'my-project',
        authToken: process.env.SENTRY_AUTH_TOKEN,

        // Upload options
        widenClientFileUpload: true,
        hideSourceMaps: true,  // Delete after upload

        // Release
        release: process.env.NEXT_PUBLIC_RELEASE,
    }
);
```

#### TypeScript Configuration

```json
// tsconfig.json
{
    "compilerOptions": {
        "sourceMap": true,
        "declarationMap": true,
        "inlineSourceMap": false,
        "inlineSources": false
    }
}
```

### Uploading Source Maps

#### Manual Upload with sentry-cli

```bash
# Install sentry-cli
npm install -g @sentry/cli

# Configure
export SENTRY_AUTH_TOKEN=your-token
export SENTRY_ORG=my-org
export SENTRY_PROJECT=my-project

# Create release
VERSION=$(git describe --tags --always)
sentry-cli releases new "$VERSION"

# Upload source maps
sentry-cli releases files "$VERSION" upload-sourcemaps ./dist \
    --url-prefix '~/static/js' \
    --validate \
    --strip-prefix dist/

# Finalize release
sentry-cli releases finalize "$VERSION"

# List uploaded files
sentry-cli releases files "$VERSION" list
```

#### CI/CD Upload

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for commits

      - name: Build
        run: |
          npm install
          npm run build

      - name: Create Sentry release
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: my-org
          SENTRY_PROJECT: my-project
        run: |
          VERSION=$(git describe --tags --always)

          # Create release
          sentry-cli releases new "$VERSION"

          # Associate commits (for regression detection)
          sentry-cli releases set-commits "$VERSION" --auto

          # Upload source maps
          sentry-cli releases files "$VERSION" upload-sourcemaps ./dist \
            --url-prefix '~/static/js'

          # Finalize
          sentry-cli releases finalize "$VERSION"

      - name: Deploy notification
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
        run: |
          VERSION=$(git describe --tags --always)
          sentry-cli releases deploys "$VERSION" new -e production
```

### Source Map Security

```javascript
// Option 1: Hidden source maps (not linked in bundle)
// webpack.config.js
module.exports = {
    devtool: 'hidden-source-map',  // No reference in bundle
};

// Bundle output:
// ❌ No: //# sourceMappingURL=app.js.map

// Option 2: Restricted access
// nginx.conf
location ~ \.map$ {
    # Only allow from trusted IPs
    allow 192.168.1.0/24;  # Internal network
    deny all;

    # Or require authentication
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}

// Option 3: Delete after upload
// webpack.config.js
new SentryWebpackPlugin({
    // ...
    cleanArtifacts: true,  // Delete source maps after upload
    filesToDeleteAfterUpload: ['**/*.map'],
});
```

### Debugging Source Map Issues

```bash
# Verify source map uploaded
sentry-cli releases files <version> list

# Expected output:
#  ~/static/js/main.abc123.js
#  ~/static/js/main.abc123.js.map
#  ~/static/js/vendor.def456.js
#  ~/static/js/vendor.def456.js.map

# Test source map resolution
curl -X POST https://sentry.io/api/0/projects/org/project/events/ \
  -H 'Authorization: Bearer TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "exception": {
      "values": [{
        "type": "Error",
        "value": "Test error",
        "stacktrace": {
          "frames": [{
            "filename": "~/static/js/main.abc123.js",
            "lineno": 1,
            "colno": 234
          }]
        }
      }]
    },
    "release": "1.0.0"
  }'

# Check Sentry UI:
# - Stack trace should show original source file/line
# - Source code context should be visible
```

**Common issues**:
1. **Mismatch between release and source map**: Ensure same version
2. **Wrong URL prefix**: Match production URL structure
3. **Minified code changes**: Source map out of sync
4. **Missing source map**: Upload failed or deleted

---

## Release Tracking

### Release Lifecycle

```
Create Release → Associate Commits → Upload Artifacts → Finalize → Deploy → Monitor
```

### Creating Releases

```bash
# Create release
sentry-cli releases new "myapp@1.2.3"

# Alternative: Use git commit hash
VERSION=$(git rev-parse --short HEAD)
sentry-cli releases new "$VERSION"

# Or semantic version + commit
VERSION="v1.2.3+${GITHUB_SHA:0:7}"
sentry-cli releases new "$VERSION"
```

### Associating Commits

```bash
# Auto-detect commits (requires repo integration)
sentry-cli releases set-commits "myapp@1.2.3" --auto

# Manual commit range
sentry-cli releases set-commits "myapp@1.2.3" \
    --commit "my-org/my-repo@abc123..def456"

# Single commit
sentry-cli releases set-commits "myapp@1.2.3" \
    --commit "my-org/my-repo@abc123"
```

**Why associate commits**:
- Identify who authored code that caused error
- Link to commit in GitHub/GitLab
- Detect regressions (fixed error reappears)
- Track suspect commits for new issues

### Release Finalization

```bash
# Finalize release (locks commits/artifacts)
sentry-cli releases finalize "myapp@1.2.3"

# After finalization:
# - Cannot add more commits
# - Cannot upload more artifacts
# - Release is "published" and active
```

### Deploy Notifications

```bash
# Notify Sentry of deployment
sentry-cli releases deploys "myapp@1.2.3" new \
    --env production \
    --name "Production Deploy" \
    --url "https://github.com/org/repo/actions/runs/123"

# Multiple environments
sentry-cli releases deploys "myapp@1.2.3" new --env staging
sentry-cli releases deploys "myapp@1.2.3" new --env production
```

**Benefits**:
- Track errors per environment
- Measure error rate change after deploy
- Alert on deploy-related issues
- Link errors to specific deployments

### Release Configuration in Code

```python
# Python: Set release in SDK
import sentry_sdk

sentry_sdk.init(
    dsn="...",
    release="myapp@1.2.3",  # Match release created in Sentry
    environment="production",
)
```

```javascript
// JavaScript: Set release
Sentry.init({
    dsn: "...",
    release: "myapp@1.2.3",
    environment: "production",
});
```

**Dynamic release version**:
```python
# From environment variable
import os
sentry_sdk.init(
    dsn="...",
    release=os.getenv("RELEASE_VERSION", "dev"),
)
```

```javascript
// From webpack build
Sentry.init({
    dsn: "...",
    release: process.env.RELEASE_VERSION,
});
```

### Regression Detection

When error reappears after resolution:

```python
# 1. Create release v1.0.0
sentry-cli releases new "v1.0.0"

# 2. Deploy to production
# 3. Issue ABC-123 occurs (error X)
# 4. Fix and deploy v1.0.1

# 5. Mark issue resolved in v1.0.1
# (via Sentry UI or API)
PUT /api/0/issues/ABC-123/
{
    "status": "resolved",
    "statusDetails": {
        "inRelease": "v1.0.1"
    }
}

# 6. Deploy v1.0.2
# 7. Error X occurs again → Sentry automatically:
#    - Reopens issue ABC-123
#    - Labels as "REGRESSION"
#    - Alerts with high priority
#    - Links to commit that may have broken it
```

### Release Health

```python
# Track release health (crash-free rate)
import sentry_sdk

# Start session on app launch
sentry_sdk.start_session()

# End session on app exit
sentry_sdk.end_session()

# Session automatically ends on crash
```

**Metrics tracked**:
- **Crash-free sessions**: % of sessions without crashes
- **Crash-free users**: % of users without crashes
- **Session duration**: Average session length
- **Adoption**: % of users on each release

**View in Sentry**:
```
Releases → Select release → Health tab
- Crash-free sessions: 99.8%
- Crash-free users: 99.9%
- Session duration: 5m 32s
- Adoption: 87% of users
```

---

## Alert Strategies

### Alert Types

#### 1. New Issue Alert

```yaml
name: "New Error in Production"
conditions:
  - first_seen_event
filters:
  - environment: production
  - level: [error, fatal]
actions:
  - slack_notification:
      channel: "#alerts"
      message: |
        New error in production:
        {issue.title}
        {issue.culprit}
        {issue.url}
```

**When to use**:
- Production environments
- Critical services
- Low error rate applications

**Avoid when**:
- High volume of unique errors
- Development/staging environments

#### 2. Frequency Alert

```yaml
name: "High Error Frequency"
conditions:
  - event_frequency:
      value: 100
      interval: 1h
      comparison_type: count
filters:
  - environment: production
actions:
  - pagerduty_alert:
      service_key: "backend-service"
  - slack_notification:
      channel: "#incidents"
```

**Tuning frequency thresholds**:
```python
# Low traffic service (< 1000 req/day)
threshold = 10 errors/hour

# Medium traffic (1000-10000 req/day)
threshold = 50 errors/hour

# High traffic (> 10000 req/day)
threshold = 100 errors/hour

# Or percentage-based
threshold = error_rate > 1%  # 1% of total requests
```

#### 3. User Impact Alert

```yaml
name: "High User Impact"
conditions:
  - event_unique_user_frequency:
      value: 50
      interval: 1h
filters:
  - environment: production
actions:
  - email_notification:
      target_type: team
      target_identifier: "engineering"
```

**Why user count matters**:
- 100 errors from 1 user → Lower priority (specific use case)
- 100 errors from 100 users → Higher priority (widespread issue)

#### 4. Regression Alert

```yaml
name: "Regression Detected"
conditions:
  - regression_event
filters:
  - environment: production
actions:
  - slack_notification:
      channel: "#incidents"
      tags: ["regression", "high-priority"]
  - assign:
      target_type: user
      target_identifier: "commit_author"  # Assign to who made the change
```

**Regression detection requires**:
- Release tracking enabled
- Issues marked resolved in specific release
- Commits associated with releases

#### 5. Rate Change Alert

```yaml
name: "Error Rate Spike"
conditions:
  - event_frequency_percent:
      value: 200  # 200% increase
      interval: 1h
      comparison_interval: 1d  # Compared to same hour yesterday
filters:
  - environment: production
actions:
  - pagerduty_alert:
      service_key: "backend-service"
```

**Rate change detection**:
- Compares current rate to baseline
- Accounts for traffic patterns (time of day, day of week)
- More robust than absolute thresholds

### Alert Routing

```python
# Route alerts based on error properties

# Route 1: Critical errors → PagerDuty
if error.level == 'fatal' or error.tags['severity'] == 'critical':
    send_to_pagerduty(error)

# Route 2: Payment errors → Payment team Slack
if 'payment' in error.culprit:
    send_to_slack(error, channel='#payment-team')

# Route 3: High frequency → Incidents channel
if error.count_1h > 100:
    send_to_slack(error, channel='#incidents')

# Route 4: New errors → General alerts
if error.is_new:
    send_to_slack(error, channel='#alerts')

# Route 5: Regressions → Commit author
if error.is_regression:
    send_email(error, recipient=error.commit_author)
```

### Alert Fatigue Prevention

```yaml
# Strategy 1: Group similar alerts
alert_grouping:
  group_by: [issue_id, environment]
  group_window: 5m  # Group alerts within 5 minutes

# Strategy 2: Rate limiting
rate_limit:
  max_alerts_per_hour: 10
  per: issue  # Per issue, not global

# Strategy 3: Intelligent silencing
silence_rules:
  - if: known_issue
    for: 24h
  - if: external_dependency_down
    for: 1h
  - if: expected_during_deploy
    for: 30m

# Strategy 4: Escalation only if unacknowledged
escalation:
  - wait: 15m
    if: not_acknowledged
    then: escalate_to_secondary
```

### Alert Best Practices

```python
# DO: Alert on actionable issues
if requires_human_intervention(error):
    alert(error)

# DO: Include context in alerts
alert_message = f"""
Error: {error.title}
Environment: {error.environment}
Impact: {error.user_count} users affected
Frequency: {error.count_1h} occurrences in last hour
Runbook: {error.runbook_url}
Dashboard: {error.dashboard_url}
"""

# DO: Different severity for different channels
if error.severity == 'critical':
    send_to_pagerduty(error)  # Page on-call
elif error.severity == 'high':
    send_to_slack(error, channel='#incidents')  # Team notification
else:
    create_ticket(error)  # Background tracking

# DON'T: Alert on expected errors
if error.type in ['ValidationError', 'NotFoundError']:
    log(error)  # Log but don't alert
    return

# DON'T: Alert on low-impact issues
if error.user_count < 5 and error.count_1h < 10:
    return  # Ignore noise

# DON'T: Send duplicate alerts
if recently_alerted(error, within=timedelta(hours=1)):
    return
```

---

## Error Prioritization

### Prioritization Framework

```python
def calculate_priority_score(issue):
    """Calculate priority score (0-100)."""
    score = 0

    # Frequency (0-30 points)
    if issue.count_24h > 1000:
        score += 30
    elif issue.count_24h > 100:
        score += 20
    elif issue.count_24h > 10:
        score += 10

    # User impact (0-30 points)
    if issue.unique_users_24h > 100:
        score += 30
    elif issue.unique_users_24h > 10:
        score += 20
    elif issue.unique_users_24h > 1:
        score += 10

    # Environment (0-15 points)
    if issue.environment == 'production':
        score += 15
    elif issue.environment == 'staging':
        score += 5

    # Error level (0-10 points)
    if issue.level == 'fatal':
        score += 10
    elif issue.level == 'error':
        score += 7
    elif issue.level == 'warning':
        score += 3

    # Regression (0-10 points)
    if issue.status == 'regression':
        score += 10

    # Newness (0-5 points)
    if issue.first_seen_within_hours(24):
        score += 5

    return score

def get_priority_level(score):
    """Convert score to priority level."""
    if score >= 70:
        return 'P0'  # Critical - Immediate action
    elif score >= 50:
        return 'P1'  # High - Same day
    elif score >= 30:
        return 'P2'  # Medium - This week
    else:
        return 'P3'  # Low - Backlog
```

### P0: Critical Issues

**Criteria**:
- Service down or completely unavailable
- Data loss or corruption
- Security breach
- Payment processing failures
- > 100 users affected in last hour

**Response**:
- Page on-call engineer immediately
- War room / incident response
- Halt deployments
- Executive notification if > 1 hour
- Post-mortem required

**Example**:
```python
{
    "title": "Database connection pool exhausted",
    "frequency": 500 errors/hour,
    "user_impact": 350 users affected,
    "environment": "production",
    "level": "fatal",
    "priority": "P0",
    "sla": "< 15 minutes"
}
```

### P1: High Priority Issues

**Criteria**:
- Significant feature degraded
- 10-100 users affected
- Payment processing slow (not failing)
- Frequent errors (> 100/hour)
- Recent regression

**Response**:
- Notify team in Slack
- Assign to engineer immediately
- Fix within same business day
- Deploy as soon as ready
- Brief post-incident review

**Example**:
```python
{
    "title": "Image upload failing for some users",
    "frequency": 50 errors/hour,
    "user_impact": 30 users affected,
    "environment": "production",
    "level": "error",
    "priority": "P1",
    "sla": "< 4 hours"
}
```

### P2: Medium Priority Issues

**Criteria**:
- Non-critical feature affected
- 1-10 users affected
- Infrequent errors (10-100/day)
- Workaround available
- Staging/development errors

**Response**:
- Create ticket in issue tracker
- Assign to sprint backlog
- Fix within current sprint
- Deploy with next regular release
- No post-mortem needed

**Example**:
```python
{
    "title": "PDF export fails for certain reports",
    "frequency": 5 errors/day,
    "user_impact": 3 users affected,
    "environment": "production",
    "level": "error",
    "priority": "P2",
    "sla": "< 1 week"
}
```

### P3: Low Priority Issues

**Criteria**:
- Edge case or rare scenario
- < 1 user affected per day
- Warning-level issues
- Known limitations
- Nice-to-have improvements

**Response**:
- Add to backlog
- Fix when convenient
- May defer indefinitely
- No SLA

**Example**:
```python
{
    "title": "Deprecation warning in third-party library",
    "frequency": 1 error/week,
    "user_impact": 0 users affected,
    "environment": "production",
    "level": "warning",
    "priority": "P3",
    "sla": "None"
}
```

### Prioritization Dashboard

```python
# Generate prioritization dashboard
def generate_priority_dashboard(issues):
    """Create dashboard showing issue priorities."""

    priorities = {
        'P0': {'issues': [], 'total_users': 0, 'total_events': 0},
        'P1': {'issues': [], 'total_users': 0, 'total_events': 0},
        'P2': {'issues': [], 'total_users': 0, 'total_events': 0},
        'P3': {'issues': [], 'total_users': 0, 'total_events': 0},
    }

    for issue in issues:
        score = calculate_priority_score(issue)
        priority = get_priority_level(score)

        priorities[priority]['issues'].append({
            'id': issue.id,
            'title': issue.title,
            'score': score,
            'users': issue.unique_users_24h,
            'events': issue.count_24h,
            'url': issue.url,
        })
        priorities[priority]['total_users'] += issue.unique_users_24h
        priorities[priority]['total_events'] += issue.count_24h

    # Sort by score within each priority
    for p in priorities.values():
        p['issues'].sort(key=lambda x: x['score'], reverse=True)

    return priorities

# Output
"""
P0 - CRITICAL (3 issues, 450 users, 1,234 events)
  1. [95] Database connection pool exhausted (350 users, 500 events)
  2. [87] Payment API timeout (80 users, 600 events)
  3. [72] Authentication service down (20 users, 134 events)

P1 - HIGH (5 issues, 87 users, 456 events)
  1. [65] Image upload failing (30 users, 200 events)
  ...

P2 - MEDIUM (12 issues, 15 users, 89 events)
  ...

P3 - LOW (34 issues, 2 users, 45 events)
  ...
"""
```

---

## PII and Privacy

### What is PII?

**Personally Identifiable Information** (PII):
- Email addresses
- Phone numbers
- Physical addresses
- Credit card numbers
- Social Security Numbers
- IP addresses (in some jurisdictions)
- Names
- Biometric data
- Health information

### Data Protection Regulations

**GDPR** (EU):
- User consent required for data collection
- Right to be forgotten (data deletion)
- Data minimization
- Breach notification (72 hours)
- Penalties up to €20M or 4% of revenue

**CCPA** (California):
- Right to know what data is collected
- Right to delete data
- Right to opt-out of data sale
- Penalties up to $7,500 per violation

**HIPAA** (US Healthcare):
- Protected Health Information (PHI)
- Strict access controls
- Encryption required
- Audit trails
- Penalties up to $50,000 per violation

### PII Scrubbing Strategies

#### Strategy 1: Default Scrubbing

```python
# Sentry default scrubbing (enabled by default)
sentry_sdk.init(
    dsn="...",
    send_default_pii=False,  # Don't send cookies, headers, etc.

    # Additional scrubbing (enabled by default)
    _experiments={
        "attach_http_data": False,  # No request/response bodies
    }
)
```

**Default scrubbed fields**:
- `password`, `passwd`, `secret`
- `api_key`, `apikey`, `access_token`
- `auth`, `authorization`
- `ssn`, `social_security`
- `credit_card`, `card_number`

#### Strategy 2: Custom Field Scrubbing

```python
def scrub_pii(event, hint):
    """Scrub PII from error events."""

    # Scrub request data
    if 'request' in event:
        # Remove specific headers
        if 'headers' in event['request']:
            event['request']['headers'].pop('Authorization', None)
            event['request']['headers'].pop('Cookie', None)
            event['request']['headers'].pop('X-API-Key', None)

        # Scrub query parameters
        if 'query_string' in event['request']:
            event['request']['query_string'] = scrub_query_string(
                event['request']['query_string']
            )

        # Remove request body
        event['request'].pop('data', None)

    # Scrub user data
    if 'user' in event:
        # Keep ID, but remove email
        if 'email' in event['user']:
            email = event['user']['email']
            # Hash email instead of removing
            event['user']['email'] = hashlib.sha256(email.encode()).hexdigest()

        # Remove IP address (or hash it)
        if 'ip_address' in event:
            event['user'].pop('ip_address')

    # Scrub exception messages
    if 'exception' in event:
        for exc in event['exception'].get('values', []):
            if 'value' in exc:
                exc['value'] = scrub_exception_message(exc['value'])

    # Scrub breadcrumbs
    if 'breadcrumbs' in event:
        for crumb in event['breadcrumbs'].get('values', []):
            if 'message' in crumb:
                crumb['message'] = scrub_text(crumb['message'])

    return event

def scrub_query_string(qs):
    """Scrub sensitive query parameters."""
    parsed = parse_qs(qs)

    sensitive_params = [
        'token', 'api_key', 'password', 'secret',
        'ssn', 'credit_card', 'email'
    ]

    for param in sensitive_params:
        if param in parsed:
            parsed[param] = ['[Filtered]']

    return urlencode(parsed, doseq=True)

def scrub_exception_message(message):
    """Scrub PII from exception messages."""

    # Remove email addresses
    message = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[email]',
        message
    )

    # Remove phone numbers
    message = re.sub(
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        '[phone]',
        message
    )

    # Remove SSN
    message = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[ssn]',
        message
    )

    # Remove credit cards
    message = re.sub(
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        '[credit_card]',
        message
    )

    return message

sentry_sdk.init(
    dsn="...",
    before_send=scrub_pii
)
```

#### Strategy 3: Field Allowlist

```python
# Only allow specific fields, scrub everything else
ALLOWED_FIELDS = {
    'request': ['method', 'url', 'headers.content-type'],
    'user': ['id', 'username'],
    'tags': ['environment', 'release', 'server'],
}

def allowlist_filter(event, hint):
    """Keep only allowed fields."""

    # Filter request fields
    if 'request' in event:
        filtered_request = {}
        if 'method' in event['request']:
            filtered_request['method'] = event['request']['method']
        if 'url' in event['request']:
            # Keep URL path, remove query string
            filtered_request['url'] = event['request']['url'].split('?')[0]
        event['request'] = filtered_request

    # Filter user fields
    if 'user' in event:
        filtered_user = {}
        if 'id' in event['user']:
            filtered_user['id'] = event['user']['id']
        if 'username' in event['user']:
            filtered_user['username'] = event['user']['username']
        event['user'] = filtered_user

    return event

sentry_sdk.init(
    dsn="...",
    before_send=allowlist_filter
)
```

#### Strategy 4: Client-Side Scrubbing

```javascript
// Scrub PII before sending to Sentry
Sentry.init({
    dsn: "...",
    beforeSend(event, hint) {
        // Scrub form values
        if (event.request && event.request.data) {
            const scrubbed = {};
            for (const [key, value] of Object.entries(event.request.data)) {
                if (key.toLowerCase().includes('password') ||
                    key.toLowerCase().includes('credit') ||
                    key.toLowerCase().includes('ssn')) {
                    scrubbed[key] = '[Filtered]';
                } else {
                    scrubbed[key] = value;
                }
            }
            event.request.data = scrubbed;
        }

        return event;
    }
});
```

### Data Retention Policies

```python
# Configure retention in Sentry project settings
{
    "dataScrubber": True,
    "dataScrubberDefaults": True,
    "sensitiveFields": ["password", "api_key", "token"],
    "safeFields": ["username", "user_id"],
    "scrubIPAddresses": True,

    # Retention
    "retentionDays": 90,  # Keep errors for 90 days

    # Automatic deletion
    "deletionPolicy": {
        "enabled": True,
        "days": 90
    }
}
```

### GDPR Compliance Checklist

- [ ] PII scrubbing enabled (default + custom)
- [ ] IP address scrubbing/hashing
- [ ] User consent for error tracking
- [ ] Data retention policy (< 1 year recommended)
- [ ] Right to be forgotten (user data deletion)
- [ ] Data processing agreement with error tracking vendor
- [ ] Breach notification procedure
- [ ] Privacy policy updated with error tracking disclosure
- [ ] Employee training on PII handling
- [ ] Regular audits of collected data

---

## Multi-Language Integration

### Python Integration

```python
# Flask
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="...",
    integrations=[FlaskIntegration()]
)

app = Flask(__name__)

# Django
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="...",
    integrations=[DjangoIntegration()]
)

# FastAPI
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

sentry_sdk.init(dsn="...")

app = FastAPI()
app.add_middleware(SentryAsgiMiddleware)

# Celery
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn="...",
    integrations=[CeleryIntegration()]
)
```

### Node.js Integration

```javascript
// Express
const Sentry = require("@sentry/node");
const express = require("express");

Sentry.init({ dsn: "..." });

const app = express();
app.use(Sentry.Handlers.requestHandler());
app.use(Sentry.Handlers.errorHandler());

// Koa
const Sentry = require("@sentry/node");
const Koa = require("koa");

Sentry.init({ dsn: "..." });

const app = new Koa();
app.on('error', (err) => {
    Sentry.captureException(err);
});

// Next.js
// next.config.js
const { withSentryConfig } = require('@sentry/nextjs');
module.exports = withSentryConfig({...});
```

### Go Integration

```go
package main

import (
    "github.com/getsentry/sentry-go"
    sentryhttp "github.com/getsentry/sentry-go/http"
    "net/http"
)

func main() {
    err := sentry.Init(sentry.ClientOptions{
        Dsn: "...",
        Environment: "production",
        Release: "myapp@1.0.0",
    })
    if err != nil {
        log.Fatalf("sentry.Init: %s", err)
    }
    defer sentry.Flush(2 * time.Second)

    // HTTP handler
    sentryHandler := sentryhttp.New(sentryhttp.Options{})
    http.Handle("/", sentryHandler.Handle(handler))

    http.ListenAndServe(":8080", nil)
}

func handler(w http.ResponseWriter, r *http.Request) {
    // Manual capture
    if err := riskyOperation(); err != nil {
        sentry.CaptureException(err)
    }
}
```

### Java Integration

```java
// Spring Boot
import io.sentry.Sentry;
import io.sentry.spring.boot.EnableSentry;

@SpringBootApplication
@EnableSentry(dsn = "...")
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

// Manual capture
try {
    riskyOperation();
} catch (Exception e) {
    Sentry.captureException(e);
    throw e;
}
```

### Ruby Integration

```ruby
# Rails
# Gemfile
gem 'sentry-ruby'
gem 'sentry-rails'

# config/initializers/sentry.rb
Sentry.init do |config|
  config.dsn = ENV['SENTRY_DSN']
  config.environment = Rails.env
  config.release = ENV['RELEASE_VERSION']
end

# Manual capture
begin
  risky_operation
rescue => e
  Sentry.capture_exception(e)
  raise
end
```

### PHP Integration

```php
<?php
// Laravel
// config/sentry.php
return [
    'dsn' => env('SENTRY_DSN'),
    'environment' => env('APP_ENV'),
    'release' => env('RELEASE_VERSION'),
];

// Manual capture
try {
    riskyOperation();
} catch (Exception $e) {
    app('sentry')->captureException($e);
    throw $e;
}
```

---

## Distributed Systems

### Error Correlation

```python
# Propagate trace ID across services

# Service A (initiator)
import sentry_sdk
import requests

trace_id = str(uuid.uuid4())
sentry_sdk.set_tag("trace_id", trace_id)

response = requests.post(
    "https://service-b/api/process",
    headers={"X-Trace-ID": trace_id},
    json=data
)

# Service B (downstream)
import sentry_sdk

@app.route("/api/process", methods=["POST"])
def process():
    trace_id = request.headers.get("X-Trace-ID")
    if trace_id:
        sentry_sdk.set_tag("trace_id", trace_id)

    # If error occurs here, it will have same trace_id
    result = process_data(request.json)
    return result

# Now search Sentry for trace_id to see all related errors
```

### Distributed Tracing Integration

```python
# Integrate Sentry with OpenTelemetry
import sentry_sdk
from sentry_sdk.integrations.opentelemetry import SentrySpanProcessor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Set up OpenTelemetry
provider = TracerProvider()
provider.add_span_processor(SentrySpanProcessor())
trace.set_tracer_provider(provider)

# Initialize Sentry
sentry_sdk.init(
    dsn="...",
    enable_tracing=True,
    traces_sample_rate=0.1,
)

# Traces and errors now correlated
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    try:
        order = process_order(order_id)
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.total", order.total)
    except Exception as e:
        span.set_status(Status(StatusCode.ERROR))
        span.record_exception(e)
        sentry_sdk.capture_exception(e)  # Correlated with span
        raise
```

### Service Mesh Integration

```yaml
# Istio sidecar propagates trace headers
# Service A sends request with headers:
# - X-Request-ID
# - X-B3-TraceId
# - X-B3-SpanId
# - X-B3-ParentSpanId

# Service B receives and propagates
apiVersion: v1
kind: Service
metadata:
  name: service-b
  annotations:
    # Enable distributed tracing
    sidecar.istio.io/inject: "true"
spec:
  # ...
```

```python
# Application code extracts trace info
import sentry_sdk

@app.before_request
def before_request():
    # Extract trace ID from Istio headers
    trace_id = request.headers.get("X-B3-TraceId")
    span_id = request.headers.get("X-B3-SpanId")

    if trace_id:
        sentry_sdk.set_tag("trace_id", trace_id)
        sentry_sdk.set_tag("span_id", span_id)

    # Set service name
    sentry_sdk.set_tag("service", "service-b")
```

### Cross-Service Error Propagation

```python
# Service A
class ServiceClient:
    def call_service_b(self, data):
        try:
            response = requests.post(
                "https://service-b/api/endpoint",
                json=data,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Service B returned error
            # Extract error ID from response
            error_id = e.response.headers.get("X-Sentry-ID")

            # Capture error in Service A with reference
            sentry_sdk.set_context("downstream_error", {
                "service": "service-b",
                "error_id": error_id,
                "status_code": e.response.status_code,
            })
            sentry_sdk.capture_exception(e)
            raise

# Service B
@app.errorhandler(Exception)
def handle_error(e):
    # Capture error
    event_id = sentry_sdk.capture_exception(e)

    # Return error ID in response header
    response = jsonify({"error": "Internal server error"})
    response.status_code = 500
    response.headers["X-Sentry-ID"] = event_id
    return response
```

---

## Performance and Sampling

### Why Sampling Matters

```python
# High volume application
requests_per_second = 10000
errors_per_second = 100  # 1% error rate

# Without sampling
monthly_events = errors_per_second * 60 * 60 * 24 * 30
# = 259,200,000 events/month
# Cost: ~$50,000/month at Sentry pricing

# With 10% sampling
monthly_events = 25,920,000 events/month
# Cost: ~$5,000/month

# With 1% sampling
monthly_events = 2,592,000 events/month
# Cost: ~$500/month
```

### Sampling Strategies

#### Strategy 1: Uniform Sampling

```python
# Sample X% of all errors uniformly
import random

def before_send(event, hint):
    # Sample 10% of events
    if random.random() > 0.1:
        return None
    return event

sentry_sdk.init(
    dsn="...",
    before_send=before_send
)
```

#### Strategy 2: Priority Sampling

```python
def before_send(event, hint):
    """Sample based on error priority."""

    # Always send critical errors
    if event.get('level') == 'fatal':
        return event

    # Always send errors in production
    if event.get('environment') == 'production':
        return event

    # Always send errors affecting multiple users
    if 'user' in event and is_high_value_user(event['user']):
        return event

    # Sample others
    if event.get('level') == 'error':
        sample_rate = 0.1  # 10%
    else:
        sample_rate = 0.01  # 1%

    if random.random() > sample_rate:
        return None

    return event
```

#### Strategy 3: Rate-Based Sampling

```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_per_second=100):
        self.max_per_second = max_per_second
        self.counts = defaultdict(int)
        self.last_reset = time()

    def should_send(self):
        now = time()
        if now - self.last_reset > 1.0:
            self.counts.clear()
            self.last_reset = now

        self.counts['total'] += 1
        return self.counts['total'] <= self.max_per_second

rate_limiter = RateLimiter(max_per_second=100)

def before_send(event, hint):
    if rate_limiter.should_send():
        return event
    return None
```

#### Strategy 4: Error-Type Sampling

```python
def before_send(event, hint):
    """Sample differently based on error type."""

    if 'exception' in event:
        exc_type = event['exception']['values'][0]['type']

        # Common, low-priority errors: Sample heavily
        if exc_type in ['ConnectionError', 'TimeoutError', 'NotFoundError']:
            sample_rate = 0.01  # 1%

        # Business logic errors: Sample moderately
        elif exc_type in ['ValidationError', 'PermissionError']:
            sample_rate = 0.1  # 10%

        # Unexpected errors: Send all
        else:
            sample_rate = 1.0  # 100%

        if random.random() > sample_rate:
            return None

    return event
```

### Performance Impact

```python
# Measure Sentry overhead
import time

def measure_sentry_overhead():
    # Without error tracking
    start = time.time()
    for _ in range(1000):
        try:
            risky_operation()
        except:
            pass
    baseline = time.time() - start

    # With error tracking
    start = time.time()
    for _ in range(1000):
        try:
            risky_operation()
        except Exception as e:
            sentry_sdk.capture_exception(e)
    with_sentry = time.time() - start

    overhead = (with_sentry - baseline) / baseline * 100
    print(f"Sentry overhead: {overhead:.2f}%")

# Typical results:
# - Synchronous capture: 1-5% overhead
# - Asynchronous capture: < 1% overhead
```

### Async Error Capture

```python
# Async capture (non-blocking)
sentry_sdk.init(
    dsn="...",
    transport=sentry_sdk.transport.HttpTransport,
    shutdown_timeout=2,  # Wait max 2s on shutdown
)

# Error is queued and sent in background thread
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)  # Non-blocking
    # Execution continues immediately
```

```javascript
// JavaScript async capture
Sentry.init({
    dsn: "...",
    transport: Sentry.makeFetchTransport,  // Async transport
});

// Non-blocking
try {
    riskyOperation();
} catch (err) {
    Sentry.captureException(err);  // Returns immediately
}
```

---

## Testing Error Tracking

### Unit Testing Error Capture

```python
# test_error_tracking.py
import sentry_sdk
from sentry_sdk.transport import Transport
import pytest

class MockTransport(Transport):
    """Mock transport to capture events without sending."""
    def __init__(self):
        super().__init__()
        self.events = []

    def capture_event(self, event):
        self.events.append(event)
        return event

@pytest.fixture
def mock_sentry():
    """Set up mock Sentry for testing."""
    transport = MockTransport()
    sentry_sdk.init(
        dsn="https://mock@o0.ingest.sentry.io/0",
        transport=transport
    )
    yield transport
    sentry_sdk.flush()

def test_error_captured(mock_sentry):
    """Test that error is captured."""
    try:
        raise ValueError("Test error")
    except Exception as e:
        sentry_sdk.capture_exception(e)

    assert len(mock_sentry.events) == 1
    event = mock_sentry.events[0]
    assert event['exception']['values'][0]['type'] == 'ValueError'
    assert event['exception']['values'][0]['value'] == 'Test error'

def test_error_context(mock_sentry):
    """Test that context is included."""
    sentry_sdk.set_user({"id": "123", "email": "test@example.com"})
    sentry_sdk.set_tag("environment", "test")

    try:
        raise RuntimeError("Context test")
    except Exception as e:
        sentry_sdk.capture_exception(e)

    event = mock_sentry.events[0]
    assert event['user']['id'] == '123'
    assert event['tags']['environment'] == 'test'

def test_pii_scrubbed(mock_sentry):
    """Test that PII is scrubbed."""
    sentry_sdk.set_user({
        "id": "123",
        "email": "test@example.com",
        "password": "secret123"
    })

    try:
        raise ValueError("PII test")
    except Exception as e:
        sentry_sdk.capture_exception(e)

    event = mock_sentry.events[0]
    assert 'password' not in event['user']
```

### Integration Testing

```python
# test_integration.py
import requests

def test_error_sent_to_sentry():
    """Test error is actually sent to Sentry."""

    # Trigger error in application
    response = requests.post(
        "http://localhost:5000/api/test-error",
        json={"trigger": "error"}
    )

    # Wait for async send
    time.sleep(2)

    # Check Sentry API for event
    sentry_events = get_recent_sentry_events(
        project="test-project",
        since=datetime.now() - timedelta(minutes=5)
    )

    # Verify event was captured
    assert any(
        'test error' in event['title'].lower()
        for event in sentry_events
    )

def get_recent_sentry_events(project, since):
    """Fetch recent events from Sentry API."""
    response = requests.get(
        f"https://sentry.io/api/0/projects/org/{project}/events/",
        headers={"Authorization": f"Bearer {SENTRY_API_TOKEN}"},
        params={"start": since.isoformat()}
    )
    return response.json()
```

### End-to-End Testing

```python
# Send test error and verify in Sentry UI
def test_error_tracking_e2e():
    """End-to-end test of error tracking."""

    # 1. Trigger error
    sentry_sdk.init(dsn="https://...")
    test_id = str(uuid.uuid4())

    try:
        raise ValueError(f"E2E Test Error: {test_id}")
    except Exception as e:
        event_id = sentry_sdk.capture_exception(e)

    # 2. Wait for processing
    time.sleep(5)

    # 3. Verify via API
    event = get_sentry_event(event_id)
    assert event is not None
    assert test_id in event['title']
    assert event['level'] == 'error'

    # 4. Clean up
    resolve_sentry_issue(event['issue_id'])
```

### Load Testing

```python
# Simulate high error volume
import concurrent.futures

def send_test_error(i):
    """Send single test error."""
    try:
        raise ValueError(f"Load test error #{i}")
    except Exception as e:
        sentry_sdk.capture_exception(e)

def load_test_error_tracking(num_errors=1000):
    """Send many errors concurrently."""

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(send_test_error, i)
            for i in range(num_errors)
        ]
        concurrent.futures.wait(futures)

    duration = time.time() - start
    rate = num_errors / duration

    print(f"Sent {num_errors} errors in {duration:.2f}s ({rate:.0f}/s)")

    # Wait for all to be sent
    sentry_sdk.flush(timeout=10)

    # Verify count in Sentry
    time.sleep(10)
    issue_count = get_sentry_issue_count(
        since=datetime.now() - timedelta(minutes=5)
    )

    # With grouping, should be 1 issue (not 1000)
    assert issue_count == 1, f"Expected 1 issue, got {issue_count}"
```

---

## Operational Patterns

### Error Tracking Workflow

```
1. Error occurs in production
   ↓
2. Captured by Sentry SDK
   ↓
3. Sent to Sentry (with context)
   ↓
4. Grouped with similar errors
   ↓
5. Alert triggered (if threshold met)
   ↓
6. Engineer notified
   ↓
7. Investigate using:
   - Stack trace
   - User context
   - Breadcrumbs
   - Recent deployments
   ↓
8. Identify root cause
   ↓
9. Deploy fix
   ↓
10. Mark issue resolved in release
    ↓
11. Monitor for regression
```

### Daily Triage Process

```python
# Daily error triage script
def daily_triage():
    """Review and prioritize errors from last 24 hours."""

    # 1. Get new issues
    new_issues = get_sentry_issues(
        status='unresolved',
        query='is:unresolved firstSeen:>=24h',
        sort='priority'
    )

    print(f"📋 {len(new_issues)} new issues in last 24h\n")

    # 2. Categorize by priority
    critical = [i for i in new_issues if calculate_priority_score(i) >= 70]
    high = [i for i in new_issues if 50 <= calculate_priority_score(i) < 70]
    medium = [i for i in new_issues if 30 <= calculate_priority_score(i) < 50]
    low = [i for i in new_issues if calculate_priority_score(i) < 30]

    # 3. Report
    print("🚨 CRITICAL (immediate action):")
    for issue in critical:
        print(f"  - {issue['title']} ({issue['count']} events, {issue['userCount']} users)")
        # Auto-assign and page
        assign_issue(issue, team='oncall')
        send_page(issue)

    print("\n⚠️  HIGH (today):")
    for issue in high:
        print(f"  - {issue['title']} ({issue['count']} events)")
        # Assign to team
        assign_issue(issue, team='backend')

    print("\n📌 MEDIUM (this week):")
    for issue in medium:
        print(f"  - {issue['title']}")
        # Create ticket
        create_jira_ticket(issue)

    print("\n📝 LOW (backlog):")
    print(f"  {len(low)} low-priority issues")

    # 4. Ignore noise
    for issue in low:
        if issue['count'] < 5:  # Very low frequency
            ignore_issue(issue, reason="Low impact")

# Run daily
if __name__ == "__main__":
    daily_triage()
```

### Weekly Review Process

```python
def weekly_review():
    """Weekly review of error tracking health."""

    print("📊 WEEKLY ERROR TRACKING REVIEW\n")

    # 1. Overall trends
    issues_last_week = get_sentry_issues(query='firstSeen:>=7d')
    issues_prev_week = get_sentry_issues(query='firstSeen:>=14d firstSeen:<7d')

    trend = len(issues_last_week) - len(issues_prev_week)
    trend_pct = trend / len(issues_prev_week) * 100 if issues_prev_week else 0

    print(f"New issues: {len(issues_last_week)} ({'↑' if trend > 0 else '↓'} {abs(trend_pct):.1f}%)")

    # 2. Top issues by volume
    print("\n🔥 TOP ISSUES BY VOLUME:")
    top_by_volume = sorted(issues_last_week, key=lambda x: x['count'], reverse=True)[:5]
    for i, issue in enumerate(top_by_volume, 1):
        print(f"  {i}. {issue['title']} ({issue['count']} events)")

    # 3. Top issues by user impact
    print("\n👥 TOP ISSUES BY USER IMPACT:")
    top_by_users = sorted(issues_last_week, key=lambda x: x['userCount'], reverse=True)[:5]
    for i, issue in enumerate(top_by_users, 1):
        print(f"  {i}. {issue['title']} ({issue['userCount']} users)")

    # 4. Regression analysis
    regressions = get_sentry_issues(query='is:regression firstSeen:>=7d')
    print(f"\n🔄 REGRESSIONS: {len(regressions)}")
    for issue in regressions:
        print(f"  - {issue['title']} (fixed in {issue['resolution']['inRelease']}, broke again)")

    # 5. Team performance
    print("\n👨‍💻 TEAM METRICS:")
    resolved_last_week = get_sentry_issues(query='status:resolved resolvedAt:>=7d')
    print(f"  Issues resolved: {len(resolved_last_week)}")

    avg_time_to_resolve = calculate_avg_resolution_time(resolved_last_week)
    print(f"  Avg time to resolve: {avg_time_to_resolve:.1f} hours")

    # 6. Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if len(regressions) > 5:
        print("  ⚠️  High regression rate - review test coverage")
    if len(top_by_volume) > 0 and top_by_volume[0]['count'] > 1000:
        print("  ⚠️  Very high volume issue - consider sampling")
    if trend_pct > 50:
        print("  ⚠️  Significant increase in new issues - investigate recent changes")

# Run weekly
if __name__ == "__main__":
    weekly_review()
```

### On-Call Runbook

```markdown
# Error Tracking On-Call Runbook

## Alert Received

### 1. Acknowledge
- Acknowledge alert in PagerDuty/Slack
- Open Sentry issue link

### 2. Assess Severity
- **P0** (Service down):
  - Check: Is service completely unavailable?
  - Action: Immediate war room, halt deployments

- **P1** (Degraded):
  - Check: What % of users affected?
  - Action: Investigate immediately, fix within 4h

- **P2** (Minor):
  - Check: Workaround available?
  - Action: Create ticket, fix in sprint

### 3. Investigate
- **Stack trace**: What's the root cause?
- **Breadcrumbs**: What led to the error?
- **User context**: Which users affected?
- **Environment**: Production/staging?
- **Frequency**: How often occurring?
- **Recent changes**: Any related deployments?

### 4. Diagnose
- Check monitoring dashboards
- Review recent deployments
- Check dependencies (databases, APIs)
- Search logs for related errors
- Test in staging if possible

### 5. Remediate
- **Immediate**: Rollback bad deployment
- **Short-term**: Apply hotfix
- **Long-term**: Root cause fix + tests

### 6. Communicate
- Update incident channel
- Notify affected users (if needed)
- Update status page

### 7. Resolve
- Deploy fix
- Mark issue resolved in Sentry
- Monitor for regression

### 8. Post-Mortem (if P0/P1)
- Document timeline
- Identify root cause
- List action items
- Update runbooks
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Events Not Appearing in Sentry

**Symptoms**:
- `sentry_sdk.capture_exception()` called but no events in Sentry

**Diagnosis**:
```python
# Enable debug mode
sentry_sdk.init(
    dsn="...",
    debug=True,  # Print debug info
)

# Check if DSN is correct
print(sentry_sdk.Hub.current.client.options['dsn'])

# Verify SDK initialized
assert sentry_sdk.Hub.current.client is not None
```

**Common causes**:
1. **Wrong DSN**: Check environment variable
2. **Network blocking**: Firewall/proxy blocking sentry.io
3. **before_send returning None**: PII scrubbing too aggressive
4. **Async flush**: Call `sentry_sdk.flush()` before exit

**Solutions**:
```python
# 1. Verify DSN
dsn = os.getenv('SENTRY_DSN')
assert dsn, "SENTRY_DSN not set"

# 2. Test connectivity
import requests
response = requests.get('https://sentry.io/api/0/projects/')
assert response.status_code == 401  # Unauthorized (but reachable)

# 3. Check before_send
def before_send(event, hint):
    print(f"Sending event: {event}")
    return event  # Don't return None accidentally

# 4. Flush before exit
sentry_sdk.capture_exception(Exception("test"))
sentry_sdk.flush(timeout=2)
```

#### Issue 2: Source Maps Not Working

**Symptoms**:
- Stack traces show minified code, not original source

**Diagnosis**:
```bash
# Check if source maps uploaded
sentry-cli releases files <version> list

# Test source map resolution
curl https://sentry.io/api/0/projects/org/project/events/<event-id>/ \
  -H "Authorization: Bearer TOKEN"
# Check if 'context' shows original source
```

**Common causes**:
1. **Not uploaded**: Forgot to run `sentry-cli releases files upload-sourcemaps`
2. **Wrong URL prefix**: Mismatch between bundle URL and upload prefix
3. **Wrong release**: Release in code doesn't match uploaded source maps
4. **Source map reference stripped**: Using `hidden-source-map` without manual upload

**Solutions**:
```javascript
// 1. Upload source maps in build
"scripts": {
    "build": "webpack && sentry-cli releases files upload-sourcemaps dist/"
}

// 2. Match URL prefix
sentry-cli releases files "$VERSION" upload-sourcemaps ./dist \
    --url-prefix '~/static/js'  // Match production URL structure

// 3. Match release version
// In code:
Sentry.init({ release: "1.2.3" });

// In upload:
sentry-cli releases files "1.2.3" upload-sourcemaps dist/

// 4. Use hidden-source-map
// webpack.config.js
devtool: 'hidden-source-map'
```

#### Issue 3: Too Many Events (High Cost)

**Symptoms**:
- Sentry bill unexpectedly high
- Rate limit errors in logs

**Diagnosis**:
```python
# Check event volume
GET https://sentry.io/api/0/organizations/{org}/stats/
?stat=received
&since=1609459200  # Unix timestamp
&until=1612137600
```

**Solutions**:
```python
# 1. Implement sampling
def before_send(event, hint):
    # Sample 10%
    if random.random() > 0.1:
        return None
    return event

# 2. Ignore common errors
sentry_sdk.init(
    dsn="...",
    ignore_errors=[
        'ConnectionError',
        'TimeoutError',
        'NotFoundError',
    ]
)

# 3. Set rate limits
# Project Settings → Client Keys → Rate Limits
# Max events: 1000/minute

# 4. Use error budget
# Only send errors that matter
def should_send(event):
    # Don't send if too many events today
    if get_events_today() > ERROR_BUDGET:
        return False
    return True
```

#### Issue 4: Poor Error Grouping

**Symptoms**:
- Similar errors creating separate issues
- Or unrelated errors grouped together

**Diagnosis**:
```python
# Check fingerprints of related issues
GET https://sentry.io/api/0/issues/{id}/
# Look at 'title' and 'culprit'

# View fingerprint
event['fingerprint']  # Default is ['{{ default }}']
```

**Solutions**:
```python
# Custom fingerprinting
def before_send(event, hint):
    # Remove dynamic parts from grouping
    if 'exception' in event:
        exc_value = event['exception']['values'][0]['value']

        # "User 123 not found" → "User not found"
        exc_value = re.sub(r'User \d+', 'User', exc_value)
        event['fingerprint'] = ['user-not-found']

    return event

# Or split overly-broad groups
# Project Settings → Issue Grouping → Custom Fingerprinting
# error.value:"*timeout*" -> network-timeout
```

#### Issue 5: High SDK Overhead

**Symptoms**:
- Application slow after adding Sentry
- High CPU usage from Sentry SDK

**Diagnosis**:
```python
# Measure overhead
import time

start = time.time()
for _ in range(1000):
    try:
        raise ValueError("test")
    except Exception as e:
        sentry_sdk.capture_exception(e)
duration = time.time() - start

print(f"Time per event: {duration/1000*1000:.2f}ms")
# Should be < 5ms
```

**Solutions**:
```python
# 1. Reduce sample rate
sentry_sdk.init(
    dsn="...",
    traces_sample_rate=0.01,  # 1% instead of 10%
)

# 2. Async transport (default)
# Events sent in background thread, non-blocking

# 3. Disable local variables
sentry_sdk.init(
    dsn="...",
    with_locals=False,  # Don't capture local variables
)

# 4. Reduce breadcrumbs
sentry_sdk.init(
    dsn="...",
    max_breadcrumbs=10,  # Default is 100
)

# 5. Use Relay
# Deploy Sentry Relay for local buffering
# Reduces latency and network overhead
```

---

## Anti-Patterns

### 1. Catching and Logging Without Re-raising

```python
# ❌ WRONG: Swallow exception
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)
    # Exception lost! Caller thinks it succeeded

# ✅ CORRECT: Re-raise after capturing
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise  # Propagate exception
```

### 2. Capturing Expected Errors

```python
# ❌ WRONG: Capture validation errors
try:
    validate_input(data)
except ValidationError as e:
    sentry_sdk.capture_exception(e)  # Creates noise

# ✅ CORRECT: Don't capture expected errors
try:
    validate_input(data)
except ValidationError as e:
    logger.info(f"Validation failed: {e}")
    return {"error": str(e)}, 400
```

### 3. Including Sensitive Data in Errors

```python
# ❌ WRONG: PII in error message
raise ValueError(f"Invalid credit card: {credit_card_number}")

# ✅ CORRECT: Generic message, details in context
sentry_sdk.set_context("payment", {
    "card_last4": credit_card_number[-4:]  # Only last 4 digits
})
raise ValueError("Invalid credit card")
```

### 4. Not Using Release Tracking

```python
# ❌ WRONG: No release specified
sentry_sdk.init(dsn="...")

# ✅ CORRECT: Specify release
sentry_sdk.init(
    dsn="...",
    release="myapp@1.2.3"  # Enables regression detection
)
```

### 5. Alerting on Every Error

```yaml
# ❌ WRONG: Alert on everything
- alert: NewError
  conditions: [first_seen_event]
  actions: [pagerduty_alert]

# ✅ CORRECT: Alert on high-impact errors
- alert: CriticalError
  conditions:
    - first_seen_event
    - event_frequency:
        value: 10
        interval: 5m
  filters:
    - environment: production
    - level: [error, fatal]
  actions: [pagerduty_alert]
```

### 6. Ignoring Error Budget

```python
# ❌ WRONG: Send every single error
sentry_sdk.capture_exception(e)

# ✅ CORRECT: Implement error budget
class ErrorBudget:
    def __init__(self, daily_limit=10000):
        self.daily_limit = daily_limit
        self.count = 0
        self.reset_at = datetime.now() + timedelta(days=1)

    def can_send(self):
        if datetime.now() > self.reset_at:
            self.count = 0
            self.reset_at = datetime.now() + timedelta(days=1)

        return self.count < self.daily_limit

    def track(self):
        self.count += 1

error_budget = ErrorBudget()

def capture_exception_with_budget(e):
    if error_budget.can_send():
        error_budget.track()
        sentry_sdk.capture_exception(e)
```

### 7. Not Testing Error Tracking

```python
# ❌ WRONG: No tests for error tracking

# ✅ CORRECT: Test error tracking
def test_error_tracking():
    """Verify errors are captured."""
    with pytest.raises(ValueError):
        try:
            raise ValueError("test error")
        except Exception as e:
            event_id = sentry_sdk.capture_exception(e)
            assert event_id is not None
            raise
```

### 8. Missing Context

```python
# ❌ WRONG: No context
try:
    process_order(order_id)
except Exception as e:
    sentry_sdk.capture_exception(e)

# ✅ CORRECT: Rich context
sentry_sdk.set_user({"id": user.id, "email": user.email})
sentry_sdk.set_tag("order_id", order_id)
sentry_sdk.set_context("order", {
    "id": order_id,
    "total": order.total,
    "items": len(order.items)
})

try:
    process_order(order_id)
except Exception as e:
    sentry_sdk.capture_exception(e)
```

---

## Conclusion

This comprehensive reference covers:
- Error tracking architecture and lifecycle
- Tool comparison (Sentry, Rollbar, Bugsnag, etc.)
- Sentry deep dive (setup, configuration, SDK)
- Error context enrichment (user, tags, breadcrumbs)
- Error grouping and custom fingerprinting
- Stack trace analysis
- Source maps (generation, upload, debugging)
- Release tracking and regression detection
- Alert strategies and fatigue prevention
- Error prioritization frameworks
- PII scrubbing and privacy compliance
- Multi-language integration patterns
- Distributed systems error correlation
- Performance optimization and sampling
- Testing strategies
- Operational patterns (triage, review, on-call)
- Troubleshooting common issues
- Anti-patterns to avoid

**Key takeaways**:
1. **Capture with context**: User, tags, breadcrumbs, environment
2. **Group intelligently**: Custom fingerprinting when needed
3. **Alert strategically**: High-impact issues only
4. **Prioritize systematically**: Frequency + user impact + environment
5. **Scrub PII**: Privacy compliance is critical
6. **Sample wisely**: Control volume and cost
7. **Track releases**: Enable regression detection
8. **Test thoroughly**: Verify error tracking works
9. **Review regularly**: Triage daily, review weekly
10. **Avoid anti-patterns**: Re-raise, don't capture expected errors

For production-ready scripts and examples, see the `scripts/` and `examples/` directories.
