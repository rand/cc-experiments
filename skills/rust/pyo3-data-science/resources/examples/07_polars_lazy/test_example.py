"""Test Polars lazy evaluation."""

import pytest

try:
    import polars as pl
    import polars_lazy
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pytest.skip("Polars not installed", allow_module_level=True)


def test_lazy_execution():
    """Test lazy DataFrame execution."""
    lazy_df = polars_lazy.create_lazy_df()
    result = polars_lazy.execute_lazy(lazy_df)
    assert isinstance(result, pl.DataFrame)
    assert result.shape == (5, 2)


if __name__ == "__main__":
    if POLARS_AVAILABLE:
        test_lazy_execution()
        print("All tests passed!")
