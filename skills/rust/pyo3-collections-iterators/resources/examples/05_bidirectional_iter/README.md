# Example 05: Bidirectional Iterator

Master bidirectional iteration, peekable iterators, and window-based iteration patterns.

## What You'll Learn

- Implementing forward and reverse iteration
- Creating peekable iterators (lookahead without consuming)
- Building window iterators for sliding window algorithms
- Using VecDeque for efficient bidirectional operations

## Components

- **BiDirectionalDeque**: Double-ended queue with push/pop from both ends
- **PeekableIterator**: Look ahead without consuming values
- **WindowIterator**: Sliding windows over sequences

## Usage

```python
import bidirectional_iter

# Bidirectional deque
deque = bidirectional_iter.BiDirectionalDeque([1, 2, 3, 4, 5])
deque.pop_front()  # 1
deque.pop_back()   # 5

# Peekable iterator
it = bidirectional_iter.PeekableIterator([1, 2, 3])
it.peek()    # 1 (doesn't consume)
next(it)     # 1 (now consumed)

# Window iterator
windows = bidirectional_iter.WindowIterator([1, 2, 3, 4], 2)
list(windows)  # [[1,2], [2,3], [3,4]]
```

## Real-World Applications

- Parser lookahead
- Sliding window algorithms
- Undo/redo stacks
- LRU caches

Build: `maturin develop && python test_example.py`
