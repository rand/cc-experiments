---
name: protocols-http-fundamentals
description: HTTP/1.1 protocol fundamentals including methods, headers, status codes, and request/response cycle
---

# HTTP/1.1 Fundamentals

**Scope**: HTTP/1.1 protocol specification, methods, headers, status codes, connection model
**Lines**: ~380
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building HTTP APIs or web services
- Debugging HTTP communication issues
- Understanding request/response cycles
- Implementing HTTP clients or servers
- Troubleshooting caching or connection problems
- Designing RESTful APIs
- Working with HTTP headers and status codes
- Optimizing HTTP performance

## Core Concepts

### HTTP Request/Response Cycle

**Request Structure**:
```http
GET /api/users/123 HTTP/1.1
Host: api.example.com
User-Agent: Mozilla/5.0
Accept: application/json
Authorization: Bearer eyJhbGc...
Connection: keep-alive
```

**Response Structure**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 156
Cache-Control: max-age=3600
Connection: keep-alive

{"id": 123, "name": "Alice", "email": "alice@example.com"}
```

**Key Components**:
- **Request Line**: Method, URI, HTTP version
- **Headers**: Metadata about the request/response
- **Body**: Optional payload data
- **Status Line**: HTTP version, status code, reason phrase

### HTTP Methods

**Safe Methods** (read-only, no side effects):
```http
GET /api/users/123 HTTP/1.1
HEAD /api/users/123 HTTP/1.1
OPTIONS /api/users HTTP/1.1
```

**Idempotent Methods** (multiple identical requests = same result):
```http
PUT /api/users/123 HTTP/1.1
DELETE /api/users/123 HTTP/1.1
```

**Non-Idempotent Methods**:
```http
POST /api/users HTTP/1.1
PATCH /api/users/123 HTTP/1.1
```

**Method Semantics**:
- **GET**: Retrieve resource, no body, cacheable
- **POST**: Create resource, has body, not idempotent
- **PUT**: Replace resource, idempotent, create or update
- **PATCH**: Partial update, not necessarily idempotent
- **DELETE**: Remove resource, idempotent
- **HEAD**: Like GET but only returns headers
- **OPTIONS**: Query available methods
- **TRACE**: Echo request for debugging (rarely used)

### Status Codes

**1xx Informational**:
- `100 Continue` - Client should continue sending request body
- `101 Switching Protocols` - Used for WebSocket upgrade

**2xx Success**:
- `200 OK` - Request succeeded
- `201 Created` - Resource created (POST/PUT)
- `202 Accepted` - Request accepted but processing not complete
- `204 No Content` - Success but no response body
- `206 Partial Content` - Range request succeeded

**3xx Redirection**:
- `301 Moved Permanently` - Resource permanently moved
- `302 Found` - Temporary redirect (use 307 for preserving method)
- `304 Not Modified` - Cached version still valid
- `307 Temporary Redirect` - Preserves request method
- `308 Permanent Redirect` - Preserves request method

**4xx Client Errors**:
- `400 Bad Request` - Malformed request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Authenticated but not authorized
- `404 Not Found` - Resource doesn't exist
- `405 Method Not Allowed` - Method not supported for this resource
- `409 Conflict` - Request conflicts with current state
- `410 Gone` - Resource permanently deleted
- `429 Too Many Requests` - Rate limit exceeded

**5xx Server Errors**:
- `500 Internal Server Error` - Generic server error
- `502 Bad Gateway` - Invalid response from upstream server
- `503 Service Unavailable` - Server temporarily unavailable
- `504 Gateway Timeout` - Upstream server timeout

### Connection Management

**HTTP/1.0 - Close by Default**:
```http
GET /page1 HTTP/1.0
Host: example.com
Connection: keep-alive
```

**HTTP/1.1 - Keep-Alive by Default**:
```http
GET /page1 HTTP/1.1
Host: example.com
Connection: keep-alive
```

**Connection: close**:
```http
GET /page1 HTTP/1.1
Host: example.com
Connection: close
```

---

## Patterns

### Pattern 1: Content Negotiation

**Use Case**: Client specifies preferred content type

```http
# ❌ Bad: Ignoring client preferences
GET /api/users/123 HTTP/1.1
Host: api.example.com

Response:
Content-Type: application/xml
```

```http
# ✅ Good: Respecting Accept header
GET /api/users/123 HTTP/1.1
Host: api.example.com
Accept: application/json

Response:
Content-Type: application/json
```

**Benefits**:
- Client gets data in preferred format
- Single endpoint serves multiple formats
- Follows HTTP specification

### Pattern 2: Conditional Requests

**Use Case**: Efficient caching with validation

```http
# ❌ Bad: Always downloading full resource
GET /api/users/123 HTTP/1.1
Host: api.example.com
```

```http
# ✅ Good: Using ETags
GET /api/users/123 HTTP/1.1
Host: api.example.com
If-None-Match: "33a64df551425fcc55e4d42a148795d9f25f89d4"

Response if unchanged:
HTTP/1.1 304 Not Modified
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

**Benefits**:
- Reduces bandwidth
- Faster response times
- Server resources saved

### Pattern 3: Range Requests

**Use Case**: Resumable downloads, partial content

```http
# ✅ Request first 1000 bytes
GET /files/video.mp4 HTTP/1.1
Host: cdn.example.com
Range: bytes=0-999

Response:
HTTP/1.1 206 Partial Content
Content-Range: bytes 0-999/50000
Content-Length: 1000

[First 1000 bytes]
```

**Benefits**:
- Resume interrupted downloads
- Stream large files
- Reduce initial load time

### Pattern 4: CORS Headers

**Use Case**: Cross-origin resource sharing

