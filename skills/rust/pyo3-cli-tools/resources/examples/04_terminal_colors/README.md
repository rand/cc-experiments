# Example 04: Terminal Colors and Formatting

This example demonstrates ANSI color codes and terminal text formatting with PyO3 for creating beautiful CLI output.

## Concepts Covered

- **ANSI Color Codes**: 8-color and 24-bit RGB colors
- **Text Styling**: Bold, dim, italic, underline
- **Status Messages**: Formatted success/error/warning/info messages
- **Table Formatting**: Aligned columns with colors
- **ANSI Stripping**: Remove codes for length calculation
- **Unicode Symbols**: Status indicators (✓, ✗, ⚠, ℹ)

## Key Functions

### `colorize(text: str, color: str, bold: bool, background: bool) -> str`
Apply named colors (red, green, blue, yellow, magenta, cyan, white, black).

### `colorize_rgb(text: str, r: int, g: int, b: int, background: bool) -> str`
Apply 24-bit RGB colors for more color options.

### `stylize(text: str, style: str) -> str`
Apply text styles (bold, dim, italic, underline).

### `format_status(status: str, message: str) -> str`
Create formatted status messages with colored icons.

### `format_table_row(columns: List[str], widths: List[int], color: Optional[str]) -> str`
Format aligned table rows with optional colors.

### `format_separator(width: int, style: str) -> str`
Create horizontal separator lines (single, double, thick, dotted).

### `strip_ansi(text: str) -> str`
Remove ANSI codes from text.

### `visible_length(text: str) -> int`
Get visible text length (excluding ANSI codes).

## Building and Testing

```bash
pip install maturin
maturin develop --release
python test_example.py
```

## Example Usage

```python
import terminal_colors as tc

# Basic colors
print(tc.colorize("Success!", "green", True, False))
print(tc.colorize("Error!", "red", True, False))

# RGB colors
print(tc.colorize_rgb("Custom color", 255, 128, 0, False))

# Text styles
print(tc.stylize("Important", "bold"))
print(tc.stylize("Emphasized", "italic"))

# Status messages
print(tc.format_status("success", "File processed"))
print(tc.format_status("error", "File not found"))
print(tc.format_status("warning", "Deprecated feature"))
print(tc.format_status("info", "Starting process"))

# Tables
header = tc.format_table_row(["Name", "Status", "Time"], [20, 10, 10], "cyan")
print(header)
print(tc.format_separator(45, "single"))

row1 = tc.format_table_row(["file1.txt", "OK", "0.5s"], [20, 10, 10], None)
print(row1)
```

## Performance Benefits

- **No Dependencies**: Pure ANSI codes, no external libraries
- **Fast String Operations**: Rust string formatting
- **Regex Caching**: Compiled regex for ANSI stripping
- **Zero Allocation**: Efficient string building

## Learning Points

1. **ANSI Escape Codes**: Standard terminal color/style codes
2. **String Formatting**: Efficient text manipulation in Rust
3. **Unicode Handling**: Proper Unicode symbol support
4. **Length Calculation**: Accounting for invisible ANSI codes
5. **Error Handling**: Validation of color/style names

## Next Steps

- Example 05: Progress bars and spinners
- Example 06: Parallel file processing with progress
