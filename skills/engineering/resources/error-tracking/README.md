# Error Tracking - Level 3 Resources

Complete production-ready resources for implementing comprehensive error tracking with Sentry and alternatives.

## Overview

This directory contains:
- **Comprehensive reference** (4,000+ lines)
- **3 production scripts** (2,400+ lines total)
- **9 production examples** covering all major use cases

## Quick Start

### 1. Read the Main Skill

```bash
cat ../../error-tracking.md
```

Start here for core concepts, patterns, and quick reference.

### 2. Explore the Reference

```bash
cat REFERENCE.md
```

Comprehensive 4,000+ line reference covering:
- Error tracking architecture
- Sentry deep dive (setup, configuration, SDK)
- Alternative tools (Rollbar, Bugsnag, Airbrake)
- Error grouping and fingerprinting strategies
- Stack trace analysis
- Source map support
- Release tracking and regression detection
- Alert strategies
- Error prioritization frameworks
- PII scrubbing and privacy compliance
- Multi-language integration
- Distributed systems error correlation
- Performance optimization and sampling
- Operational patterns
- Troubleshooting guide

### 3. Use Production Scripts

#### Setup Error Tracking

```bash
# Set up new Sentry project
./scripts/setup_error_tracking.py \
  --org myorg \
  --project backend-api \
  --platform python \
  --sentry-token $SENTRY_TOKEN \
  --apply

# Generate configuration from YAML
./scripts/setup_error_tracking.py --config project-config.yml --apply

# List existing projects
./scripts/setup_error_tracking.py --org myorg --list-projects --json
```

**Features**:
- Automated project creation and configuration
- Multi-project setup
- Integration configuration (Slack, PagerDuty, GitHub)
- Alert rule generation
- SDK code generation
- CLI with --help, --json, --verbose

#### Analyze Errors

```bash
# Analyze last 7 days
./scripts/analyze_errors.py \
  --org myorg \
  --project api \
  --days 7

# Generate priority report
./scripts/analyze_errors.py \
  --org myorg \
  --project api \
  --report-type priority \
  --json

# Detect regressions
./scripts/analyze_errors.py \
  --org myorg \
  --project api \
  --detect-regressions \
  --verbose

# Generate HTML report
./scripts/analyze_errors.py \
  --org myorg \
  --project api \
  --days 30 \
  --output report.html
```

**Features**:
- Error pattern detection and clustering
- Regression detection across releases
- Impact assessment (frequency + user count)
- Priority scoring and triage recommendations
- Trend analysis over time
- Multiple report formats (text, JSON, HTML)

#### Test Error Tracking

```bash
# Test error capture
./scripts/test_error_tracking.py \
  --dsn $SENTRY_DSN \
  --test-capture \
  --count 10

# Test error grouping
./scripts/test_error_tracking.py \
  --dsn $SENTRY_DSN \
  --test-grouping

# Test performance impact
./scripts/test_error_tracking.py \
  --dsn $SENTRY_DSN \
  --test-performance \
  --iterations 1000

# Run all tests
./scripts/test_error_tracking.py \
  --dsn $SENTRY_DSN \
  --all \
  --json
```

**Features**:
- Error capture and delivery testing
- Grouping and fingerprinting validation
- User impact tracking verification
- Context enrichment testing
- Performance impact measurement
- Sampling validation
- Concurrent sending tests

## Production Examples

### 1. Self-Hosted Sentry

```bash
cd examples/sentry-self-hosted
docker-compose up -d
```

Complete self-hosted Sentry deployment with:
- PostgreSQL database
- Redis cache
- ClickHouse for events
- Kafka for message streaming
- Snuba for queries
- Symbolicator for source maps
- Optional Relay and Nginx

### 2. Python Integration

**Flask**:
```bash
cd examples/python-integration
export SENTRY_DSN="https://..."
python flask-sentry.py
```

**Django**:
```python
# Add to settings.py
from .django_sentry import init_sentry
init_sentry()
```

Features:
- Automatic exception capture
- User context tracking
- Custom error fingerprinting
- PII scrubbing
- Performance monitoring
- Request/response breadcrumbs

### 3. Node.js Integration

```bash
cd examples/nodejs-integration
export SENTRY_DSN="https://..."
node express-sentry.js
```

Features:
- Express middleware integration
- Automatic error handler
- User and request context
- Performance monitoring
- Custom fingerprinting

### 4. Go Integration

```bash
cd examples/go-integration
export SENTRY_DSN="https://..."
go run sentry-middleware.go
```

Features:
- HTTP middleware
- User context tracking
- Breadcrumb support
- Custom error handling

### 5. Source Maps

```bash
cd examples/source-maps
npm run build
```

Webpack configuration for:
- Hidden source maps (not exposed publicly)
- Automatic upload to Sentry
- Release tracking
- Clean up after upload

### 6. Custom Fingerprinting

```bash
cd examples/fingerprinting
python custom-grouping.py
```

Strategies:
- Group by exception type and context
- Parameterize dynamic data (IDs, timestamps)
- Group by business impact
- Group by root cause
- API endpoint-based grouping

