---
name: cloud-aws-api-gateway
description: AWS API Gateway REST APIs, HTTP APIs, WebSocket APIs, authorization, and integration patterns
---

# AWS API Gateway

**Scope**: API Gateway configuration - REST vs HTTP APIs, WebSocket, authorization, CORS, throttling, integrations
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building REST APIs with Lambda backend
- Creating HTTP APIs for lower latency and cost
- Implementing WebSocket APIs for real-time communication
- Configuring API authorization (IAM, Lambda, Cognito, API keys)
- Setting up CORS for cross-origin requests
- Implementing API throttling and usage plans
- Integrating with Lambda, HTTP endpoints, or AWS services
- Troubleshooting API Gateway request/response issues

## Core Concepts

### Concept 1: REST API vs HTTP API

**REST API**:
- Full-featured, more expensive ($3.50/million requests)
- API keys, usage plans, request validation
- Request/response transformations
- Caching support
- Use for: Complex authorization, legacy systems

**HTTP API**:
- Simpler, cheaper ($1.00/million requests)
- 60% lower latency than REST APIs
- JWT authorization built-in
- CORS configuration simplified
- Use for: Modern APIs, Lambda proxy integration

```bash
# Create HTTP API (recommended for new projects)
aws apigatewayv2 create-api \
  --name my-http-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:123456789012:function:my-function

# Create REST API (for advanced features)
aws apigateway create-rest-api \
  --name my-rest-api \
  --endpoint-configuration types=REGIONAL
```

### Concept 2: Lambda Proxy Integration

**Proxy integration**:
- Lambda receives full HTTP request as event
- Lambda returns HTTP response format
- No request/response mapping needed
- Simpler configuration

```python
# Lambda function for API Gateway proxy integration
import json

def lambda_handler(event, context):
    """
    Handle API Gateway proxy integration

    Event structure:
    {
      'httpMethod': 'GET',
      'path': '/users/123',
      'queryStringParameters': {'filter': 'active'},
      'headers': {'Content-Type': 'application/json'},
      'body': '{"name": "John"}',
      'pathParameters': {'id': '123'},
      'requestContext': {...}
    }
    """

    # Parse request
    method = event['httpMethod']
    path = event['path']
    body = json.loads(event.get('body', '{}'))

    # Route request
    if method == 'GET' and path.startswith('/users/'):
        user_id = event['pathParameters']['id']
        return get_user(user_id)
    elif method == 'POST' and path == '/users':
        return create_user(body)

    # Return 404 for unmatched routes
    return {
        'statusCode': 404,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': 'Not found'})
    }

def get_user(user_id):
    """Get user by ID"""
    # Your logic here
    user = {'id': user_id, 'name': 'John Doe'}

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(user)
    }
```

### Concept 3: WebSocket APIs

**WebSocket use cases**:
- Real-time chat applications
- Live dashboards and notifications
- Collaborative editing tools
- Gaming backends

```python
import boto3
import json

apigateway_management = None

def lambda_handler(event, context):
    """
    Handle WebSocket events

    Routes:
    - $connect: Client connects
    - $disconnect: Client disconnects
    - sendMessage: Custom route
    """

    route_key = event['requestContext']['routeKey']
    connection_id = event['requestContext']['connectionId']

    if route_key == '$connect':
        return handle_connect(connection_id)
    elif route_key == '$disconnect':
        return handle_disconnect(connection_id)
    elif route_key == 'sendMessage':
        return handle_message(event, connection_id)

    return {'statusCode': 400, 'body': 'Unknown route'}

def handle_connect(connection_id):
    """Store connection in DynamoDB"""
    table.put_item(Item={
        'connectionId': connection_id,
        'timestamp': datetime.utcnow().isoformat()
    })
    return {'statusCode': 200, 'body': 'Connected'}

def handle_message(event, connection_id):
    """Broadcast message to all connections"""
    global apigateway_management

    # Initialize API Gateway Management API client
    if not apigateway_management:
        endpoint_url = f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
        apigateway_management = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)

    # Parse message
    body = json.loads(event.get('body', '{}'))
    message = body.get('message', '')

    # Get all connections
    response = table.scan()
    connections = response['Items']

    # Send to all connections
    for conn in connections:
        try:
            apigateway_management.post_to_connection(
                ConnectionId=conn['connectionId'],
                Data=json.dumps({'message': message})
            )
        except apigateway_management.exceptions.GoneException:
            # Connection no longer exists
            table.delete_item(Key={'connectionId': conn['connectionId']})

    return {'statusCode': 200, 'body': 'Message sent'}
```

