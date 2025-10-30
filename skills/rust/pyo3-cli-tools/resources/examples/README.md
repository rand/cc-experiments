# PyO3 CLI Tools Examples

This directory contains 10 progressive examples demonstrating PyO3 CLI tool development, from basic argument parsing to production-ready applications.

## Example Structure

Each example includes:
- `src/lib.rs` - Rust PyO3 implementation
- `Cargo.toml` - Rust dependencies
- `pyproject.toml` - Maturin packaging configuration
- `test_example.py` - Pytest test suite
- `README.md` - Documentation and usage guide

## Examples Overview

### 01. Basic Argparse Integration (395 lines)
**File**: `01_argparse_basic/`
**Concepts**: Function integration, error handling, file operations, type conversions
**Functions**: `search_file`, `search_files`, `count_lines`, `file_stats`

Demonstrates integrating PyO3 functions with Python's argparse for building CLI tools.

### 02. Click Command Groups (579 lines)
**File**: `02_click_commands/`
**Concepts**: Command groups, directory operations, pattern matching, dry-run mode
**Functions**: `list_files`, `copy_files`, `delete_files`, `directory_stats`

Shows how to build multi-command CLI tools with Click and fast file operations.

### 03. Typer Application (600 lines)
**File**: `03_typer_app/`
**Concepts**: Type hints, PyClass, JSON processing, serde integration
**Classes**: `JsonStats`
**Functions**: `validate_json`, `format_json`, `merge_json`, `extract_json_value`

Modern CLI with Typer, demonstrating JSON processing and PyClass usage.

### 04. Terminal Colors and Formatting (515 lines)
**File**: `04_terminal_colors/`
**Concepts**: ANSI codes, RGB colors, text styling, table formatting
**Functions**: `colorize`, `colorize_rgb`, `stylize`, `format_status`, `format_table_row`, `strip_ansi`

Beautiful terminal output with ANSI colors and formatting utilities.

### 05. Progress Bars and Spinners (352 lines)
**File**: `05_progress_bars/`
**Concepts**: Progress tracking, ETA calculation, animations, multi-progress
**Classes**: `ProgressBar`, `Spinner`, `MultiProgress`

Progress indicators with bars, spinners, and multi-progress displays.

### 06. Parallel File Processing (323 lines)
**File**: `06_file_processing/`
**Concepts**: Rayon parallelism, GIL release, callbacks, par_bridge
**Functions**: `process_files_parallel`, `find_files_parallel`, `count_lines_parallel`, `search_parallel`

High-performance parallel file operations with progress callbacks.

### 07. Configuration Management (247 lines)
**File**: `07_config_management/`
**Concepts**: TOML/YAML parsing, serde, config merging
**Functions**: `load_toml`, `save_toml`, `load_yaml`, `save_yaml`, `merge_configs`

Fast configuration file handling with multiple format support.

### 08. Interactive Prompts (243 lines)
**File**: `08_interactive_prompts/`
**Concepts**: User input, password input, validation, selections
**Functions**: `prompt`, `prompt_password`, `confirm`, `select`, `multiselect`, `prompt_int`

User interaction patterns with validation and hidden input.

### 09. TUI Components (272 lines)
**File**: `09_tui_components/`
**Concepts**: Box drawing, menus, panels, trees, cursor control
**Functions**: `draw_box`, `draw_menu`, `draw_panel`, `draw_tree`, `clear_screen`, `move_cursor`

Terminal UI components for building rich CLI interfaces.

### 10. Production CLI Tool (427 lines)
**File**: `10_production_cli/`
**Concepts**: Complete CLI app, config, parallel processing, reporting
**Classes**: `CliConfig`, `FileAnalysis`, `FileProcessor`
**Methods**: `analyze_directory`, `search_content`, `generate_report`

Production-ready CLI tool combining all previous concepts.

## Total Statistics

- **Total Examples**: 10
- **Total Lines**: 3,953 lines
- **Average per Example**: 395 lines
- **Languages**: Rust (PyO3), Python (tests), TOML (config)

## Progression Path

1. **Beginner (01-03)**: Basic integration with Python CLI frameworks
2. **Intermediate (04-06)**: Terminal output, progress, parallelism
3. **Advanced (07-09)**: Configuration, interaction, TUI components
4. **Production (10)**: Complete application with all features

## Building Examples

Each example can be built independently:

```bash
cd 01_argparse_basic/
pip install maturin
maturin develop --release
python test_example.py
```

Or use pytest:

```bash
pip install pytest
pytest test_example.py -v
```

## Key Technologies

- **PyO3 0.20**: Python/Rust bindings
- **Maturin**: Build and packaging
- **Rayon**: Data parallelism
- **Serde**: Serialization
- **WalkDir**: Directory traversal
- **Regex**: Pattern matching

## Learning Path

Follow the examples in order for a comprehensive understanding of PyO3 CLI development:

1. Start with argparse basics
2. Progress through Click and Typer
3. Learn terminal formatting
4. Add progress indicators
5. Implement parallelism
6. Handle configuration
7. Add user interaction
8. Build TUI components
9. Combine everything in production tool

## Related Skills

- **pyo3-fundamentals.md**: Core PyO3 concepts
- **pyo3-performance-gil-parallel.md**: Parallel processing patterns
- **pyo3-packaging-distribution.md**: Distribution strategies
- **pyo3-testing-debugging.md**: Testing approaches

## Standards Compliance

All examples follow Wave 10-11 standards:
- ✅ Type hints in Python
- ✅ Comprehensive error handling
- ✅ Full test coverage
- ✅ Documentation with examples
- ✅ Proper resource cleanup
- ✅ Performance optimizations

## Next Steps

After completing these examples, you can:
- Build custom CLI tools for your projects
- Integrate with existing Python CLIs
- Create distributable command-line applications
- Optimize Python CLI performance with Rust
