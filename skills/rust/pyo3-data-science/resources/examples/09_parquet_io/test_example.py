"""Test Parquet file I/O."""

import pandas as pd
import pytest
import parquet_io
import tempfile
import os


def test_write_read_parquet():
    """Test writing and reading Parquet files."""
    df = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'value': [10.5, 20.3, 15.7, 30.2, 25.1]
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.parquet")

        # Write
        parquet_io.write_parquet(df, path)
        assert parquet_io.parquet_exists(path)

        # Read
        df_read = parquet_io.read_parquet(path)
        pd.testing.assert_frame_equal(df, df_read)


def test_parquet_metadata():
    """Test metadata extraction."""
    df = pd.DataFrame({'x': [1, 2, 3]})

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.parquet")
        parquet_io.write_parquet(df, path)

        try:
            metadata = parquet_io.get_parquet_metadata(path)
            assert metadata['num_rows'] == 3
        except ImportError:
            pytest.skip("PyArrow not installed")


if __name__ == "__main__":
    test_write_read_parquet()
    test_parquet_metadata()
    print("All tests passed!")
