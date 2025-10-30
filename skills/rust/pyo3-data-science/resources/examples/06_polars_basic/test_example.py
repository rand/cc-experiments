"""Test basic Polars DataFrame operations."""

import pytest

try:
    import polars as pl
    import polars_basic
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pytest.skip("Polars not installed", allow_module_level=True)


def test_create_polars_df():
    """Test Polars DataFrame creation."""
    df = polars_basic.create_polars_df()
    assert isinstance(df, pl.DataFrame)
    assert df.shape == (5, 3)


def test_filter_dataframe():
    """Test filtering."""
    df = polars_basic.create_polars_df()
    filtered = polars_basic.filter_dataframe(df, "value", 20.0)
    assert filtered.shape[0] < df.shape[0]


def test_select_columns():
    """Test column selection."""
    df = polars_basic.create_polars_df()
    selected = polars_basic.select_columns(df, ["id", "value"])
    assert selected.shape[1] == 2


def test_sort_dataframe():
    """Test sorting."""
    df = polars_basic.create_polars_df()
    sorted_df = polars_basic.sort_dataframe(df, "value", False)
    assert sorted_df.shape == df.shape


def test_get_shape():
    """Test shape extraction."""
    df = polars_basic.create_polars_df()
    rows, cols = polars_basic.get_shape(df)
    assert rows == 5
    assert cols == 3


if __name__ == "__main__":
    if POLARS_AVAILABLE:
        test_create_polars_df()
        test_filter_dataframe()
        test_select_columns()
        test_sort_dataframe()
        test_get_shape()
        print("All tests passed!")
