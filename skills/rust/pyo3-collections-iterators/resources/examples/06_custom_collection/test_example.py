"""Test custom collections."""
import custom_collection

def test_hybrid_collection():
    hc = custom_collection.HybridCollection()
    hc.add("apple")
    hc.add("banana")
    hc.add("cherry")
    assert len(hc) == 3
    assert "banana" in hc
    assert hc.get_by_index(1) == "banana"
    assert hc.get_index("cherry") == 2

def test_priority_queue():
    pq = custom_collection.PriorityQueue()
    pq.push(1, "low")
    pq.push(10, "high")
    pq.push(5, "medium")
    assert pq.pop() == (10, "high")
    assert pq.peek() == (5, "medium")

def test_circular_buffer():
    cb = custom_collection.CircularBuffer(3)
    cb.push(1)
    cb.push(2)
    cb.push(3)
    cb.push(4)  # Overwrites oldest
    assert list(cb) == [2, 3, 4]

if __name__ == "__main__":
    test_hybrid_collection()
    test_priority_queue()
    test_circular_buffer()
    print("All tests passed!")
