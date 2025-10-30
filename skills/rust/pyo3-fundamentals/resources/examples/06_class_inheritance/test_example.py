"""Test suite for class_inheritance module."""
import pytest
import class_inheritance as ci

def test_circle():
    c = ci.Circle(5.0)
    assert abs(c.area() - 78.54) < 0.01

def test_employee_manager():
    emp = ci.Employee("Alice", 30, "E001", "Engineering", 100000.0)
    mgr = ci.Manager(emp, 5, 50000.0)
    assert mgr.get_name() == "Alice"

def test_vehicle():
    car = ci.Vehicle.car("Toyota", "Camry", 2020, 4)
    assert "Car(4 doors)" in car.vehicle_type

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