### 7. Release Tracking

```bash
cd examples/release-tracking
```

CI/CD automation for:
- GitHub Actions
- GitLab CI
- CircleCI
- Manual scripts

Features:
- Automatic release creation
- Commit association (regression detection)
- Source map upload
- Deployment notifications

### 8. Alert Rules

```bash
cd examples/alerts
cat alert-rules.json
```

Production-ready alert rules:
- New errors in production
- High error frequency
- High user impact
- Regression detection
- Error rate spikes
- Payment errors (critical)
- Staging environment errors

### 9. Error Budget Tracking

```bash
cd examples/error-budget
./error-budget-tracker.py \
  --org myorg \
  --project api \
  --threshold 0.001
```

Features:
- Track error budget consumption
- Dynamic sampling based on budget
- Alert generation
- Status reporting

## File Structure

```
error-tracking/
├── README.md (this file)
├── REFERENCE.md                           # 4,071 lines
│
├── scripts/
│   ├── setup_error_tracking.py            # 856 lines
│   ├── analyze_errors.py                  # 749 lines
│   └── test_error_tracking.py             # 800 lines
│
└── examples/
    ├── sentry-self-hosted/
    │   └── docker-compose.yml             # Complete self-hosted setup
    ├── python-integration/
    │   ├── flask-sentry.py                # Flask + Sentry
    │   └── django-sentry.py               # Django + Sentry
    ├── nodejs-integration/
    │   └── express-sentry.js              # Express + Sentry
    ├── go-integration/
    │   └── sentry-middleware.go           # Go + Sentry
    ├── source-maps/
    │   └── webpack-sourcemap-config.js    # Source map setup
    ├── fingerprinting/
    │   └── custom-grouping.py             # Custom error grouping
    ├── release-tracking/
    │   └── ci-release-automation.yml      # CI/CD integration
    ├── alerts/
    │   └── alert-rules.json               # Alert configurations
    └── error-budget/
        └── error-budget-tracker.py        # Error budget tracking
```

## Quality Standards

All resources follow Wave 10 enhanced standards:

- ✅ Executable scripts with proper shebangs
- ✅ Type hints throughout Python code
- ✅ Comprehensive error handling
- ✅ --help, --json, --verbose support
- ✅ No TODO/stub/mock comments
- ✅ Production-ready examples
- ✅ Real-world variable names
- ✅ Complete error handling
- ✅ Security best practices (PII scrubbing)

## Usage Patterns

### Development Workflow

1. **Setup Phase**:
   ```bash
   # Create Sentry project
   ./scripts/setup_error_tracking.py --config project.yml --apply

   # Integrate SDK (see examples/)
   # Configure fingerprinting
   # Set up alert rules
   ```

2. **Testing Phase**:
   ```bash
   # Verify error capture
   ./scripts/test_error_tracking.py --dsn $DSN --all

   # Test in staging
   # Verify grouping, context, sampling
   ```

3. **Production Monitoring**:
   ```bash
   # Daily triage
   ./scripts/analyze_errors.py --org myorg --project api --report-type priority

   # Weekly review
   ./scripts/analyze_errors.py --org myorg --project api --days 7 --report-type trends

   # Regression detection
   ./scripts/analyze_errors.py --org myorg --project api --detect-regressions
   ```

### CI/CD Integration

```yaml
# .github/workflows/deploy.yml
- name: Create Sentry release
  uses: examples/release-tracking/ci-release-automation.yml
```

### Error Budget Monitoring

```bash
# Run daily
./examples/error-budget/error-budget-tracker.py \
  --org myorg \
  --project api \
  --json > /tmp/error-budget.json
```

## Best Practices

### 1. Error Capture

- ✅ Capture with rich context (user, tags, breadcrumbs)
- ✅ Re-raise exceptions after capturing
- ✅ Don't capture expected errors (validation, 404s)
- ✅ Use custom fingerprinting for better grouping

### 2. Privacy

- ✅ Scrub PII before sending (see examples)
- ✅ Use `send_default_pii=False`
- ✅ Remove sensitive headers and query params
- ✅ Comply with GDPR/CCPA

### 3. Performance

- ✅ Sample based on environment (5% prod, 100% dev)
- ✅ Use async capture (non-blocking)
- ✅ Implement error budget-based sampling
- ✅ Monitor SDK overhead (< 5%)

### 4. Alerting

- ✅ Alert on high-impact issues only
- ✅ Different severities for different channels
- ✅ Include runbook links
- ✅ Prevent alert fatigue

### 5. Release Tracking

- ✅ Always track releases
- ✅ Associate commits (regression detection)
- ✅ Upload source maps
- ✅ Notify deployments

## Troubleshooting

See REFERENCE.md § Troubleshooting for:
- Events not appearing
- Source maps not working
- Too many events (high cost)
- Poor error grouping
- High SDK overhead

## Support

- **Sentry Docs**: https://docs.sentry.io
- **Sentry Community**: https://discord.gg/sentry
- **Self-Hosted**: https://github.com/getsentry/self-hosted

## License

These resources are part of the cc-polymath skills library.