---

## Patterns

### Pattern 1: CORS Configuration

**When to use**: Frontend apps making cross-origin requests

```bash
# HTTP API - simple CORS configuration
aws apigatewayv2 update-api \
  --api-id abc123 \
  --cors-configuration AllowOrigins="https://example.com",AllowMethods="GET,POST,PUT,DELETE",AllowHeaders="Content-Type,Authorization"

# REST API - requires OPTIONS method and response headers
# Created via console or CloudFormation (more complex)
```

```python
# Lambda function with CORS headers
def lambda_handler(event, context):
    """Return CORS headers with all responses"""

    # Handle preflight request
    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://example.com',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Max-Age': '3600'
            },
            'body': ''
        }

    # Normal request with CORS headers
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'https://example.com'
        },
        'body': json.dumps({'message': 'Success'})
    }
```

### Pattern 2: Lambda Authorizer (Custom Authorization)

**Use case**: Custom authentication logic (API tokens, OAuth, etc.)

```python
def lambda_handler(event, context):
    """
    Lambda authorizer for API Gateway

    Event structure:
    {
      'type': 'REQUEST',
      'methodArn': 'arn:aws:execute-api:...',
      'headers': {'Authorization': 'Bearer token123'}
    }
    """

    # Extract token
    token = event['headers'].get('Authorization', '').replace('Bearer ', '')

    # Validate token
    user = validate_token(token)

    if not user:
        raise Exception('Unauthorized')  # Returns 401

    # Generate IAM policy
    return {
        'principalId': user['id'],
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }
            ]
        },
        'context': {
            'userId': user['id'],
            'email': user['email']
        }
    }

def validate_token(token):
    """Validate JWT or API token"""
    # Your validation logic
    if token == 'valid-token':
        return {'id': 'user123', 'email': 'user@example.com'}
    return None
```

```python
# Access authorizer context in Lambda function
def api_handler(event, context):
    """Lambda function receiving authorized request"""

    # Access authorizer context
    user_id = event['requestContext']['authorizer']['userId']
    email = event['requestContext']['authorizer']['email']

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Hello {email}',
            'userId': user_id
        })
    }
```

### Pattern 3: Cognito User Pool Authorization

**Use case**: User authentication with Cognito

```bash
# Create HTTP API with Cognito authorizer
aws apigatewayv2 create-authorizer \
  --api-id abc123 \
  --name cognito-auth \
  --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --jwt-configuration Audience=abc123,Issuer=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123

# Attach to route
aws apigatewayv2 update-route \
  --api-id abc123 \
  --route-id xyz789 \
  --authorization-type JWT \
  --authorizer-id auth123
```

```python
# Lambda function with Cognito authorization
def lambda_handler(event, context):
    """Access Cognito claims from request context"""

    # Cognito user claims available in request context
    claims = event['requestContext']['authorizer']['claims']

    user_id = claims['sub']
    email = claims['email']
    username = claims['cognito:username']

    return {
        'statusCode': 200,
        'body': json.dumps({
            'userId': user_id,
            'email': email,
            'username': username
        })
    }
```

### Pattern 4: Throttling and Usage Plans

**Use case**: Rate limiting, quotas, API monetization

```bash
# Create usage plan with throttling
aws apigateway create-usage-plan \
  --name basic-plan \
  --throttle burstLimit=100,rateLimit=50 \
  --quota limit=10000,period=MONTH

# Create API key
aws apigateway create-api-key \
  --name customer-key \
  --enabled

# Associate key with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id plan123 \
  --key-id key123 \
  --key-type API_KEY
```

```python
# Lambda function - API key available in request context
def lambda_handler(event, context):
    """Check API key usage"""

    # API key ID available if request includes x-api-key header
    api_key_id = event['requestContext'].get('identity', {}).get('apiKeyId')

    if api_key_id:
        print(f"Request from API key: {api_key_id}")

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Success'})
    }
```

### Pattern 5: Request Validation

**Use case**: Validate request schema before Lambda invocation

```json
// Request body JSON schema
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "email": {"type": "string", "format": "email"},
    "age": {"type": "integer", "minimum": 0}
  },
  "required": ["name", "email"]
}
```

