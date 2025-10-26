---
name: modal-web-endpoints
description: Creating HTTP APIs on Modal
---



# Modal Web Endpoints

**Use this skill when:**
- Creating HTTP APIs on Modal
- Building REST endpoints for ML models
- Integrating FastAPI with Modal functions
- Serving web applications from Modal
- Creating webhooks and API integrations

## Basic Web Endpoints

### Simple HTTP Endpoint

Create HTTP endpoints with `@app.function()`

```python
import modal

app = modal.App("web-app")

@app.function()
@modal.web_endpoint()
def hello():
    return "Hello, World!"

# Access at: https://<username>--web-app-hello.modal.run
```

### With Path Parameters

Handle URL parameters:

```python
@app.function()
@modal.web_endpoint()
def greet(name: str):
    return f"Hello, {name}!"

# GET /greet?name=Alice
# Returns: "Hello, Alice!"
```

### Method-Specific Endpoints

Specify HTTP methods:

```python
@app.function()
@modal.web_endpoint(method="POST")
def create_item(item: dict):
    # Process item
    return {"id": 123, "status": "created"}

@app.function()
@modal.web_endpoint(method="GET")
def get_item(item_id: int):
    return {"id": item_id, "data": "..."}
```

## FastAPI Integration

### FastAPI App

Build full REST APIs with FastAPI:

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

web_app = FastAPI()

class PredictionRequest(BaseModel):
    text: str
    max_length: int = 100

class PredictionResponse(BaseModel):
    result: str
    confidence: float

@web_app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    # ML inference logic
    result = run_model(request.text, request.max_length)
    return PredictionResponse(
        result=result,
        confidence=0.95
    )

@web_app.get("/health")
def health():
    return {"status": "healthy"}

# Mount FastAPI app
@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app
```

### With GPU Model

Serve ML models via HTTP:

```python
from fastapi import FastAPI
from pydantic import BaseModel

web_app = FastAPI()

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7

class GenerateResponse(BaseModel):
    text: str
    tokens_generated: int

image = modal.Image.debian_slim().uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0",
    "fastapi==0.104.1"
)

@app.cls(gpu="l40s", image=image)
class ModelAPI:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print("Loading model...")
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.model = AutoModelForCausalLM.from_pretrained(
            "gpt2",
            torch_dtype=torch.float16,
            device_map="auto"
        )
        print("Model loaded")

    @modal.method()
    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> dict:
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True
            )

        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return {
            "text": text,
            "tokens_generated": len(outputs[0]) - len(inputs.input_ids[0])
        }

    @modal.asgi_app()
    def web(self):
        @web_app.post("/generate", response_model=GenerateResponse)
        def generate_endpoint(request: GenerateRequest):
            result = self.generate(
                request.prompt,
                request.max_tokens,
                request.temperature
            )
            return GenerateResponse(**result)

        @web_app.get("/health")
        def health():
            return {"status": "ready"}

        return web_app
```

## Request Handling

### JSON Requests

Handle JSON payloads:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List

web_app = FastAPI()

class BatchRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=100)
    model: str = "default"

@web_app.post("/batch")
def batch_process(request: BatchRequest):
    results = []

    for text in request.texts:
        result = process(text, model=request.model)
        results.append(result)

    return {"results": results, "count": len(results)}

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

### File Uploads

Accept file uploads:

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import io

web_app = FastAPI()

@web_app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    # Read file content
    contents = await file.read()

    # Process image
    result = process_image(contents)

    return JSONResponse({
        "filename": file.filename,
        "size": len(contents),
        "result": result
    })

@web_app.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    import pandas as pd

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    return {
        "rows": len(df),
        "columns": list(df.columns)
    }

@app.function(image=image_with_pandas)
@modal.asgi_app()
def api():
    return web_app
```

### Response Types

Return various response types:

```python
from fastapi import FastAPI
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
    FileResponse
)

web_app = FastAPI()

@web_app.get("/json")
def json_response():
    return {"status": "ok", "data": [1, 2, 3]}

@web_app.get("/text", response_class=PlainTextResponse)
def text_response():
    return "Plain text response"

@web_app.get("/stream")
def streaming_response():
    def generate():
        for i in range(100):
            yield f"Line {i}\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )

@web_app.get("/download")
def file_download():
    # Serve file from volume
    return FileResponse(
        "/data/report.pdf",
        filename="report.pdf",
        media_type="application/pdf"
    )

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## Authentication

### API Key Authentication

Implement API key auth:

```python
from fastapi import FastAPI, HTTPException, Header
from typing import Optional

