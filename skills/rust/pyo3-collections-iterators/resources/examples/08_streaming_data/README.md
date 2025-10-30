# Example 08: Streaming Data

Process large datasets efficiently using streaming and chunking strategies.

## What You'll Learn

- Reading large files in batches
- Chunked data processing
- CSV streaming
- Buffered stream processing
- Memory-efficient data handling

## Components

- **StreamingLineReader**: Read large text files in batches
- **ChunkedProcessor**: Process data in fixed-size chunks
- **StreamingCSVReader**: Parse CSV data incrementally
- **BufferedStream**: Buffer data until batch size reached

## Usage

```python
import streaming_data

# Stream large file
reader = streaming_data.StreamingLineReader("huge.log", batch_size=1000)
for batch in reader:
    process_batch(batch)  # Process 1000 lines at a time

# Chunked processing
processor = streaming_data.ChunkedProcessor(data, chunk_size=100)
for chunk in processor:
    analyze(chunk)

# CSV streaming
csv_reader = streaming_data.StreamingCSVReader(csv_text)
for row in csv_reader:
    process_row(row)

# Buffered stream
stream = streaming_data.BufferedStream(buffer_size=1000)
for item in incoming_data:
    if batch := stream.push(item):
        process_batch(batch)
```

## Real-World Applications

- Log file analysis (GB+ files)
- Large dataset processing
- Real-time data streams
- ETL pipelines with memory constraints

Build: `maturin develop && python test_example.py`
