"""Test Apache Arrow operations."""

import pytest

try:
    import pyarrow as pa
    import arrow_basic
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False
    pytest.skip("PyArrow not installed", allow_module_level=True)


def test_create_arrow_table():
    """Test Arrow table creation."""
    table = arrow_basic.create_arrow_table()
    assert isinstance(table, pa.Table)
    assert arrow_basic.num_rows(table) == 5


def test_get_schema():
    """Test schema extraction."""
    table = arrow_basic.create_arrow_table()
    schema = arrow_basic.get_schema(table)
    assert "id" in schema
    assert "value" in schema


if __name__ == "__main__":
    if ARROW_AVAILABLE:
        test_create_arrow_table()
        test_get_schema()
        print("All tests passed!")
