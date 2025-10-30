"""Test streaming data processing."""
import streaming_data
import tempfile
import os

def test_chunked_processor():
    processor = streaming_data.ChunkedProcessor(list(range(10)), 3)
    chunks = list(processor)
    assert len(chunks) == 4
    assert chunks[0] == [0, 1, 2]
    assert chunks[-1] == [9]

def test_chunked_sum():
    processor = streaming_data.ChunkedProcessor(list(range(10)), 3)
    sums = processor.process_sum()
    assert sums == [3, 12, 21, 9]  # Sum of each chunk

def test_csv_reader():
    csv = """name,age,city
Alice,30,NYC
Bob,25,LA
Charlie,35,SF"""

    reader = streaming_data.StreamingCSVReader(csv)
    rows = list(reader)
    assert len(rows) == 4
    assert rows[0] == ["name", "age", "city"]
    assert rows[1] == ["Alice", "30", "NYC"]

def test_buffered_stream():
    stream = streaming_data.BufferedStream(3)
    assert stream.push(1) is None
    assert stream.push(2) is None
    result = stream.push(3)
    assert result == [1, 2, 3]

def test_file_streaming():
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        for i in range(100):
            f.write(f"line {i}\n")
        fname = f.name

    try:
        reader = streaming_data.StreamingLineReader(fname, 25)
        batches = list(reader)
        assert len(batches) == 4  # 100 lines / 25 per batch
        assert len(batches[0]) == 25
    finally:
        os.unlink(fname)

if __name__ == "__main__":
    test_chunked_processor()
    test_chunked_sum()
    test_csv_reader()
    test_buffered_stream()
    test_file_streaming()
    print("All tests passed!")
