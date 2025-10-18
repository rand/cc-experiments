---
name: api-api-error-handling
description: Designing error responses for REST APIs
---



# API Error Handling

**Use this skill when:**
- Designing error responses for REST APIs
- Handling validation errors in API endpoints
- Implementing consistent error formatting
- Building user-friendly error messages
- Setting up error logging and correlation
- Choosing appropriate HTTP status codes

## Error Response Structure

### Standard Error Format

Design a consistent error response structure:

```typescript
interface ErrorResponse {
  code: string;              // Machine-readable error code
  message: string;           // Human-readable message
  details?: ErrorDetail[];   // Additional context
  trace_id?: string;         // Request correlation ID
  timestamp: string;         // ISO 8601 timestamp
}

interface ErrorDetail {
  field?: string;            // Field name for validation errors
  message: string;           // Specific error message
  code?: string;             // Field-specific error code
}

// Example response
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format",
      "code": "INVALID_FORMAT"
    },
    {
      "field": "age",
      "message": "Must be at least 18",
      "code": "MIN_VALUE"
    }
  ],
  "trace_id": "a1b2c3d4-e5f6-7890",
  "timestamp": "2025-10-18T10:30:00Z"
}
```

### Python/FastAPI Implementation

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from datetime import datetime
import uuid

app = FastAPI()

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    trace_id: str
    timestamp: str

    @classmethod
    def create(
        cls,
        code: str,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        trace_id: Optional[str] = None
    ):
        return cls(
            code=code,
            message=message,
            details=details,
            trace_id=trace_id or str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        details.append(ErrorDetail(
            field=field,
            message=error["msg"],
            code=error["type"].upper()
        ))

    error_response = ErrorResponse.create(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_response = ErrorResponse.create(
        code=get_error_code_for_status(exc.status_code),
        message=exc.detail
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

def get_error_code_for_status(status: int) -> str:
    """Map HTTP status to error code"""
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    return codes.get(status, "UNKNOWN_ERROR")
```

## HTTP Status Code Selection

### Common Status Codes

Choose appropriate status codes for different errors:

```python
from enum import IntEnum

class HTTPStatus(IntEnum):
    # 2xx Success
    OK = 200                    # Request succeeded
    CREATED = 201               # Resource created
    NO_CONTENT = 204           # Success, no response body

    # 4xx Client Errors
    BAD_REQUEST = 400          # Invalid request format
    UNAUTHORIZED = 401         # Missing/invalid authentication
    FORBIDDEN = 403            # Authenticated but no permission
    NOT_FOUND = 404            # Resource doesn't exist
    METHOD_NOT_ALLOWED = 405   # HTTP method not supported
    CONFLICT = 409             # Resource state conflict
    GONE = 410                 # Resource permanently deleted
    UNPROCESSABLE_ENTITY = 422 # Validation error
    TOO_MANY_REQUESTS = 429    # Rate limit exceeded

    # 5xx Server Errors
    INTERNAL_ERROR = 500       # Unexpected server error
    NOT_IMPLEMENTED = 501      # Feature not implemented
    SERVICE_UNAVAILABLE = 503  # Temporary unavailability
    GATEWAY_TIMEOUT = 504      # Upstream timeout

# Usage examples
@app.post("/users")
async def create_user(user: UserCreate):
    if await user_exists(user.email):
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="User with this email already exists"
        )

    return await create_user_record(user)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await find_user(user_id)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    return user
```

## Validation Error Formatting

### Field-Level Validation

Format validation errors clearly:

```python
from pydantic import BaseModel, Field, validator, EmailStr
from typing import List

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    age: int = Field(..., ge=18, le=120)
    tags: List[str] = Field(default=[], max_items=10)

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v

# Produces error like:
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": [
    {
      "field": "email",
      "message": "value is not a valid email address",
      "code": "VALUE_ERROR_EMAIL"
    },
    {
      "field": "password",
      "message": "Password must contain uppercase letter",
      "code": "VALUE_ERROR"
    },
    {
      "field": "age",
      "message": "ensure this value is greater than or equal to 18",
      "code": "VALUE_ERROR_NUMBER_GE"
    }
  ],
  "trace_id": "abc123",
  "timestamp": "2025-10-18T10:30:00Z"
}
```

### Custom Validation Messages

Provide user-friendly validation messages:

```python
class ErrorMessages:
    """Centralized error messages"""

    EMAIL_INVALID = "Please enter a valid email address"
    EMAIL_EXISTS = "An account with this email already exists"

    PASSWORD_TOO_SHORT = "Password must be at least 8 characters"
    PASSWORD_NO_UPPERCASE = "Password must contain an uppercase letter"
    PASSWORD_NO_DIGIT = "Password must contain a number"

    AGE_TOO_YOUNG = "You must be at least 18 years old"
    AGE_INVALID = "Please enter a valid age"

    REQUIRED_FIELD = "{field} is required"
    FIELD_TOO_LONG = "{field} must be at most {max} characters"

