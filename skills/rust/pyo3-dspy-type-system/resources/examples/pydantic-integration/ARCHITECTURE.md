# Architecture: Pydantic Integration

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Rust Application                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  UserProfile struct (Rust + serde)                           │
│  ┌────────────────────────────────────┐                      │
│  │ email: String                      │                      │
│  │ age: u8                            │                      │
│  │ role: Role (enum)                  │                      │
│  │ bio: Option<String>                │                      │
│  │ website: Option<String>            │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
│                     │ serde_json::to_string()                │
│                     ▼                                         │
│              JSON String                                      │
│  ┌────────────────────────────────────┐                      │
│  │ {                                  │                      │
│  │   "email": "alice@example.com",    │                      │
│  │   "age": 28,                       │                      │
│  │   "role": "premium",               │                      │
│  │   "bio": "Software engineer...",   │                      │
│  │   "website": "https://alice.dev"   │                      │
│  │ }                                  │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
└─────────────────────┼─────────────────────────────────────────┘
                      │ PyO3 bridge
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Runtime                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  UserProfile.model_validate_json(json_str)                   │
│                     │                                         │
│                     ▼                                         │
│  Pydantic Validation Pipeline                                │
│  ┌────────────────────────────────────┐                      │
│  │ 1. Parse JSON                      │                      │
│  │ 2. Validate field types            │                      │
│  │ 3. Run field validators:           │                      │
│  │    - Email format check            │                      │
│  │    - Age range (13-120)            │                      │
│  │    - Role enum validation          │                      │
│  │    - Bio length (max 500)          │                      │
│  │    - Website URL format            │                      │
│  │ 4. Run model validators:           │                      │
│  │    - Premium users need bio        │                      │
│  │ 5. Apply transformations:          │                      │
│  │    - Lowercase email               │                      │
│  │    - Strip whitespace from bio     │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
│                     ▼                                         │
│         Validated Pydantic Model                             │
│  ┌────────────────────────────────────┐                      │
│  │ email: "alice@example.com"         │                      │
│  │ age: 28                            │                      │
│  │ role: "premium"                    │                      │
│  │ bio: "Software engineer..."        │                      │
│  │ website: "https://alice.dev"       │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
│                     │ .model_dump_json()                     │
│                     ▼                                         │
│         Validated JSON String                                │
│  ┌────────────────────────────────────┐                      │
│  │ {                                  │                      │
│  │   "email": "alice@example.com",    │                      │
│  │   "age": 28,                       │                      │
│  │   "role": "premium",               │                      │
│  │   "bio": "Software engineer...",   │                      │
│  │   "website": "https://alice.dev"   │                      │
│  │ }                                  │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
└─────────────────────┼─────────────────────────────────────────┘
                      │ PyO3 bridge
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Rust Application                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  serde_json::from_str(&validated_json)                       │
│                     │                                         │
│                     ▼                                         │
│  UserProfile struct (validated)                              │
│  ┌────────────────────────────────────┐                      │
│  │ email: "alice@example.com"         │                      │
│  │ age: 28                            │                      │
│  │ role: Role::Premium                │                      │
│  │ bio: Some("Software engineer...")  │                      │
│  │ website: Some("https://alice.dev") │                      │
│  └────────────────────────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Validation Error Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Invalid Data (e.g., bad email)                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Pydantic Validation                                         │
│  ┌────────────────────────────────────┐                      │
│  │ Field: email                       │                      │
│  │ Value: "not-an-email"              │                      │
│  │ Validator: validate_email()        │                      │
│  │ Pattern: ^[a-zA-Z0-9._%+-]+@...    │                      │
│  │                                    │                      │
│  │ ❌ Match failed                    │                      │
│  └────────────────────────────────────┘                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  ValidationError raised                                      │
│  ┌────────────────────────────────────┐                      │
│  │ {                                  │                      │
│  │   "type": "value_error",           │                      │
│  │   "loc": ["email"],                │                      │
│  │   "msg": "Invalid email format",   │                      │
│  │   "input": "not-an-email"          │                      │
│  │ }                                  │                      │
│  └────────────────────────────────────┘                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ PyO3 exception
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Rust Error Handling                                         │
│  ┌────────────────────────────────────┐                      │
│  │ PyErr caught by PyO3                │                      │
│  │ Converted to anyhow::Error          │                      │
│  │ Context: "Pydantic validation       │                      │
│  │           failed"                   │                      │
│  └────────────────────────────────────┘                      │
│                     │                                         │
│                     ▼                                         │
│  match validate_user_profile() {                             │
│      Ok(valid) => /* use valid data */,                      │
│      Err(e) => /* handle error */                            │
│  }                                                            │
└─────────────────────────────────────────────────────────────┘
```

## Type Mapping

### Rust → Python

| Rust Type           | Serde Serialization | Pydantic Type        | Validation           |
|---------------------|---------------------|----------------------|----------------------|
| `String`            | `"text"`            | `str`                | Field validators     |
| `u8`                | `28`                | `int`                | `ge=`, `le=`         |
| `Role::Premium`     | `"premium"`         | `Literal[...]`       | Enum validation      |
| `Option<String>`    | `null` / `"text"`   | `Optional[str]`      | Optional validators  |
| `bool`              | `true` / `false`    | `bool`               | Type coercion        |

### Serde Attributes → Pydantic Config

| Serde Attribute          | Pydantic Equivalent      | Purpose                    |
|--------------------------|--------------------------|----------------------------|
| `#[serde(rename_all)]`   | Alias generator          | Consistent naming          |
| `#[serde(skip_serializing_if)]` | `Optional[T]`   | Omit null fields           |
| `#[derive(Serialize)]`   | `.model_dump()`          | To dict/JSON               |
| `#[derive(Deserialize)]` | `.model_validate()`      | From dict/JSON             |

