---
name: cloud-gcp-serverless
description: Google Cloud serverless services including Cloud Functions, Cloud Run, and App Engine
---

# GCP Serverless Computing

**Scope**: Cloud Functions event-driven functions, Cloud Run containers, App Engine applications, and serverless patterns
**Lines**: ~360
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building event-driven applications with Cloud Functions
- Deploying stateless containerized services with Cloud Run
- Running web applications and APIs on App Engine
- Choosing between serverless compute options
- Configuring triggers and event routing with Eventarc
- Scheduling tasks with Cloud Scheduler and Cloud Tasks
- Optimizing cold start performance and concurrency
- Managing secrets and environment variables in serverless environments

## Core Concepts

### Concept 1: Cloud Functions Triggers

**Trigger types**:
- **HTTP**: Direct HTTP requests (synchronous)
- **Cloud Pub/Sub**: Message queue (asynchronous)
- **Cloud Storage**: Object lifecycle events
- **Firestore**: Document changes
- **Firebase Auth**: User authentication events

```python
import functions_framework
from google.cloud import storage

# HTTP trigger
@functions_framework.http
def hello_http(request):
    name = request.args.get('name', 'World')
    return f'Hello, {name}!'

# Pub/Sub trigger
@functions_framework.cloud_event
def process_message(cloud_event):
    import base64
    message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    print(f"Processing message: {message}")

# Cloud Storage trigger
@functions_framework.cloud_event
def process_file(cloud_event):
    bucket = cloud_event.data["bucket"]
    name = cloud_event.data["name"]
    print(f"File uploaded: gs://{bucket}/{name}")

    # Process file
    storage_client = storage.Client()
    blob = storage_client.bucket(bucket).blob(name)
    content = blob.download_as_text()
    # Process content...
```

```bash
# Deploy HTTP function
gcloud functions deploy hello-http \
  --runtime=python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region=us-central1

# Deploy Pub/Sub function
gcloud functions deploy process-message \
  --runtime=python311 \
  --trigger-topic=message-queue \
  --region=us-central1

# Deploy Cloud Storage function
gcloud functions deploy process-file \
  --runtime=python311 \
  --trigger-event=google.storage.object.finalize \
  --trigger-resource=upload-bucket \
  --region=us-central1
```

### Concept 2: Cloud Run Service Configuration

**Key features**:
- Deploy any container (not limited to specific runtimes)
- Automatic HTTPS endpoints
- Traffic splitting for gradual rollouts
- Concurrency control (requests per container)

```bash
# Build container with Cloud Build
gcloud builds submit --tag gcr.io/my-project/api-service

# Deploy to Cloud Run
gcloud run deploy api-service \
  --image=gcr.io/my-project/api-service \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=100 \
  --concurrency=80 \
  --timeout=300 \
  --set-env-vars="DATABASE_URL=postgresql://host/db" \
  --set-secrets="API_KEY=api-key:latest"
```

```python
# Cloud Run service example (FastAPI)
from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from Cloud Run"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### Concept 3: App Engine Environments

**Standard vs Flexible**:
- **Standard**: Fast scaling, language-specific runtimes, free tier
- **Flexible**: Custom containers, more control, no free tier

```yaml
# app.yaml for App Engine Standard (Python 3.11)
runtime: python311
instance_class: F2

env_variables:
  DATABASE_URL: "postgresql://host/db"

handlers:
- url: /static
  static_dir: static

- url: /.*
  script: auto
  secure: always

automatic_scaling:
  target_cpu_utilization: 0.65
  min_instances: 1
  max_instances: 10
  min_pending_latency: 30ms
  max_pending_latency: 100ms
```

```yaml
# app.yaml for App Engine Flexible (custom runtime)
runtime: custom
env: flex

automatic_scaling:
  min_num_instances: 1
  max_num_instances: 10
  cpu_utilization:
    target_utilization: 0.65

resources:
  cpu: 1
  memory_gb: 2
  disk_size_gb: 10

env_variables:
  DATABASE_URL: "postgresql://host/db"
