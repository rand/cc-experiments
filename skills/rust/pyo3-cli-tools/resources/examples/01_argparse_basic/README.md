# Example 01: Basic Argparse Integration

This example demonstrates how to integrate PyO3 Rust functions with Python's `argparse` module for building command-line tools with high-performance backends.

## Concepts Covered

- **Function Integration**: Exposing Rust functions to Python's argparse
- **Error Handling**: Proper PyO3 error types (PyFileNotFoundError, PyIOError)
- **File Operations**: Reading and processing files efficiently in Rust
- **Type Conversions**: Rust Vec/tuple to Python list/tuple conversions
- **CLI Patterns**: Search, count, and statistics operations

## Key Functions

### `search_file(pattern: str, filepath: str, case_sensitive: bool) -> List[Tuple[int, str]]`
Searches a single file for a pattern and returns matching lines with line numbers.

### `search_files(pattern: str, filepaths: List[str], case_sensitive: bool) -> List[Tuple[str, List[Tuple[int, str]]]]`
Searches multiple files for a pattern, returning results grouped by file.

### `count_lines(filepath: str) -> int`
Efficiently counts lines in a file.

### `file_stats(filepath: str) -> Tuple[int, int, int]`
Returns (lines, words, bytes) statistics for a file.

## Building and Testing

```bash
# Install maturin if not already installed
pip install maturin

# Build and install the extension
maturin develop --release

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Example CLI Usage

```python
import argparse
import argparse_basic

def main():
    parser = argparse.ArgumentParser(description='Fast file search')
    parser.add_argument('pattern', help='Search pattern')
    parser.add_argument('files', nargs='+', help='Files to search')
    parser.add_argument('-i', '--ignore-case', action='store_true')

    args = parser.parse_args()

    results = argparse_basic.search_files(
        args.pattern,
        args.files,
        not args.ignore_case
    )

    for filepath, matches in results:
        print(f"{filepath}:")
        for line_num, line in matches:
            print(f"  {line_num}: {line}")

if __name__ == '__main__':
    main()
```

## Performance Benefits

- **Fast File I/O**: Rust's file operations are significantly faster than Python
- **Efficient String Operations**: Pattern matching without Python overhead
- **No GIL**: File operations release the GIL automatically
- **Zero-copy Returns**: Efficient data transfer to Python

## Learning Points

1. **PyO3 Error Types**: Use appropriate Python exception types (`PyFileNotFoundError`, `PyIOError`)
2. **Result Handling**: Convert Rust `Result<T, E>` to `PyResult<T>`
3. **String Processing**: Handle both owned `String` and borrowed `&str`
4. **Tuple Returns**: Multiple return values via Rust tuples
5. **Vector Returns**: Automatic conversion to Python lists

## Next Steps

- Example 02: Click command groups with PyO3
- Example 03: Typer applications with type hints
