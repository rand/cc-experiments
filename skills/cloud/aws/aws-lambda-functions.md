---
name: cloud-aws-lambda-functions
description: AWS Lambda function development, runtime configuration, triggers, and optimization
---

# AWS Lambda Functions

**Scope**: Lambda function development - handlers, runtimes, layers, triggers, cold starts, concurrency
**Lines**: ~350
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building serverless functions triggered by events
- Processing API requests without managing servers
- Implementing event-driven architectures with Lambda
- Optimizing Lambda cold start times and memory usage
- Configuring Lambda layers for shared dependencies
- Setting up triggers from API Gateway, S3, DynamoDB, SQS
- Managing Lambda concurrency and performance
- Troubleshooting Lambda timeout or memory issues

## Core Concepts

### Concept 1: Lambda Handler and Context

**Handler function**:
- Entry point for Lambda execution
- Receives event data and context object
- Returns response or raises exception
- Initialize resources outside handler for reuse

```python
import os
import boto3

# Initialize outside handler - reused across warm invocations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    """
    Lambda handler - invoked for each request

    Args:
        event: Input data (varies by trigger source)
        context: Runtime information and methods

    Returns:
        Response dict (format depends on integration type)
    """
    # Access context information
    request_id = context.request_id
    remaining_ms = context.get_remaining_time_in_millis()
    memory_limit = context.memory_limit_in_mb

    print(f"Request {request_id}, {remaining_ms}ms remaining, {memory_limit}MB limit")

    # Process event
    try:
        result = process_event(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def process_event(event):
    """Business logic - separate from handler"""
    # Your logic here
    return {'message': 'Success'}
```

### Concept 2: Lambda Runtimes and Execution Environment

**Runtime selection**:
- Python 3.11/3.12: Fast cold start, good for data processing
- Node.js 18/20: Fastest cold start, excellent for APIs
- Java 17/21: High throughput, slower cold start
- Go: Compiled binary, fast execution
- Custom runtimes: Container images up to 10GB

```python
# Python runtime best practices
import json
import os
from datetime import datetime

# Environment variables for configuration
STAGE = os.environ.get('STAGE', 'dev')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Lambda layers for shared code
# Add layer ARN in Lambda configuration
# Layer content available in /opt directory
from shared_utils import logger, metrics  # From layer

def lambda_handler(event, context):
    """Using Lambda layers for shared utilities"""

    # Structured logging from layer
    logger.info('Processing request', extra={
        'request_id': context.request_id,
        'function_name': context.function_name
    })

    # Emit metrics from layer
    metrics.increment('requests.count')

    # Your logic
    return {'statusCode': 200}
```

### Concept 3: Cold Starts vs Warm Starts

**Cold start optimization**:
- Minimize function package size
- Initialize connections outside handler
- Use provisioned concurrency for critical paths
- Consider Lambda SnapStart (Java 11+)

```python
import boto3
from functools import lru_cache

# ❌ Bad: Initialize inside handler
def lambda_handler_slow(event, context):
    dynamodb = boto3.resource('dynamodb')  # New connection every time
    table = dynamodb.Table('Users')
    # Cold AND warm invocations pay initialization cost
    return table.get_item(Key={'id': event['userId']})

# ✅ Good: Initialize outside handler
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Users')

def lambda_handler_fast(event, context):
    # Warm invocations reuse connection
    return table.get_item(Key={'id': event['userId']})

# ✅ Better: Lazy initialization with caching
@lru_cache(maxsize=1)
def get_table():
    """Initialize on first use, cache for subsequent calls"""
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table('Users')

def lambda_handler_lazy(event, context):
    table = get_table()  # Cached after first call
    return table.get_item(Key={'id': event['userId']})
```

### Concept 4: Lambda Layers

**Layer benefits**:
- Share code across multiple functions
- Separate dependencies from function code
- Reduce deployment package size
- Version dependencies independently

```bash
# Create Lambda layer structure
mkdir -p layer/python
cd layer/python

# Install dependencies
pip install requests boto3-stubs -t .

# Create layer zip
cd ..
zip -r layer.zip python/

# Publish layer
aws lambda publish-layer-version \
  --layer-name shared-dependencies \
  --description "Common Python dependencies" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11 python3.12
```

```python
# Use layer in Lambda function
# Layer ARN added in function configuration
# Code available in /opt/python

import requests  # From layer
from shared_utils import validate_input  # From layer

def lambda_handler(event, context):
    """Function using dependencies from layer"""

    # Validate using shared utility
    if not validate_input(event):
        return {'statusCode': 400, 'body': 'Invalid input'}

    # Use third-party library from layer
    response = requests.get('https://api.example.com/data')

    return {
        'statusCode': 200,
        'body': response.text
    }
```

---

## Patterns

