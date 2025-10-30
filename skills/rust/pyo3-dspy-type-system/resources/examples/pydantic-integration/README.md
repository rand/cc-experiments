# Pydantic Integration Example

Complete demonstration of Pydantic model validation integrated with Rust serde types for type-safe DSPy interactions.

## Overview

This example shows production-ready patterns for:
- Bidirectional type mapping between Rust serde and Pydantic
- Field-level validation with Pydantic validators
- Validation error handling and recovery
- Type coercion and constraint enforcement
- Round-trip data flow: Rust → JSON → Pydantic → DSPy → Pydantic → JSON → Rust

## Architecture

```
Rust serde struct
    ↓ (serialize to JSON)
Pydantic model
    ↓ (validate fields)
DSPy signature input
    ↓ (LLM processing)
DSPy prediction output
    ↓ (validate with Pydantic)
Pydantic model
    ↓ (serialize to JSON)
Rust serde struct
```

## Files

- `src/main.rs` - Rust implementation with serde types
- `python/models.py` - Pydantic models with validators
- `Cargo.toml` - Dependencies

## Key Features

### Pydantic Side
- Field validators for email, URL, enum values
- Range constraints (min/max values)
- String pattern matching (regex)
- Custom validation logic
- Model-level validators
- Validation error collection

### Rust Side
- Serde attributes matching Pydantic config
- Option types for optional fields
- Enum variants with serde annotations
- Validation error handling
- Type-safe deserialization

## Data Models

### UserProfile
Models a user profile with comprehensive validation:
- Email format validation
- Age range constraints (13-120)
- Role enum validation
- Bio length limits
- Website URL validation

### ProductReview
Models a product review with validation:
- Rating range (1-5)
- Sentiment enum
- Verified purchase boolean
- Review text length constraints

## Setup

Install Pydantic:

```bash
pip3 install pydantic
```

Or use the provided script which handles installation automatically:

```bash
./run.sh
```

## Usage

```bash
cargo run --release
```

## Example Output

```
=== Pydantic Integration Example ===

Creating valid user profile...
✓ User profile validated successfully

User details:
  Email: alice@example.com
  Age: 28
  Role: premium
  Bio: Software engineer interested in AI
  Website: https://alice.dev

Creating invalid user (bad email)...
✗ Validation failed (expected): Invalid email format

Creating invalid user (age out of range)...
✗ Validation failed (expected): Age must be between 13 and 120

Creating product review...
✓ Product review validated successfully

Review details:
  Product: Ergonomic Keyboard
  Rating: 5
  Text: Excellent keyboard, great for typing all day
  Sentiment: positive
  Verified: true

Testing validation recovery...
Attempting to fix invalid data...
✓ Data fixed and validated successfully
```

## Validation Patterns

### Field Validators

```python
@field_validator('email')
def validate_email(cls, v: str) -> str:
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
        raise ValueError('Invalid email format')
    return v.lower()
```

### Range Constraints

```python
age: int = Field(..., ge=13, le=120)
rating: int = Field(..., ge=1, le=5)
```

### Model Config

```python
class Config:
    str_strip_whitespace = True
    json_schema_extra = {
        "example": {...}
    }
```

### Serde Matching

```rust
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
enum Role {
    Basic,
    Premium,
    Admin,
}
```

## Error Handling

The example demonstrates three error scenarios:

1. **Invalid email format** - Regex validation failure
2. **Age out of range** - Numeric constraint violation
3. **Invalid enum value** - Variant validation failure

Each error is caught, logged, and optionally recovered.

## Production Patterns

### Type Safety
- Rust enums match Python Literal types
- Option types for nullable fields
- Strict deserialization with serde

### Validation
- Field-level validators for format
- Range validators for numeric bounds
- Custom validators for business logic
- Model-level validation for cross-field constraints

### Error Recovery
- Graceful validation error handling
- Detailed error messages with field paths
- Automatic retry with corrected data
- Fallback values for optional fields

## Integration with DSPy

```python
class UserAnalysis(dspy.Signature):
    """Analyze user profile and provide insights"""
    user_profile: UserProfile = dspy.InputField()
    insights: str = dspy.OutputField()
    recommendations: List[str] = dspy.OutputField()
```

The validated Pydantic models can be used directly as DSPy fields, ensuring type safety throughout the pipeline.

## Dependencies

- `pyo3 = "0.20"` - Python bindings
- `serde = { version = "1.0", features = ["derive"] }`
- `serde_json = "1.0"`
- `anyhow = "1.0"` - Error handling
- `pydantic = "^2.0"` - Python validation

## Testing

The example includes:
- Valid data flow (happy path)
- Invalid email validation
- Out-of-range numeric values
- Invalid enum variants
- Validation recovery patterns

## Best Practices

1. **Keep Rust and Pydantic types synchronized** - Use matching field names and serde attributes
2. **Validate at boundaries** - Always validate data entering/leaving Python
3. **Use typed errors** - Return structured validation errors
4. **Document constraints** - Keep validation rules visible in both languages
5. **Test edge cases** - Validate boundary conditions and invalid data

## Extending

To add new validated types:

1. Define Pydantic model with validators in `python/models.py`
2. Create matching Rust struct with serde in `src/main.rs`
3. Add validation tests for edge cases
4. Document constraints in both type definitions

## Notes

- Pydantic v2 uses different validator syntax than v1
- Serde's `rename_all` must match Pydantic's `alias_generator`
- Use `Config.populate_by_name = True` for flexible field names
- Always test round-trip serialization
