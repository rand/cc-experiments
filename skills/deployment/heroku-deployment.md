---
name: deployment-heroku-deployment
description: Deploying web applications, APIs, or worker processes to Heroku
---



# Heroku Deployment

**Scope**: Heroku app deployment, Procfile, buildpacks, pipelines, review apps
**Lines**: ~330
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Deploying web applications, APIs, or worker processes to Heroku
- Setting up Heroku pipelines for staging/production environments
- Configuring Procfile for process types (web, worker, release)
- Troubleshooting Heroku deployment failures or build errors
- Implementing review apps for pull request previews
- Migrating from other platforms to Heroku
- Setting up custom buildpacks or multi-buildpack configurations

## Core Concepts

### Heroku Application Architecture

**Dynos**: Lightweight Linux containers running app processes
- Web dynos: Handle HTTP traffic, must bind to `$PORT`
- Worker dynos: Background jobs, queues, scheduled tasks
- One-off dynos: Run scripts, migrations, maintenance tasks
- Dyno types: Basic ($7/mo), Standard ($25/mo), Performance ($250+/mo)

**Procfile**: Process type definition file
- Lives at repository root
- Defines how to start each process type
- Required for non-standard app types
- Format: `<process-type>: <command>`

**Buildpacks**: Transform code into runnable apps
- Auto-detection: Heroku detects language from files
- Official buildpacks: Ruby, Node.js, Python, Java, PHP, Go, etc.
- Custom buildpacks: Add system dependencies
- Multi-buildpack: Combine multiple buildpacks (buildpacks in `.buildpacks` file)

### Deployment Methods

**Git Push Deployment** (Standard):
```bash
# Add Heroku remote
heroku git:remote -a myapp

# Deploy
git push heroku main
```

**GitHub Integration**:
- Automatic deploys from branch
- Wait for CI to pass before deploy
- Review apps for PRs
- Manual promotion to production

**Docker Deployment**:
```bash
# Login to container registry
heroku container:login

# Build and push
heroku container:push web -a myapp

# Release
heroku container:release web -a myapp
```

### Release Phase

**Purpose**: Run tasks before new release goes live
- Database migrations
- Asset compilation
- Cache warming
- Validation checks

**Configuration** (Procfile):
```
release: python manage.py migrate
web: gunicorn myapp.wsgi
```

**Behavior**:
- Runs on new release only (not dyno restart)
- Blocks release if command fails (exit code != 0)
- Runs in ephemeral dyno (no persistent storage)
- 60 minute timeout

---

## Patterns

### Pattern 1: Standard Web Application Deployment

**Python (Django/Flask) with Procfile**:

```procfile
web: gunicorn myapp.wsgi --bind 0.0.0.0:$PORT --workers 4
release: python manage.py migrate --noinput
```

**Node.js (Express/Next.js)**:

```procfile
web: npm start
release: npm run migrate
```

**Requirements**:
```bash
# Python: runtime.txt
python-3.11.9

# Python: requirements.txt
gunicorn==21.2.0
django==4.2.0

# Node.js: package.json engines
{
  "engines": {
    "node": "20.x",
    "npm": "10.x"
  }
}
```

**Deploy steps**:
```bash
# Create app
heroku create myapp

# Add Postgres
heroku addons:create heroku-postgresql:essential-0

# Set environment variables
heroku config:set SECRET_KEY=xxx DJANGO_SETTINGS_MODULE=myapp.settings.production

# Deploy
git push heroku main

# Scale dynos
heroku ps:scale web=1

# Open app
heroku open
```

### Pattern 2: Worker Dyno for Background Jobs

**Procfile with web and worker**:

```procfile
web: gunicorn myapp.wsgi --workers 4
worker: celery -A myapp worker --loglevel=info
release: python manage.py migrate
```

**Deploy and scale**:
```bash
# Deploy changes
git push heroku main

# Scale worker dynos
heroku ps:scale worker=2

# Check dyno status
heroku ps

# View worker logs
heroku logs --dyno=worker.1 --tail
```

**Cost optimization**:
```bash
# Scale down workers during off-hours (use Heroku Scheduler)
heroku ps:scale worker=0  # Night
heroku ps:scale worker=2  # Day
```

