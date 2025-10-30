"""
pytest fixtures for python_tests module
"""
import pytest


@pytest.fixture
def sample_data():
    """Provide standard test data."""
    return [1.0, 2.0, 3.0, 4.0, 5.0]


@pytest.fixture
def large_data():
    """Provide large dataset for performance tests."""
    return list(range(1000))


@pytest.fixture
def negative_data():
    """Provide negative numbers."""
    return [-5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0]


@pytest.fixture
def single_value():
    """Provide single value."""
    return [42.0]


@pytest.fixture
def empty_data():
    """Provide empty list."""
    return []


@pytest.fixture
def float_data():
    """Provide floating point data."""
    return [1.5, 2.7, 3.2, 4.8, 5.1]
