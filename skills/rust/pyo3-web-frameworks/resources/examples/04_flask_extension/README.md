# Example 04: Flask Extension

Flask extension pattern with PyO3 for high-performance request/response processing.

## Features

- Response compression (gzip)
- Query string parsing
- Request hashing for caching
- Rate limiting
- Response timing

## Building

```bash
pip install maturin flask pytest
maturin develop
```

## Usage

```python
from flask import Flask, request, Response
import flask_extension

app = Flask(__name__)
limiter = flask_extension.RateLimiter(limit=100, window_seconds=60)

@app.before_request
def check_rate_limit():
    ip = request.remote_addr
    if not limiter.check_limit(ip):
        return Response("Rate limit exceeded", status=429)

@app.after_request
def compress_response(response):
    if response.status_code == 200:
        compressed = flask_extension.compress_response(
            response.get_data(),
            level=6
        )
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
    return response
```

## Next Steps

- **05_flask_middleware**: Advanced middleware patterns