### Pattern 1: API Gateway Lambda Proxy Integration

**When to use**:
- Building REST APIs with Lambda backend
- Need access to HTTP headers and query parameters
- Return custom HTTP status codes

```python
import json

def lambda_handler(event, context):
    """Handle API Gateway proxy integration"""

    # Parse request
    http_method = event['httpMethod']
    path = event['path']
    query_params = event.get('queryStringParameters') or {}
    headers = event['headers']
    body = json.loads(event.get('body', '{}'))

    # Route request
    if http_method == 'GET':
        return get_items(query_params)
    elif http_method == 'POST':
        return create_item(body)
    elif http_method == 'PUT':
        item_id = path.split('/')[-1]
        return update_item(item_id, body)
    elif http_method == 'DELETE':
        item_id = path.split('/')[-1]
        return delete_item(item_id)
    else:
        return {
            'statusCode': 405,
            'headers': {'Allow': 'GET, POST, PUT, DELETE'},
            'body': json.dumps({'error': 'Method not allowed'})
        }

def get_items(query_params):
    """Get items with pagination"""
    limit = int(query_params.get('limit', 20))

    # Your logic
    items = fetch_items(limit)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'items': items, 'count': len(items)})
    }
```

**Benefits**:
- Full control over HTTP response
- Access to request metadata
- Simple routing logic

### Pattern 2: S3 Event Processing

**Use case**: Process files uploaded to S3 bucket

```python
import urllib.parse
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Process S3 upload events"""

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']

        print(f"Processing s3://{bucket}/{key} ({size} bytes)")

        try:
            # Download file
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()

            # Process based on file type
            if key.endswith('.json'):
                data = json.loads(content)
                process_json(data)
            elif key.endswith('.csv'):
                process_csv(content.decode('utf-8'))
            else:
                print(f"Unsupported file type: {key}")
                continue

            # Upload result
            output_key = f"processed/{key}"
            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps({'status': 'processed'})
            )

        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            raise

    return {'statusCode': 200, 'message': f'Processed {len(event["Records"])} files'}
```

### Pattern 3: DynamoDB Stream Processing

**Use case**: React to DynamoDB table changes

```python
def lambda_handler(event, context):
    """Process DynamoDB stream events"""

    for record in event['Records']:
        event_name = record['eventName']  # INSERT, MODIFY, REMOVE
        event_id = record['eventID']

        if event_name == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            handle_insert(deserialize_item(new_image))

        elif event_name == 'MODIFY':
            old_image = record['dynamodb']['OldImage']
            new_image = record['dynamodb']['NewImage']
            handle_update(
                deserialize_item(old_image),
                deserialize_item(new_image)
            )

        elif event_name == 'REMOVE':
            old_image = record['dynamodb']['OldImage']
            handle_delete(deserialize_item(old_image))

        print(f"Processed event {event_id}: {event_name}")

def deserialize_item(dynamo_item):
    """Convert DynamoDB JSON format to Python dict"""
    from boto3.dynamodb.types import TypeDeserializer
    deserializer = TypeDeserializer()
    return {k: deserializer.deserialize(v) for k, v in dynamo_item.items()}

def handle_insert(item):
    """Handle new item - send notification, update cache, etc."""
    print(f"New item: {item}")
    # Send SNS notification, update ElastiCache, etc.

def handle_update(old_item, new_item):
    """Handle update - audit log, trigger workflow, etc."""
    changes = {k: new_item[k] for k in new_item if old_item.get(k) != new_item[k]}
    print(f"Updated fields: {changes}")

def handle_delete(item):
    """Handle delete - cleanup, archive, etc."""
    print(f"Deleted item: {item}")
```

### Pattern 4: SQS Queue Processing with Batching

**Use case**: Process messages from SQS queue in batch

```python
import boto3

sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """Process SQS messages with batch failure handling"""

    successful = []
    failed = []

    for record in event['Records']:
        message_id = record['messageId']
        body = json.loads(record['body'])

        try:
            result = process_message(body)
            successful.append(message_id)
            print(f"Processed {message_id}: {result}")

        except Exception as e:
            failed.append({
                'itemIdentifier': message_id,
                'failureReason': str(e)
            })
            print(f"Failed {message_id}: {str(e)}")

    # Report batch item failures (SQS will retry only failed messages)
    return {
        'batchItemFailures': [
            {'itemIdentifier': msg_id} for msg_id in failed
        ]
    }

def process_message(message):
    """Business logic for message processing"""
    # Validate
    if not message.get('userId'):
        raise ValueError('Missing userId')

    # Process
    result = perform_work(message)

    return result
```

### Pattern 5: Timeout Handling and Progress Checkpointing

**Use case**: Long-running tasks that may exceed Lambda timeout

