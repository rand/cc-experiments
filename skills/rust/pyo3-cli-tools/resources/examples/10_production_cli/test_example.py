"""Test suite for production CLI tool."""
import tempfile
from pathlib import Path
import production_cli


def test_config():
    """Test configuration management."""
    config = production_cli.CliConfig()
    assert config.verbose == False
    assert config.threads > 0
    print(f"Config: threads={config.threads}, format={config.output_format}")

    # Test save/load
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        filepath = f.name

    try:
        config.save(filepath)
        config2 = production_cli.CliConfig()
        config2.load(filepath)
        assert config2.threads == config.threads
        print("Config save/load works")
    finally:
        Path(filepath).unlink()


def test_file_processor():
    """Test file analysis."""
    processor = production_cli.FileProcessor(production_cli.CliConfig())

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        Path(tmpdir, "file1.py").write_text("line1\nline2\nline3\n")
        Path(tmpdir, "file2.txt").write_text("hello world\n")

        # Analyze directory
        results = processor.analyze_directory(tmpdir, None, None)
        assert len(results) == 2
        print(f"Analyzed {len(results)} files")

        # Generate report
        report = processor.generate_report(results)
        assert report['total_files'] == 2
        print(f"Report: {report}")


def test_search():
    """Test content search."""
    processor = production_cli.FileProcessor(production_cli.CliConfig())

    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "file1.txt").write_text("hello world\n")
        Path(tmpdir, "file2.txt").write_text("goodbye world\n")

        results = processor.search_content(tmpdir, "world", True)
        assert len(results) == 2
        print(f"Found pattern in {len(results)} files")


if __name__ == "__main__":
    print("=" * 60)
    print("Production CLI Tests")
    print("=" * 60)
    test_config()
    test_file_processor()
    test_search()
    print("\nAll tests passed!")
