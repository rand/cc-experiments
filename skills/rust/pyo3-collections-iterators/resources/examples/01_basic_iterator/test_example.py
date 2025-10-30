"""Test basic iterator functionality."""

import basic_iterator


def test_number_range():
    """Test NumberRange iterator."""
    # Test forward range
    numbers = list(basic_iterator.NumberRange(0, 5, 1))
    assert numbers == [0, 1, 2, 3, 4]

    # Test with step
    evens = list(basic_iterator.NumberRange(0, 10, 2))
    assert evens == [0, 2, 4, 6, 8]

    # Test backwards
    backwards = list(basic_iterator.NumberRange(5, 0, -1))
    assert backwards == [5, 4, 3, 2, 1]


def test_counter():
    """Test Counter and CounterIterator."""
    counter = basic_iterator.Counter()
    assert counter.get_count() == 0

    # Increment counter
    for _ in range(5):
        counter.increment()

    assert counter.get_count() == 5

    # Iterate over counter
    values = list(counter.iter())
    assert values == [0, 1, 2, 3, 4]


def test_sum_iterator():
    """Test consuming Python iterator from Rust."""
    # Create a Python iterator
    py_iter = iter([1, 2, 3, 4, 5])

    # Sum it in Rust
    result = basic_iterator.sum_iterator(py_iter)
    assert result == 15


def test_create_iterator():
    """Test creating Python iterator from Rust."""
    rust_list = [10, 20, 30, 40]
    py_iter = basic_iterator.create_iterator(rust_list)

    # Consume the iterator
    values = list(py_iter)
    assert values == [10, 20, 30, 40]


def test_iterator_protocol():
    """Test that iterators implement Python iterator protocol."""
    range_iter = basic_iterator.NumberRange(0, 3, 1)

    # Should support iter()
    assert iter(range_iter) is range_iter

    # Should support next()
    assert next(range_iter) == 0
    assert next(range_iter) == 1
    assert next(range_iter) == 2

    # Should raise StopIteration when exhausted
    try:
        next(range_iter)
        assert False, "Should have raised StopIteration"
    except StopIteration:
        pass


def test_iterator_reusability():
    """Test that Counter.iter() creates new iterators."""
    counter = basic_iterator.Counter()
    for _ in range(3):
        counter.increment()

    # First iteration
    iter1 = counter.iter()
    values1 = list(iter1)
    assert values1 == [0, 1, 2]

    # Second iteration should work independently
    iter2 = counter.iter()
    values2 = list(iter2)
    assert values2 == [0, 1, 2]


if __name__ == "__main__":
    test_number_range()
    test_counter()
    test_sum_iterator()
    test_create_iterator()
    test_iterator_protocol()
    test_iterator_reusability()
    print("All tests passed!")