### Pattern 3: Heroku Pipeline (Staging → Production)

**Create pipeline**:
```bash
# Create pipeline
heroku pipelines:create myapp-pipeline --team=myteam

# Create staging app
heroku create myapp-staging --pipeline=myapp-pipeline --stage=staging

# Create production app
heroku create myapp-production --pipeline=myapp-pipeline --stage=production

# Connect to GitHub
heroku pipelines:connect myapp-pipeline --repo=myorg/myapp
```

**Enable review apps** (app.json):
```json
{
  "name": "myapp",
  "description": "My awesome app",
  "repository": "https://github.com/myorg/myapp",
  "env": {
    "SECRET_KEY": {
      "description": "Django secret key",
      "generator": "secret"
    },
    "DEBUG": {
      "value": "False"
    }
  },
  "formation": {
    "web": {
      "quantity": 1,
      "size": "basic"
    }
  },
  "addons": [
    "heroku-postgresql:mini"
  ],
  "buildpacks": [
    {
      "url": "heroku/python"
    }
  ],
  "scripts": {
    "postdeploy": "python manage.py migrate && python manage.py loaddata fixtures/demo.json"
  }
}
```

**Promotion workflow**:
```bash
# Auto-deploy staging from main branch (via dashboard)
# Manual promotion to production:
heroku pipelines:promote -r staging

# Or promote specific release
heroku releases -a myapp-staging
heroku pipelines:promote -r staging --release v123
```

### Pattern 4: Multi-Buildpack Setup

**Use case**: Python app requiring Node.js for asset compilation

**Create `.buildpacks` file**:
```
https://github.com/heroku/heroku-buildpack-nodejs
https://github.com/heroku/heroku-buildpack-python
```

**Or via CLI**:
```bash
heroku buildpacks:add --index 1 heroku/nodejs
heroku buildpacks:add --index 2 heroku/python

# Verify order
heroku buildpacks
```

**Order matters**: Buildpacks run in sequence, last one determines dyno type

### Pattern 5: Custom Domain Configuration

**Add custom domain**:
```bash
# Add domain
heroku domains:add www.example.com

# Get DNS target
heroku domains

# Output:
# === myapp Custom Domains
# Domain Name           DNS Target
# www.example.com       myapp-12345.herokudns.com
```

**DNS configuration** (at domain registrar):
```
Type    Name    Value
CNAME   www     myapp-12345.herokudns.com
```

**SSL certificate** (automatic with ACM):
```bash
# Enable Automated Certificate Management (free)
heroku certs:auto:enable

# Check status
heroku certs:auto
```

### Pattern 6: Environment Configuration

**Set config vars**:
```bash
# Single variable
heroku config:set DATABASE_URL=postgres://...

# Multiple variables
heroku config:set \
  SECRET_KEY=xxx \
  DEBUG=False \
  ALLOWED_HOSTS=myapp.com

# From .env file (requires heroku-dotenv plugin)
heroku plugins:install heroku-config
heroku config:push

# View all config
heroku config

# Unset variable
heroku config:unset DEBUG
```

**Access in code** (Python):
```python
import os

SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
```

### Pattern 7: Database Migration on Deploy

**Procfile with release phase**:
```procfile
release: python manage.py migrate && python manage.py createcachetable
web: gunicorn myapp.wsgi
```

**Alternative: Post-deploy hook** (app.json):
```json
{
  "scripts": {
    "postdeploy": "python manage.py migrate"
  }
}
```

**Manual migration** (for complex changes):
```bash
# Run one-off dyno
heroku run python manage.py migrate

# With custom settings
heroku run python manage.py migrate --settings=myapp.settings.production
```

### Pattern 8: Docker Container Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Heroku provides $PORT dynamically
CMD gunicorn myapp.wsgi --bind 0.0.0.0:$PORT
```

**Deploy**:
```bash
# Build and push (uses heroku.yml or Dockerfile)
heroku container:push web

# Release (starts new dynos)
heroku container:release web

# View logs
heroku logs --tail
```

**heroku.yml** (advanced):
```yaml
build:
  docker:
    web: Dockerfile
    worker: Dockerfile.worker
