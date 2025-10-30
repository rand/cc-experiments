"""Tests for module_constants example."""
import pytest
import module_constants as mc

def test_constants():
    assert mc.VERSION == "1.0.0"
    assert mc.MAX_CONNECTIONS == 100
    assert mc.DEFAULT_TIMEOUT == 30.0
    assert abs(mc.PI - 3.14159) < 0.001

def test_status_enum():
    status = mc.Status.Pending
    assert str(status) == "Pending"

def test_log_level():
    level = mc.LogLevel.Error
    assert level.to_int() == 40
    level = mc.LogLevel.from_string("info")
    assert level.to_int() == 20

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
