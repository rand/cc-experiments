"""Test suite for parallel file processing."""
import tempfile
import time
from pathlib import Path
import file_processing


def test_process_files_parallel():
    """Test parallel file processing with callback."""
    files = []
    for i in range(5):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"Content {i}\n" * 10)
            files.append(f.name)

    try:
        processed = []

        def callback(path, size):
            processed.append((path, size))

        results = file_processing.process_files_parallel(files, callback)
        assert len(results) == 5
        assert len(processed) == 5
        print(f"Processed {len(results)} files in parallel")
    finally:
        for f in files:
            Path(f).unlink()


def test_find_files_parallel():
    """Test parallel file finding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").touch()
        Path(tmpdir, "file2.py").touch()
        Path(tmpdir, "file3.txt").touch()

        results = file_processing.find_files_parallel(tmpdir, "*.txt", None)
        assert len(results) == 2
        print(f"Found {len(results)} files matching pattern")


def test_count_lines_parallel():
    """Test parallel line counting."""
    files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line\n" * (10 * (i + 1)))
            files.append(f.name)

    try:
        results = file_processing.count_lines_parallel(files)
        assert len(results) == 3
        assert results[0][1] == 10
        assert results[1][1] == 20
        print(f"Counted lines in {len(results)} files")
    finally:
        for f in files:
            Path(f).unlink()


def test_search_parallel():
    """Test parallel content search."""
    files = []
    for i, content in enumerate(["hello world", "goodbye world", "hello there"]):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            files.append(f.name)

    try:
        results = file_processing.search_parallel("hello", files, True)
        assert len(results) == 2
        print(f"Found pattern in {len(results)} files")
    finally:
        for f in files:
            Path(f).unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("File Processing Example Tests")
    print("=" * 60)

    test_process_files_parallel()
    test_find_files_parallel()
    test_count_lines_parallel()
    test_search_parallel()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
