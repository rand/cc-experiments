"""
Test suite for Click integration example.
Demonstrates PyO3 file operations with Click command groups.
"""
import tempfile
import os
import shutil
from pathlib import Path
import click_commands


def test_list_files_non_recursive():
    """Test non-recursive file listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        Path(tmpdir, "file1.txt").touch()
        Path(tmpdir, "file2.py").touch()
        Path(tmpdir, "file3.rs").touch()

        # List all files
        files = click_commands.list_files(tmpdir, False, None)
        assert len(files) == 3
        print(f"Found {len(files)} files (non-recursive)")

        # Filter by extension
        py_files = click_commands.list_files(tmpdir, False, ["py"])
        assert len(py_files) == 1
        assert any("file2.py" in f for f in py_files)
        print(f"Found {len(py_files)} Python files")


def test_list_files_recursive():
    """Test recursive file listing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested structure
        Path(tmpdir, "file1.txt").touch()
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "file2.txt").touch()
        Path(subdir, "file3.py").touch()

        # Recursive listing
        files = click_commands.list_files(tmpdir, True, None)
        assert len(files) == 3
        print(f"Found {len(files)} files (recursive)")

        # Filter recursively
        txt_files = click_commands.list_files(tmpdir, True, ["txt"])
        assert len(txt_files) == 2
        print(f"Found {len(txt_files)} text files (recursive)")


def test_copy_files():
    """Test file copying operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source files
        src_dir = Path(tmpdir, "src")
        src_dir.mkdir()
        file1 = src_dir / "file1.txt"
        file2 = src_dir / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        # Create destination
        dest_dir = Path(tmpdir, "dest")

        # Copy files
        copied = click_commands.copy_files(
            [str(file1), str(file2)],
            str(dest_dir),
            False
        )

        assert copied == 2
        assert (dest_dir / "file1.txt").exists()
        assert (dest_dir / "file2.txt").exists()
        print(f"Copied {copied} files")


def test_copy_files_overwrite():
    """Test file copying with overwrite control."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source and destination
        src_file = Path(tmpdir, "source.txt")
        src_file.write_text("New content")

        dest_dir = Path(tmpdir, "dest")
        dest_dir.mkdir()
        dest_file = dest_dir / "source.txt"
        dest_file.write_text("Old content")

        # Try without overwrite
        copied = click_commands.copy_files([str(src_file)], str(dest_dir), False)
        assert copied == 0
        assert dest_file.read_text() == "Old content"
        print("Correctly skipped existing file without overwrite")

        # Try with overwrite
        copied = click_commands.copy_files([str(src_file)], str(dest_dir), True)
        assert copied == 1
        assert dest_file.read_text() == "New content"
        print("Correctly overwrote existing file")


def test_delete_files():
    """Test file deletion with pattern matching."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        Path(tmpdir, "file1.tmp").touch()
        Path(tmpdir, "file2.tmp").touch()
        Path(tmpdir, "file3.txt").touch()

        # Dry run
        found, deleted = click_commands.delete_files(tmpdir, "*.tmp", True)
        assert found == 2
        assert deleted == 0
        assert Path(tmpdir, "file1.tmp").exists()
        print(f"Dry run: found {found} files, deleted {deleted}")

        # Actual deletion
        found, deleted = click_commands.delete_files(tmpdir, "*.tmp", False)
        assert found == 2
        assert deleted == 2
        assert not Path(tmpdir, "file1.tmp").exists()
        assert Path(tmpdir, "file3.txt").exists()
        print(f"Actual run: found {found} files, deleted {deleted}")


def test_directory_stats():
    """Test directory statistics calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure
        Path(tmpdir, "file1.txt").write_text("Hello")
        Path(tmpdir, "file2.txt").write_text("World")
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "file3.txt").write_text("!")

        files, dirs, size = click_commands.directory_stats(tmpdir)

        assert files == 3
        assert dirs >= 1  # At least subdir
        assert size > 0
        print(f"Stats: {files} files, {dirs} dirs, {size} bytes")


def test_click_integration():
    """Demonstrate integration with Click commands."""
    import click
    from click.testing import CliRunner

    @click.group()
    def cli():
        """File management CLI tool."""
        pass

    @cli.command()
    @click.argument('directory')
    @click.option('-r', '--recursive', is_flag=True, help='Recursive listing')
    @click.option('-e', '--extension', multiple=True, help='Filter by extension')
    def list(directory, recursive, extension):
        """List files in directory."""
        exts = list(extension) if extension else None
        files = click_commands.list_files(directory, recursive, exts)
        for f in files:
            click.echo(f)
        click.echo(f"\nTotal: {len(files)} files")

    @cli.command()
    @click.argument('directory')
    def stats(directory):
        """Show directory statistics."""
        files, dirs, size = click_commands.directory_stats(directory)
        click.echo(f"Files: {files}")
        click.echo(f"Directories: {dirs}")
        click.echo(f"Total size: {size} bytes")

    # Test the CLI
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").touch()
        Path(tmpdir, "file2.py").touch()

        # Test list command
        result = runner.invoke(cli, ['list', tmpdir])
        assert result.exit_code == 0
        assert "Total: 2 files" in result.output
        print("\nClick integration test:")
        print(result.output)

        # Test stats command
        result = runner.invoke(cli, ['stats', tmpdir])
        assert result.exit_code == 0
        assert "Files: 2" in result.output


def test_error_handling():
    """Test error handling for invalid paths."""
    try:
        click_commands.list_files("/nonexistent/directory", False, None)
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        print(f"Correctly raised FileNotFoundError: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Click Commands Example Tests")
    print("=" * 60)

    test_list_files_non_recursive()
    test_list_files_recursive()
    test_copy_files()
    test_copy_files_overwrite()
    test_delete_files()
    test_directory_stats()
    test_click_integration()
    test_error_handling()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
