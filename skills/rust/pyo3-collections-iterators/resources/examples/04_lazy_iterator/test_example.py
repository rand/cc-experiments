"""Test lazy iterator functionality."""

import lazy_iterator


def test_fibonacci():
    """Test Fibonacci lazy iterator."""
    fib = lazy_iterator.Fibonacci(max_value=100)

    result = list(fib)
    assert result == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def test_fibonacci_unlimited():
    """Test Fibonacci without limit (manually stopped)."""
    fib = lazy_iterator.Fibonacci(max_value=None)

    result = []
    for i, val in enumerate(fib):
        if i >= 10:
            break
        result.append(val)

    assert result == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]


def test_lazy_file_reader():
    """Test lazy file reading."""
    content = """line 1
line 2
line 3
line 4"""

    reader = lazy_iterator.LazyFileReader(content)
    lines = list(reader)

    assert len(lines) == 4
    assert lines[0] == "line 1"
    assert lines[3] == "line 4"


def test_filtered_iterator():
    """Test filtered lazy iteration."""
    content = """apple
banana
apricot
cherry
avocado"""

    reader = lazy_iterator.LazyFileReader(content)
    filtered = reader.filter_prefix("a")

    result = list(filtered)
    assert result == ["apple", "apricot", "avocado"]


def test_lazy_range_identity():
    """Test lazy range with identity transform."""
    lazy_range = lazy_iterator.LazyRange(0, 5, 1, None)

    result = list(lazy_range)
    assert result == [0, 1, 2, 3, 4]


def test_lazy_range_square():
    """Test lazy range with square transform."""
    lazy_range = lazy_iterator.LazyRange(0, 5, 1, "square")

    result = list(lazy_range)
    assert result == [0, 1, 4, 9, 16]


def test_lazy_range_double():
    """Test lazy range with double transform."""
    lazy_range = lazy_iterator.LazyRange(1, 6, 1, "double")

    result = list(lazy_range)
    assert result == [2, 4, 6, 8, 10]


def test_chained_iterator():
    """Test chaining two lazy ranges."""
    range1 = lazy_iterator.LazyRange(0, 3, 1, None)
    range2 = lazy_iterator.LazyRange(10, 13, 1, None)

    chained = range1.chain(range2)
    result = list(chained)

    assert result == [0, 1, 2, 10, 11, 12]


def test_lazy_evaluation():
    """Test that iteration is truly lazy (no computation until needed)."""
    # Create a large Fibonacci iterator
    fib = lazy_iterator.Fibonacci(max_value=10**15)

    # Only consume first 5 items
    result = []
    for i, val in enumerate(fib):
        if i >= 5:
            break
        result.append(val)

    # Should only compute 5 values, not all
    assert result == [0, 1, 1, 2, 3]


def test_iterator_composition():
    """Test composing multiple lazy operations."""
    # Create range with transformation
    lazy_range = lazy_iterator.LazyRange(1, 10, 1, "square")

    # Filter evens using Python
    evens = [x for x in lazy_range if x % 2 == 0]

    assert evens == [4, 16, 36, 64]


if __name__ == "__main__":
    test_fibonacci()
    test_fibonacci_unlimited()
    test_lazy_file_reader()
    test_filtered_iterator()
    test_lazy_range_identity()
    test_lazy_range_square()
    test_lazy_range_double()
    test_chained_iterator()
    test_lazy_evaluation()
    test_iterator_composition()
    print("All tests passed!")
