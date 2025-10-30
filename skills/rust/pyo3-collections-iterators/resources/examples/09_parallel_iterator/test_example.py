"""Test parallel iteration."""
import parallel_iterator

def test_parallel_map():
    mapper = parallel_iterator.ParallelMapper()
    result = mapper.map_square([1, 2, 3, 4, 5])
    assert result == [1, 4, 9, 16, 25]

def test_parallel_filter():
    filter_obj = parallel_iterator.ParallelFilter()
    result = filter_obj.filter_even([1, 2, 3, 4, 5, 6])
    assert result == [2, 4, 6]

def test_parallel_prime_filter():
    filter_obj = parallel_iterator.ParallelFilter()
    result = filter_obj.filter_prime([2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    assert set(result) == {2, 3, 5, 7, 11}

def test_parallel_reduce():
    reducer = parallel_iterator.ParallelReducer()
    assert reducer.sum([1, 2, 3, 4, 5]) == 15
    assert reducer.min([5, 2, 8, 1, 9]) == 1
    assert reducer.max([5, 2, 8, 1, 9]) == 9
    assert reducer.count_if([1, 5, 3, 8, 2], 3) == 2  # Count > 3

def test_parallel_sort():
    sorter = parallel_iterator.ParallelSorter()
    result = sorter.sort([5, 2, 8, 1, 9])
    assert result == [1, 2, 5, 8, 9]

    result = sorter.sort_descending([5, 2, 8, 1, 9])
    assert result == [9, 8, 5, 2, 1]

def test_parallel_batch():
    processor = parallel_iterator.ParallelBatchProcessor(3)
    result = processor.process_batches([1, 2, 3, 4, 5])
    assert result == [2, 4, 6, 8, 10]

    sums = processor.sum_batches([1, 2, 3, 4, 5, 6])
    assert sums == [6, 15]  # [1+2+3, 4+5+6]

if __name__ == "__main__":
    test_parallel_map()
    test_parallel_filter()
    test_parallel_prime_filter()
    test_parallel_reduce()
    test_parallel_sort()
    test_parallel_batch()
    print("All tests passed!")
