use pyo3::prelude::*;
use std::sync::mpsc::{channel, Sender, Receiver};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

/// Producer-consumer pattern with channels
#[pyfunction]
fn producer_consumer(
    py: Python,
    items: Vec<f64>,
    worker_count: usize,
) -> PyResult<Vec<f64>> {
    let (tx, rx) = channel();
    let rx = Arc::new(Mutex::new(rx));
    let results = Arc::new(Mutex::new(Vec::new()));

    py.allow_threads(|| {
        // Producer thread
        let producer = {
            let tx = tx.clone();
            thread::spawn(move || {
                for item in items {
                    tx.send(item).unwrap();
                }
                drop(tx); // Close channel
            })
        };

        // Consumer threads
        let consumers: Vec<_> = (0..worker_count)
            .map(|_| {
                let rx = Arc::clone(&rx);
                let results = Arc::clone(&results);
                thread::spawn(move || loop {
                    let item = rx.lock().unwrap().recv();
                    match item {
                        Ok(val) => {
                            let result = val * val;
                            results.lock().unwrap().push(result);
                        }
                        Err(_) => break,
                    }
                })
            })
            .collect();

        producer.join().unwrap();
        for consumer in consumers {
            consumer.join().unwrap();
        }
    });

    let final_results = results.lock().unwrap().clone();
    Ok(final_results)
}

/// Pipeline pattern with multiple stages
#[pyfunction]
fn pipeline_processing(py: Python, numbers: Vec<i64>) -> PyResult<Vec<String>> {
    let (tx1, rx1) = channel();
    let (tx2, rx2) = channel();
    let (tx3, rx3) = channel();

    py.allow_threads(|| {
        // Stage 1: Filter evens
        let stage1 = thread::spawn(move || {
            for num in numbers {
                if num % 2 == 0 {
                    tx1.send(num).unwrap();
                }
            }
        });

        // Stage 2: Square
        let stage2 = thread::spawn(move || {
            while let Ok(num) = rx1.recv() {
                tx2.send(num * num).unwrap();
            }
        });

        // Stage 3: Convert to string
        let stage3 = thread::spawn(move || {
            while let Ok(num) = rx2.recv() {
                tx3.send(num.to_string()).unwrap();
            }
        });

        // Collector
        let collector = thread::spawn(move || {
            let mut results = Vec::new();
            while let Ok(s) = rx3.recv() {
                results.push(s);
            }
            results
        });

        stage1.join().unwrap();
        drop(tx1);
        stage2.join().unwrap();
        drop(tx2);
        stage3.join().unwrap();
        drop(tx3);

        collector.join().unwrap()
    })
}

/// Fan-out / Fan-in pattern
#[pyfunction]
fn fan_out_fan_in(py: Python, tasks: Vec<f64>, workers: usize) -> PyResult<f64> {
    let (work_tx, work_rx) = channel();
    let (result_tx, result_rx) = channel();
    let work_rx = Arc::new(Mutex::new(work_rx));

    let sum = py.allow_threads(|| {
        // Distribute work
        let distributor = thread::spawn(move || {
            for task in tasks {
                work_tx.send(task).unwrap();
            }
        });

        // Workers process
        let worker_handles: Vec<_> = (0..workers)
            .map(|_| {
                let work_rx = Arc::clone(&work_rx);
                let result_tx = result_tx.clone();
                thread::spawn(move || {
                    while let Ok(val) = work_rx.lock().unwrap().recv() {
                        let result = val * val;
                        result_tx.send(result).unwrap();
                    }
                })
            })
            .collect();

        distributor.join().unwrap();
        drop(work_rx);

        for handle in worker_handles {
            handle.join().unwrap();
        }
        drop(result_tx);

        // Collect results
        let mut sum = 0.0;
        while let Ok(result) = result_rx.recv() {
            sum += result;
        }
        sum
    });

    Ok(sum)
}

/// Broadcast pattern - send to all workers
#[pyfunction]
fn broadcast_compute(py: Python, value: f64, worker_count: usize) -> PyResult<Vec<f64>> {
    let senders: Vec<_> = (0..worker_count).map(|_| channel()).collect();

    let results = py.allow_threads(|| {
        // Workers
        let handles: Vec<_> = senders
            .iter()
            .enumerate()
            .map(|(i, (_, rx))| {
                let rx = rx;
                thread::spawn(move || {
                    if let Ok(val) = rx.recv() {
                        val * (i + 1) as f64
                    } else {
                        0.0
                    }
                })
            })
            .collect();

        // Broadcast value
        for (tx, _) in &senders {
            tx.send(value).unwrap();
        }

        // Collect results
        handles.into_iter().map(|h| h.join().unwrap()).collect()
    });

    Ok(results)
}

#[pymodule]
fn channels(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(producer_consumer, m)?)?;
    m.add_function(wrap_pyfunction!(pipeline_processing, m)?)?;
    m.add_function(wrap_pyfunction!(fan_out_fan_in, m)?)?;
    m.add_function(wrap_pyfunction!(broadcast_compute, m)?)?;
    Ok(())
}
