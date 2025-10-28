# AWS Lambda Deployment - Comprehensive Reference

## Table of Contents
1. [Lambda Fundamentals](#lambda-fundamentals)
2. [Execution Model](#execution-model)
3. [Supported Runtimes](#supported-runtimes)
4. [Function Configuration](#function-configuration)
5. [IAM Roles and Permissions](#iam-roles-and-permissions)
6. [Event Sources and Triggers](#event-sources-and-triggers)
7. [VPC Configuration](#vpc-configuration)
8. [Deployment Methods](#deployment-methods)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Performance Optimization](#performance-optimization)
11. [Error Handling](#error-handling)
12. [Testing Strategies](#testing-strategies)
13. [Cost Optimization](#cost-optimization)
14. [Production Best Practices](#production-best-practices)
15. [Advanced Patterns](#advanced-patterns)

---

## Lambda Fundamentals

### What is AWS Lambda?

AWS Lambda is a serverless compute service that runs code in response to events and automatically manages the underlying compute resources. You pay only for the compute time consumed.

**Key Characteristics:**
- **Event-driven**: Executes in response to triggers
- **Stateless**: Each invocation is independent
- **Ephemeral**: Execution environment is temporary
- **Auto-scaling**: Automatically scales with demand
- **Pay-per-use**: Billed per 1ms of execution time

### Lambda Architecture

```
┌─────────────────────────────────────────────┐
│           Event Source                      │
│  (API Gateway, S3, DynamoDB, etc.)         │
└──────────────────┬──────────────────────────┘
                   │ Trigger
                   ▼
┌─────────────────────────────────────────────┐
│         Lambda Service                      │
│  ┌───────────────────────────────────┐     │
│  │   Execution Environment            │     │
│  │  ┌─────────────────────────────┐  │     │
│  │  │   Your Function Code        │  │     │
│  │  │   (Handler)                 │  │     │
│  │  └─────────────────────────────┘  │     │
│  │  ┌─────────────────────────────┐  │     │
│  │  │   Runtime                   │  │     │
│  │  │   (Python, Node.js, etc.)   │  │     │
│  │  └─────────────────────────────┘  │     │
│  │  ┌─────────────────────────────┐  │     │
│  │  │   Layers (optional)         │  │     │
│  │  └─────────────────────────────┘  │     │
│  └───────────────────────────────────┘     │
└──────────────────┬──────────────────────────┘
                   │ Response
                   ▼
┌─────────────────────────────────────────────┐
│         Destination/Output                  │
│  (API Response, S3, DynamoDB, etc.)        │
└─────────────────────────────────────────────┘
```

### Lambda Lifecycle

**1. Cold Start:**
- Download code
- Start execution environment
- Bootstrap runtime
- Initialize function code (code outside handler)
- Execute handler

**2. Warm Invocation:**
- Reuse existing execution environment
- Execute handler only

**3. Freeze/Thaw:**
- Environment frozen after execution
- Thawed for next invocation
- /tmp persists during freeze

**4. Shutdown:**
- Environment destroyed after idle timeout
- Typically 15-60 minutes

---

## Execution Model

### Invocation Types

#### 1. Synchronous Invocation

Client waits for response. Used by:
- API Gateway
- Application Load Balancer
- Direct invocations via SDK

```python
import boto3

lambda_client = boto3.client('lambda')
response = lambda_client.invoke(
    FunctionName='my-function',
    InvocationType='RequestResponse',  # Synchronous
    Payload=json.dumps({'key': 'value'})
)
```

**Characteristics:**
- Immediate response
- Errors returned to caller
- No automatic retries
- 29-second timeout for API Gateway integration

#### 2. Asynchronous Invocation

Lambda queues the event and returns immediately. Used by:
- S3
- SNS
- EventBridge
- SES

```python
response = lambda_client.invoke(
    FunctionName='my-function',
    InvocationType='Event',  # Asynchronous
    Payload=json.dumps({'key': 'value'})
)
```

**Characteristics:**
- Immediate acceptance (202 response)
- Automatic retries (2 times)
- Dead Letter Queue (DLQ) for failures
- Event age up to 6 hours

#### 3. Poll-Based Invocation

Lambda polls the event source. Used by:
- SQS
- Kinesis
- DynamoDB Streams
- Kafka

**Characteristics:**
- Lambda manages polling
- Batch processing
- Configurable batch size and window
- Error handling via event source mapping

### Concurrency Model

**Reserved Concurrency:**
- Guarantees capacity for function
- Prevents other functions from using it
- Set at function level

**Provisioned Concurrency:**
- Pre-warmed execution environments
- Eliminates cold starts
- More expensive
- Ideal for latency-sensitive apps

**Unreserved Concurrency:**
- Default pool shared by all functions
- Account limit: 1000 (can be increased)
- Burst limit: 500-3000 (region-dependent)

```python
# Set reserved concurrency
lambda_client.put_function_concurrency(
    FunctionName='my-function',
    ReservedConcurrentExecutions=100
)

# Configure provisioned concurrency
lambda_client.put_provisioned_concurrency_config(
    FunctionName='my-function',
    ProvisionedConcurrentExecutions=10,
    Qualifier='v1'  # Alias or version
)
```

### Execution Context

**Available during handler execution:**
- `/tmp` storage: 512MB-10GB
- Memory: 128MB-10GB (configurable)
- Timeout: 1s-15min (900s max)
- Environment variables
- AWS SDK clients

**Context Object:**
```python
def lambda_handler(event, context):
    print(f"Request ID: {context.aws_request_id}")
    print(f"Function name: {context.function_name}")
    print(f"Memory limit: {context.memory_limit_in_mb} MB")
    print(f"Time remaining: {context.get_remaining_time_in_millis()} ms")
    print(f"Log group: {context.log_group_name}")
    print(f"Log stream: {context.log_stream_name}")
```

---

## Supported Runtimes

### Managed Runtimes

| Runtime | Versions | Architecture | Use Case |
|---------|----------|--------------|----------|
| Python | 3.8, 3.9, 3.10, 3.11, 3.12 | x86_64, arm64 | General purpose, data processing, ML |
| Node.js | 16.x, 18.x, 20.x | x86_64, arm64 | Web APIs, async processing |
| Java | 8, 11, 17, 21 | x86_64, arm64 | Enterprise apps, high performance |
| .NET | 6, 8 | x86_64, arm64 | Windows migration, enterprise |
| Go | 1.x | x86_64, arm64 | High performance, low memory |
| Ruby | 3.2, 3.3 | x86_64, arm64 | Web apps, scripting |
| Rust | Via custom runtime | x86_64, arm64 | Extreme performance |

### Python Runtime

**Handler Format:**
```python
# lambda_function.py
def lambda_handler(event, context):
    """
    event: Dict containing event data
    context: LambdaContext object with runtime info
    """
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
```

**Available Libraries:**
- boto3 (AWS SDK)
- botocore
- json, datetime, os, sys (standard library)

**Best Practices:**
```python
import json
import boto3
from datetime import datetime

# Initialize outside handler (reused across invocations)
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')

def lambda_handler(event, context):
    # Handler code here
    try:
        result = process_event(event)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_event(event):
    # Business logic
    pass
```

### Node.js Runtime

**Handler Format:**
```javascript
// index.js
exports.handler = async (event, context) => {
    console.log('Event:', JSON.stringify(event, null, 2));

    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: 'Hello from Lambda!',
            requestId: context.requestId
        })
    };
};
```

**With Callback (older style):**
```javascript
exports.handler = (event, context, callback) => {
    try {
        const result = processEvent(event);
        callback(null, result);  // Success
    } catch (error) {
        callback(error);  // Failure
    }
};
```

### Go Runtime

**Handler Format:**
```go
package main

import (
    "context"
    "encoding/json"
    "github.com/aws/aws-lambda-go/lambda"
)

type Event struct {
    Name string `json:"name"`
}

type Response struct {
    Message string `json:"message"`
}

func HandleRequest(ctx context.Context, event Event) (Response, error) {
    return Response{
        Message: "Hello " + event.Name,
    }, nil
}

func main() {
    lambda.Start(HandleRequest)
}
```

### Custom Runtimes

**Use cases:**
- Unsupported languages (Rust, PHP, C++)
- Specific runtime versions
- Custom initialization logic

**Runtime API:**
```bash
# Get next event
curl "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/next"

# Send response
curl -X POST "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/${RequestId}/response" \
  -d "$RESPONSE"

# Send error
curl -X POST "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/${RequestId}/error" \
  -d "$ERROR"
```

**Bootstrap Script:**
```bash
#!/bin/sh
set -euo pipefail

# Initialize runtime
while true; do
    # Get next event
    HEADERS=$(mktemp)
    EVENT_DATA=$(curl -sS -LD "$HEADERS" \
        "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/next")

    REQUEST_ID=$(grep -Fi Lambda-Runtime-Aws-Request-Id "$HEADERS" | tr -d '[:space:]' | cut -d: -f2)

    # Execute function
    RESPONSE=$(echo "$EVENT_DATA" | ./function)

    # Send response
    curl -sS -X POST "http://${AWS_LAMBDA_RUNTIME_API}/2018-06-01/runtime/invocation/$REQUEST_ID/response" \
        -d "$RESPONSE"
done
```

### Container Images

Lambda supports container images up to 10GB:

**Dockerfile:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set handler
CMD ["app.lambda_handler"]
```

**Build and Deploy:**
```bash
# Build
docker build -t my-lambda-function .

# Tag
docker tag my-lambda-function:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest

# Push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest

# Create function
aws lambda create-function \
  --function-name my-function \
  --package-type Image \
  --code ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda-function:latest \
  --role arn:aws:iam::123456789012:role/lambda-role
```

---

## Function Configuration

### Memory and CPU

Memory allocation determines CPU allocation:
- **Memory**: 128MB - 10GB (1MB increments)
- **CPU**: Proportional to memory
  - 128MB = ~0.1 vCPU
  - 1792MB = 1 vCPU
  - 3584MB = 2 vCPU
  - 10240MB = 6 vCPU

**Pricing Impact:**
- More memory = more CPU = faster execution
- Cost per GB-second increases
- Total cost may decrease due to faster execution

**Finding Optimal Memory:**
```python
# Lambda Power Tuning (SAR app)
# Tests multiple memory configurations
# Provides cost/performance analysis

# Manual testing
import time

def lambda_handler(event, context):
    start = time.time()
    # Your code
    duration = time.time() - start

    memory = context.memory_limit_in_mb
    cost_per_ms = (memory / 1024) * 0.0000166667
    total_cost = cost_per_ms * (duration * 1000)

    print(f"Memory: {memory}MB, Duration: {duration}s, Cost: ${total_cost}")
```

### Timeout Configuration

**Default**: 3 seconds
**Maximum**: 900 seconds (15 minutes)

**Considerations:**
- Set slightly higher than expected execution time
- For API Gateway: max 29 seconds
- For async: consider dead letter queue
- Monitor timeout metrics

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 300
```

### Environment Variables

**Configuration:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --environment "Variables={
    DB_HOST=db.example.com,
    DB_PORT=5432,
    LOG_LEVEL=INFO
  }"
```

**Encryption:**
```bash
# Use AWS KMS for sensitive data
aws lambda update-function-configuration \
  --function-name my-function \
  --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/abcd-1234 \
  --environment "Variables={
    DB_PASSWORD=encrypted_value
  }"
```

**Access in Code:**
```python
import os
import boto3
import base64

# Plain text
db_host = os.environ['DB_HOST']

# Decrypt KMS-encrypted
def decrypt_env_var(encrypted_var):
    kms_client = boto3.client('kms')
    decrypted = kms_client.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_var)
    )
    return decrypted['Plaintext'].decode('utf-8')

db_password = decrypt_env_var(os.environ['DB_PASSWORD'])
```

**Best Practices:**
- Don't store secrets directly
- Use AWS Secrets Manager or Parameter Store
- Cache decrypted values outside handler

```python
import boto3
from functools import lru_cache

secretsmanager = boto3.client('secretsmanager')

@lru_cache(maxsize=1)
def get_secret(secret_name):
    response = secretsmanager.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

def lambda_handler(event, context):
    db_config = get_secret('prod/database')
    # Use db_config
```

### Tags

**Purposes:**
- Cost allocation
- Resource organization
- Access control
- Automation

```bash
aws lambda tag-resource \
  --resource arn:aws:lambda:us-east-1:123456789012:function:my-function \
  --tags Environment=production,Team=backend,CostCenter=engineering
```

### Ephemeral Storage

**Default**: 512MB in /tmp
**Maximum**: 10GB

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --ephemeral-storage Size=2048
```

**Use Cases:**
- Large file processing
- Caching
- Temporary data storage

**Considerations:**
- Persists across warm invocations
- Cleared on cold start
- Additional cost for >512MB

---

## IAM Roles and Permissions

### Execution Role

Every Lambda function requires an execution role with:
- Trust policy allowing Lambda to assume role
- Permissions to access AWS resources
- CloudWatch Logs permissions

**Basic Execution Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Managed Policies:**
```bash
# Basic execution (CloudWatch Logs)
AWSLambdaBasicExecutionRole

# VPC access
AWSLambdaVPCAccessExecutionRole

# DynamoDB streams
AWSLambdaDynamoDBExecutionRole

# Kinesis streams
AWSLambdaKinesisExecutionRole

# SQS
AWSLambdaSQSQueueExecutionRole
```

### Least Privilege Principle

**Bad (too permissive):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```

**Good (specific):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/uploads/*"
    }
  ]
}
```

### Common Permission Patterns

**S3 Access:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::my-bucket"
    }
  ]
}
```

**DynamoDB Access:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
    }
  ]
}
```

**Secrets Manager:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/*"
    }
  ]
}
```

**KMS Decryption:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abcd-1234"
    }
  ]
}
```

### Resource-Based Policies

Allow other services to invoke your function:

**API Gateway:**
```bash
aws lambda add-permission \
  --function-name my-function \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123456789012:abcd1234/*/*/*"
```

**S3:**
```bash
aws lambda add-permission \
  --function-name my-function \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::my-bucket \
  --source-account 123456789012
```

**EventBridge:**
```bash
aws lambda add-permission \
  --function-name my-function \
  --statement-id eventbridge-invoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:123456789012:rule/my-rule
```

---

## Event Sources and Triggers

### API Gateway

**REST API:**
```python
def lambda_handler(event, context):
    # Parse request
    http_method = event['httpMethod']
    path = event['path']
    query_params = event.get('queryStringParameters', {})
    headers = event['headers']
    body = json.loads(event['body']) if event.get('body') else {}

    # Process request
    if http_method == 'GET':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'message': 'GET request'})
        }
    elif http_method == 'POST':
        # Process POST
        return {
            'statusCode': 201,
            'body': json.dumps({'id': '123'})
        }
```

**HTTP API (v2):**
```python
def lambda_handler(event, context):
    # Simpler event structure
    http = event['requestContext']['http']
    method = http['method']
    path = http['path']

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Hello'})
    }
```

### S3 Events

**Event Structure:**
```python
def lambda_handler(event, context):
    for record in event['Records']:
        # S3 event
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        event_name = record['eventName']  # e.g., 'ObjectCreated:Put'

        print(f"Processing {bucket}/{key}")

        # Get object
        s3_client = boto3.client('s3')
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read()

        # Process content
```

**S3 Configuration:**
```bash
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:my-function",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [{
            "Name": "prefix",
            "Value": "uploads/"
          }, {
            "Name": "suffix",
            "Value": ".jpg"
          }]
        }
      }
    }]
  }'
```

### DynamoDB Streams

**Event Structure:**
```python
def lambda_handler(event, context):
    for record in event['Records']:
        event_name = record['eventName']  # INSERT, MODIFY, REMOVE

        if event_name == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            # Process new item
        elif event_name == 'MODIFY':
            old_image = record['dynamodb']['OldImage']
            new_image = record['dynamodb']['NewImage']
            # Process update
        elif event_name == 'REMOVE':
            old_image = record['dynamodb']['OldImage']
            # Process deletion
```

**Stream Configuration:**
```bash
# Enable stream
aws dynamodb update-table \
  --table-name MyTable \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name my-function \
  --event-source-arn arn:aws:dynamodb:us-east-1:123456789012:table/MyTable/stream/2024-01-01T00:00:00.000 \
  --starting-position LATEST \
  --batch-size 100
```

### SQS

**Event Structure:**
```python
def lambda_handler(event, context):
    for record in event['Records']:
        message_id = record['messageId']
        body = json.loads(record['body'])
        attributes = record['attributes']

        try:
            process_message(body)
            # Message automatically deleted on success
        except Exception as e:
            # Message returns to queue on failure
            print(f"Error processing message {message_id}: {e}")
            raise
```

**Queue Configuration:**
```bash
aws lambda create-event-source-mapping \
  --function-name my-function \
  --event-source-arn arn:aws:sqs:us-east-1:123456789012:my-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5
```

**Partial Batch Response:**
```python
def lambda_handler(event, context):
    batch_item_failures = []

    for record in event['Records']:
        try:
            process_message(record)
        except Exception as e:
            batch_item_failures.append({
                'itemIdentifier': record['messageId']
            })

    return {
        'batchItemFailures': batch_item_failures
    }
```

### Kinesis

**Event Structure:**
```python
import base64

def lambda_handler(event, context):
    for record in event['Records']:
        # Decode data
        payload = base64.b64decode(record['kinesis']['data'])
        data = json.loads(payload)

        # Process record
        process_data(data)
```

**Stream Configuration:**
```bash
aws lambda create-event-source-mapping \
  --function-name my-function \
  --event-source-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-stream \
  --starting-position LATEST \
  --batch-size 100 \
  --parallelization-factor 10
```

### EventBridge (CloudWatch Events)

**Scheduled Events:**
```bash
# Create rule
aws events put-rule \
  --name daily-backup \
  --schedule-expression "cron(0 2 * * ? *)"

# Add target
aws events put-targets \
  --rule daily-backup \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:123456789012:function:backup-function"
```

**Event Pattern:**
```bash
aws events put-rule \
  --name ec2-state-change \
  --event-pattern '{
    "source": ["aws.ec2"],
    "detail-type": ["EC2 Instance State-change Notification"],
    "detail": {
      "state": ["terminated"]
    }
  }'
```

**Handler:**
```python
def lambda_handler(event, context):
    # Scheduled event
    if 'source' in event and event['source'] == 'aws.events':
        if 'detail-type' in event:
            # Event pattern match
            detail = event['detail']
            # Process event
        else:
            # Scheduled event
            pass
```

### SNS

**Event Structure:**
```python
def lambda_handler(event, context):
    for record in event['Records']:
        message = record['Sns']['Message']
        subject = record['Sns']['Subject']
        topic_arn = record['Sns']['TopicArn']

        # Process notification
        process_notification(message)
```

### Application Load Balancer

**Event Structure:**
```python
def lambda_handler(event, context):
    # ALB request
    http_method = event['requestContext']['elb']['method']
    path = event['path']
    headers = event['headers']
    body = event['body']
    is_base64 = event['isBase64Encoded']

    if is_base64:
        body = base64.b64decode(body)

    # Multi-value headers
    if 'multiValueHeaders' in event:
        cookies = event['multiValueHeaders'].get('cookie', [])

    return {
        'statusCode': 200,
        'statusDescription': '200 OK',
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': '<html><body>Hello</body></html>'
    }
```

---

## VPC Configuration

### When to Use VPC

**Use VPC when:**
- Accessing RDS databases
- Accessing ElastiCache
- Connecting to private resources
- Network isolation required

**Don't use VPC when:**
- Accessing public AWS services (S3, DynamoDB)
- Internet-only APIs
- Performance is critical (cold starts increase)

### VPC Architecture

```
┌─────────────────────────────────────────────┐
│                   VPC                       │
│  ┌──────────────────────────────────────┐  │
│  │      Private Subnet (AZ-A)           │  │
│  │  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Lambda    │  │    RDS     │     │  │
│  │  │   ENI      │──│  Primary   │     │  │
│  │  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │      Private Subnet (AZ-B)           │  │
│  │  ┌────────────┐  ┌────────────┐     │  │
│  │  │  Lambda    │  │    RDS     │     │  │
│  │  │   ENI      │──│  Standby   │     │  │
│  │  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │      Public Subnet                   │  │
│  │  ┌────────────┐                      │  │
│  │  │    NAT     │────────► Internet    │  │
│  │  │  Gateway   │                      │  │
│  │  └────────────┘                      │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Configuration

```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --vpc-config SubnetIds=subnet-1234,subnet-5678,SecurityGroupIds=sg-1234
```

**Terraform:**
```hcl
resource "aws_lambda_function" "example" {
  function_name = "my-function"

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }
}

resource "aws_security_group" "lambda" {
  name        = "lambda-sg"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name   = "rds-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }
}
```

### Internet Access

Lambda in VPC has no internet access by default.

**Options:**

**1. NAT Gateway (recommended):**
```hcl
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}
```

**2. VPC Endpoints (for AWS services):**
```hcl
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.s3"

  route_table_ids = [aws_route_table.private.id]
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.us-east-1.dynamodb"

  route_table_ids = [aws_route_table.private.id]
}
```

### Best Practices

**1. Use multiple subnets in different AZs:**
- Ensures high availability
- Spreads ENIs across AZs

**2. Minimize ENI cold start penalty:**
- Use Hyperplane ENIs (automatic for new functions)
- Reduces cold start from 10-30s to <1s

**3. Security group rules:**
- Outbound: Allow necessary ports only
- Inbound: Usually not needed for Lambda

**4. Monitor ENI usage:**
```bash
# Check ENI count
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=AWS Lambda VPC ENI*" \
  --query 'NetworkInterfaces[].NetworkInterfaceId' \
  --output table
```

---

## Deployment Methods

### 1. AWS CLI

**Zip Deployment:**
```bash
# Create deployment package
zip -r function.zip lambda_function.py requirements.txt

# Create function
aws lambda create-function \
  --function-name my-function \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 512

# Update code
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip

# Update configuration
aws lambda update-function-configuration \
  --function-name my-function \
  --timeout 60 \
  --environment "Variables={KEY=VALUE}"
```

**With Layers:**
```bash
# Create layer
mkdir -p layer/python
pip install -r requirements.txt -t layer/python
cd layer
zip -r ../layer.zip .
cd ..

# Publish layer
aws lambda publish-layer-version \
  --layer-name my-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12

# Add layer to function
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:my-dependencies:1
```

### 2. AWS SAM (Serverless Application Model)

**template.yaml:**
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 30
    MemorySize: 512
    Runtime: python3.12
    Tracing: Active
    Environment:
      Variables:
        LOG_LEVEL: INFO

Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: my-function
      CodeUri: src/
      Handler: app.lambda_handler
      Policies:
        - S3ReadPolicy:
            BucketName: my-bucket
        - DynamoDBCrudPolicy:
            TableName: !Ref MyTable
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /items
            Method: GET

  MyTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: my-table
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH

Outputs:
  ApiUrl:
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/items"
```

**Commands:**
```bash
# Validate template
sam validate

# Build
sam build

# Deploy (guided)
sam deploy --guided

# Deploy
sam deploy --stack-name my-stack

# Local testing
sam local invoke MyFunction -e events/event.json
sam local start-api

# Tail logs
sam logs -n MyFunction --tail

# Delete
sam delete
```

### 3. Serverless Framework

**serverless.yml:**
```yaml
service: my-service

provider:
  name: aws
  runtime: python3.12
  region: us-east-1
  stage: ${opt:stage, 'dev'}
  memorySize: 512
  timeout: 30

  environment:
    STAGE: ${self:provider.stage}
    TABLE_NAME: ${self:custom.tableName}

  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:GetItem
            - dynamodb:PutItem
          Resource: !GetAtt MyTable.Arn

functions:
  api:
    handler: handler.main
    events:
      - http:
          path: /items
          method: GET
      - http:
          path: /items
          method: POST

  processor:
    handler: handler.process
    events:
      - sqs:
          arn: !GetAtt MyQueue.Arn
          batchSize: 10

resources:
  Resources:
    MyTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:custom.tableName}
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: id
            AttributeType: S
        KeySchema:
          - AttributeName: id
            KeyType: HASH

    MyQueue:
      Type: AWS::SQS::Queue
      Properties:
        QueueName: ${self:service}-${self:provider.stage}-queue

custom:
  tableName: ${self:service}-${self:provider.stage}-table

plugins:
  - serverless-python-requirements
```

**Commands:**
```bash
# Deploy
serverless deploy

# Deploy function only
serverless deploy function -f api

# Invoke
serverless invoke -f api

# Logs
serverless logs -f api --tail

# Remove
serverless remove
```

### 4. AWS CDK

**Python CDK:**
```python
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    Duration
)

class MyStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # DynamoDB table
        table = dynamodb.Table(
            self, "MyTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # Lambda function
        fn = lambda_.Function(
            self, "MyFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        # Grant permissions
        table.grant_read_write_data(fn)

        # API Gateway
        api = apigw.LambdaRestApi(
            self, "MyApi",
            handler=fn,
            proxy=False
        )

        items = api.root.add_resource("items")
        items.add_method("GET")
        items.add_method("POST")
```

**Commands:**
```bash
# Synthesize CloudFormation
cdk synth

# Deploy
cdk deploy

# Diff
cdk diff

# Destroy
cdk destroy
```

### 5. Terraform

**main.tf:**
```hcl
resource "aws_lambda_function" "main" {
  function_name = "my-function"
  role         = aws_iam_role.lambda.arn

  filename         = "function.zip"
  source_code_hash = filebase64sha256("function.zip")

  runtime = "python3.12"
  handler = "lambda_function.lambda_handler"

  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.main.name
    }
  }

  tracing_config {
    mode = "Active"
  }
}

resource "aws_iam_role" "lambda" {
  name = "lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_dynamodb_table" "main" {
  name         = "my-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
```

**Commands:**
```bash
terraform init
terraform plan
terraform apply
terraform destroy
```

### 6. Container Images

**Dockerfile:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY app.py ${LAMBDA_TASK_ROOT}

# Set handler
CMD ["app.lambda_handler"]
```

**Deploy:**
```bash
# Build
docker build -t my-lambda:latest .

# Create ECR repository
aws ecr create-repository --repository-name my-lambda

# Login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag
docker tag my-lambda:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest

# Push
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest

# Create/update function
aws lambda create-function \
  --function-name my-function \
  --package-type Image \
  --code ImageUri=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest \
  --role arn:aws:iam::123456789012:role/lambda-role
```

---

## Monitoring and Logging

### CloudWatch Logs

**Log Groups:**
- Automatically created: `/aws/lambda/function-name`
- Retention: Set manually (default: never expire)
- Permissions: Required in execution role

**Logging in Code:**
```python
import json

def lambda_handler(event, context):
    # Automatic logging to CloudWatch
    print("INFO: Processing event")
    print(json.dumps(event))  # Structured logging

    # Use logging module
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.info("Processing started")
    logger.error("Error occurred", exc_info=True)
```

**Structured Logging:**
```python
import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_event(level, message, **kwargs):
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,
        'message': message,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

def lambda_handler(event, context):
    log_event('INFO', 'Function invoked',
              request_id=context.aws_request_id,
              function_name=context.function_name)

    try:
        result = process_event(event)
        log_event('INFO', 'Processing complete',
                  result=result,
                  duration_ms=context.get_remaining_time_in_millis())
        return result
    except Exception as e:
        log_event('ERROR', 'Processing failed',
                  error=str(e),
                  error_type=type(e).__name__)
        raise
```

**Query Logs:**
```bash
# Tail logs
aws logs tail /aws/lambda/my-function --follow

# Filter logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/my-function \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# CloudWatch Insights query
aws logs start-query \
  --log-group-name /aws/lambda/my-function \
  --start-time $(date -u -d '1 day ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20'
```

### CloudWatch Metrics

**Default Metrics:**
- Invocations
- Errors
- Duration
- Throttles
- ConcurrentExecutions
- UnreservedConcurrentExecutions

**Custom Metrics:**
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    # Publish custom metric
    cloudwatch.put_metric_data(
        Namespace='MyApp',
        MetricData=[{
            'MetricName': 'ProcessedItems',
            'Value': len(event['Records']),
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'FunctionName', 'Value': context.function_name}
            ]
        }]
    )
```

**Embedded Metric Format (better):**
```python
import json

def lambda_handler(event, context):
    # EMF format
    metrics = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "MyApp",
                "Dimensions": [["FunctionName"]],
                "Metrics": [
                    {"Name": "ProcessedItems", "Unit": "Count"},
                    {"Name": "ProcessingTime", "Unit": "Milliseconds"}
                ]
            }]
        },
        "FunctionName": context.function_name,
        "ProcessedItems": len(event['Records']),
        "ProcessingTime": 123
    }

    print(json.dumps(metrics))  # Automatically parsed by CloudWatch
```

### AWS X-Ray

**Enable Tracing:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --tracing-config Mode=Active
```

**Add to Code:**
```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch all supported libraries
patch_all()

@xray_recorder.capture('process_event')
def process_event(event):
    # Automatic tracing
    result = expensive_operation()
    return result

def lambda_handler(event, context):
    # Add annotations (indexed, searchable)
    xray_recorder.put_annotation('user_id', event.get('user_id'))
    xray_recorder.put_annotation('environment', os.environ['STAGE'])

    # Add metadata (not indexed)
    xray_recorder.put_metadata('event', event)

    # Subsegments for custom tracing
    with xray_recorder.capture('database_query'):
        result = query_database()

    return result
```

**Query Traces:**
```bash
# Get trace summaries
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --filter-expression 'service("my-function")'

# Get specific trace
aws xray batch-get-traces \
  --trace-ids 1-5e8c7c1e-38ec5d29e4c891c9
```

### CloudWatch Alarms

**High Error Rate:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-high-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts
```

**High Duration:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-slow-execution \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 2
```

### Lambda Insights

Enhanced monitoring with additional metrics:

**Enable:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:14
```

**Additional Metrics:**
- CPU usage
- Memory utilization
- Network I/O
- Disk I/O
- Init duration

---

## Performance Optimization

### Cold Start Optimization

**What Causes Cold Starts:**
- New execution environment creation
- Runtime initialization
- Code initialization (outside handler)
- VPC ENI attachment (older functions)

**Measurement:**
```python
import time

# Track initialization time
init_start = time.time()
# Initialization code here
init_end = time.time()

def lambda_handler(event, context):
    handler_start = time.time()

    # Handler code

    handler_end = time.time()

    print(f"Init duration: {(init_end - init_start) * 1000}ms")
    print(f"Handler duration: {(handler_end - handler_start) * 1000}ms")
```

**Optimization Strategies:**

**1. Minimize Package Size:**
```bash
# Remove unnecessary files
pip install --target ./package boto3  # Already in Lambda runtime
zip -r function.zip . -x "*.pyc" -x "__pycache__/*"

# Use layers for dependencies
# Main function zip: 1MB vs 50MB with dependencies
```

**2. Choose Efficient Runtime:**
- Python, Node.js: Fast cold starts (~100-300ms)
- Java, .NET: Slower cold starts (1-3s)
- Go, Rust (custom runtime): Fastest (~50-100ms)

**3. Optimize Initialization:**
```python
# BAD - heavy initialization in global scope
import pandas as pd
import tensorflow as tf

model = tf.keras.models.load_model('large_model.h5')  # Slow cold start

def lambda_handler(event, context):
    # Handler code
    pass

# GOOD - lazy initialization
import json

model = None

def get_model():
    global model
    if model is None:
        import tensorflow as tf
        model = tf.keras.models.load_model('large_model.h5')
    return model

def lambda_handler(event, context):
    if event.get('use_model'):
        m = get_model()
        # Use model
    else:
        # Fast path without model loading
        pass
```

**4. Use Provisioned Concurrency:**
```bash
# Publish version
VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --query 'Version' --output text)

# Create alias
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version $VERSION

# Set provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 5
```

**5. SnapStart (Java only):**
```bash
aws lambda update-function-configuration \
  --function-name my-java-function \
  --snap-start ApplyOn=PublishedVersions
```

**6. Keep Functions Warm:**
```python
# EventBridge scheduled rule (every 5 minutes)
# Keeps 1-2 instances warm
# Trade-off: Small cost vs better latency
```

### Memory Tuning

**Impact of Memory:**
- More memory = More CPU
- Faster execution may reduce cost
- Use Lambda Power Tuning tool

**Testing Script:**
```python
import time
import json

def lambda_handler(event, context):
    # CPU-intensive task
    start = time.time()

    result = 0
    for i in range(10000000):
        result += i * i

    duration_ms = (time.time() - start) * 1000
    memory_mb = context.memory_limit_in_mb

    # Cost calculation
    gb_seconds = (memory_mb / 1024) * (duration_ms / 1000)
    cost = gb_seconds * 0.0000166667

    return {
        'memory': memory_mb,
        'duration_ms': duration_ms,
        'cost': cost,
        'cost_per_1M_invocations': cost * 1000000
    }
```

**Results Analysis:**
```
Memory   Duration   Cost/invocation   Cost/1M invocations
128MB    1000ms     $0.000002083     $2.08
256MB    500ms      $0.000002083     $2.08
512MB    250ms      $0.000002083     $2.08   <- Sweet spot
1024MB   125ms      $0.000002083     $2.08
2048MB   125ms      $0.000004167     $4.17   <- No improvement
```

### Connection Pooling

**Database Connections:**
```python
import psycopg2
from functools import lru_cache

# Connection pool outside handler
connection_pool = None

def get_connection():
    global connection_pool
    if connection_pool is None:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 5,  # Min/max connections
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
    return connection_pool.getconn()

def lambda_handler(event, context):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        results = cursor.fetchall()
        return {'count': len(results)}
    finally:
        connection_pool.putconn(conn)
```

**RDS Proxy (recommended):**
```python
# No connection pooling needed
import pymysql

def lambda_handler(event, context):
    # RDS Proxy handles connection pooling
    conn = pymysql.connect(
        host=os.environ['RDS_PROXY_ENDPOINT'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME']
    )
    # Use connection
    conn.close()
```

### Caching Strategies

**In-Memory Cache (across warm invocations):**
```python
from functools import lru_cache
import time

# Cache configuration data
@lru_cache(maxsize=1)
def get_config():
    # Cached for lifetime of execution environment
    print("Loading config...")
    import boto3
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name='/app/config')
    return json.loads(response['Parameter']['Value'])

# Cache with TTL
cache = {}
CACHE_TTL = 300  # 5 minutes

def get_data_with_ttl(key):
    now = time.time()
    if key in cache:
        data, timestamp = cache[key]
        if now - timestamp < CACHE_TTL:
            return data

    # Fetch new data
    data = fetch_from_dynamodb(key)
    cache[key] = (data, now)
    return data
```

**/tmp Storage:**
```python
import os
import json
import hashlib

CACHE_DIR = '/tmp/cache'

def cached_api_call(url):
    # Create cache key
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_path = f"{CACHE_DIR}/{cache_key}"

    # Check cache
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)

    # Fetch and cache
    response = requests.get(url)
    data = response.json()

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(data, f)

    return data
```

**ElastiCache/Redis:**
```python
import redis
import json

# Initialize outside handler
redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=os.environ['REDIS_HOST'],
            port=6379,
            decode_responses=True
        )
    return redis_client

def lambda_handler(event, context):
    cache = get_redis()
    key = f"user:{event['user_id']}"

    # Try cache first
    cached = cache.get(key)
    if cached:
        return json.loads(cached)

    # Fetch and cache
    data = fetch_user(event['user_id'])
    cache.setex(key, 3600, json.dumps(data))  # 1 hour TTL
    return data
```

### Async Processing

**Non-Blocking I/O:**
```python
import asyncio
import aiohttp
import aioboto3

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def process_parallel():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_url(session, f"https://api.example.com/item/{i}")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        return results

def lambda_handler(event, context):
    results = asyncio.run(process_parallel())
    return {'count': len(results)}
```

**Batch Operations:**
```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MyTable')

def lambda_handler(event, context):
    # Batch write (25 items max per batch)
    with table.batch_writer() as batch:
        for item in event['items']:
            batch.put_item(Item=item)

    # Batch get
    response = dynamodb.batch_get_item(
        RequestItems={
            'MyTable': {
                'Keys': [{'id': id} for id in event['ids']]
            }
        }
    )
    return response['Responses']['MyTable']
```

---

## Error Handling

### Exception Handling

**Basic Pattern:**
```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class BusinessError(Exception):
    """Recoverable business logic error"""
    pass

class SystemError(Exception):
    """Unrecoverable system error"""
    pass

def lambda_handler(event, context):
    try:
        result = process_event(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except BusinessError as e:
        # Recoverable - return error to client
        logger.warning(f"Business error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
    except SystemError as e:
        # Unrecoverable - fail and retry
        logger.error(f"System error: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        # Unexpected - log and fail
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

### Retry Behavior

**Synchronous Invocation:**
- No automatic retries
- Client responsible for retries

**Asynchronous Invocation:**
- 2 automatic retries
- Exponential backoff
- Configurable retry settings

```bash
aws lambda put-function-event-invoke-config \
  --function-name my-function \
  --maximum-retry-attempts 1 \
  --maximum-event-age-in-seconds 3600
```

**Event Source Mapping (SQS, Kinesis, DynamoDB):**
```bash
aws lambda update-event-source-mapping \
  --uuid <mapping-uuid> \
  --maximum-retry-attempts 3 \
  --maximum-record-age-in-seconds 604800 \
  --bisect-batch-on-function-error \
  --parallelization-factor 10
```

### Dead Letter Queues

**Configure DLQ:**
```bash
# Create DLQ
aws sqs create-queue --queue-name lambda-dlq

# Add to function
aws lambda update-function-configuration \
  --function-name my-function \
  --dead-letter-config TargetArn=arn:aws:sqs:us-east-1:123456789012:lambda-dlq
```

**Process DLQ:**
```python
def dlq_handler(event, context):
    """Process failed events from DLQ"""
    for record in event['Records']:
        body = json.loads(record['body'])

        # Determine failure reason
        if 'errorMessage' in body:
            error = body['errorMessage']
            # Log to monitoring system
            send_to_monitoring(error)

        # Attempt reprocessing or manual intervention
```

### Destinations

**On Success and Failure:**
```bash
aws lambda put-function-event-invoke-config \
  --function-name my-function \
  --destination-config '{
    "OnSuccess": {
      "Destination": "arn:aws:sns:us-east-1:123456789012:success-topic"
    },
    "OnFailure": {
      "Destination": "arn:aws:sqs:us-east-1:123456789012:failure-queue"
    }
  }'
```

**In Code:**
```python
def lambda_handler(event, context):
    try:
        result = process_event(event)
        # On success, result sent to OnSuccess destination
        return {'status': 'success', 'data': result}
    except Exception as e:
        # On failure, error sent to OnFailure destination
        raise
```

### Idempotency

**Ensure operations are safe to retry:**

```python
import hashlib
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('IdempotencyTable')

def get_idempotency_key(event):
    """Generate deterministic key from event"""
    event_str = json.dumps(event, sort_keys=True)
    return hashlib.sha256(event_str.encode()).hexdigest()

def lambda_handler(event, context):
    idempotency_key = get_idempotency_key(event)

    # Check if already processed
    try:
        response = table.get_item(Key={'id': idempotency_key})
        if 'Item' in response:
            # Already processed
            return response['Item']['result']
    except Exception as e:
        logger.error(f"Idempotency check failed: {e}")

    # Process event
    try:
        result = process_event(event)

        # Store result
        table.put_item(Item={
            'id': idempotency_key,
            'result': result,
            'timestamp': int(time.time()),
            'ttl': int(time.time()) + 86400  # 24 hours
        })

        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
```

**Using Powertools:**
```python
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    idempotent
)

persistence_layer = DynamoDBPersistenceLayer(table_name='IdempotencyTable')

@idempotent(persistence_store=persistence_layer)
def lambda_handler(event, context):
    # Automatically handles idempotency
    return process_event(event)
```

---

## Testing Strategies

### Unit Testing

**Test Handler:**
```python
# lambda_function.py
def process_order(order_data):
    if not order_data.get('items'):
        raise ValueError("Order must have items")

    total = sum(item['price'] * item['quantity']
                for item in order_data['items'])

    return {
        'order_id': order_data['id'],
        'total': total,
        'status': 'confirmed'
    }

def lambda_handler(event, context):
    try:
        result = process_order(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except ValueError as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }

# test_lambda_function.py
import pytest
from lambda_function import lambda_handler, process_order

def test_process_order_success():
    order = {
        'id': '123',
        'items': [
            {'name': 'Item 1', 'price': 10.0, 'quantity': 2},
            {'name': 'Item 2', 'price': 5.0, 'quantity': 1}
        ]
    }

    result = process_order(order)

    assert result['order_id'] == '123'
    assert result['total'] == 25.0
    assert result['status'] == 'confirmed'

def test_process_order_no_items():
    order = {'id': '123', 'items': []}

    with pytest.raises(ValueError):
        process_order(order)

def test_lambda_handler_success():
    event = {
        'id': '123',
        'items': [{'name': 'Item', 'price': 10.0, 'quantity': 1}]
    }

    class Context:
        aws_request_id = 'test-id'

    response = lambda_handler(event, Context())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['total'] == 10.0

def test_lambda_handler_validation_error():
    event = {'id': '123', 'items': []}

    class Context:
        aws_request_id = 'test-id'

    response = lambda_handler(event, Context())

    assert response['statusCode'] == 400
```

**Run Tests:**
```bash
pytest test_lambda_function.py -v
pytest test_lambda_function.py --cov=lambda_function --cov-report=html
```

### Integration Testing

**With AWS Services (LocalStack):**
```python
# test_integration.py
import boto3
import pytest
from moto import mock_dynamodb, mock_s3

@mock_dynamodb
def test_lambda_with_dynamodb():
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='TestTable',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )

    # Test Lambda function
    event = {'id': '123', 'name': 'Test'}
    result = lambda_handler(event, None)

    # Verify DynamoDB write
    response = table.get_item(Key={'id': '123'})
    assert 'Item' in response
    assert response['Item']['name'] == 'Test'

@mock_s3
def test_lambda_with_s3():
    # Create mock S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')

    # Test S3 trigger
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'test.txt'}
            }
        }]
    }

    s3.put_object(Bucket='test-bucket', Key='test.txt', Body=b'test content')

    result = lambda_handler(event, None)
    assert result['status'] == 'success'
