"""Test suite for custom_converters module."""
import pytest
import custom_converters as cc

def test_color_from_dict():
    result = cc.make_color_darker({"r": 100, "g": 150, "b": 200}, 50)
    assert result == (50, 100, 150)

def test_color_from_tuple():
    result = cc.make_color_darker((100, 150, 200), 50)
    assert result == (50, 100, 150)

def test_color_from_hex():
    result = cc.make_color_darker("#FF0000", 50)
    assert result[0] == 205  # 255 - 50

def test_coordinate():
    dist = cc.distance_between({"x": 0.0, "y": 0.0}, (3.0, 4.0))
    assert abs(dist - 5.0) < 0.01

def test_duration():
    result = cc.sleep_for({"hours": 1, "minutes": 30, "seconds": 45})
    assert "5445" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
