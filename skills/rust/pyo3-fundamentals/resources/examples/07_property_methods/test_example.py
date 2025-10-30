"""Test suite for property_methods module."""
import pytest
import property_methods as pm

def test_temperature():
    t = pm.Temperature(0.0)
    assert abs(t.fahrenheit - 32.0) < 0.01
    t.fahrenheit = 212.0
    assert abs(t.celsius - 100.0) < 0.01

def test_validated_account():
    acc = pm.ValidatedAccount(1000.0, 100.0)
    assert acc.available_balance == 900.0

def test_person_with_name():
    p = pm.PersonWithName("John", "Doe")
    assert p.full_name == "John Doe"
    assert p.initials == "JD"

def test_smart_rectangle():
    r = pm.SmartRectangle(4.0, 5.0)
    assert r.area == 20.0
    assert not r.is_square

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
