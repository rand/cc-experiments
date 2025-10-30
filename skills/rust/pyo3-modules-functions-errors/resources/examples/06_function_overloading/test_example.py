"""Tests for function_overloading example."""
import pytest
import function_overloading as fo

def test_add_specific_types():
    assert fo.add_ints(2, 3) == 5
    assert fo.add_floats(2.5, 3.5) == 6.0

def test_add_any_integers():
    assert fo.add_any(10, 20) == 30

def test_add_any_floats():
    assert fo.add_any(1.5, 2.5) == 4.0

def test_add_any_strings():
    assert fo.add_any("Hello, ", "World!") == "Hello, World!"

def test_format_variants():
    assert fo.format_basic("hello") == "hello"
    assert fo.format_basic("hello", uppercase=True) == "HELLO"
    assert fo.format_advanced("  hello  ", trim=True) == "hello"
    assert fo.format_full("hi", repeat=3) == "hihihi"

def test_config_builder():
    cfg = fo.Config()
    assert "localhost" in repr(cfg)
    cfg.with_host("example.com")
    assert "example.com" in repr(cfg)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
