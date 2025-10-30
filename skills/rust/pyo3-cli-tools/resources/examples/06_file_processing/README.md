# Example 06: Parallel File Processing

Demonstrates high-performance parallel file processing with progress tracking using Rayon.

## Key Features

- Parallel file processing with callbacks
- Fast directory traversal with pattern matching
- Parallel line counting
- Concurrent content search
- GIL-releasing operations

## Usage

```python
import file_processing

# Process files with progress
def progress(path, size):
    print(f"Processed: {path} ({size} bytes)")

results = file_processing.process_files_parallel(files, progress)

# Find files in parallel
files = file_processing.find_files_parallel("/path", "*.txt", 3)

# Search across files
matches = file_processing.search_parallel("pattern", files, True)
```

## Next Steps

- Example 07: Configuration management