```

### Concept 4: Serverless Comparison Matrix

**When to use each service**:

```
Feature             | Cloud Functions | Cloud Run      | App Engine Std | App Engine Flex
--------------------|-----------------|----------------|----------------|----------------
Container support   | No              | Yes (any)      | No             | Yes (any)
Max request timeout | 9 min           | 60 min         | 10 min         | 60 min
Concurrency/instance| 1               | Up to 1000     | Up to 80       | Up to 80
Cold start          | ~1-2s           | ~1-3s          | <1s            | Minutes
Scaling to zero     | Yes             | Yes            | Yes            | No (min 1)
Free tier           | 2M invocations  | 2M requests    | 28 hrs/day     | No
Best for            | Event handlers  | APIs, websites | Web apps       | Docker apps
```

---

## Patterns

### Pattern 1: Cloud Functions with Pub/Sub for Async Processing

**When to use**:
- Decouple long-running tasks from HTTP requests
- Retry failed operations automatically

```python
# ❌ Bad: Long-running task in HTTP function (times out)
@functions_framework.http
def process_video(request):
    video_url = request.json['video_url']
    # This takes 5 minutes, function times out!
    processed_video = expensive_video_processing(video_url)
    return {"status": "done"}

# ✅ Good: Publish to Pub/Sub, process asynchronously
from google.cloud import pubsub_v1

@functions_framework.http
def submit_video(request):
    video_url = request.json['video_url']

    # Publish to Pub/Sub (fast)
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('my-project', 'video-processing')
    publisher.publish(topic_path, video_url.encode())

    return {"status": "queued"}, 202

# Separate function processes videos asynchronously
@functions_framework.cloud_event
def process_video_async(cloud_event):
    import base64
    video_url = base64.b64decode(cloud_event.data["message"]["data"]).decode()

    # Process for as long as needed (up to 9 minutes)
    processed_video = expensive_video_processing(video_url)
    # Pub/Sub automatically retries on failure
```

**Benefits**:
- HTTP endpoint responds immediately
- Automatic retries on failure
- Scale processing independently from API

### Pattern 2: Cloud Run Traffic Splitting

**Use case**: Canary deployment with gradual rollout

```bash
# Deploy baseline version
gcloud run deploy api-service \
  --image=gcr.io/my-project/api:v1 \
  --region=us-central1 \
  --tag=v1

# Deploy new version with tag (no traffic)
gcloud run deploy api-service \
  --image=gcr.io/my-project/api:v2 \
  --region=us-central1 \
  --tag=v2 \
  --no-traffic

# Test new version directly via tagged URL
curl https://v2---api-service-xxx-uc.a.run.app

# Send 10% traffic to new version
gcloud run services update-traffic api-service \
  --region=us-central1 \
  --to-revisions=v1=90,v2=10

# Monitor metrics, then gradually increase
gcloud run services update-traffic api-service \
  --region=us-central1 \
  --to-revisions=v1=50,v2=50

# Fully cutover to new version
gcloud run services update-traffic api-service \
  --region=us-central1 \
  --to-latest
```

### Pattern 3: Eventarc for Event-Driven Architecture

**Use case**: React to events from multiple sources with unified routing

```bash
# Create Eventarc trigger for Cloud Storage events
gcloud eventarc triggers create storage-trigger \
  --location=us-central1 \
  --destination-run-service=process-uploads \
  --destination-run-region=us-central1 \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=upload-bucket"

# Create trigger for Pub/Sub messages
gcloud eventarc triggers create pubsub-trigger \
  --location=us-central1 \
  --destination-run-service=process-messages \
  --destination-run-region=us-central1 \
  --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
  --transport-topic=message-queue

# Cloud Run service receives CloudEvents
from flask import Flask, request
import json

app = Flask(__name__)

@app.post("/")
def handle_event():
    event = request.get_json()
    print(f"Event type: {event['type']}")
    print(f"Event data: {event['data']}")

    # Process event based on type
    if event['type'] == 'google.cloud.storage.object.v1.finalized':
        bucket = event['data']['bucket']
        name = event['data']['name']
        # Process uploaded file
    elif event['type'] == 'google.cloud.pubsub.topic.v1.messagePublished':
        message = event['data']['message']['data']
        # Process message

    return "", 204
```

### Pattern 4: Cold Start Optimization

**Use case**: Reduce latency for first requests after scaling to zero

```python
# ❌ Bad: Load heavy dependencies in request handler
@functions_framework.http
def api_endpoint(request):
    import tensorflow as tf  # 2 second import!
    import numpy as np
    model = tf.keras.models.load_model('model.h5')  # 5 second load!
    # Process request...

# ✅ Good: Load dependencies at module level (once per instance)
import tensorflow as tf
import numpy as np

# Load model once when instance starts
MODEL = tf.keras.models.load_model('model.h5')

@functions_framework.http
def api_endpoint(request):
    # Model already loaded, fast response
    result = MODEL.predict(request.json['data'])
    return {"prediction": result.tolist()}

