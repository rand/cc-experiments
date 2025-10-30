# Example 03: Pydantic Integration

Integrate Rust validation with Pydantic models for high-performance data validation.

## What You'll Learn

- Extract data from Pydantic models in Rust
- Perform complex validation logic in Rust
- Return structured validation results
- Sanitize user input
- Normalize data formats

## Building

```bash
pip install maturin fastapi pydantic pytest
maturin develop
```

## Running Tests

```bash
pytest test_example.py -v
```

## Usage Example

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pydantic_integration

app = FastAPI()

class User(BaseModel):
    username: str
    email: str
    age: int

@app.post("/users")
async def create_user(user: User):
    # Validate with Rust
    result = pydantic_integration.validate_user_model(user)

    if not result.valid:
        raise HTTPException(400, detail={"errors": result.errors})

    return {"message": "User valid", "warnings": result.warnings}
```

## Next Steps

- **04_flask_extension**: Build Flask extensions with PyO3
- **08_jwt_auth**: Add JWT authentication
