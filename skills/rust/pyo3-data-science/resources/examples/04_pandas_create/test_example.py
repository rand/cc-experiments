"""Test Pandas DataFrame creation from Rust."""

import pandas as pd
import pytest
import pandas_create


def test_create_simple_dataframe():
    """Test simple DataFrame creation."""
    df = pandas_create.create_simple_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert list(df.columns) == ['id', 'value', 'name']
    assert df['id'].tolist() == [1, 2, 3, 4, 5]
    assert df['name'].tolist() == ['Alice', 'Bob', 'Charlie', 'David', 'Eve']


def test_create_from_vecs():
    """Test DataFrame from vectors."""
    ids = [1, 2, 3]
    values = [10.5, 20.5, 30.5]
    names = ["Alice", "Bob", "Charlie"]

    df = pandas_create.create_from_vecs(ids, values, names)

    assert len(df) == 3
    assert df['id'].tolist() == ids
    assert df['value'].tolist() == values
    assert df['name'].tolist() == names


def test_create_from_vecs_mismatch():
    """Test error on mismatched vector lengths."""
    with pytest.raises(ValueError, match="All vectors must have same length"):
        pandas_create.create_from_vecs([1, 2], [10.5], ["Alice"])


def test_create_time_series():
    """Test time series DataFrame creation."""
    df = pandas_create.create_time_series("2024-01-01", 10)

    assert len(df) == 10
    assert 'date' in df.columns
    assert 'value' in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['date'])


def test_create_complex_dataframe():
    """Test complex DataFrame creation."""
    df = pandas_create.create_complex_dataframe(9)

    assert len(df) == 9
    assert set(df.columns) == {'id', 'category', 'value', 'is_even'}
    assert set(df['category'].unique()) == {'A', 'B', 'C'}
    assert df['is_even'].dtype == bool


def test_create_and_transform():
    """Test DataFrame creation with transformation."""
    df = pandas_create.create_and_transform(5, 2.5)

    assert len(df) == 5
    assert 'original' in df.columns
    assert 'transformed' in df.columns

    for i in range(5):
        assert abs(df['transformed'].iloc[i] - df['original'].iloc[i] * 2.5) < 1e-10


def test_extract_column():
    """Test column extraction."""
    df = pandas_create.create_simple_dataframe()
    ids = pandas_create.extract_column(df, 'id')

    assert ids == [1, 2, 3, 4, 5]


def test_get_shape():
    """Test shape extraction."""
    df = pandas_create.create_complex_dataframe(10)
    rows, cols = pandas_create.get_shape(df)

    assert rows == 10
    assert cols == 4


def test_records_to_dataframe():
    """Test conversion from Record objects."""
    records = [
        pandas_create.Record(1, "Alice", 95.5),
        pandas_create.Record(2, "Bob", 87.3),
        pandas_create.Record(3, "Charlie", 92.1),
    ]

    df = pandas_create.records_to_dataframe(records)

    assert len(df) == 3
    assert list(df.columns) == ['id', 'name', 'score']
    assert df['id'].tolist() == [1, 2, 3]
    assert df['name'].tolist() == ['Alice', 'Bob', 'Charlie']
    assert df['score'].tolist() == [95.5, 87.3, 92.1]


def test_record_class():
    """Test Record class."""
    record = pandas_create.Record(1, "Test", 100.0)

    assert record.id == 1
    assert record.name == "Test"
    assert record.score == 100.0

    # Test mutation
    record.score = 95.0
    assert record.score == 95.0


if __name__ == "__main__":
    test_create_simple_dataframe()
    test_create_from_vecs()
    test_create_from_vecs_mismatch()
    test_create_time_series()
    test_create_complex_dataframe()
    test_create_and_transform()
    test_extract_column()
    test_get_shape()
    test_records_to_dataframe()
    test_record_class()
    print("All tests passed!")
