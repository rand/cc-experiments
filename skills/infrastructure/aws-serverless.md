---
name: infrastructure-aws-serverless
description: Building serverless APIs and backends
---


# AWS Serverless

**Scope**: AWS serverless architecture - Lambda, API Gateway, DynamoDB, S3, EventBridge, Step Functions
**Lines**: 392
**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

**Activate when**:
- Building serverless APIs and backends
- Processing events asynchronously (S3 uploads, DynamoDB streams, SQS)
- Creating scheduled tasks and cron jobs
- Orchestrating complex workflows
- Building event-driven architectures
- Minimizing infrastructure management

**Prerequisites**:
- AWS account with IAM permissions
- AWS CLI configured (`aws configure`)
- Node.js, Python, or other Lambda runtime installed
- Basic understanding of HTTP and REST APIs
- Familiarity with JSON and IAM policies

**Common scenarios**:
- REST/GraphQL API backends
- Image/video processing pipelines
- Data transformation and ETL
- Webhook handlers
- Scheduled data syncs
- Microservices architectures

---

## Core Concepts

### 1. Lambda Functions

```python
# lambda_function.py
import json
import boto3
import os
from datetime import datetime

# Initialize clients outside handler for connection reuse
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    """
    Lambda handler function

    Args:
        event: Event data (API Gateway, S3, etc.)
        context: Runtime information

    Returns:
        Response with statusCode and body
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))

        # Process request
        item_id = body.get('id')
        if not item_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing id field'})
            }

        # DynamoDB operation
        response = table.put_item(
            Item={
                'id': item_id,
                'data': body.get('data'),
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Success',
                'id': item_id
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")  # CloudWatch Logs
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

### 2. API Gateway Integration

```python
# API Gateway REST API with Lambda proxy integration
def handler(event, context):
    """Handle different HTTP methods"""

    http_method = event['httpMethod']
    path = event['path']

    # Route handling
    if http_method == 'GET' and path == '/items':
        return list_items(event)
    elif http_method == 'GET' and path.startswith('/items/'):
        item_id = path.split('/')[-1]
        return get_item(item_id)
    elif http_method == 'POST' and path == '/items':
        return create_item(event)
    elif http_method == 'PUT' and path.startswith('/items/'):
        item_id = path.split('/')[-1]
        return update_item(item_id, event)
    elif http_method == 'DELETE' and path.startswith('/items/'):
        item_id = path.split('/')[-1]
        return delete_item(item_id)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }

def list_items(event):
    """List all items with pagination"""
    query_params = event.get('queryStringParameters', {}) or {}
    limit = int(query_params.get('limit', 20))

    response = table.scan(Limit=limit)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'items': response['Items'],
            'count': len(response['Items'])
        })
    }
```

### 3. DynamoDB Operations

```python
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Users')

# Put item
def create_user(user_id, email, name):
    table.put_item(
        Item={
            'userId': user_id,
            'email': email,
            'name': name,
            'createdAt': datetime.utcnow().isoformat()
        },
        ConditionExpression='attribute_not_exists(userId)'  # Prevent overwrites
    )

# Get item
def get_user(user_id):
    response = table.get_item(
        Key={'userId': user_id}
    )
    return response.get('Item')

# Query with index
def get_user_by_email(email):
    response = table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq(email)
    )
    return response['Items']

# Update item
def update_user(user_id, name):
    response = table.update_item(
        Key={'userId': user_id},
        UpdateExpression='SET #name = :name, updatedAt = :timestamp',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={
            ':name': name,
            ':timestamp': datetime.utcnow().isoformat()
        },
        ReturnValues='ALL_NEW'
    )
    return response['Attributes']

# Delete item
def delete_user(user_id):
    table.delete_item(
        Key={'userId': user_id}
    )

# Batch operations
def batch_write_users(users):
    with table.batch_writer() as batch:
        for user in users:
            batch.put_item(Item=user)

# Scan with filter
def get_active_users():
    response = table.scan(
        FilterExpression=Attr('status').eq('active')
    )
    return response['Items']