# For Cloud Run, also use min-instances to keep warm
# gcloud run deploy service --min-instances=1
```

### Pattern 5: Cloud Scheduler for Cron Jobs

**Use case**: Run periodic tasks on schedule

```bash
# Create job to call HTTP endpoint every hour
gcloud scheduler jobs create http hourly-cleanup \
  --location=us-central1 \
  --schedule="0 * * * *" \
  --uri="https://api-service-xxx.run.app/cleanup" \
  --http-method=POST \
  --oidc-service-account-email=scheduler@my-project.iam.gserviceaccount.com

# Create job to publish Pub/Sub message daily
gcloud scheduler jobs create pubsub daily-report \
  --location=us-central1 \
  --schedule="0 9 * * *" \
  --topic=report-generation \
  --message-body='{"report_type": "daily"}' \
  --time-zone="America/Los_Angeles"
```

### Pattern 6: Cloud Tasks for Task Queues

**Use case**: Schedule tasks for specific times or rate-limit processing

```python
from google.cloud import tasks_v2
import json

def enqueue_task(project_id, location, queue_name, url, payload, delay_seconds=0):
    client = tasks_v2.CloudTasksClient()

    parent = client.queue_path(project_id, location, queue_name)

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode()
        }
    }

    # Schedule task for future execution
    if delay_seconds:
        import datetime
        timestamp = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay_seconds)
        task["schedule_time"] = timestamp

    response = client.create_task(request={"parent": parent, "task": task})
    return response

# Example: Send notification email in 1 hour
enqueue_task(
    'my-project',
    'us-central1',
    'email-queue',
    'https://api-service-xxx.run.app/send-email',
    {'to': 'user@example.com', 'subject': 'Reminder'},
    delay_seconds=3600
)
```

### Pattern 7: VPC Connector for Private Resources

**Use case**: Access Cloud SQL, Memorystore, or internal services from serverless

```bash
# Create Serverless VPC Access connector
gcloud compute networks vpc-access connectors create serverless-connector \
  --region=us-central1 \
  --subnet=default \
  --subnet-project=my-project \
  --min-instances=2 \
  --max-instances=10

# Deploy Cloud Run with VPC connector
gcloud run deploy api-service \
  --image=gcr.io/my-project/api \
  --region=us-central1 \
  --vpc-connector=serverless-connector \
  --vpc-egress=private-ranges-only

# Now service can access Cloud SQL via private IP
# DATABASE_URL=postgresql://10.0.0.3:5432/db
```

### Pattern 8: Secrets Management

**Use case**: Securely inject database passwords and API keys

```bash
# ❌ Bad: Environment variables for secrets (visible in console)
gcloud run deploy api-service \
  --set-env-vars="DB_PASSWORD=super_secret"  # Visible in UI!

# ✅ Good: Secret Manager integration
# Create secret
echo -n "super_secret" | gcloud secrets create db-password --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding db-password \
  --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor

# Deploy with secret
gcloud run deploy api-service \
  --set-secrets=DB_PASSWORD=db-password:latest

# Access in code
import os
db_password = os.environ['DB_PASSWORD']  # Automatically injected
```

---

## Quick Reference

### Serverless Service Selection

```
Use Case                  | Best Choice        | Why
--------------------------|--------------------|---------------------------------
Event handler (<9 min)    | Cloud Functions    | Simple, event-driven
HTTP API                  | Cloud Run          | Any language/framework
Web application           | App Engine Std     | Integrated services, free tier
Custom Docker app         | Cloud Run          | Full container control
Long-running tasks        | Cloud Run Jobs     | Up to 24 hours
Legacy app migration      | App Engine Flex    | Docker, gradual migration
```

### Key gcloud Commands

```bash
# Cloud Functions
gcloud functions deploy NAME --runtime=RUNTIME --trigger-http
gcloud functions logs read NAME --limit=50
gcloud functions delete NAME

# Cloud Run
gcloud run deploy SERVICE --image=IMAGE --region=REGION
gcloud run services list
gcloud run services delete SERVICE --region=REGION

# App Engine
gcloud app deploy
gcloud app browse
gcloud app logs tail

# Cloud Scheduler
gcloud scheduler jobs create http JOB --schedule="CRON" --uri=URL
gcloud scheduler jobs run JOB