```

### Local Testing

**SAM Local:**
```bash
# Invoke with event
sam local invoke MyFunction -e events/event.json

# Start API locally
sam local start-api

# Start Lambda endpoint
sam local start-lambda

# Invoke via AWS CLI
aws lambda invoke --function-name MyFunction \
  --endpoint-url http://127.0.0.1:3001 \
  --payload '{"key":"value"}' \
  response.json
```

**Docker:**
```bash
# Build image
docker build -t my-lambda .

# Run locally
docker run -p 9000:8080 my-lambda

# Invoke
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"key":"value"}'
```

### Load Testing

**Artillery:**
```yaml
# load-test.yml
config:
  target: "https://api.example.com"
  phases:
    - duration: 60
      arrivalRate: 10
      rampTo: 50
  processor: "./processor.js"

scenarios:
  - name: "API Load Test"
    flow:
      - post:
          url: "/items"
          json:
            name: "Test Item"
            price: 10.99
```

```bash
artillery run load-test.yml
```

**Custom Load Test:**
```python
import boto3
import concurrent.futures
import time
import json

lambda_client = boto3.client('lambda')

def invoke_lambda():
    start = time.time()
    try:
        response = lambda_client.invoke(
            FunctionName='my-function',
            Payload=json.dumps({'test': 'data'})
        )
        duration = time.time() - start
        status_code = response['StatusCode']
        return {'success': status_code == 200, 'duration': duration}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def load_test(concurrency, duration_seconds):
    results = []
    end_time = time.time() + duration_seconds

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        while time.time() < end_time:
            futures = [executor.submit(invoke_lambda) for _ in range(concurrency)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

    # Analyze results
    successful = sum(1 for r in results if r.get('success'))
    failed = len(results) - successful
    avg_duration = sum(r.get('duration', 0) for r in results) / len(results)

    print(f"Total requests: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Average duration: {avg_duration:.3f}s")

if __name__ == '__main__':
    load_test(concurrency=10, duration_seconds=60)
```

---

## Cost Optimization

### Understanding Pricing

**Components:**
1. **Requests**: $0.20 per 1M requests
2. **Duration**: $0.0000166667 per GB-second
3. **Provisioned Concurrency**: $0.0000041667 per GB-hour
4. **Ephemeral Storage**: $0.0000000309 per GB-second (>512MB)

**Example Calculation:**
```
Function: 512MB, 200ms average duration, 10M requests/month

Requests: 10M * $0.20/1M = $2.00
Duration: 10M * 0.2s * 0.5GB * $0.0000166667 = $16.67
Total: $18.67/month
```

### Optimization Strategies

**1. Right-Size Memory:**
```python
# Test different memory configurations
# Find sweet spot where cost/execution is minimized

# Use AWS Lambda Power Tuning
# https://github.com/alexcasalboni/aws-lambda-power-tuning
```

**2. Reduce Duration:**
- Optimize code
- Use efficient libraries
- Cache results
- Batch operations
- Use faster runtimes (Go, Rust)

**3. Minimize Cold Starts:**
- Small deployment packages
- Lazy initialization
- Provisioned concurrency (if cost-effective)

**4. Use Arm64:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --architectures arm64
```

Arm64 (Graviton2):
- 20% better price/performance
- Same code (for most runtimes)

**5. Optimize Free Tier:**
- 1M requests/month free
- 400,000 GB-seconds/month free
- Use for development/testing

**6. Clean Up:**
```bash
# Delete old versions
aws lambda list-versions-by-function \
  --function-name my-function \
  --query 'Versions[?Version!=`$LATEST`].Version' \
  --output text | xargs -I {} aws lambda delete-function \
  --function-name my-function --qualifier {}

# Delete old layers
aws lambda list-layer-versions --layer-name my-layer \
  --query 'LayerVersions[*].Version' --output text | \
  xargs -I {} aws lambda delete-layer-version \
  --layer-name my-layer --version-number {}
```

**7. Cost Monitoring:**
```python
# Tag functions for cost allocation
aws lambda tag-resource \
  --resource arn:aws:lambda:us-east-1:123456789012:function:my-function \
  --tags CostCenter=engineering,Environment=production

# Use AWS Cost Explorer
# Filter by tag, function, or region
```

### Cost Comparison

**Provisioned vs On-Demand:**

```
On-Demand:
- $0.20/1M requests
- $0.0000166667/GB-second
- Cold starts

Provisioned (for 512MB, 5 concurrent):
- $0.20/1M requests
- $0.0000166667/GB-second
- $0.0000041667/GB-hour * 24 * 30 * 0.5GB * 5 = $7.50/month
- No cold starts

Break-even: If cold starts cost >$7.50/month in user experience
```

---

## Production Best Practices

### Deployment Best Practices

**1. Use Versions and Aliases:**
```bash
# Publish version
VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --description "Release v1.2.3" \
  --query 'Version' --output text)

# Create/update alias
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version $VERSION

# Gradual deployment
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --routing-config AdditionalVersionWeights={"2"=0.1}  # 10% to v2
```

**2. Blue/Green Deployment:**
```bash
# Deploy new version to 'staging' alias
aws lambda update-alias \
  --function-name my-function \
  --name staging \
  --function-version 2

# Test staging

# Shift traffic gradually
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 2 \
  --routing-config AdditionalVersionWeights={"1"=0.5}  # 50/50

# Monitor metrics

# Complete shift
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 2
```

**3. Automated Testing:**
```yaml
# .github/workflows/deploy.yml
name: Deploy Lambda

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/ --cov

      - name: Deploy to staging
        run: |
          sam build
          sam deploy --config-env staging

      - name: Integration tests
        run: |
          pytest tests/integration/

      - name: Deploy to production
        run: |
          sam deploy --config-env production
```

**4. Configuration Management:**
```python
# Use Parameter Store or Secrets Manager
import boto3
import json

ssm = boto3.client('ssm')

def get_config(environment):
    response = ssm.get_parameters_by_path(
        Path=f'/app/{environment}/',
        Recursive=True,
        WithDecryption=True
    )

    config = {}
    for param in response['Parameters']:
        key = param['Name'].split('/')[-1]
        config[key] = param['Value']

    return config

# In Lambda
config = get_config(os.environ['ENVIRONMENT'])
```

### Security Best Practices

**1. Least Privilege IAM:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/specific-prefix/*"
    }
  ]
}
```

**2. Encrypt Environment Variables:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/abcd-1234
```

**3. Use Secrets Manager:**
```python
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

def lambda_handler(event, context):
    db_config = get_secret('prod/database')
    # Use credentials
```

**4. VPC Security:**
- Use security groups
- Limit egress traffic
- Use VPC endpoints for AWS services

**5. Code Signing:**
```bash
# Create signing profile
aws signer put-signing-profile \
  --profile-name lambda-signing-profile \
  --platform-id AWSLambda-SHA384-ECDSA

# Sign deployment package
aws signer start-signing-job \
  --source file://function.zip \
  --destination s3://bucket/signed/function.zip \
  --profile-name lambda-signing-profile

# Enforce code signing
aws lambda update-function-configuration \
  --function-name my-function \
  --code-signing-config-arn arn:aws:lambda:us-east-1:123456789012:code-signing-config:csc-1234
```

### Monitoring and Alerting

**Essential Alarms:**
```bash
# Error rate
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts

# Throttling
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-throttles \
  --metric-name Throttles \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 1

# Duration
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-duration \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 2

# Concurrent executions
aws cloudwatch put-metric-alarm \
  --alarm-name lambda-concurrency \
  --metric-name ConcurrentExecutions \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 60 \
  --threshold 800 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function \
  --evaluation-periods 1
```

### Disaster Recovery

**1. Cross-Region Backup:**
```bash
# Replicate to DR region
aws lambda get-function \
  --function-name my-function \
  --region us-east-1 \
  --query 'Code.Location' --output text | \
  xargs wget -O function.zip

aws lambda create-function \
  --function-name my-function \
  --region us-west-2 \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip
```

**2. Infrastructure as Code:**
- Version control all infrastructure
- Automate deployments
- Test disaster recovery procedures

**3. Multi-Region Active-Active:**
```
Route53 (Latency-based routing)
        │
        ├─► us-east-1: Lambda + DynamoDB Global Table
        └─► us-west-2: Lambda + DynamoDB Global Table
```

---

## Advanced Patterns

### Lambda Layers

**Create Layer:**
```bash
# Create layer structure
mkdir -p layer/python
pip install requests -t layer/python/

# Package layer
cd layer
zip -r ../layer.zip .
cd ..

# Publish layer
aws lambda publish-layer-version \
  --layer-name common-dependencies \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.12 python3.11 \
  --compatible-architectures x86_64 arm64
```

**Use Layer:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:common-dependencies:1
```

**Benefits:**
- Reduce deployment package size
- Share code across functions
- Separate dependencies from code

### Lambda Extensions

**Create Extension:**
```bash
#!/bin/bash
# extensions/my-extension

set -euo pipefail

echo "[$(date)] Extension initialized"

# Register extension
RESPONSE=$(curl -sS -X POST \
  "http://${AWS_LAMBDA_RUNTIME_API}/2020-01-01/extension/register" \
  -H "Lambda-Extension-Name: ${LAMBDA_EXTENSION_NAME}" \
  -d '{"events":["INVOKE","SHUTDOWN"]}')

EXTENSION_ID=$(echo $RESPONSE | jq -r '.identifier')

# Event loop
while true; do
  EVENT=$(curl -sS -X GET \
    "http://${AWS_LAMBDA_RUNTIME_API}/2020-01-01/extension/event/next" \
    -H "Lambda-Extension-Identifier: ${EXTENSION_ID}")

  EVENT_TYPE=$(echo $EVENT | jq -r '.eventType')

  if [ "$EVENT_TYPE" = "SHUTDOWN" ]; then
    echo "[$(date)] Extension shutting down"
    exit 0
  fi

  echo "[$(date)] Processing event: $EVENT_TYPE"
done
```

**Use Cases:**
- Log processing
- Metrics collection
- Security scanning
- Caching

### Step Functions Integration

**State Machine:**
```json
{
  "Comment": "Order processing workflow",
  "StartAt": "ValidateOrder",
  "States": {
    "ValidateOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:validate-order",
      "Next": "ProcessPayment",
      "Catch": [{
        "ErrorEquals": ["ValidationError"],
        "Next": "OrderFailed"
      }]
    },
    "ProcessPayment": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-payment",
      "Next": "ShipOrder",
      "Retry": [{
        "ErrorEquals": ["PaymentServiceError"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2
      }]
    },
    "ShipOrder": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ship-order",
      "Next": "OrderComplete"
    },
    "OrderComplete": {
      "Type": "Succeed"
    },
    "OrderFailed": {
      "Type": "Fail",
      "Error": "OrderProcessingFailed",
      "Cause": "Order validation or payment failed"
    }
  }
}
```

### Lambda@Edge / CloudFront Functions

**Use Cases:**
- Request/response manipulation
- Authentication
- A/B testing
- Redirects

**CloudFront Function (simpler, faster):**
```javascript
function handler(event) {
    var request = event.request;
    var headers = request.headers;

    // Add security headers
    var response = {
        statusCode: 200,
        statusDescription: 'OK',
        headers: {
            'strict-transport-security': { value: 'max-age=31536000' },
            'x-content-type-options': { value: 'nosniff' },
            'x-frame-options': { value: 'DENY' }
        }
    };

    return response;
}
```

**Lambda@Edge (more powerful):**
```python
import json

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']

    # Authentication
    auth_header = headers.get('authorization', [{}])[0].get('value', '')
    if not validate_token(auth_header):
        return {
            'status': '401',
            'statusDescription': 'Unauthorized'
        }

    # A/B testing
    if 'cookie' in headers:
        if 'variant=B' in headers['cookie'][0]['value']:
            request['uri'] = '/variant-b' + request['uri']

    return request
```

### Async/Event-Driven Patterns

**Fan-Out:**
```python
# Producer Lambda
import boto3
import json

sns = boto3.client('sns')

def lambda_handler(event, context):
    message = {
        'event_type': 'order_created',
        'order_id': event['order_id'],
        'customer_id': event['customer_id']
    }

    # Fan out to multiple consumers via SNS
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:123456789012:orders',
        Message=json.dumps(message)
    )
```

**Saga Pattern:**
```python
# Orchestrator Lambda
def lambda_handler(event, context):
    try:
        # Step 1: Reserve inventory
        reserve_result = invoke_lambda('reserve-inventory', event)

        # Step 2: Charge payment
        payment_result = invoke_lambda('charge-payment', {
            **event,
            'reservation_id': reserve_result['id']
        })

        # Step 3: Ship order
        ship_result = invoke_lambda('ship-order', {
            **event,
            'payment_id': payment_result['id']
        })

        return {'status': 'success', 'order_id': ship_result['order_id']}

    except Exception as e:
        # Compensating transactions
        if 'payment_result' in locals():
            invoke_lambda('refund-payment', payment_result)
        if 'reserve_result' in locals():
            invoke_lambda('release-inventory', reserve_result)

        raise
```

---

## Summary

This reference covers:
- Lambda fundamentals and execution model
- All supported runtimes and configuration options
- IAM roles and security best practices
- Event sources and triggers
- VPC configuration and networking
- Multiple deployment methods (CLI, SAM, Serverless, CDK, Terraform)
- Comprehensive monitoring and logging
- Performance optimization techniques
- Error handling and retry strategies
- Testing at all levels
- Cost optimization
- Production best practices
- Advanced patterns and integrations

For hands-on examples, see the `examples/` directory.
For deployment scripts, see the `scripts/` directory.