```http
# Preflight request
OPTIONS /api/users HTTP/1.1
Host: api.example.com
Origin: https://webapp.example.com
Access-Control-Request-Method: POST

Response:
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://webapp.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

---

## Common HTTP Headers

### Request Headers

**Authentication & Authorization**:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Cookie: session_id=abc123; user_pref=dark_mode
```

**Content Negotiation**:
```http
Accept: application/json, text/plain
Accept-Language: en-US, en;q=0.9, es;q=0.8
Accept-Encoding: gzip, deflate, br
```

**Caching**:
```http
If-None-Match: "686897696a7c876b7e"
If-Modified-Since: Wed, 21 Oct 2015 07:28:00 GMT
Cache-Control: no-cache
```

**Client Info**:
```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Referer: https://previous-page.com
Host: api.example.com
```

### Response Headers

**Content Description**:
```http
Content-Type: application/json; charset=utf-8
Content-Length: 1234
Content-Encoding: gzip
Content-Language: en
```

**Caching**:
```http
Cache-Control: public, max-age=3600
ETag: "686897696a7c876b7e"
Expires: Wed, 21 Oct 2015 07:28:00 GMT
Last-Modified: Wed, 21 Oct 2015 06:28:00 GMT
```

**Security**:
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
```

---

## Implementation Examples

### Python HTTP Server (Flask)

```python
from flask import Flask, request, jsonify, make_response
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # Get user data (example)
    user = {"id": user_id, "name": "Alice", "email": "alice@example.com"}

    # Create response
    response = make_response(jsonify(user))

    # Set caching headers
    response.headers['Cache-Control'] = 'public, max-age=3600'
    response.headers['ETag'] = f'"{hash(str(user))}"'

    # Handle conditional request
    if request.headers.get('If-None-Match') == response.headers['ETag']:
        return '', 304

    return response

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()

    # Validate content type
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    # Create user (example)
    new_user = {"id": 456, **data}

    response = make_response(jsonify(new_user), 201)
    response.headers['Location'] = f'/api/users/{new_user["id"]}'

    return response

if __name__ == '__main__':
    app.run(port=8080)
```

### Go HTTP Client

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

func main() {
    // Create client with timeouts
    client := &http.Client{
        Timeout: 10 * time.Second,
    }

    // GET request with headers
    req, _ := http.NewRequest("GET", "https://api.example.com/users/123", nil)
    req.Header.Set("Accept", "application/json")
    req.Header.Set("Authorization", "Bearer token123")

    resp, err := client.Do(req)
    if err != nil {
        panic(err)
    }
    defer resp.Body.Close()

    // Check status
    if resp.StatusCode != http.StatusOK {
        fmt.Printf("Error: %d %s\n", resp.StatusCode, resp.Status)
        return
    }

    // Read body
    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("Response: %s\n", body)

    // POST request
    user := map[string]string{"name": "Bob", "email": "bob@example.com"}
    jsonData, _ := json.Marshal(user)

    postReq, _ := http.NewRequest("POST", "https://api.example.com/users", bytes.NewBuffer(jsonData))
    postReq.Header.Set("Content-Type", "application/json")

    postResp, _ := client.Do(postReq)
    defer postResp.Body.Close()

    fmt.Printf("Created: %d\n", postResp.StatusCode)
    fmt.Printf("Location: %s\n", postResp.Header.Get("Location"))
}
```

---

## Best Practices

### 1. Use Appropriate Methods

```http
# ❌ Bad: Using GET for state-changing operations
GET /api/users/123/delete HTTP/1.1

# ✅ Good: Using DELETE
DELETE /api/users/123 HTTP/1.1
```

### 2. Return Meaningful Status Codes

```python
# ❌ Bad: Always returning 200
@app.route('/api/users', methods=['POST'])
def create_user():
    if invalid_data:
        return jsonify({"error": "Invalid"}), 200  # Wrong!

# ✅ Good: Appropriate status codes
@app.route('/api/users', methods=['POST'])
def create_user():
    if invalid_data:
        return jsonify({"error": "Invalid email"}), 400

    user = create_user_in_db()
    return jsonify(user), 201
```

### 3. Set Proper Content-Type

```http
# ✅ Good: Explicit content type
POST /api/users HTTP/1.1
Content-Type: application/json; charset=utf-8

{"name": "Alice"}
```

### 4. Use Connection Keep-Alive

```python
# ✅ Good: Reuse connection
import requests

session = requests.Session()
for i in range(10):
    response = session.get(f'https://api.example.com/users/{i}')
    # Connection reused across requests
```

---

## Troubleshooting

### Issue 1: 400 Bad Request

**Symptoms**: Server rejects request
**Common Causes**:
- Missing required headers (Content-Type, Host)
- Malformed JSON in body
- Invalid URL encoding
- Request too large

**Solution**:
```bash
# Debug with curl verbose
curl -v https://api.example.com/users
```

### Issue 2: Connection Timeouts

**Symptoms**: Requests hang or timeout
**Common Causes**:
- No Connection: keep-alive
- Firewall blocking
- Server not responding

**Solution**:
```python
# Set explicit timeouts
response = requests.get(url, timeout=(3.0, 10.0))  # (connect, read)
```

---

## Related Skills

- `protocols-http2-multiplexing` - HTTP/2 improvements
- `protocols-http3-quic` - HTTP/3 and QUIC protocol
- `protocols-tcp-fundamentals` - Underlying TCP protocol
- `networking-tls-troubleshooting` - HTTPS debugging
- `api-rest-api-design` - RESTful API design patterns
- `proxies-cache-control` - HTTP caching strategies

---

**Last Updated**: 2025-10-27