run:
  web: gunicorn myapp.wsgi
  worker: celery -A myapp worker
```

---

## Quick Reference

### Essential Commands

```
Command                              | Purpose
-------------------------------------|------------------------------------------
heroku create [name]                 | Create new Heroku app
heroku git:remote -a myapp           | Add Heroku remote to existing repo
git push heroku main                 | Deploy via git
heroku logs --tail                   | View live logs
heroku ps                            | Check dyno status
heroku ps:scale web=1 worker=2       | Scale dynos
heroku run bash                      | Open shell on dyno
heroku releases                      | View release history
heroku rollback v123                 | Rollback to specific version
heroku domains:add domain.com        | Add custom domain
heroku config:set KEY=value          | Set environment variable
heroku addons:create addon:plan      | Add add-on
heroku pg:backups:capture            | Create database backup
heroku maintenance:on                | Enable maintenance mode
heroku restart                       | Restart all dynos
```

### Procfile Process Types

```
Process Type | Purpose                        | Example Command
-------------|--------------------------------|--------------------------------
web          | HTTP traffic handler           | gunicorn app:app
worker       | Background jobs                | celery worker -A tasks
release      | Pre-release tasks              | python manage.py migrate
clock        | Scheduled tasks (deprecated)   | python clock.py
```

### Deployment Checklist

```
✅ DO: Use Procfile for custom start commands
✅ DO: Set Python/Node version explicitly (runtime.txt, engines)
✅ DO: Use release phase for migrations
✅ DO: Set production environment variables before first deploy
✅ DO: Add .gitignore entries for local files (.env, db.sqlite3)
✅ DO: Use pipelines for staging → production flow
✅ DO: Enable automatic SSL for custom domains
✅ DO: Configure proper dyno type for workload (Basic/Standard/Performance)

❌ DON'T: Hardcode secrets in code (use config vars)
❌ DON'T: Commit .env files to git
❌ DON'T: Use SQLite in production (use Postgres)
❌ DON'T: Store files on dyno filesystem (use S3/Cloudinary)
❌ DON'T: Deploy without testing locally first
❌ DON'T: Ignore Procfile (causes wrong start command)
❌ DON'T: Use development dependencies in production
```

---

## Anti-Patterns

❌ **Hardcoded secrets in repository**: Exposes credentials in git history
✅ Use `heroku config:set SECRET_KEY=xxx` and `os.environ.get('SECRET_KEY')`

❌ **No Procfile for non-standard apps**: Heroku may guess wrong start command
✅ Always include Procfile with explicit process definitions

❌ **Using SQLite in production**: Data loss on dyno restart (ephemeral filesystem)
✅ Use `heroku addons:create heroku-postgresql:essential-0`

❌ **Storing uploaded files on dyno**: Files disappear on restart/scale
✅ Use S3, Cloudinary, or Heroku add-on for persistent storage

❌ **Not setting Python/Node version**: Unpredictable runtime
✅ Create `runtime.txt` (Python) or set `engines` in package.json (Node)

❌ **Deploying without migrations**: Database schema mismatch
✅ Use `release: python manage.py migrate` in Procfile

❌ **Wrong dyno type for workload**: Over/under-provisioning
✅ Basic for low-traffic, Standard for production, Performance for high-demand

❌ **Not using pipelines**: No staging environment, deploy directly to production
✅ Create pipeline with staging app for testing before production

❌ **Ignoring build logs**: Silent deployment failures
✅ Always check `git push heroku main` output for errors

❌ **Manual scaling only**: No auto-scaling for traffic spikes
✅ Consider Heroku Autoscaling add-on or Standard+ dynos with built-in autoscaling

---

## Related Skills

- `heroku-addons.md` - Postgres, Redis, monitoring, email services
- `heroku-troubleshooting.md` - Debugging crashes, logs, performance issues
- `docker-deployment.md` - Container-based deployment patterns
- `ci-cd-pipelines.md` - Continuous deployment automation
- `environment-configuration.md` - Managing secrets and config across environments
- `database-migrations.md` - Safe migration strategies for production

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
