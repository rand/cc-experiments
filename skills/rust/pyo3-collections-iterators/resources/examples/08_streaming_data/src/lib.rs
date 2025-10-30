use pyo3::prelude::*;
use std::fs::File;
use std::io::{BufRead, BufReader};

/// Streaming line reader for large files
#[pyclass]
struct StreamingLineReader {
    lines: Vec<String>,
    index: usize,
    batch_size: usize,
}

#[pymethods]
impl StreamingLineReader {
    #[new]
    fn new(filename: String, batch_size: Option<usize>) -> PyResult<Self> {
        let file = File::open(filename)?;
        let reader = BufReader::new(file);
        let lines: Vec<String> = reader.lines().filter_map(Result::ok).collect();

        Ok(StreamingLineReader {
            lines,
            index: 0,
            batch_size: batch_size.unwrap_or(1000),
        })
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<Vec<String>> {
        if slf.index >= slf.lines.len() {
            return None;
        }

        let end = (slf.index + slf.batch_size).min(slf.lines.len());
        let batch = slf.lines[slf.index..end].to_vec();
        slf.index = end;

        if batch.is_empty() {
            None
        } else {
            Some(batch)
        }
    }
}

/// Chunked data processor
#[pyclass]
struct ChunkedProcessor {
    data: Vec<i32>,
    chunk_size: usize,
    index: usize,
}

#[pymethods]
impl ChunkedProcessor {
    #[new]
    fn new(data: Vec<i32>, chunk_size: usize) -> Self {
        ChunkedProcessor {
            data,
            chunk_size,
            index: 0,
        }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<Vec<i32>> {
        if slf.index >= slf.data.len() {
            return None;
        }

        let end = (slf.index + slf.chunk_size).min(slf.data.len());
        let chunk = slf.data[slf.index..end].to_vec();
        slf.index = end;

        Some(chunk)
    }

    /// Process chunk with sum
    fn process_sum(&self) -> Vec<i32> {
        let mut results = Vec::new();
        let mut index = 0;

        while index < self.data.len() {
            let end = (index + self.chunk_size).min(self.data.len());
            let chunk_sum: i32 = self.data[index..end].iter().sum();
            results.push(chunk_sum);
            index = end;
        }

        results
    }
}

/// Streaming CSV parser
#[pyclass]
struct StreamingCSVReader {
    rows: Vec<Vec<String>>,
    index: usize,
}

#[pymethods]
impl StreamingCSVReader {
    #[new]
    fn new(csv_content: String) -> Self {
        let rows: Vec<Vec<String>> = csv_content
            .lines()
            .map(|line| line.split(',').map(|s| s.trim().to_string()).collect())
            .collect();

        StreamingCSVReader { rows, index: 0 }
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> Option<Vec<String>> {
        if slf.index < slf.rows.len() {
            let row = slf.rows[slf.index].clone();
            slf.index += 1;
            Some(row)
        } else {
            None
        }
    }

    fn headers(&self) -> Option<Vec<String>> {
        self.rows.first().cloned()
    }

    fn rows_as_dicts(&self, py: Python) -> PyResult<Vec<PyObject>> {
        use pyo3::types::PyDict;

        if self.rows.is_empty() {
            return Ok(Vec::new());
        }

        let headers = &self.rows[0];
        let mut results = Vec::new();

        for row in &self.rows[1..] {
            let dict = PyDict::new(py);
            for (i, value) in row.iter().enumerate() {
                if let Some(header) = headers.get(i) {
                    dict.set_item(header, value)?;
                }
            }
            results.push(dict.into());
        }

        Ok(results)
    }
}

/// Buffered stream processor
#[pyclass]
struct BufferedStream {
    buffer: Vec<i32>,
    buffer_size: usize,
}

#[pymethods]
impl BufferedStream {
    #[new]
    fn new(buffer_size: usize) -> Self {
        BufferedStream {
            buffer: Vec::with_capacity(buffer_size),
            buffer_size,
        }
    }

    fn push(&mut self, value: i32) -> Option<Vec<i32>> {
        self.buffer.push(value);

        if self.buffer.len() >= self.buffer_size {
            let flushed = self.buffer.clone();
            self.buffer.clear();
            Some(flushed)
        } else {
            None
        }
    }

    fn flush(&mut self) -> Vec<i32> {
        let flushed = self.buffer.clone();
        self.buffer.clear();
        flushed
    }

    fn __len__(&self) -> usize {
        self.buffer.len()
    }
}

#[pymodule]
fn streaming_data(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<StreamingLineReader>()?;
    m.add_class::<ChunkedProcessor>()?;
    m.add_class::<StreamingCSVReader>()?;
    m.add_class::<BufferedStream>()?;
    Ok(())
}
