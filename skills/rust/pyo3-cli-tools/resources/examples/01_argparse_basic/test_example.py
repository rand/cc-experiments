"""
Test suite for argparse integration example.
Demonstrates PyO3 functions integrated with Python's argparse module.
"""
import argparse
import tempfile
import os
import argparse_basic


def test_search_file():
    """Test single file search functionality."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Hello World\n")
        f.write("Python is great\n")
        f.write("hello again\n")
        f.write("Rust is fast\n")
        filepath = f.name

    try:
        # Case-sensitive search
        results = argparse_basic.search_file("hello", filepath, True)
        assert len(results) == 1
        assert results[0][0] == 3  # Line 3
        assert "hello again" in results[0][1]

        # Case-insensitive search
        results = argparse_basic.search_file("hello", filepath, False)
        assert len(results) == 2
        print(f"Found 'hello' (case-insensitive) in {len(results)} lines")

    finally:
        os.unlink(filepath)


def test_search_files():
    """Test multi-file search functionality."""
    files = []
    for i, content in enumerate([
        "Python programming\n",
        "Rust programming\n",
        "Java programming\n"
    ]):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            files.append(f.name)

    try:
        results = argparse_basic.search_files("programming", files, True)
        assert len(results) == 3
        print(f"Found 'programming' in {len(results)} files")

        # Search for pattern in subset
        results = argparse_basic.search_files("Python", files, True)
        assert len(results) == 1

    finally:
        for f in files:
            os.unlink(f)


def test_count_lines():
    """Test line counting."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        f.write("Line 3\n")
        filepath = f.name

    try:
        count = argparse_basic.count_lines(filepath)
        assert count == 3
        print(f"Counted {count} lines")
    finally:
        os.unlink(filepath)


def test_file_stats():
    """Test file statistics."""
    content = "Hello World\nPython Rust\n"
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(content)
        filepath = f.name

    try:
        lines, words, bytes_count = argparse_basic.file_stats(filepath)
        assert lines == 2
        assert words == 4
        assert bytes_count == len(content)
        print(f"Stats: {lines} lines, {words} words, {bytes_count} bytes")
    finally:
        os.unlink(filepath)


def test_argparse_integration():
    """Demonstrate integration with argparse."""
    # Create a simple CLI parser
    parser = argparse.ArgumentParser(description='Fast file search tool')
    parser.add_argument('pattern', help='Search pattern')
    parser.add_argument('files', nargs='+', help='Files to search')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                        help='Case-insensitive search')
    parser.add_argument('-c', '--count', action='store_true',
                        help='Only show counts')

    # Simulate command line args
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Hello World\n")
        f.write("hello rust\n")
        filepath = f.name

    try:
        # Parse args
        args = parser.parse_args(['hello', filepath, '-i'])

        # Use Rust backend
        results = argparse_basic.search_file(
            args.pattern,
            args.files[0],
            not args.ignore_case
        )

        print(f"\nArgparse Integration Test:")
        print(f"  Pattern: {args.pattern}")
        print(f"  Ignore case: {args.ignore_case}")
        print(f"  Found {len(results)} matches")

        assert len(results) == 2  # Both "Hello" and "hello"

    finally:
        os.unlink(filepath)


def test_error_handling():
    """Test error handling for invalid files."""
    try:
        argparse_basic.search_file("test", "/nonexistent/file.txt", True)
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        print(f"Correctly raised FileNotFoundError: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Argparse Integration Example Tests")
    print("=" * 60)

    test_search_file()
    test_search_files()
    test_count_lines()
    test_file_stats()
    test_argparse_integration()
    test_error_handling()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
