---
name: deployment-heroku-addons
description: Adding databases (Postgres, MySQL, MongoDB) to Heroku apps
---



# Heroku Add-ons

**Scope**: Heroku add-on ecosystem, Postgres, Redis, monitoring, logging, email services
**Lines**: ~310
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Adding databases (Postgres, MySQL, MongoDB) to Heroku apps
- Setting up caching with Redis or Memcached
- Implementing application monitoring and error tracking
- Configuring log aggregation and analysis
- Adding email delivery services (SendGrid, Mailgun)
- Setting up scheduled jobs with Heroku Scheduler
- Optimizing add-on costs and performance

## Core Concepts

### Add-on Architecture

**Provisioning**: Add-ons as managed services
- Single command installation: `heroku addons:create`
- Automatic configuration injection (environment variables)
- Independent lifecycle from app code
- Shared or dedicated resources (plan-dependent)

**Connection Pattern**:
```bash
# Add-on creates config var automatically
heroku addons:create heroku-postgresql:essential-0

# Check created config vars
heroku config | grep DATABASE_URL
# DATABASE_URL: postgres://user:pass@host:5432/dbname
```

**Pricing Tiers**:
- Free/Hobby: Development and testing
- Essential: Small production apps
- Premium/Standard: Production-grade with SLA
- Enterprise: High availability, dedicated resources

### Add-on Categories

**Data Stores**:
- Heroku Postgres: Primary relational database
- Heroku Redis: Caching, sessions, queues
- MongoDB Atlas: Document database
- Apache Kafka: Event streaming

**Developer Tools**:
- Heroku Scheduler: Cron-like job runner
- Heroku Exec: SSH into running dynos
- Heroku Connect: Salesforce data sync

**Monitoring & Logging**:
- Papertrail: Log aggregation and search
- New Relic: APM and performance monitoring
- Sentry: Error tracking and debugging
- LogDNA: Advanced log analysis

**Performance**:
- Fastly: CDN and edge caching
- Cloudflare: DDoS protection and CDN
- Advanced Scheduler: High-frequency cron jobs

**Communication**:
- SendGrid: Transactional email
- Mailgun: Email API and SMTP
- Twilio: SMS and voice

---

## Patterns

### Pattern 1: Heroku Postgres Setup

**Provision database**:
```bash
# Essential plan (~$5/mo, 10GB storage, 20 connections)
heroku addons:create heroku-postgresql:essential-0

# Check status
heroku pg:info

# Output:
# Plan:                  Essential 0
# Status:                Available
# Connections:           0/20
# PG Version:            15.3
# Created:               2025-10-18
# Data Size:             8.2 MB
```

**Connection pooling** (recommended for >20 connections):
```bash
# Enable connection pooling (increases connection limit)
heroku pg:connection-pooling:attach DATABASE --as DATABASE_CONNECTION_POOL

# Use pooled connection
heroku config:set DATABASE_URL=$(heroku config:get DATABASE_CONNECTION_POOL_URL)
```

**Python connection** (using psycopg2):
```python
import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.environ['DATABASE_URL']

# Parse connection URL
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    database=url.path[1:],  # Remove leading '/'
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

# Or use Django DATABASE setting
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port,
    }
}
```

**Backup and restore**:
```bash
# Create manual backup
heroku pg:backups:capture --app myapp

# List backups
heroku pg:backups

# Restore from backup
heroku pg:backups:restore b101 DATABASE_URL --app myapp

# Download backup
heroku pg:backups:download

# Schedule automatic backups (Premium plans only)
heroku pg:backups:schedule DATABASE_URL --at '02:00 America/Los_Angeles'
```

### Pattern 2: Heroku Redis for Caching

**Provision Redis**:
```bash
# Mini plan (~$3/mo, 25MB memory)
heroku addons:create heroku-redis:mini

# Check status
heroku redis:info

# Output:
# Plan:                  Mini
# Status:                available
# Version:               7.0.8
# Max Memory:            25 MB
```

**Python (Django cache)**:
```python
# settings.py
import os

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}

# Use cache
from django.core.cache import cache

cache.set('key', 'value', 300)  # 5 minutes
value = cache.get('key')
```

**Node.js (with ioredis)**:
```javascript
const Redis = require('ioredis');
const redis = new Redis(process.env.REDIS_URL);

// Set with expiration
await redis.set('user:123', JSON.stringify(userData), 'EX', 3600);

// Get
const data = await redis.get('user:123');
const user = JSON.parse(data);

// Pub/Sub pattern
const subscriber = new Redis(process.env.REDIS_URL);
subscriber.subscribe('notifications');

subscriber.on('message', (channel, message) => {
  console.log(`Received ${message} from ${channel}`);
});

// Publish
await redis.publish('notifications', 'New order received');
```