```bash
# Create model
aws apigateway create-model \
  --rest-api-id abc123 \
  --name UserModel \
  --content-type application/json \
  --schema file://user-schema.json

# Create request validator
aws apigateway create-request-validator \
  --rest-api-id abc123 \
  --name body-validator \
  --validate-request-body
```

### Pattern 6: HTTP Endpoint Integration (No Lambda)

**Use case**: Proxy to existing HTTP backend

```bash
# Create HTTP API with HTTP proxy integration
aws apigatewayv2 create-integration \
  --api-id abc123 \
  --integration-type HTTP_PROXY \
  --integration-uri https://api.example.com/{proxy} \
  --integration-method ANY \
  --payload-format-version 1.0

# Create route
aws apigatewayv2 create-route \
  --api-id abc123 \
  --route-key 'ANY /api/{proxy+}' \
  --target integrations/integration123
```

**Benefits**:
- No Lambda invocation cost
- Direct proxy to backend
- API Gateway adds throttling, caching, authorization

---

## Quick Reference

### API Types Comparison

| Feature | HTTP API | REST API | WebSocket API |
|---------|----------|----------|---------------|
| **Price** | $1.00/M requests | $3.50/M requests | $1.00/M messages |
| **Latency** | Lower | Higher | N/A |
| **CORS** | Simple config | Manual setup | N/A |
| **Caching** | No | Yes | No |
| **Usage plans** | No | Yes | No |
| **Request validation** | No | Yes | No |
| **Best for** | Modern APIs | Complex APIs | Real-time |

### Authorization Methods

```
Method              | Use Case                          | Complexity
--------------------|-----------------------------------|------------
IAM                 | AWS service-to-service            | Medium
Lambda Authorizer   | Custom authentication logic       | High
Cognito             | User authentication (JWT)         | Medium
API Key             | Simple client identification      | Low
```

### Key Guidelines

```
✅ DO: Use HTTP API for new projects (lower cost, latency)
✅ DO: Use Lambda proxy integration (simpler than custom)
✅ DO: Configure CORS for cross-origin requests
✅ DO: Use Cognito for user authentication
✅ DO: Set throttling limits to protect backend
✅ DO: Enable CloudWatch logging for troubleshooting

❌ DON'T: Use REST API unless you need advanced features
❌ DON'T: Hardcode CORS origins (use environment variables)
❌ DON'T: Skip throttling (risk backend overload)
❌ DON'T: Return large responses (6 MB limit)
❌ DON'T: Use API keys for authentication (use Cognito/Lambda authorizer)
```

---

## Anti-Patterns

### Critical Violations

```python
# ❌ NEVER: Hardcode CORS origins in production
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'  # Allows any origin
        },
        'body': json.dumps({'data': 'sensitive'})
    }

# ✅ CORRECT: Use environment variable or whitelist
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',')

def lambda_handler(event, context):
    origin = event['headers'].get('origin', '')

    # Check origin
    if origin in ALLOWED_ORIGINS:
        cors_origin = origin
    else:
        cors_origin = ALLOWED_ORIGINS[0]  # Default

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': cors_origin
        },
        'body': json.dumps({'data': 'sensitive'})
    }
```

❌ **Allow-Origin: ***: Exposes APIs to any website, security risk for authenticated APIs

✅ **Correct approach**: Whitelist specific origins, validate origin header

### Common Mistakes

```python
# ❌ Don't skip error handling
def lambda_handler(event, context):
    user = get_user(event['pathParameters']['id'])  # May not exist
    return {'statusCode': 200, 'body': json.dumps(user)}

# ✅ Correct: Handle errors and return proper status codes
def lambda_handler(event, context):
    try:
        user_id = event.get('pathParameters', {}).get('id')

        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing user ID'})
            }

        user = get_user(user_id)

        if not user:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'User not found'})
            }

        return {
            'statusCode': 200,
            'body': json.dumps(user)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

❌ **Missing error handling**: Returns 200 even for errors, confuses clients

✅ **Better**: Return appropriate HTTP status codes (400, 404, 500)

---

## Related Skills

- `aws-lambda-functions.md` - Lambda function development for API Gateway backends
- `aws-iam-security.md` - IAM policies for API Gateway authorization
- `aws-networking.md` - CloudFront integration for API caching and global distribution
- `infrastructure/aws-serverless.md` - Complete serverless API architecture patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