## Validation Patterns

### Field Validators

```python
@field_validator('email')
@classmethod
def validate_email(cls, v: str) -> str:
    """
    - Input: Raw string from JSON
    - Process: Regex validation
    - Transform: Lowercase normalization
    - Output: Validated, normalized string
    - Error: ValueError with message
    """
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
        raise ValueError('Invalid email format')
    return v.lower()
```

### Range Validators

```python
age: int = Field(..., ge=13, le=120)
"""
- Constraint: 13 ≤ age ≤ 120
- Automatic: No custom validator needed
- Error: "Input should be greater than or equal to 13"
"""
```

### Model Validators

```python
@model_validator(mode='after')
def validate_premium_features(self):
    """
    - Cross-field validation
    - Runs after all field validators
    - Access to complete model state
    - Can validate business rules
    """
    if self.role == 'premium' and not self.bio:
        raise ValueError('Premium users must provide a bio')
    return self
```

## Integration Points

### 1. Rust → Pydantic

```rust
let json = serde_json::to_string(&rust_struct)?;
let validated = python_class.call_method1("model_validate_json", (json,))?;
```

### 2. Pydantic → Rust

```rust
let validated_json = pydantic_model.call_method0("model_dump_json")?.extract::<String>()?;
let rust_struct: MyStruct = serde_json::from_str(&validated_json)?;
```

### 3. Error Propagation

```rust
match validate_user_profile(py, &profile) {
    Ok(validated) => {
        // Use validated data with confidence
        // All constraints verified by Pydantic
    }
    Err(e) => {
        // Handle validation error
        // Contains field path and error message
        log::error!("Validation failed: {}", e);
    }
}
```

## DSPy Integration Pattern

```python
import dspy
from models import UserProfile, ProductReview

class UserAnalysis(dspy.Signature):
    """Analyze user profile and generate recommendations"""
    profile: UserProfile = dspy.InputField()  # Validated input
    analysis: str = dspy.OutputField()
    recommendations: list[str] = dspy.OutputField()

class ReviewSummarizer(dspy.Signature):
    """Summarize product reviews"""
    reviews: list[ProductReview] = dspy.InputField()  # Batch validated
    summary: str = dspy.OutputField()
    sentiment: str = dspy.OutputField()
```

From Rust:

```rust
// Validate input before DSPy
let validated_profile = validate_user_profile(py, &profile)?;

// Call DSPy with validated data
let result = call_dspy_signature(py, "UserAnalysis", validated_profile)?;

// Validate output if needed
let validated_result = validate_analysis_result(py, &result)?;
```

## Performance Considerations

1. **JSON Serialization**: Two-way JSON conversion adds overhead
2. **Validation Cost**: Pydantic validation is comprehensive but not free
3. **PyO3 Bridge**: FFI calls have cost; batch validations when possible
4. **Caching**: Consider caching validation results for identical inputs
5. **Batch Processing**: Validate collections once rather than item-by-item

## Best Practices

1. **Keep types synchronized**: Any change to Rust struct requires Pydantic update
2. **Document constraints**: Write validation rules in both type definitions
3. **Test edge cases**: Validate boundary conditions in both languages
4. **Use typed errors**: Structured validation errors aid debugging
5. **Version compatibility**: Pin Pydantic version to prevent breaking changes
6. **Fail fast**: Validate at system boundaries before expensive operations

## Testing Strategy

1. **Valid data**: Confirm round-trip preservation
2. **Invalid fields**: Test each validator independently
3. **Boundary values**: Test min/max constraints
4. **Type mismatches**: Ensure clean error messages
5. **Transformations**: Verify normalization (lowercase, trim, etc.)
6. **Recovery**: Test error handling and retry logic
