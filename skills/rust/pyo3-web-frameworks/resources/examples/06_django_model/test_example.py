"""Test suite for django_model."""

import pytest
import django_model


def test_bulk_validate():
    """Test bulk validation."""
    data = ["valid", "", "x" * 101]
    results = django_model.bulk_validate(data)
    assert results == [True, False, False]


def test_filter_fields():
    """Test field filtering."""
    json_data = '{"name": "test", "age": 30, "secret": "hidden"}'
    filtered = django_model.filter_fields(json_data, ["name", "age"])
    assert "name" in filtered
    assert "age" in filtered
    assert "secret" not in filtered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