```python
import time

def lambda_handler(event, context):
    """Process items with timeout awareness"""

    items = event['items']
    processed = []

    # Reserve 30 seconds for cleanup/checkpoint
    deadline_buffer_ms = 30000

    for i, item in enumerate(items):
        # Check remaining time
        remaining_ms = context.get_remaining_time_in_millis()

        if remaining_ms < deadline_buffer_ms:
            print(f"Approaching timeout, processed {len(processed)}/{len(items)}")

            # Save checkpoint
            save_checkpoint({
                'processed': processed,
                'remaining': items[i:],
                'next_index': i
            })

            # Trigger continuation Lambda
            invoke_continuation(event, i)

            return {
                'statusCode': 202,
                'message': f'Partial completion: {len(processed)} items',
                'checkpoint': i
            }

        # Process item
        result = process_item(item)
        processed.append(result)

    return {
        'statusCode': 200,
        'message': f'Completed all {len(processed)} items',
        'results': processed
    }

def save_checkpoint(state):
    """Save processing state to DynamoDB"""
    table.put_item(Item={
        'id': state['job_id'],
        'state': json.dumps(state),
        'timestamp': datetime.utcnow().isoformat()
    })
```

### Pattern 6: Provisioned Concurrency for Low Latency

**Use case**: Eliminate cold starts for critical endpoints

```bash
# Enable provisioned concurrency via AWS CLI
aws lambda put-provisioned-concurrency-config \
  --function-name critical-api-function \
  --provisioned-concurrent-executions 10 \
  --qualifier v1

# Use with alias
aws lambda create-alias \
  --function-name critical-api-function \
  --name prod \
  --function-version 1

aws lambda put-provisioned-concurrency-config \
  --function-name critical-api-function \
  --provisioned-concurrent-executions 5 \
  --qualifier prod
```

```python
def lambda_handler(event, context):
    """
    Function with provisioned concurrency
    - Always warm (no cold starts)
    - Consistent latency
    - Higher cost (charged for provisioned capacity)
    """

    # Immediate response, no initialization delay
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Fast response'})
    }
```

---

## Quick Reference

### Lambda Runtime Configuration

| Setting | Range | Recommended | Notes |
|---------|-------|-------------|-------|
| Memory | 128 MB - 10,240 MB | 1024 MB | CPU scales with memory |
| Timeout | 1 sec - 15 min | 30 sec (API), 5 min (processing) | Set based on workload |
| Ephemeral storage | 512 MB - 10,240 MB | 512 MB | Temporary /tmp storage |
| Reserved concurrency | 0 - account limit | Only if needed | Limits max concurrent executions |
| Provisioned concurrency | 0 - reserved limit | Critical paths only | Pre-warmed instances |

### Common Triggers and Event Sources

```
Trigger Type       | Use Case                  | Invocation Type
-------------------|---------------------------|------------------
API Gateway        | REST/HTTP APIs            | Synchronous
S3                 | File upload processing    | Asynchronous
DynamoDB Streams   | Table change reactions    | Synchronous (stream)
SQS                | Queue processing          | Synchronous (batch)
SNS                | Notifications             | Asynchronous
EventBridge        | Scheduled tasks, events   | Asynchronous
CloudWatch Logs    | Log processing            | Asynchronous
ALB                | Load balanced APIs        | Synchronous
```

### Key Guidelines

```
✅ DO: Initialize SDK clients outside handler function
✅ DO: Use environment variables for configuration
✅ DO: Set appropriate memory based on workload (monitor CloudWatch)
✅ DO: Use Lambda layers for shared dependencies
✅ DO: Check remaining time for long operations
✅ DO: Return early with informative errors
✅ DO: Use structured logging (JSON format)

❌ DON'T: Store credentials in code (use IAM roles)
❌ DON'T: Create new connections on every invocation
❌ DON'T: Assume unlimited execution time
❌ DON'T: Use /tmp for permanent storage (ephemeral)
❌ DON'T: Return large payloads (6 MB limit for API Gateway)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Hardcode credentials
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# ✅ CORRECT: Use IAM execution role (automatic credentials)
# No credentials needed - boto3 uses role automatically

# ❌ NEVER: Initialize clients inside handler
def lambda_handler(event, context):
    s3 = boto3.client('s3')  # Created every invocation
    return s3.list_buckets()

# ✅ CORRECT: Initialize outside handler
s3 = boto3.client('s3')  # Reused across warm invocations

def lambda_handler(event, context):
    return s3.list_buckets()
```

❌ **Cold start on every invocation**: Initializing heavy resources inside handler adds latency to every request, not just cold starts

✅ **Correct approach**: Initialize outside handler, use provisioned concurrency for critical paths

### Common Mistakes