```

### 4. S3 Event Processing

```python
import json
import urllib.parse
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Process S3 upload events"""

    # Parse S3 event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        print(f"Processing {bucket}/{key}")

        try:
            # Download file
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()

            # Process content (e.g., resize image, parse CSV)
            processed = process_file(content)

            # Upload processed file
            output_key = f"processed/{key}"
            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=processed,
                ContentType=response['ContentType']
            )

            print(f"Uploaded to {output_key}")

        except Exception as e:
            print(f"Error processing {key}: {str(e)}")
            raise e

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }
```

---

## Patterns

### Event-Driven Architecture

```python
# EventBridge integration
import boto3

events = boto3.client('events')

def publish_event(event_type, detail):
    """Publish custom event to EventBridge"""
    response = events.put_events(
        Entries=[
            {
                'Source': 'my.application',
                'DetailType': event_type,
                'Detail': json.dumps(detail),
                'EventBusName': 'default'
            }
        ]
    )
    return response

# Lambda handler that publishes events
def lambda_handler(event, context):
    # Process request
    user_id = create_user(event)

    # Publish event for other services to consume
    publish_event(
        'UserCreated',
        {
            'userId': user_id,
            'email': event['email'],
            'timestamp': datetime.utcnow().isoformat()
        }
    )

    return {'statusCode': 200, 'body': json.dumps({'userId': user_id})}
```

### Step Functions Workflow

```json
{
  "Comment": "Image processing workflow",
  "StartAt": "ValidateImage",
  "States": {
    "ValidateImage": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ValidateImage",
      "Next": "IsValid",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "HandleError"
      }]
    },
    "IsValid": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.valid",
        "BooleanEquals": true,
        "Next": "ProcessImage"
      }],
      "Default": "RejectImage"
    },
    "ProcessImage": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "GenerateThumbnail",
          "States": {
            "GenerateThumbnail": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789012:function:GenerateThumbnail",
              "End": true
            }
          }
        },
        {
          "StartAt": "ExtractMetadata",
          "States": {
            "ExtractMetadata": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ExtractMetadata",
              "End": true
            }
          }
        }
      ],
      "Next": "SaveResults"
    },
    "SaveResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:SaveResults",
      "End": true
    },
    "RejectImage": {
      "Type": "Fail",
      "Error": "InvalidImage",
      "Cause": "Image failed validation"
    },
    "HandleError": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:HandleError",
      "End": true
    }
  }
}
```

### SQS Queue Processing

```python
import boto3
import json

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']

def lambda_handler(event, context):
    """Process SQS messages in batch"""

    for record in event['Records']:
        message_body = json.loads(record['body'])
        receipt_handle = record['receiptHandle']

        try:
            # Process message
            result = process_message(message_body)

            # Delete message from queue after successful processing
            sqs.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=receipt_handle
            )

            print(f"Processed message: {result}")

        except Exception as e:
            # Message will return to queue for retry
            print(f"Error processing message: {str(e)}")
            # Optionally send to DLQ after max retries

def process_message(message):
    """Business logic for message processing"""
    # Your processing logic here
    return {'status': 'processed', 'id': message['id']}

# Send message to SQS (from another Lambda)
def send_to_queue(message):
    response = sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message),
        MessageAttributes={
            'Priority': {
                'StringValue': 'high',
                'DataType': 'String'
            }
        }
    )
    return response['MessageId']
```

### DynamoDB Streams

```python
def lambda_handler(event, context):
    """Process DynamoDB stream events"""

    for record in event['Records']:
        event_name = record['eventName']  # INSERT, MODIFY, REMOVE

        if event_name == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            handle_insert(new_image)

        elif event_name == 'MODIFY':
            old_image = record['dynamodb']['OldImage']
            new_image = record['dynamodb']['NewImage']
            handle_update(old_image, new_image)

        elif event_name == 'REMOVE':
            old_image = record['dynamodb']['OldImage']
            handle_delete(old_image)

def handle_insert(item):
    """Handle new item creation"""
    # Send notification, update cache, etc.
    print(f"New item created: {item}")

def handle_update(old_item, new_item):
    """Handle item updates"""
    # Track changes, invalidate cache, etc.
    print(f"Item updated: {old_item} -> {new_item}")

def handle_delete(item):
    """Handle item deletion"""
    # Cleanup related resources
    print(f"Item deleted: {item}")
```

### Lambda Layers for Shared Code

```python
# layer/python/utils.py (shared utilities)
import boto3
import json
from datetime import datetime

def get_secret(secret_name):
    """Retrieve secret from Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

def send_notification(message, topic_arn):
    """Send SNS notification"""
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject='Lambda Notification'
    )

# Use layer in Lambda function
from utils import get_secret, send_notification

def lambda_handler(event, context):
    # Access shared utilities from layer
    db_creds = get_secret('database-credentials')
    send_notification('Processing started', os.environ['SNS_TOPIC'])

    # Your logic here
    return {'statusCode': 200}
```

### Scheduled Tasks (EventBridge Cron)

```python
# Lambda triggered by EventBridge schedule
def lambda_handler(event, context):
    """
    Scheduled task that runs daily at 2 AM UTC
    EventBridge rule: cron(0 2 * * ? *)
    """

    print(f"Scheduled task started at {datetime.utcnow()}")

    try:
        # Daily cleanup task
        cleanup_old_records()

        # Generate daily report
        report = generate_daily_report()

        # Send report via email
        send_report_email(report)

        return {
            'statusCode': 200,
            'body': json.dumps('Scheduled task completed')
        }

    except Exception as e:
        print(f"Error in scheduled task: {str(e)}")
        raise e

def cleanup_old_records():
    """Delete records older than 30 days"""
    cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()

    response = table.scan(
        FilterExpression=Attr('createdAt').lt(cutoff_date)
    )

    with table.batch_writer() as batch:
        for item in response['Items']:
            batch.delete_item(Key={'id': item['id']})

    print(f"Deleted {len(response['Items'])} old records")
