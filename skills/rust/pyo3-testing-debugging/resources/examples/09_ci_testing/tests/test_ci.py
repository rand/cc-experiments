"""
CI/CD tests
"""
import sys
import pytest
from ci_testing import add, multiply, process_data


class TestBasicOperations:
    """Test basic operations"""

    def test_add(self):
        assert add(2, 3) == 5
        assert add(-1, 1) == 0

    def test_multiply(self):
        assert multiply(2, 3) == 6
        assert multiply(-2, 3) == -6

    def test_process_data(self):
        data = [1.0, 2.0, 3.0]
        assert process_data(data) == 6.0


class TestPlatformSpecific:
    """Platform-specific tests"""

    def test_platform_info(self):
        """Verify test runs on expected platforms."""
        assert sys.platform in ["linux", "darwin", "win32"]

    @pytest.mark.skipif(sys.platform != "linux", reason="Linux only")
    def test_linux_specific(self):
        """Linux-specific test."""
        assert add(1, 1) == 2

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_macos_specific(self):
        """macOS-specific test."""
        assert add(1, 1) == 2

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows_specific(self):
        """Windows-specific test."""
        assert add(1, 1) == 2


class TestPythonVersions:
    """Test Python version compatibility"""

    def test_python_version(self):
        """Verify Python version is supported."""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 8