def format_validation_error(field: str, error_type: str, **context) -> str:
    """Format validation errors with context"""
    messages = {
        "email_invalid": ErrorMessages.EMAIL_INVALID,
        "password_too_short": ErrorMessages.PASSWORD_TOO_SHORT,
        "age_too_young": ErrorMessages.AGE_TOO_YOUNG.format(**context),
        "required": ErrorMessages.REQUIRED_FIELD.format(field=field),
    }
    return messages.get(error_type, f"Validation failed for {field}")
```

## User-Friendly vs Developer-Friendly Errors

### Dual Error Messages

Provide different messages for different audiences:

```python
class APIError(Exception):
    def __init__(
        self,
        code: str,
        user_message: str,
        dev_message: Optional[str] = None,
        status_code: int = 500,
        details: Optional[List[ErrorDetail]] = None
    ):
        self.code = code
        self.user_message = user_message
        self.dev_message = dev_message or user_message
        self.status_code = status_code
        self.details = details
        super().__init__(self.dev_message)

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    # Log developer message
    logger.error(
        f"API Error: {exc.code}",
        extra={
            "dev_message": exc.dev_message,
            "trace_id": request.state.trace_id,
            "path": request.url.path,
        }
    )

    # Return user-friendly message
    error_response = ErrorResponse.create(
        code=exc.code,
        message=exc.user_message,  # User sees this
        details=exc.details,
        trace_id=request.state.trace_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

# Usage
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        user = await db.get_user(user_id)
    except DatabaseError as e:
        raise APIError(
            code="DATABASE_ERROR",
            user_message="We're having trouble retrieving your data. Please try again.",
            dev_message=f"Database query failed: {str(e)}",
            status_code=500
        )

    if not user:
        raise APIError(
            code="USER_NOT_FOUND",
            user_message="We couldn't find a user with that ID",
            dev_message=f"User {user_id} not found in database",
            status_code=404
        )

    return user
```

## Error Logging and Correlation

### Request Tracing

Implement trace IDs for error correlation:

```python
from fastapi import Request
import logging
import uuid

logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    # Generate or extract trace ID
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    request.state.trace_id = trace_id

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id

    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    # Log full error details
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "trace_id": trace_id,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host,
        }
    )

    # Return sanitized error to client
    error_response = ErrorResponse.create(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please contact support with trace ID.",
        trace_id=trace_id
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )
```

### Structured Logging

Log errors with structured data:

```python
import structlog

logger = structlog.get_logger()

async def log_error(
    error: Exception,
    trace_id: str,
    request: Request,
    user_id: Optional[str] = None
):
    """Log error with full context"""
    logger.error(
        "api_error",
        error_type=type(error).__name__,
        error_message=str(error),
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
        status_code=getattr(error, "status_code", 500),
        user_id=user_id,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
    )
```

## RFC 7807 Problem Details

### Standard Problem Format

Implement RFC 7807 for errors:

```python
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any

