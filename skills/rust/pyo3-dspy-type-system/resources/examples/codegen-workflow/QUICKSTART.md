# Quick Start Guide

Get up and running with automated Rust type generation in 5 minutes.

## Prerequisites

- Rust toolchain (1.70+)
- Python 3.8+
- signature_codegen.py (located at `../../signature_codegen.py`)

## 1. Build the Project

```bash
cd codegen-workflow
cargo build
```

**What happens:**
- `build.rs` runs automatically
- Reads `signatures.txt` (8 DSPy signatures)
- Executes `signature_codegen.py`
- Generates `src/generated.rs` with 8 Rust structs
- Compiles the project

## 2. Run the Example

```bash
cargo run
```

**Output:**
- Demonstrates all 8 generated types
- Shows JSON serialization
- Validates type safety
- Explains the workflow

## 3. Add Your Own Signature

```bash
# Add a new signature
echo "user_query -> search_results" >> signatures.txt

# Rebuild (automatically regenerates types)
cargo build

# Use the new type
cat >> src/main.rs << 'EOF'

let search = UserQueryToSearchResults {
    user_query: "Rust async programming".to_string(),
    search_results: "Found 1,234 results".to_string(),
};
println!("{:?}", search);
EOF

cargo run
```

## 4. Modify Existing Signature

```bash
# Edit signatures.txt
vim signatures.txt

# Rebuild to regenerate
cargo build

# Types automatically update
```

## 5. View Generated Types

```bash
# After building, check generated code
cat src/generated.rs
```

## Common Commands

```bash
# Clean and rebuild (full regeneration)
cargo clean && cargo build

# Check without building
cargo check

# Run with verbose output
cargo build --verbose

# Format code
cargo fmt

# Run clippy lints
cargo clippy
```

## Signature Format Reference

```
# Single input/output
input -> output

# Multiple inputs
input1, input2 -> output

# Multiple outputs
input -> output1, output2

# Complex signature
context, question, constraints -> reasoning, answer, confidence
```

## Generated Type Pattern

Input signature:
```
question -> answer
```

Generated Rust:
```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct QuestionToAnswer {
    pub question: String,
    pub answer: String,
}
```

## Troubleshooting

**Problem:** Build fails with "signature_codegen.py not found"

**Solution:**
```bash
# Check path
ls ../../signature_codegen.py

# Should exist at:
# skills/rust/pyo3-dspy-type-system/signature_codegen.py
```

**Problem:** Generated file is empty

**Solution:**
```bash
# Run codegen manually
python3 ../../signature_codegen.py signatures.txt src/generated.rs

# Check for Python errors
python3 --version
```

**Problem:** Type not found after adding signature

**Solution:**
```bash
# Ensure rebuild happened
cargo clean
cargo build

# Verify generated.rs updated
cat src/generated.rs | grep "pub struct"
```

## Next Steps

1. Read full [README.md](README.md) for detailed documentation
2. Explore other examples in `../`
3. Integrate into your project
4. Add validation and custom types

## Integration Checklist

- [ ] Copy `build.rs` to your project
- [ ] Add dependencies to `Cargo.toml`
- [ ] Create `signatures.txt` with your signatures
- [ ] Add `mod generated;` to your code
- [ ] Run `cargo build` to generate types
- [ ] Use generated types in your application

## Learning Path

1. **Beginner**: Run example, modify signatures, observe regeneration
2. **Intermediate**: Add validation in build.rs, custom type mappings
3. **Advanced**: Extend codegen, add trait generation, integrate with proc macros

## Resources

- [Build Scripts](https://doc.rust-lang.org/cargo/reference/build-scripts.html)
- [Serde](https://serde.rs/)
- [DSPy](https://github.com/stanfordnlp/dspy)

## Support

For issues or questions, refer to the main skill documentation at:
`skills/rust/pyo3-dspy-type-system/`