web_app = FastAPI()

# Store in Modal secrets
VALID_API_KEYS = {"key123", "key456"}

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@web_app.post("/protected")
def protected_endpoint(
    data: dict,
    api_key: str = Depends(verify_api_key)
):
    return {"status": "authorized", "data": data}

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

### Bearer Token

Use bearer tokens:

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

web_app = FastAPI()
security = HTTPBearer()

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    # Validate token (check against database, JWT, etc.)
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    return token

@web_app.post("/inference")
def inference(
    request: dict,
    token: str = Depends(verify_token)
):
    return run_inference(request)

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## CORS Configuration

### Enable CORS

Allow cross-origin requests:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

web_app = FastAPI()

# Configure CORS
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],  # Specific origins
    # allow_origins=["*"],  # Allow all (development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@web_app.get("/data")
def get_data():
    return {"data": [1, 2, 3]}

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## Webhooks

### Receive Webhooks

Handle incoming webhooks:

```python
from fastapi import FastAPI, Request
import hmac
import hashlib

web_app = FastAPI()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)

@web_app.post("/webhook/github")
async def github_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload = await request.body()

    if not verify_signature(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    # Process webhook
    process_github_event(data)

    return {"status": "received"}

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## Error Handling

### Custom Error Responses

Handle errors gracefully:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

web_app = FastAPI()

class ModelError(Exception):
    def __init__(self, message: str):
        self.message = message

@web_app.exception_handler(ModelError)
async def model_error_handler(request: Request, exc: ModelError):
    return JSONResponse(
        status_code=500,
        content={"error": "Model error", "detail": exc.message}
    )

@web_app.post("/predict")
def predict(text: str):
    try:
        result = run_model(text)
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise ModelError(str(e))

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## Rate Limiting

### Simple Rate Limiting

Implement basic rate limiting:

```python
from fastapi import FastAPI, HTTPException, Request
from collections import defaultdict
from datetime import datetime, timedelta

web_app = FastAPI()

# In-memory rate limit tracker
request_counts = defaultdict(list)
RATE_LIMIT = 100  # requests per minute

def check_rate_limit(client_ip: str):
    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)

    # Clean old requests
    request_counts[client_ip] = [
        t for t in request_counts[client_ip]
        if t > minute_ago
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    request_counts[client_ip].append(now)

@web_app.post("/api/endpoint")
def endpoint(request: Request, data: dict):
    check_rate_limit(request.client.host)
    return process(data)

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

## Testing Web Endpoints

### Local Testing

Test endpoints locally:

```python
# test_api.py
from fastapi.testclient import TestClient

def test_endpoint():
    client = TestClient(web_app)

    response = client.post("/predict", json={"text": "test"})

    assert response.status_code == 200
    assert "result" in response.json()
```

## Anti-Patterns to Avoid

**DON'T load models on every request:**
```python
# ❌ BAD
@web_app.post("/predict")
def predict(text: str):
    model = load_model()  # Slow!
    return model(text)

# ✅ GOOD - Use class with @enter
@app.cls(gpu="l40s")
class API:
    @modal.enter()
    def load(self):
        self.model = load_model()

    @modal.asgi_app()
    def web(self):
        @web_app.post("/predict")
        def predict(text: str):
            return self.model(text)

        return web_app
```

**DON'T expose endpoints without authentication:**
```python
# ❌ BAD - No auth on expensive endpoint
@web_app.post("/expensive-operation")
def expensive(data: dict):
    return run_expensive_gpu_task(data)

# ✅ GOOD
@web_app.post("/expensive-operation")
def expensive(
    data: dict,
    token: str = Depends(verify_token)
):
    return run_expensive_gpu_task(data)
```

## Related Skills

- **modal-functions-basics.md** - Basic Modal patterns
- **modal-gpu-workloads.md** - Serving GPU models
- **modal-volumes-secrets.md** - Managing secrets for auth
- **modal-scheduling.md** - Background processing for webhooks