# Cloud Tasks
gcloud tasks queues create QUEUE --location=LOCATION
gcloud tasks queues describe QUEUE --location=LOCATION
```

### Concurrency and Scaling

```
Service         | Max Concurrency | Scale to Zero | Cold Start
----------------|-----------------|---------------|------------
Cloud Functions | 1               | Yes           | ~1-2s
Cloud Run       | 1-1000          | Yes           | ~1-3s
App Engine Std  | 1-80            | Yes           | <1s
App Engine Flex | 1-80            | No (min 1)    | Minutes
```

### Key Guidelines

```
✅ DO: Load dependencies at module level to reduce cold starts
✅ DO: Use Pub/Sub for async processing in Cloud Functions
✅ DO: Set min-instances for latency-sensitive services
✅ DO: Use Secret Manager for credentials (not env vars)
✅ DO: Implement proper health check endpoints
✅ DO: Configure appropriate concurrency based on backend capacity

❌ DON'T: Use Cloud Functions for long-running tasks (use Cloud Run)
❌ DON'T: Store secrets in environment variables
❌ DON'T: Set max-instances too high without testing backend capacity
❌ DON'T: Use App Engine Flexible when Standard suffices (higher cost)
❌ DON'T: Ignore cold start optimization for user-facing APIs
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Perform long-running task synchronously in HTTP function
@functions_framework.http
def process_batch(request):
    for item in request.json['items']:  # 10,000 items!
        process_item(item)  # Takes 10 minutes total
    return "Done"
# Function times out at 9 minutes!

# ✅ CORRECT: Use Pub/Sub or Cloud Run for long tasks
@functions_framework.http
def submit_batch(request):
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('my-project', 'batch-processing')

    # Enqueue each item
    for item in request.json['items']:
        publisher.publish(topic_path, json.dumps(item).encode())

    return {"status": "queued", "count": len(request.json['items'])}

# Or use Cloud Run with higher timeout
# gcloud run deploy batch-processor --timeout=3600  # 1 hour
```

❌ **Synchronous long tasks**: Cloud Functions have 9-minute max timeout. Long-running tasks cause failures.
✅ **Correct approach**: Use Pub/Sub for async processing or Cloud Run for longer timeout (up to 60 minutes).

### Common Mistakes

```bash
# ❌ Don't: Store secrets in environment variables
gcloud run deploy api-service \
  --set-env-vars="API_KEY=sk_live_abc123,DB_PASSWORD=secret"
# Secrets visible in console, logs, error messages

# ✅ Correct: Use Secret Manager
gcloud secrets create api-key --data-file=- <<< "sk_live_abc123"
gcloud secrets create db-password --data-file=- <<< "secret"

gcloud run deploy api-service \
  --set-secrets="API_KEY=api-key:latest,DB_PASSWORD=db-password:latest"
```

❌ **Env vars for secrets**: Environment variables are visible in console, logs, and error messages.
✅ **Better**: Use Secret Manager integration for secure secret injection.

```python
# ❌ Don't: Set unbounded concurrency without testing
# gcloud run deploy api-service --concurrency=1000
# Each instance handles 1000 concurrent requests!

@app.get("/query")
def query_database():
    # Database has connection pool of 10
    result = db.execute("SELECT * FROM large_table")
    return result
# Database connection pool exhausted, queries fail!

# ✅ Correct: Set concurrency based on backend capacity
# gcloud run deploy api-service --concurrency=5
# Each instance handles max 5 requests (within connection pool limit)
```

❌ **Unbounded concurrency**: Default Cloud Run concurrency of 80 can overwhelm databases and external APIs.
✅ **Better**: Set max concurrency based on backend capacity (e.g., database connection pool size).

```python
# ❌ Don't: Import heavy dependencies in request handler
@functions_framework.http
def predict(request):
    import tensorflow as tf  # 2 second import on every cold start!
    model = tf.keras.models.load_model('model.h5')
    # Process request...

# ✅ Correct: Import at module level (once per instance)
import tensorflow as tf

MODEL = tf.keras.models.load_model('model.h5')  # Load once

@functions_framework.http
def predict(request):
    result = MODEL.predict(request.json['data'])
    return {"prediction": result.tolist()}
```

❌ **Request-level imports**: Importing heavy libraries in request handler increases cold start latency.
✅ **Better**: Import at module level so libraries load once per instance, not per request.

---

## Related Skills

- `gcp-compute.md` - Comparing serverless with VM-based compute
- `gcp-storage.md` - Cloud Functions triggers for Cloud Storage events
- `gcp-databases.md` - Connecting serverless to Cloud SQL and Firestore
- `gcp-iam-security.md` - Service accounts for serverless workloads
- `gcp-networking.md` - VPC connectors for private resource access

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
