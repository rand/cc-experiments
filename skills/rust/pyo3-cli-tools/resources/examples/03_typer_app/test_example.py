"""
Test suite for Typer integration example.
Demonstrates PyO3 JSON operations with Typer type hints and validation.
"""
import tempfile
import json
from pathlib import Path
import typer_app


def test_validate_json():
    """Test JSON validation and statistics."""
    data = {
        "user": {
            "name": "Alice",
            "age": 30,
            "hobbies": ["reading", "coding"]
        },
        "active": True
    }

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(data, f)
        filepath = f.name

    try:
        stats = typer_app.validate_json(filepath)
        assert stats.keys == 4  # user, name, age, hobbies
        assert stats.arrays == 1  # hobbies array
        assert stats.total_size > 0
        print(f"JSON stats: {stats}")
        print(f"  Keys: {stats.keys}")
        print(f"  Size: {stats.total_size} bytes")
        print(f"  Objects: {stats.nested_objects}")
        print(f"  Arrays: {stats.arrays}")
    finally:
        Path(filepath).unlink()


def test_format_json():
    """Test JSON formatting."""
    data = {"a": 1, "b": 2, "c": {"d": 3}}

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        # Write compact JSON
        json.dump(data, f, separators=(',', ':'))
        input_file = f.name

    try:
        # Format and return
        formatted = typer_app.format_json(input_file, None, 2)
        assert "{\n" in formatted
        assert formatted.count('\n') > 1
        print(f"\nFormatted JSON (in-memory):\n{formatted}")

        # Format to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            output_file = f.name

        result = typer_app.format_json(input_file, output_file, 2)
        assert result == ""
        assert Path(output_file).exists()

        # Verify formatted output
        with open(output_file) as f:
            content = f.read()
            assert "{\n" in content
            print(f"Formatted JSON (to file): {len(content)} bytes")

        Path(output_file).unlink()
    finally:
        Path(input_file).unlink()


def test_merge_json():
    """Test merging multiple JSON files."""
    files = []

    # Create test files
    for i, data in enumerate([
        {"key1": "value1"},
        {"key2": "value2"},
        {"key3": "value3"}
    ]):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(data, f)
            files.append(f.name)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        output_file = f.name

    try:
        count = typer_app.merge_json(files, output_file)
        assert count == 3

        # Verify merged content
        with open(output_file) as f:
            merged = json.load(f)
            assert "key1" in merged
            assert "key2" in merged
            assert "key3" in merged
            assert merged["key1"] == "value1"
            print(f"\nMerged {count} JSON files")
            print(f"Merged data: {merged}")

    finally:
        for f in files:
            Path(f).unlink()
        Path(output_file).unlink()


def test_extract_json_value():
    """Test extracting values from JSON."""
    data = {
        "user": {
            "profile": {
                "name": "Bob"
            }
        },
        "count": 42
    }

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(data, f)
        filepath = f.name

    try:
        # Extract nested value
        name = typer_app.extract_json_value(filepath, "user.profile.name")
        assert '"Bob"' in name
        print(f"\nExtracted user.profile.name: {name}")

        # Extract top-level value
        count = typer_app.extract_json_value(filepath, "count")
        assert "42" in count
        print(f"Extracted count: {count}")

    finally:
        Path(filepath).unlink()


def test_typer_integration():
    """Demonstrate integration with Typer."""
    import typer
    from typer.testing import CliRunner

    app = typer.Typer()

    @app.command()
    def validate(
        filepath: Path = typer.Argument(..., help="JSON file to validate"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
    ):
        """Validate a JSON file and show statistics."""
        stats = typer_app.validate_json(str(filepath))
        typer.echo(f"Valid JSON file: {filepath}")
        typer.echo(f"Keys: {stats.keys}")
        typer.echo(f"Size: {stats.total_size} bytes")
        if verbose:
            typer.echo(f"Nested objects: {stats.nested_objects}")
            typer.echo(f"Arrays: {stats.arrays}")

    @app.command()
    def format(
        input_file: Path = typer.Argument(..., help="Input JSON file"),
        output_file: Path = typer.Option(None, "--output", "-o", help="Output file"),
        indent: int = typer.Option(2, "--indent", "-i", help="Indentation spaces")
    ):
        """Format a JSON file."""
        result = typer_app.format_json(
            str(input_file),
            str(output_file) if output_file else None,
            indent
        )
        if output_file:
            typer.echo(f"Formatted JSON written to {output_file}")
        else:
            typer.echo(result)

    runner = CliRunner()

    # Create test file
    data = {"test": "data", "number": 123}
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(data, f)
        test_file = f.name

    try:
        # Test validate command
        result = runner.invoke(app, ['validate', test_file])
        assert result.exit_code == 0
        assert "Valid JSON file" in result.output
        assert "Keys:" in result.output
        print(f"\nTyper integration test:")
        print(result.output)

        # Test validate with verbose
        result = runner.invoke(app, ['validate', test_file, '--verbose'])
        assert result.exit_code == 0
        assert "Nested objects:" in result.output

    finally:
        Path(test_file).unlink()


def test_error_handling():
    """Test error handling."""
    # Invalid file
    try:
        typer_app.validate_json("/nonexistent/file.json")
        assert False, "Should have raised IOError"
    except IOError as e:
        print(f"\nCorrectly raised IOError: {e}")

    # Invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write("not valid json{{{")
        bad_file = f.name

    try:
        typer_app.validate_json(bad_file)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"Correctly raised ValueError: {e}")
    finally:
        Path(bad_file).unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("Typer App Example Tests")
    print("=" * 60)

    test_validate_json()
    test_format_json()
    test_merge_json()
    test_extract_json_value()
    test_typer_integration()
    test_error_handling()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
