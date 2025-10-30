# Optional Fields Example

## Purpose

This example demonstrates safe handling of `Option<T>` fields in DSPy-style type systems, showing patterns for default values, missing field handling, and optional chaining.

## Key Concepts

### 1. Optional Field Types
- `Option<String>` - Optional text fields
- `Option<i64>` - Optional numeric fields
- `Option<Vec<String>>` - Optional collections
- `Option<bool>` - Optional flags

### 2. Default Value Strategies
- `Default::default()` - Type-specific defaults
- `.unwrap_or_default()` - Safe extraction with fallback
- `.unwrap_or(value)` - Custom default values
- `.unwrap_or_else(|| compute())` - Lazy default computation

### 3. Serialization Control
- `#[serde(skip_serializing_if = "Option::is_none")]` - Omit None values
- `#[serde(default)]` - Use Default on deserialization
- Clean JSON output without null noise

## Running the Example

```bash
cd skills/rust/pyo3-dspy-type-system/resources/examples/optional-fields
cargo run
```

## Expected Output

The example demonstrates:

1. **Complete Profile** - All fields present
2. **Minimal Profile** - Only required fields
3. **Partial Profile** - Mix of Some and None
4. **Safe Extraction** - Using unwrap_or patterns
5. **Optional Chaining** - Processing nested Options
6. **Default Implementations** - Custom defaults
7. **Serialization** - Clean JSON without nulls

## Code Structure

### UserProfile Struct
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserProfile {
    // Required fields (no Option)
    pub user_id: String,
    pub username: String,

    // Optional fields with different types
    pub email: Option<String>,
    pub age: Option<i64>,
    pub bio: Option<String>,
    pub tags: Option<Vec<String>>,
    pub is_verified: Option<bool>,
    pub metadata: Option<HashMap<String, String>>,
}
```

### Safe Extraction Patterns

```rust
// Pattern 1: unwrap_or_default
let email = profile.email.unwrap_or_default(); // ""

// Pattern 2: unwrap_or with custom default
let age = profile.age.unwrap_or(18);

// Pattern 3: unwrap_or_else with computation
let bio = profile.bio.unwrap_or_else(|| "No bio provided".to_string());

// Pattern 4: Optional chaining with map
let tag_count = profile.tags.as_ref().map(|t| t.len()).unwrap_or(0);

// Pattern 5: Pattern matching
match profile.is_verified {
    Some(true) => "Verified",
    Some(false) => "Not verified",
    None => "Unknown",
}
```

### Default Implementations

```rust
impl Default for UserProfile {
    fn default() -> Self {
        Self {
            user_id: String::new(),
            username: String::new(),
            email: None,
            age: None,
            bio: None,
            tags: Some(Vec::new()), // Default empty collection
            is_verified: Some(false), // Default to unverified
            metadata: None,
        }
    }
}
```

## Best Practices

### 1. Required vs Optional
- Make fields `Option<T>` only when absence is meaningful
- Required fields should not be wrapped in Option
- Consider business logic when choosing

### 2. Default Values
- Implement `Default` for structs with many optional fields
- Use `#[serde(default)]` for graceful deserialization
- Document default behavior clearly

### 3. Safe Extraction
- Prefer `.unwrap_or_default()` over `.unwrap()`
- Use `.unwrap_or_else()` for expensive defaults
- Chain operations with `.as_ref()` to avoid moves

### 4. Serialization
- Use `skip_serializing_if` to keep JSON clean
- Consider readability of None vs omitted fields
- Be consistent across your API

### 5. Validation
- Validate after extraction, not during
- Check business rules on concrete values
- Return meaningful errors for invalid states

## Common Pitfalls

### 1. Nested Options
```rust
// Bad: Option<Option<T>> from chaining
let email_length = profile.email.map(|e| e.len()); // Option<usize>

// Good: Flatten or use as_ref
let email_length = profile.email.as_ref().map(|e| e.len()).unwrap_or(0);
```

### 2. Premature unwrap()
```rust
// Bad: Panics on None
let email = profile.email.unwrap();

// Good: Safe with default
let email = profile.email.unwrap_or_default();
```

### 3. Cloning for no reason
```rust
// Bad: Unnecessary clone
let email = profile.email.clone().unwrap_or_default();

// Good: Use as_ref or take ownership
let email = profile.email.unwrap_or_default();
```

### 4. Forgetting #[serde(default)]
```rust
// Without default, missing fields cause deserialization errors
#[derive(Deserialize)]
#[serde(default)] // Add this!
pub struct Config {
    pub timeout: Option<u64>,
}
```

## Integration with DSPy

When working with DSPy predictions:

```python
# Python DSPy prediction
prediction = predictor(
    user_id="123",
    username="alice"
    # Optional fields may be missing
)

# Rust handles missing fields gracefully
let profile: UserProfile = serde_json::from_value(prediction)?;
let email = profile.email.unwrap_or_default(); // Safe!
```

## Testing Strategies

1. **Test all Some cases** - Verify correct value extraction
2. **Test all None cases** - Verify safe defaults
3. **Test partial data** - Mix of Some/None
4. **Test serialization roundtrip** - JSON -> Struct -> JSON
5. **Test default implementation** - `UserProfile::default()`

## Related Examples

- `basic-types/` - Simple type mapping
- `nested-structures/` - Complex nested Options
- `validation-patterns/` - Validating optional fields
- `error-handling/` - Error cases with Options

## References

- [Rust Option enum](https://doc.rust-lang.org/std/option/enum.Option.html)
- [Serde skip_serializing_if](https://serde.rs/field-attrs.html#skip_serializing_if)
- [Default trait](https://doc.rust-lang.org/std/default/trait.Default.html)
