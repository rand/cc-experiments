# Example 10: Production CLI Tool

Complete production-ready CLI tool combining config, progress, parallel processing, and reporting.

## Features
- Configuration management (load/save TOML)
- Parallel directory analysis
- Content search across files
- Progress tracking with callbacks
- Report generation
- Type-safe configuration

## Components

### CliConfig
- Persistent configuration
- Thread control
- Output format selection

### FileProcessor
- Parallel file analysis
- Content search
- Statistics generation
- Progress callbacks

## Usage

```python
import production_cli

# Create config
config = production_cli.CliConfig()
config.threads = 8
config.verbose = True

# Process files
processor = production_cli.FileProcessor(config)

def progress(current, total):
    print(f"Progress: {current}/{total}")

# Analyze directory
results = processor.analyze_directory("/path", ["py", "rs"], progress)

# Generate report
report = processor.generate_report(results)
print(f"Total files: {report['total_files']}")
print(f"Total lines: {report['total_lines']}")

# Search content
matches = processor.search_content("/path", "pattern", True)
```

## Building

```bash
pip install maturin
maturin develop --release
python test_example.py
```

## Complete Example

This example demonstrates all concepts from examples 01-09 in a production-ready package.