class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs"""

    type: str                           # URI reference identifying problem type
    title: str                          # Short, human-readable summary
    status: int                         # HTTP status code
    detail: Optional[str] = None        # Human-readable explanation
    instance: Optional[str] = None      # URI reference to specific occurrence
    extensions: Optional[Dict[str, Any]] = None  # Additional context

    class Config:
        json_schema_extra = {
            "example": {
                "type": "https://api.example.com/errors/validation",
                "title": "Validation Error",
                "status": 422,
                "detail": "The request body contains invalid fields",
                "instance": "/users/create",
                "trace_id": "abc-123",
                "invalid_fields": ["email", "age"]
            }
        }

@app.exception_handler(RequestValidationError)
async def rfc7807_validation_handler(
    request: Request,
    exc: RequestValidationError
):
    invalid_fields = [
        ".".join(str(loc) for loc in error["loc"][1:])
        for error in exc.errors()
    ]

    problem = ProblemDetail(
        type="https://api.example.com/errors/validation",
        title="Validation Error",
        status=422,
        detail="The request contains invalid or missing fields",
        instance=str(request.url.path),
        extensions={
            "trace_id": request.state.trace_id,
            "invalid_fields": invalid_fields,
            "errors": exc.errors()
        }
    )

    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"}
    )
```

## Error Internationalization

### Multi-Language Errors

Support error messages in multiple languages:

```python
from typing import Dict
from enum import Enum

class Language(str, Enum):
    EN = "en"
    ES = "es"
    FR = "fr"

ERROR_MESSAGES: Dict[str, Dict[Language, str]] = {
    "USER_NOT_FOUND": {
        Language.EN: "User not found",
        Language.ES: "Usuario no encontrado",
        Language.FR: "Utilisateur non trouvé"
    },
    "VALIDATION_ERROR": {
        Language.EN: "Request validation failed",
        Language.ES: "Error de validación de solicitud",
        Language.FR: "Échec de validation de la demande"
    },
    "UNAUTHORIZED": {
        Language.EN: "Authentication required",
        Language.ES: "Autenticación requerida",
        Language.FR: "Authentification requise"
    }
}

def get_error_message(code: str, lang: Language = Language.EN) -> str:
    """Get localized error message"""
    messages = ERROR_MESSAGES.get(code, {})
    return messages.get(lang, messages.get(Language.EN, code))

@app.middleware("http")
async def add_language_context(request: Request, call_next):
    # Extract language from header
    accept_lang = request.headers.get("Accept-Language", "en")
    lang = accept_lang.split(",")[0].split("-")[0].lower()

    try:
        request.state.language = Language(lang)
    except ValueError:
        request.state.language = Language.EN

    return await call_next(request)

@app.exception_handler(HTTPException)
async def localized_http_exception_handler(
    request: Request,
    exc: HTTPException
):
    lang = getattr(request.state, "language", Language.EN)
    code = get_error_code_for_status(exc.status_code)

    error_response = ErrorResponse.create(
        code=code,
        message=get_error_message(code, lang)
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )
```

## Best Practices

### Security Considerations

Avoid leaking sensitive information:

```python
# ❌ BAD - Exposes internal details
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        result = await db.execute(f"SELECT * FROM users WHERE id = {user_id}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"  # Leaks SQL details!
        )

# ✅ GOOD - Generic error, detailed logging
@app.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    try:
        result = await db.execute(query, user_id=user_id)
    except Exception as e:
        # Log full details
        logger.exception("Database query failed", extra={
            "trace_id": request.state.trace_id,
            "query": query,
            "user_id": user_id
        })

        # Return generic error
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving user data"
        )
```

### Consistent Error Codes

Define error codes consistently:

```python
class ErrorCode:
    """Centralized error code definitions"""

    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"

    # Resource Errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FORMAT = "INVALID_FORMAT"
    MISSING_FIELD = "MISSING_FIELD"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
```

### Error Response Templates

Create reusable error responses:

```python
class ErrorTemplates:
    @staticmethod
    def not_found(resource: str, identifier: str) -> APIError:
        return APIError(
            code=ErrorCode.NOT_FOUND,
            user_message=f"{resource} not found",
            dev_message=f"{resource} with id '{identifier}' does not exist",
            status_code=404
        )

    @staticmethod
    def already_exists(resource: str, field: str, value: str) -> APIError:
        return APIError(
            code=ErrorCode.ALREADY_EXISTS,
            user_message=f"{resource} already exists",
            dev_message=f"{resource} with {field}='{value}' already exists",
            status_code=409
        )

    @staticmethod
    def unauthorized(reason: Optional[str] = None) -> APIError:
        return APIError(
            code=ErrorCode.UNAUTHORIZED,
            user_message="Authentication required",
            dev_message=reason or "No valid authentication credentials",
            status_code=401
        )

# Usage
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.get_user(user_id)
    if not user:
        raise ErrorTemplates.not_found("User", user_id)
    return user

@app.post("/users")
async def create_user(user: UserCreate):
    existing = await db.find_by_email(user.email)
    if existing:
        raise ErrorTemplates.already_exists("User", "email", user.email)
    return await db.create_user(user)
```

## Related Skills

- **modal-web-endpoints.md** - Error handling in Modal APIs
- **ios-networking.md** - Client-side error handling
- **network-resilience-patterns.md** - Retry and timeout patterns
