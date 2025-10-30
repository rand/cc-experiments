"""Test suite for generic_types module."""
import pytest
import generic_types as gt

def test_stack():
    stack = gt.Stack()
    stack.push(10)
    stack.push("hello")
    assert stack.size() == 2
    assert stack.pop() == "hello"

def test_int_stack():
    stack = gt.IntStack()
    stack.push(10)
    stack.push(20)
    assert stack.sum() == 30

def test_queue():
    queue = gt.Queue()
    queue.enqueue(1)
    queue.enqueue(2)
    assert queue.dequeue() == 1

def test_typed_container():
    container = gt.TypedContainer()
    container.add_int(42)
    container.add_string("hello")
    assert container.total_items() == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
