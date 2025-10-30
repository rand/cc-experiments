"""Test Pandas GroupBy operations."""

import numpy as np
import pandas as pd
import pytest
import pandas_groupby


def test_fast_groupby_sum():
    """Test fast groupby sum."""
    groups = np.array([1, 2, 1, 2, 1, 3])
    values = np.array([10.0, 20.0, 15.0, 25.0, 5.0, 30.0])

    result = pandas_groupby.fast_groupby_sum(groups, values)

    assert result[1] == 30.0  # 10 + 15 + 5
    assert result[2] == 45.0  # 20 + 25
    assert result[3] == 30.0


def test_fast_groupby_mean():
    """Test fast groupby mean."""
    groups = np.array([1, 2, 1, 2, 1])
    values = np.array([10.0, 20.0, 20.0, 30.0, 30.0])

    result = pandas_groupby.fast_groupby_mean(groups, values)

    assert result[1] == 20.0  # (10 + 20 + 30) / 3
    assert result[2] == 25.0  # (20 + 30) / 2


def test_fast_groupby_agg():
    """Test fast groupby with multiple aggregations."""
    groups = np.array([1, 1, 2, 2])
    values = np.array([10.0, 20.0, 5.0, 15.0])

    result = pandas_groupby.fast_groupby_agg(groups, values)

    assert result[1]['sum'] == 30.0
    assert result[1]['mean'] == 15.0
    assert result[1]['count'] == 2
    assert result[1]['min'] == 10.0
    assert result[1]['max'] == 20.0


def test_fast_value_counts():
    """Test value counts."""
    groups = np.array([1, 2, 1, 3, 2, 1])

    result = pandas_groupby.fast_value_counts(groups)

    assert result[1] == 3
    assert result[2] == 2
    assert result[3] == 1


def test_filter_groups_by_size():
    """Test filtering groups by size."""
    groups = np.array([1, 1, 1, 2, 2, 3])

    mask = pandas_groupby.filter_groups_by_size(groups, min_size=2)

    # Groups 1 and 2 have size >= 2, group 3 has size 1
    expected = np.array([True, True, True, True, True, False])
    np.testing.assert_array_equal(mask, expected)


if __name__ == "__main__":
    test_fast_groupby_sum()
    test_fast_groupby_mean()
    test_fast_groupby_agg()
    test_fast_value_counts()
    test_filter_groups_by_size()
    print("All tests passed!")
