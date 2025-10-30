# Pydantic Integration Example - Manifest

## Overview

Complete production-ready example demonstrating Pydantic model validation integrated with Rust serde types for type-safe DSPy interactions.

## Files

### Core Implementation (416 lines)

1. **src/main.rs** (248 lines)
   - Rust structs: `UserProfile`, `ProductReview`, `Role`, `Sentiment`
   - Serde serialization/deserialization
   - PyO3 integration for calling Pydantic validators
   - Validation functions: `validate_user_profile()`, `validate_product_review()`
   - 6 comprehensive test scenarios
   - Error handling with anyhow
   - Round-trip validation flow

2. **python/models.py** (168 lines)
   - Pydantic v2 models: `UserProfile`, `ProductReview`
   - Field validators: email, website, bio, review_text
   - Range constraints: age (13-120), rating (1-5)
   - Model validators: premium features, sentiment-rating consistency
   - Data normalization: lowercase, strip whitespace
   - Literal types for enums

### Documentation (635 lines)

3. **README.md** (247 lines)
   - Complete overview and architecture
   - Usage instructions and setup
   - Data model descriptions
   - Example output
   - Validation patterns
   - Error handling strategies
   - Production patterns
   - Integration with DSPy
   - Best practices

4. **ARCHITECTURE.md** (388 lines)
   - Data flow diagrams (ASCII art)
   - Validation error flow
   - Type mapping tables (Rust ↔ Python)
   - Serde attributes ↔ Pydantic config
   - Validation pattern examples
   - Integration point code samples
   - DSPy integration pattern
   - Performance considerations
   - Testing strategy

### Configuration (35 lines)

5. **Cargo.toml** (10 lines)
   - Dependencies: pyo3 (0.20), serde (1.0), serde_json (1.0), anyhow (1.0)
   - Package metadata

6. **requirements.txt** (1 line)
   - Python dependencies: pydantic>=2.0

7. **run.sh** (22 lines)
   - Automated setup script
   - Pydantic installation check
   - Build and run automation

8. **.cargo/config.toml** (2 lines)
   - Linker flags for macOS Python framework

## Statistics

- **Total files**: 8 (excluding generated)
- **Total lines**: 1,086
- **Rust code**: 248 lines
- **Python code**: 168 lines
- **Documentation**: 635 lines
- **Configuration**: 35 lines

## Test Coverage

### Validation Scenarios

1. **Valid user profile** - Happy path with all fields
2. **Invalid email** - Format validation failure
3. **Age out of range** - Numeric constraint violation
4. **Valid product review** - Complete review validation
5. **Sentiment mismatch** - Model-level validator
6. **Data normalization** - Automatic corrections

### Validation Types

- ✓ Email format (regex)
- ✓ URL format (regex)
- ✓ Age range (13-120)
- ✓ Rating range (1-5)
- ✓ String length constraints
- ✓ Enum validation
- ✓ Cross-field validation
- ✓ Data transformation

## Dependencies

### Rust

- `pyo3 = "0.20"` - Python bindings
- `serde = "1.0"` - Serialization framework
- `serde_json = "1.0"` - JSON support
- `anyhow = "1.0"` - Error handling

### Python

- `pydantic >= 2.0` - Validation framework

## Build & Run

```bash
# Install dependencies
pip3 install pydantic

# Build
cargo build --release

# Run
cargo run --release

# Or use automated script
./run.sh
```

## Output Example

```
=== Pydantic Integration Example ===

Creating valid user profile...
✓ User profile validated successfully

User details:
  Email: alice@example.com
  Age: 28
  Role: Premium
  Bio: Software engineer interested in AI
  Website: https://alice.dev

Creating invalid user (bad email)...
✓ Validation failed (expected): Pydantic validation failed

Creating invalid user (age out of range)...
✓ Validation failed (expected): Pydantic validation failed

Creating product review...
✓ Product review validated successfully

Review details:
  Product: Ergonomic Keyboard
  Rating: 5
  Text: Excellent keyboard, great for typing all day
  Sentiment: Positive
  Verified: true

Creating review with sentiment-rating mismatch...
✓ Validation failed (expected): Pydantic validation failed

Testing validation recovery...
Attempting to fix invalid data...
✓ Data fixed and validated successfully
  Original email: ALICE@EXAMPLE.COM
  Fixed email: alice@example.com
  Original bio: '   Short bio   '
  Cleaned bio: 'Short bio'

=== Example Complete ===
```

## Key Features

### Type Safety

- Rust enums map to Python Literal types
- Serde attributes match Pydantic configuration
- Option types for nullable fields
- Strict deserialization

### Validation

- Field-level validators for format checking
- Range validators for numeric bounds
- Custom validators for business logic
- Model-level validation for cross-field constraints
- Automatic data normalization

### Error Handling

- Graceful validation error handling
- Detailed error messages with field paths
- Automatic retry with corrected data
- Context preservation with anyhow

### Production Patterns

- Round-trip type safety
- Comprehensive validation
- Clear error messages
- Data normalization
- Recovery strategies
- Complete documentation

## Integration Points

### Rust → Pydantic

```rust
let json = serde_json::to_string(&rust_struct)?;
let validated = class.call_method1("model_validate_json", (json,))?;
```

### Pydantic → Rust

```rust
let json = model.call_method0("model_dump_json")?.extract::<String>()?;
let rust_struct: T = serde_json::from_str(&json)?;
```

### With DSPy

```python
class UserAnalysis(dspy.Signature):
    profile: UserProfile = dspy.InputField()  # Validated!
    insights: str = dspy.OutputField()
```

## Success Criteria

- ✅ Builds without errors
- ✅ All test scenarios pass
- ✅ Valid data flows through correctly
- ✅ Invalid data caught and reported
- ✅ Data normalization works
- ✅ Error messages are clear
- ✅ Documentation is complete
- ✅ Architecture is documented
- ✅ Production-ready patterns shown

## Maintenance

- Keep Rust and Python types synchronized
- Update validators when constraints change
- Test edge cases for new validators
- Document validation rules in both languages
- Pin Pydantic version for stability

## Related Examples

- `basic-type-mapping/` - Foundation type mapping
- `dspy-integration/` - Complete DSPy workflow
- `error-handling/` - Advanced error patterns
- `async-integration/` - Async validation patterns

## Version

- Example version: 0.1.0
- Pydantic: 2.0+
- PyO3: 0.20
- Rust edition: 2021
