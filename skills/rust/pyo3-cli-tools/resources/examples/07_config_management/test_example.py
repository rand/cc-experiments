"""Test suite for configuration management."""
import tempfile
from pathlib import Path
import config_management


def test_toml_config():
    """Test TOML configuration loading/saving."""
    config_data = {"host": "localhost", "port": "8080", "debug": "true"}

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.toml') as f:
        f.write('[server]\nhost = "localhost"\nport = 8080\ndebug = true\n')
        filepath = f.name

    try:
        config = config_management.load_toml(filepath)
        assert config is not None
        print(f"Loaded TOML config: {config}")

        # Save it back
        config_management.save_toml(filepath, config)
        assert Path(filepath).exists()
    finally:
        Path(filepath).unlink()


def test_yaml_config():
    """Test YAML configuration loading/saving."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        f.write('host: localhost\nport: 8080\ndebug: true\n')
        filepath = f.name

    try:
        config = config_management.load_yaml(filepath)
        assert config is not None
        print(f"Loaded YAML config: {config}")
    finally:
        Path(filepath).unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("Config Management Tests")
    print("=" * 60)
    test_toml_config()
    test_yaml_config()
    print("\nAll tests passed!")
