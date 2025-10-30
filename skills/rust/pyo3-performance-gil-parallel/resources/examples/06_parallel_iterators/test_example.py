"""Test suite for advanced parallel iterator patterns."""
import parallel_iterators

def test_all():
    # Map
    result = parallel_iterators.parallel_map_with_error([1.0, 2.0, 3.0], 2.0)
    assert result == [0.5, 1.0, 1.5]

    # Flat map
    result = parallel_iterators.parallel_flat_map([(0, 3), (5, 8)])
    assert sorted(result) == [0, 1, 2, 5, 6, 7]

    # Filter map
    result = parallel_iterators.parallel_filter_map([1, 2, 3, 4, 5])
    assert sorted(result) == [4, 16]

    # Fold
    sum_val, min_val, max_val = parallel_iterators.parallel_fold([1.0, 2.0, 3.0, 4.0, 5.0])
    assert sum_val == 15.0 and min_val == 1.0 and max_val == 5.0

    # Partition
    below, above = parallel_iterators.parallel_partition([1, 5, 3, 8, 2], 5)
    assert sorted(below) == [1, 2, 3] and sorted(above) == [5, 8]

    # Find
    pos = parallel_iterators.parallel_find([10, 20, 30, 40], 30)
    assert pos == 2

    # Predicates
    any_neg, all_pos = parallel_iterators.parallel_predicates([1, 2, -3, 4])
    assert any_neg == True and all_pos == False

    # Zip
    result = parallel_iterators.parallel_zip_add([1.0, 2.0], [3.0, 4.0])
    assert result == [4.0, 6.0]

    # Moving average
    result = parallel_iterators.parallel_moving_average([1.0, 2.0, 3.0, 4.0, 5.0], 3)
    assert abs(result[0] - 2.0) < 0.01

    # Matrix transpose
    matrix = [[1.0, 2.0], [3.0, 4.0]]
    result = parallel_iterators.parallel_matrix_transpose(matrix)
    assert result == [[1.0, 3.0], [2.0, 4.0]]

    print("All parallel iterator tests passed!")

if __name__ == "__main__":
    test_all()