```python
# ❌ Don't ignore timeout limits
def lambda_handler(event, context):
    # May timeout after 15 minutes max
    process_all_items(event['items'])  # No progress tracking

# ✅ Correct: Monitor remaining time and checkpoint
def lambda_handler(event, context):
    for item in event['items']:
        if context.get_remaining_time_in_millis() < 30000:
            save_checkpoint_and_continue(item)
            return {'statusCode': 202, 'message': 'Continuing'}
        process_item(item)
```

❌ **Exceeding timeout without checkpointing**: Lose all progress when timeout occurs

✅ **Better**: Track remaining time, save progress, invoke continuation if needed

```python
# ❌ Don't use /tmp for permanent storage
def lambda_handler(event, context):
    with open('/tmp/cache.json', 'w') as f:
        json.dump(data, f)
    # File may disappear on next invocation

# ✅ Correct: Use S3 or DynamoDB for persistence
def lambda_handler(event, context):
    s3.put_object(
        Bucket='my-bucket',
        Key='cache.json',
        Body=json.dumps(data)
    )
```

❌ **/tmp is ephemeral**: Content may not persist across invocations

✅ **Better**: Use S3 for files, DynamoDB for structured data

---

## Level 3: Resources

### Reference Material

**Comprehensive Reference**: `/Users/rand/src/cc-polymath/skills/cloud/aws-lambda-deployment/resources/REFERENCE.md` (~1,800 lines)
- Lambda fundamentals and execution model
- All supported runtimes (Python, Node.js, Go, Rust, Java, .NET, custom)
- Function configuration (memory, timeout, environment variables, layers)
- IAM roles and permissions (least privilege patterns)
- Event sources and triggers (API Gateway, S3, DynamoDB, SQS, SNS, EventBridge, Kinesis)
- VPC configuration (when and why, NAT Gateway, VPC endpoints)
- Deployment methods (AWS CLI, SAM, Serverless Framework, CDK, Terraform, containers)
- Monitoring and logging (CloudWatch Logs, X-Ray, Lambda Insights, alarms)
- Performance optimization (cold start reduction, memory tuning, connection pooling, caching)
- Error handling (retries, DLQ, destinations, idempotency)
- Testing strategies (unit, integration, local, load testing)
- Cost optimization
- Production best practices (blue/green deployment, versioning, aliases)
- Advanced patterns (layers, extensions, Step Functions, Lambda@Edge)

### Executable Scripts

**`deploy_lambda.py`** - Deploy Lambda functions with best practices
- Automatic deployment package creation
- Layer support
- VPC configuration
- Environment variables with KMS encryption
- Versioning and aliases
- Monitoring setup (CloudWatch alarms, X-Ray)
- Blue/green deployments with traffic shifting
- Example: `./deploy_lambda.py --function-name my-function --source-dir ./src --handler app.handler --runtime python3.12 --role-arn arn:aws:iam::123456789012:role/lambda-role --blue-green --setup-monitoring`

**`analyze_performance.py`** - Analyze Lambda function performance
- Cold start detection and analysis
- Duration percentiles
- Memory utilization analysis
- Error rate tracking
- Throttle detection
- Cost analysis
- Optimization recommendations
- Example: `./analyze_performance.py --function-name my-function --hours 24 --detailed`

**`test_function.sh`** - Test Lambda functions comprehensively
- Synchronous and asynchronous invocation
- Load testing with configurable concurrency
- Event file support
- Response validation
- Performance timing
- Example: `./test_function.sh --function-name my-function --event event.json --load-test --concurrency 10 --duration 60`

### Example Implementations

**Python Examples**:
- `hello_lambda.py` - Basic Lambda function with JSON response
- `api_lambda.py` - API Gateway integration with routing, validation, error handling

**Node.js Examples**:
- `dynamodb_trigger.js` - DynamoDB Streams processor with INSERT/MODIFY/REMOVE handling

**Infrastructure as Code**:
- `sam/template.yaml` - SAM deployment with API Gateway, DynamoDB, SNS, alarms
- `terraform/lambda.tf` - Terraform deployment with API Gateway v2, DynamoDB, monitoring

**Container Images**:
- `Dockerfile` - Container Lambda examples for Python, Node.js, Go with multi-stage builds

All resources located in: `/Users/rand/src/cc-polymath/skills/cloud/aws-lambda-deployment/resources/`

---

## Related Skills

- `aws-api-gateway.md` - Configure API Gateway triggers and Lambda proxy integration
- `aws-ec2-compute.md` - Alternative to Lambda for long-running or stateful workloads
- `aws-storage.md` - S3 integration for Lambda file processing
- `aws-databases.md` - DynamoDB and RDS integration with Lambda
- `aws-iam-security.md` - IAM roles and policies for Lambda execution
- `infrastructure/aws-serverless.md` - Full serverless architecture patterns with Lambda

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
