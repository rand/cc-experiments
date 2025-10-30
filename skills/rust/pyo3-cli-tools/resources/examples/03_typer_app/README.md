# Example 03: Typer Application

This example demonstrates building a Typer-based CLI application with PyO3 Rust backend for high-performance JSON processing. Shows integration with Typer's type hints, validation, and modern CLI patterns.

## Concepts Covered

- **Typer Integration**: Modern CLI with type hints and validation
- **PyClass Usage**: Exposing Rust structs as Python classes
- **JSON Processing**: Fast JSON parsing, formatting, and manipulation
- **Serde Integration**: Using serde for serialization/deserialization
- **Path Navigation**: Extracting nested JSON values
- **File Merging**: Combining multiple JSON files efficiently

## Key Components

### `JsonStats` (PyClass)
A Python class representing JSON analysis results with properties:
- `keys`: Number of keys across all objects
- `total_size`: File size in bytes
- `nested_objects`: Count of nested objects
- `arrays`: Count of arrays

### Functions

#### `validate_json(filepath: str) -> JsonStats`
Validates JSON and returns comprehensive statistics.

#### `format_json(input_file: str, output_file: Optional[str], indent: int) -> str`
Formats JSON with specified indentation. Returns string if no output file.

#### `merge_json(input_files: List[str], output_file: str) -> int`
Merges multiple JSON files into a single file. Returns count of files merged.

#### `extract_json_value(filepath: str, path: str) -> str`
Extracts value using dot notation (e.g., "user.profile.name").

## Building and Testing

```bash
# Install dependencies
pip install maturin typer

# Build and install the extension
maturin develop --release

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Example Typer CLI

```python
import typer
from pathlib import Path
import typer_app

app = typer.Typer()

@app.command()
def validate(
    filepath: Path = typer.Argument(..., help="JSON file to validate"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """Validate JSON file and show statistics."""
    stats = typer_app.validate_json(str(filepath))
    typer.echo(f"✓ Valid JSON: {filepath}")
    typer.echo(f"  Keys: {stats.keys}")
    typer.echo(f"  Size: {stats.total_size} bytes")
    if verbose:
        typer.echo(f"  Objects: {stats.nested_objects}")
        typer.echo(f"  Arrays: {stats.arrays}")

@app.command()
def format(
    input_file: Path,
    output_file: Path = typer.Option(None, "--output", "-o"),
    indent: int = typer.Option(2, "--indent", "-i", min=0, max=8)
):
    """Format JSON file with specified indentation."""
    typer_app.format_json(str(input_file), str(output_file) if output_file else None, indent)
    typer.echo("✓ Formatted successfully")

@app.command()
def merge(
    input_files: list[Path] = typer.Argument(..., help="JSON files to merge"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file")
):
    """Merge multiple JSON files."""
    count = typer_app.merge_json([str(f) for f in input_files], str(output))
    typer.echo(f"✓ Merged {count} files into {output}")

if __name__ == '__main__':
    app()
```

## Performance Benefits

- **Fast JSON Parsing**: serde_json is significantly faster than Python's json module
- **Efficient Memory**: Streaming operations reduce memory usage
- **Native Speed**: Rust's performance for string manipulation
- **Type Safety**: Compile-time guarantees for data structures

## Learning Points

1. **PyClass Pattern**: Exposing Rust structs as Python classes with `#[pyclass]`
2. **Serde Integration**: Automatic JSON serialization/deserialization
3. **Typer Type Hints**: Full compatibility with Python type annotations
4. **Error Context**: Providing helpful error messages with context
5. **Optional Parameters**: Rust `Option<T>` maps to Python `Optional[T]`
6. **Recursive Algorithms**: Safe recursion for nested data structures

## Next Steps

- Example 04: Terminal colors and ANSI formatting
- Example 05: Progress bars and spinners
