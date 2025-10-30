# Hello World - DSPy from Rust

A minimal example demonstrating how to call DSPy from Rust using PyO3. This example shows the simplest possible integration: initializing the Python interpreter, configuring a language model, and making a basic DSPy prediction.

## What You'll Learn

- How to initialize the Python interpreter from Rust using PyO3
- How to import and configure DSPy in a Rust application
- How to create and execute a simple DSPy signature
- Proper error handling patterns for Python-Rust interop
- Memory management and cleanup best practices

## Prerequisites

1. **Rust toolchain** (1.70 or later)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Python 3.8+** with DSPy installed
   ```bash
   pip install dspy-ai
   ```

3. **OpenAI API Key**
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Setup

1. Navigate to this directory:
   ```bash
   cd skills/rust/pyo3-dspy-fundamentals/resources/examples/hello-world
   ```

2. Ensure your OpenAI API key is set:
   ```bash
   echo $OPENAI_API_KEY  # Should display your key
   ```

## Running

Build and run the example:

```bash
cargo run
```

Or run with release optimizations:

```bash
cargo run --release
```

## Expected Output

```
Initializing Python interpreter...
Importing DSPy...
Configuring OpenAI language model...
Creating DSPy signature and predictor...
Making prediction...

Question: What is the capital of France?

Answer: The capital of France is Paris.
```

The exact answer may vary slightly depending on the model's response, but it should correctly identify Paris as the capital of France.

## Code Walkthrough

### 1. Python Interpreter Initialization

```rust
pyo3::prepare_freethreaded_python();
```

This initializes Python's Global Interpreter Lock (GIL) in a way that allows Rust to safely interact with Python.

### 2. Acquiring the GIL

```rust
Python::with_gil(|py| { ... })
```

All Python operations must happen while holding the GIL. PyO3's `with_gil` ensures proper acquisition and release.

### 3. Importing DSPy

```rust
let dspy = py.import("dspy")?;
```

Python's `import dspy` statement, executed from Rust.

### 4. Configuring the Language Model

```rust
let lm = dspy.call_method1("OpenAI", (
    kwargs![py, "model" => "gpt-3.5-turbo"],
))?;
dspy.call_method1("configure", (
    kwargs![py, "lm" => lm],
))?;
```

Creates an OpenAI client and configures DSPy to use it as the default language model.

### 5. Creating a Signature

```rust
let signature = py_str!(py, "question -> answer");
```

DSPy signatures define input/output field mappings. This simple signature takes a question and produces an answer.

### 6. Making a Prediction

```rust
let predict = dspy.call_method1("Predict", (signature,))?;
let result = predict.call1((
    kwargs![py, "question" => "What is the capital of France?"],
))?;
```

Creates a `Predict` module with our signature and calls it with a question.

### 7. Extracting the Result

```rust
let answer: String = result.getattr("answer")?.extract()?;
```

Retrieves the `answer` field from the DSPy output and converts it to a Rust `String`.

## Error Handling

The example uses Rust's `Result` type with `anyhow` for error handling:

- `PyErr` from PyO3 is automatically converted to `anyhow::Error`
- The `?` operator propagates errors up the call stack
- All errors are caught in `main()` and printed with context

## Memory Management

PyO3 handles reference counting automatically:

- Python objects are reference-counted while in scope
- The GIL is released when `with_gil` completes
- All Python memory is properly cleaned up on drop

## Next Steps

After running this example, explore:

1. **Simple QA Example** - Chain multiple DSPy modules together
2. **Type-Safe Bindings** - Create Rust structs for DSPy signatures
3. **Async Integration** - Use DSPy with Tokio for concurrent requests
4. **Error Recovery** - Handle API failures and retries gracefully

## Troubleshooting

### "No module named 'dspy'"

Install DSPy:
```bash
pip install dspy-ai
```

### "OPENAI_API_KEY not set"

Export your API key:
```bash
export OPENAI_API_KEY='sk-...'
```

### "Python 3.x not found"

Ensure Python 3.8+ is in your PATH:
```bash
python3 --version
```

### Build errors with PyO3

Ensure you have Python development headers:
```bash
# macOS
brew install python3

# Ubuntu/Debian
sudo apt-get install python3-dev

# Fedora
sudo dnf install python3-devel
```
