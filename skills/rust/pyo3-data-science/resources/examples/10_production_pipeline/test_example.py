"""Test production data pipeline."""

import pandas as pd
import numpy as np
import pytest
import production_pipeline
import tempfile
import os


def test_process_pipeline():
    """Test complete pipeline."""
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'value': [10.0, 20.0, 30.0]
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "input.csv")
        parquet_path = os.path.join(tmpdir, "output.parquet")

        df.to_csv(csv_path, index=False)

        rows = production_pipeline.process_pipeline(csv_path, parquet_path, 2.0)
        assert rows == 3
        assert os.path.exists(parquet_path)

        # Verify output
        df_out = pd.read_parquet(parquet_path)
        assert 'value_transformed' in df_out.columns
        assert df_out['value_transformed'].tolist() == [20.0, 40.0, 60.0]


def test_validate_pipeline_input():
    """Test input validation."""
    df = pd.DataFrame({'id': [1], 'value': [10.0]})

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "input.csv")
        df.to_csv(csv_path, index=False)

        assert production_pipeline.validate_pipeline_input(csv_path) is True

        # Test missing file
        with pytest.raises(FileNotFoundError):
            production_pipeline.validate_pipeline_input("/nonexistent.csv")


def test_batch_process():
    """Test batch processing."""
    df1 = pd.DataFrame({'id': [1, 2], 'value': [10.0, 20.0]})
    df2 = pd.DataFrame({'id': [3, 4], 'value': [30.0, 40.0]})

    with tempfile.TemporaryDirectory() as tmpdir:
        csv1 = os.path.join(tmpdir, "input1.csv")
        csv2 = os.path.join(tmpdir, "input2.csv")

        df1.to_csv(csv1, index=False)
        df2.to_csv(csv2, index=False)

        total_rows = production_pipeline.batch_process(
            [csv1, csv2],
            tmpdir,
            1.5
        )
        assert total_rows == 4


def test_quality_check():
    """Test data quality checking."""
    values = np.array([1.0, 5.0, 10.0, 15.0, 20.0])

    valid, invalid = production_pipeline.quality_check(values, 5.0, 15.0)
    assert valid == 3  # 5, 10, 15
    assert invalid == 2  # 1, 20


if __name__ == "__main__":
    test_process_pipeline()
    test_validate_pipeline_input()
    test_batch_process()
    test_quality_check()
    print("All tests passed!")