```

---

## Quick Reference

### Lambda Best Practices

```python
# Environment variables
TABLE_NAME = os.environ['TABLE_NAME']
REGION = os.environ['AWS_REGION']

# Initialize clients outside handler
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# Use connection pooling
session = boto3.Session()
s3 = session.client('s3')

# Error handling
try:
    result = process_data(event)
    return success_response(result)
except ValueError as e:
    return error_response(400, str(e))
except Exception as e:
    print(f"Unexpected error: {str(e)}")
    return error_response(500, "Internal server error")

# Timeouts and retries
from botocore.config import Config

config = Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    connect_timeout=5,
    read_timeout=60
)
s3 = boto3.client('s3', config=config)
```

### Common Lambda Configurations

```bash
# Memory: 128 MB to 10,240 MB (affects CPU allocation)
# Recommended: 1024 MB (good balance)

# Timeout: 1 second to 15 minutes
# Recommended: 30 seconds for API, 5 minutes for processing

# Reserved concurrency: Limit concurrent executions
# Provisioned concurrency: Pre-warmed instances (reduce cold starts)

# Environment variables
TABLE_NAME=users-table
LOG_LEVEL=INFO
API_KEY=use-secrets-manager

# IAM execution role needs:
# - AWSLambdaBasicExecutionRole (CloudWatch Logs)
# - Permissions for DynamoDB, S3, etc.
```

### AWS CLI Commands

```bash
# Deploy Lambda function
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip

# Invoke function
aws lambda invoke \
  --function-name my-function \
  --payload '{"key": "value"}' \
  response.json

# Get logs
aws logs tail /aws/lambda/my-function --follow

# Update configuration
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 60 \
  --memory-size 1024

# Create layer
zip -r layer.zip python/
aws lambda publish-layer-version \
  --layer-name my-utilities \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Store credentials in code
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"  # NEVER

# ✅ CORRECT: Use IAM roles and environment variables
# Lambda execution role provides credentials automatically

# ❌ NEVER: Initialize clients inside handler
def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')  # Created every invocation
    table = dynamodb.Table('users')
    # ...

# ✅ CORRECT: Initialize outside handler
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('users')

def lambda_handler(event, context):
    # Reuses connection across warm starts
    # ...
```

```python
# ❌ NEVER: Ignore Lambda timeouts
def lambda_handler(event, context):
    # Long-running task without timeout handling
    process_large_dataset()  # May timeout after 15 minutes

# ✅ CORRECT: Check remaining time
def lambda_handler(event, context):
    deadline = context.get_remaining_time_in_millis()

    for item in items:
        if context.get_remaining_time_in_millis() < 30000:  # 30 sec buffer
            # Save progress and exit
            save_checkpoint(item)
            return {'statusCode': 202, 'message': 'Processing continues'}

        process_item(item)
```

### Common Mistakes

```python
# ❌ Don't return large responses from API Gateway
def lambda_handler(event, context):
    data = table.scan()  # Could be MB of data
    return {
        'statusCode': 200,
        'body': json.dumps(data)  # API Gateway limit: 6 MB
    }

# ✅ CORRECT: Use pagination
def lambda_handler(event, context):
    limit = int(event.get('queryStringParameters', {}).get('limit', 20))
    response = table.scan(Limit=limit)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'items': response['Items'][:limit],
            'lastKey': response.get('LastEvaluatedKey')
        })
    }
```

```python
# ❌ Don't use recursion for fan-out
def lambda_handler(event, context):
    for item in items:
        lambda_client.invoke(
            FunctionName='process-item',
            InvocationType='Event',
            Payload=json.dumps(item)
        )  # Could hit concurrency limits

# ✅ CORRECT: Use SQS for fan-out
def lambda_handler(event, context):
    entries = [
        {
            'Id': str(i),
            'MessageBody': json.dumps(item)
        }
        for i, item in enumerate(items)
    ]

    # Batch send to SQS (up to 10 per batch)
    for i in range(0, len(entries), 10):
        sqs.send_message_batch(
            QueueUrl=QUEUE_URL,
            Entries=entries[i:i+10]
        )
```

---

## Related Skills

**Infrastructure**:
- `terraform-patterns.md` - Infrastructure as Code for Lambda, API Gateway, DynamoDB
- `infrastructure-security.md` - IAM roles, policies, secrets management
- `cost-optimization.md` - Lambda pricing, DynamoDB capacity modes

**Development**:
- `modal-functions-basics.md` - Alternative serverless platform with simpler deployment
- `cloudflare-workers.md` - Edge computing alternative for API endpoints

**Standards from CLAUDE.md**:
- Use IAM roles for Lambda execution (never hardcode credentials)
- CloudWatch Logs for monitoring and debugging
- Environment variables for configuration
- Principle of least privilege for permissions

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
