"""Test iterator combinators."""
import iterator_combinators

def test_map():
    it = iterator_combinators.MapIterator([1, 2, 3, 4], "square")
    assert list(it) == [1, 4, 9, 16]

def test_filter():
    it = iterator_combinators.FilterIterator([1, 2, 3, 4, 5, 6], "even", None)
    assert list(it) == [2, 4, 6]

def test_chain():
    it = iterator_combinators.ChainIterator([1, 2], [3, 4])
    assert list(it) == [1, 2, 3, 4]

def test_zip():
    it = iterator_combinators.ZipIterator([1, 2, 3], ["a", "b", "c"])
    assert list(it) == [(1, "a"), (2, "b"), (3, "c")]

def test_take():
    it = iterator_combinators.TakeIterator([1, 2, 3, 4, 5], 3)
    assert list(it) == [1, 2, 3]

def test_skip():
    it = iterator_combinators.SkipIterator([1, 2, 3, 4, 5], 2)
    assert list(it) == [3, 4, 5]

if __name__ == "__main__":
    test_map()
    test_filter()
    test_chain()
    test_zip()
    test_take()
    test_skip()
    print("All tests passed!")