**Session storage**:
```python
# Django sessions in Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### Pattern 3: Papertrail for Log Management

**Provision Papertrail**:
```bash
# Choklad plan (free, 50MB/mo, 2-day retention)
heroku addons:create papertrail:choklad

# Open dashboard
heroku addons:open papertrail
```

**Search logs via CLI**:
```bash
# Search for errors
heroku logs --tail | grep ERROR

# Or via Papertrail CLI
papertrail -f -S 'error OR exception'

# Search specific time range
papertrail -S 'status=500' --min-time '1 hour ago'
```

**Structured logging** (Python):
```python
import logging
import json

# JSON formatter for better Papertrail parsing
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

logger = logging.getLogger('myapp')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Use logger
logger.info('User logged in', extra={'user_id': 123, 'ip': '1.2.3.4'})
```

**Alerts** (via Papertrail dashboard):
- Create search: `status=500`
- Set frequency threshold: `10 matches in 5 minutes`
- Send to: Email, Slack, PagerDuty

### Pattern 4: SendGrid for Email

**Provision SendGrid**:
```bash
# Starter plan (free, 100 emails/day)
heroku addons:create sendgrid:starter

# Get API key
heroku config:get SENDGRID_API_KEY
```

**Python (Flask-Mail)**:
```python
from flask import Flask
from flask_mail import Mail, Message
import os

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = os.environ.get('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'

mail = Mail(app)

def send_welcome_email(user_email):
    msg = Message(
        subject='Welcome to MyApp',
        recipients=[user_email],
        body='Thanks for signing up!',
        html='<h1>Thanks for signing up!</h1>'
    )
    mail.send(msg)
```

**Node.js (SendGrid SDK)**:
```javascript
const sgMail = require('@sendgrid/mail');
sgMail.setApiKey(process.env.SENDGRID_API_KEY);

async function sendWelcomeEmail(email) {
  const msg = {
    to: email,
    from: 'noreply@example.com',
    subject: 'Welcome to MyApp',
    text: 'Thanks for signing up!',
    html: '<h1>Thanks for signing up!</h1>',
  };

  await sgMail.send(msg);
}
```

### Pattern 5: Heroku Scheduler for Cron Jobs

**Provision Scheduler**:
```bash
# Free add-on
heroku addons:create scheduler:standard

# Open dashboard to configure jobs
heroku addons:open scheduler
```

**Configure job** (via dashboard):
- Frequency: `Every 10 minutes`, `Hourly`, `Daily`
- Command: `python manage.py cleanup_expired_sessions`
- Dyno size: `Standard-1X`

**Example commands**:
```bash
# Data cleanup
python manage.py cleanup_old_records

# Report generation
python manage.py generate_daily_report && python manage.py email_report

# Cache warming
python manage.py warm_cache

# Database maintenance
python manage.py vacuum_db
```

**Alternative: APScheduler** (in-process, for Standard+ dynos):
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
def cleanup_task():
    # Run at 2:00 AM daily
    cleanup_old_records()

@scheduler.scheduled_job('interval', minutes=10)
def sync_task():
    # Run every 10 minutes
    sync_external_data()

scheduler.start()
```

### Pattern 6: New Relic APM for Performance Monitoring

**Provision New Relic**:
```bash
# Wayne plan (free, 100GB/mo data)
heroku addons:create newrelic:wayne

# Open dashboard
heroku addons:open newrelic
```

**Python (Django) integration**:
```bash
# Install agent
pip install newrelic

# Generate config
newrelic-admin generate-config $NEW_RELIC_LICENSE_KEY newrelic.ini

# Update Procfile
web: newrelic-admin run-program gunicorn myapp.wsgi
```

**Environment configuration**:
```bash
heroku config:set NEW_RELIC_APP_NAME='MyApp Production'
heroku config:set NEW_RELIC_LOG=stdout
heroku config:set NEW_RELIC_LOG_LEVEL=info
```

**Custom instrumentation**:
```python
import newrelic.agent

@newrelic.agent.function_trace()
def expensive_operation():
    # Track function execution time
    pass

# Record custom metric
newrelic.agent.record_custom_metric('Custom/ActiveUsers', user_count)

# Add custom attributes to transaction
newrelic.agent.add_custom_attribute('user_id', user.id)
```

### Pattern 7: Cost Optimization Strategies

**Review add-on costs**:
```bash
# List all add-ons with pricing
heroku addons --all

# Check specific add-on details
heroku addons:info heroku-postgresql-12345
```

**Optimization tactics**:

**1. Right-size database**:
```bash
# Downgrade if under-utilized
heroku pg:info  # Check data size and connections

# If using <3GB on Standard-0 (50GB, $50/mo)
# Downgrade to Essential-0 (10GB, $5/mo)
heroku addons:upgrade heroku-postgresql-12345 essential-0
```

**2. Use connection pooling** (instead of higher plans):
```bash
# Increases effective connection limit
heroku pg:connection-pooling:attach DATABASE
```

**3. Consolidate Redis instances**:
```bash
# Use namespaces instead of multiple Redis instances
# cache:user:123
# session:abc456
# queue:high_priority
```

**4. Scale dynos during low traffic**:
```bash
# Use Heroku Scheduler to scale down at night
# Job at 11pm: heroku ps:scale web=1 worker=0
# Job at 6am: heroku ps:scale web=2 worker=1
```

**5. Remove unused add-ons**:
```bash
# Destroy add-on (DESTRUCTIVE, backs up data first!)
heroku addons:destroy heroku-postgresql-12345 --confirm myapp
```

---

## Quick Reference

### Common Add-ons

```
Add-on               | Purpose              | Free Tier        | Paid From
---------------------|----------------------|------------------|------------
heroku-postgresql    | Postgres database    | No               | $5/mo
heroku-redis         | Redis cache          | No               | $3/mo
papertrail           | Log management       | 50MB/mo          | $7/mo
sendgrid             | Email delivery       | 100/day          | $15/mo
heroku-scheduler     | Cron jobs            | Yes (Free)       | Free
newrelic             | APM monitoring       | 100GB/mo         | $99/mo
sentry               | Error tracking       | 5K events/mo     | $26/mo
cloudflare           | CDN + DDoS           | Yes              | $20/mo
mailgun              | Email API            | 5K emails/mo     | $35/mo
```

### Essential Commands

```
Command                                   | Purpose
------------------------------------------|----------------------------------------
heroku addons                             | List all add-ons for app
heroku addons:create addon:plan           | Provision add-on
heroku addons:upgrade addon plan          | Change plan
heroku addons:destroy addon               | Remove add-on (destructive)
heroku addons:info addon                  | Show add-on details
heroku addons:open addon                  | Open add-on dashboard
heroku pg:info                            | Postgres database info
heroku pg:psql                            | Connect to Postgres CLI
heroku pg:backups:capture                 | Create database backup
heroku redis:info                         | Redis instance info
heroku redis:cli                          | Connect to Redis CLI
```

### Configuration Best Practices

```
✅ DO: Use connection pooling for Postgres (increases connection limit)
✅ DO: Enable automatic backups for production databases
✅ DO: Monitor add-on metrics (CPU, memory, connections)
✅ DO: Use structured logging for better Papertrail searches
✅ DO: Set up alerts for critical errors (500s, exceptions)
✅ DO: Review add-on costs monthly and optimize
✅ DO: Use appropriate plan for workload (don't over-provision)

❌ DON'T: Use Hobby tier for production (no SLA, limited resources)
❌ DON'T: Ignore connection pool exhaustion errors
❌ DON'T: Skip backups (data loss risk)
❌ DON'T: Provision multiple add-ons when one suffices
❌ DON'T: Hardcode add-on credentials (use environment variables)
❌ DON'T: Leave unused add-ons running (ongoing costs)
```

---

## Anti-Patterns

❌ **Using Hobby Postgres in production**: No backups, limited connections, no SLA
✅ Use Essential tier minimum ($5/mo) with automatic backups enabled

❌ **Not using connection pooling**: Exhausts database connections quickly
✅ Enable `heroku pg:connection-pooling:attach` for apps with >10 dynos

❌ **Ignoring database connection leaks**: Unclosed connections accumulate
✅ Use connection context managers (`with` in Python) and properly close connections

❌ **Over-provisioning add-ons**: Paying for unused capacity
✅ Monitor usage metrics and right-size plans (downgrade if under-utilized)

❌ **Multiple Redis instances for same app**: Unnecessary cost
✅ Use single Redis with namespaced keys (`cache:`, `session:`, `queue:`)

❌ **Not monitoring add-on health**: Silent degradation
✅ Set up New Relic/Papertrail alerts for errors, slow queries, high memory

❌ **Skipping database backups**: Risk of data loss
✅ Enable automatic backups and test restore process

❌ **Hardcoding add-on URLs**: Breaks on credential rotation
✅ Always use environment variables (`DATABASE_URL`, `REDIS_URL`)

❌ **No error tracking in production**: Blind to user-facing bugs
✅ Add Sentry or similar for exception monitoring

❌ **Using free email tier for production**: Rate limits, deliverability issues
✅ Upgrade to paid SendGrid/Mailgun plan with dedicated IP

---

## Related Skills

- `heroku-deployment.md` - Deploying apps that use add-ons
- `heroku-troubleshooting.md` - Debugging add-on connection and performance issues
- `postgres-query-optimization.md` - Optimizing database queries for better performance
- `redis-caching-strategies.md` - Advanced Redis patterns for caching and queues
- `structured-logging.md` - Best practices for log formatting and analysis
- `cost-optimization-cloud.md` - General cloud cost management strategies

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
