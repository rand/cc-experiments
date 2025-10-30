"""Test bidirectional iteration."""
import bidirectional_iter

def test_deque_bidirectional():
    deque = bidirectional_iter.BiDirectionalDeque([1, 2, 3, 4, 5])
    assert deque.pop_front() == 1
    assert deque.pop_back() == 5
    assert len(deque) == 3

def test_deque_push():
    deque = bidirectional_iter.BiDirectionalDeque([2, 3])
    deque.push_front(1)
    deque.push_back(4)
    assert list(deque) == [1, 2, 3, 4]

def test_forward_iteration():
    deque = bidirectional_iter.BiDirectionalDeque([1, 2, 3])
    assert list(deque) == [1, 2, 3]

def test_reverse_iteration():
    deque = bidirectional_iter.BiDirectionalDeque([1, 2, 3])
    assert list(reversed(deque)) == [3, 2, 1]

def test_peekable():
    it = bidirectional_iter.PeekableIterator([1, 2, 3, 4])
    assert it.peek() == 1
    assert next(it) == 1
    assert it.peek() == 2
    assert it.peek_n(1) == 3

def test_window_iterator():
    it = bidirectional_iter.WindowIterator([1, 2, 3, 4, 5], 3)
    windows = list(it)
    assert windows == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]

if __name__ == "__main__":
    test_deque_bidirectional()
    test_deque_push()
    test_forward_iteration()
    test_reverse_iteration()
    test_peekable()
    test_window_iterator()
    print("All tests passed!")
