# Example 02: Click Command Groups

This example demonstrates integrating PyO3 Rust functions with Click's command group pattern for building multi-command CLI tools with high-performance file operations.

## Concepts Covered

- **Command Groups**: Building multi-command CLIs with Click
- **File Operations**: Recursive directory traversal, copying, deletion
- **Pattern Matching**: Simple wildcard pattern filtering
- **Dry Run Mode**: Safe preview before destructive operations
- **Directory Statistics**: Fast file/directory counting and size calculation
- **Extension Filtering**: Filter files by extension efficiently

## Key Functions

### `list_files(directory: str, recursive: bool, extensions: Optional[List[str]]) -> List[str]`
Lists files in a directory with optional recursive scanning and extension filtering.

### `copy_files(source_files: List[str], dest_dir: str, overwrite: bool) -> int`
Copies multiple files to a destination directory with overwrite control.

### `delete_files(directory: str, pattern: str, dry_run: bool) -> Tuple[int, int]`
Deletes files matching a pattern with dry-run support. Returns (found, deleted) counts.

### `directory_stats(directory: str) -> Tuple[int, int, int]`
Calculates directory statistics: (files, directories, total_size).

## Building and Testing

```bash
# Install dependencies
pip install maturin click

# Build and install the extension
maturin develop --release

# Run tests
python test_example.py

# Or use pytest
pytest test_example.py -v
```

## Example CLI Implementation

```python
import click
import click_commands

@click.group()
def cli():
    """High-performance file management tool."""
    pass

@cli.command()
@click.argument('directory')
@click.option('-r', '--recursive', is_flag=True)
@click.option('-e', '--extension', multiple=True)
def list(directory, recursive, extension):
    """List files in directory."""
    exts = list(extension) if extension else None
    files = click_commands.list_files(directory, recursive, exts)
    for f in files:
        click.echo(f)

@cli.command()
@click.argument('files', nargs=-1, required=True)
@click.argument('destination')
@click.option('--overwrite', is_flag=True)
def copy(files, destination, overwrite):
    """Copy files to destination."""
    count = click_commands.copy_files(list(files), destination, overwrite)
    click.echo(f"Copied {count} files")

@cli.command()
@click.argument('directory')
@click.argument('pattern')
@click.option('--dry-run', is_flag=True)
def delete(directory, pattern, dry_run):
    """Delete files matching pattern."""
    found, deleted = click_commands.delete_files(directory, pattern, dry_run)
    if dry_run:
        click.echo(f"Would delete {found} files")
    else:
        click.echo(f"Deleted {deleted} of {found} files")

if __name__ == '__main__':
    cli()
```

## Performance Benefits

- **Fast Directory Traversal**: Rust's walkdir is significantly faster than os.walk
- **Efficient File Operations**: Native file I/O without Python overhead
- **Parallel Potential**: Easy to extend with parallel processing
- **Memory Efficient**: Streaming directory iteration

## Learning Points

1. **Click Integration**: Seamlessly integrate Rust backends with Click commands
2. **Command Groups**: Organize multiple commands under a single CLI
3. **Options vs Arguments**: Both work naturally with PyO3 functions
4. **Error Propagation**: Rust errors become Python exceptions automatically
5. **Dry Run Pattern**: Safe preview pattern for destructive operations
6. **walkdir Crate**: Efficient cross-platform directory traversal

## Next Steps

- Example 03: Typer applications with rich type hints
- Example 04: Terminal colors and formatting
