use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use std::sync::mpsc;
use std::thread;

type Job = Box<dyn FnOnce() -> PyResult<f64> + Send + 'static>;

/// Custom thread pool with work stealing capabilities
#[pyclass]
pub struct ThreadPool {
    workers: Vec<Worker>,
    sender: Option<mpsc::Sender<Job>>,
    size: usize,
}

struct Worker {
    id: usize,
    thread: Option<thread::JoinHandle<()>>,
}

impl Worker {
    fn new(id: usize, receiver: Arc<Mutex<mpsc::Receiver<Job>>>) -> Worker {
        let thread = thread::spawn(move || loop {
            let job = receiver.lock().unwrap().recv();

            match job {
                Ok(job) => {
                    let _ = job();
                }
                Err(_) => {
                    break;
                }
            }
        });

        Worker {
            id,
            thread: Some(thread),
        }
    }
}

#[pymethods]
impl ThreadPool {
    #[new]
    fn new(size: usize) -> Self {
        let (sender, receiver) = mpsc::channel();
        let receiver = Arc::new(Mutex::new(receiver));

        let mut workers = Vec::with_capacity(size);

        for id in 0..size {
            workers.push(Worker::new(id, Arc::clone(&receiver)));
        }

        ThreadPool {
            workers,
            sender: Some(sender),
            size,
        }
    }

    fn size(&self) -> usize {
        self.size
    }

    fn execute_batch(&self, py: Python, tasks: Vec<f64>) -> PyResult<Vec<f64>> {
        let results = Arc::new(Mutex::new(vec![0.0; tasks.len()]));
        let (tx, rx) = mpsc::channel();

        py.allow_threads(|| {
            for (i, value) in tasks.into_iter().enumerate() {
                let results = Arc::clone(&results);
                let tx = tx.clone();

                if let Some(sender) = &self.sender {
                    sender
                        .send(Box::new(move || {
                            let result = value * value;
                            results.lock().unwrap()[i] = result;
                            tx.send(()).unwrap();
                            Ok(result)
                        }))
                        .unwrap();
                }
            }
        });

        // Wait for all tasks to complete
        py.allow_threads(|| {
            for _ in 0..results.lock().unwrap().len() {
                rx.recv().unwrap();
            }
        });

        let final_results = results.lock().unwrap().clone();
        Ok(final_results)
    }

    fn shutdown(&mut self) {
        drop(self.sender.take());

        for worker in &mut self.workers {
            if let Some(thread) = worker.thread.take() {
                thread.join().unwrap();
            }
        }
    }

    fn __del__(&mut self) {
        self.shutdown();
    }
}

/// Simple task queue for work distribution
#[pyclass]
pub struct TaskQueue {
    queue: Arc<Mutex<Vec<f64>>>,
}

#[pymethods]
impl TaskQueue {
    #[new]
    fn new(tasks: Vec<f64>) -> Self {
        TaskQueue {
            queue: Arc::new(Mutex::new(tasks)),
        }
    }

    fn process_parallel(&self, py: Python, thread_count: usize) -> PyResult<Vec<f64>> {
        let results = Arc::new(Mutex::new(Vec::new()));

        py.allow_threads(|| {
            let handles: Vec<_> = (0..thread_count)
                .map(|_| {
                    let queue = Arc::clone(&self.queue);
                    let results = Arc::clone(&results);

                    thread::spawn(move || loop {
                        let task = {
                            let mut q = queue.lock().unwrap();
                            q.pop()
                        };

                        match task {
                            Some(value) => {
                                let result = value * value;
                                results.lock().unwrap().push(result);
                            }
                            None => break,
                        }
                    })
                })
                .collect();

            for handle in handles {
                handle.join().unwrap();
            }
        });

        let final_results = results.lock().unwrap().clone();
        Ok(final_results)
    }

    fn remaining(&self) -> usize {
        self.queue.lock().unwrap().len()
    }
}

/// Work-stealing deque for load balancing
#[pyfunction]
fn process_work_stealing(
    py: Python,
    tasks: Vec<f64>,
    thread_count: usize,
) -> PyResult<Vec<f64>> {
    if tasks.is_empty() {
        return Ok(Vec::new());
    }

    let chunk_size = (tasks.len() + thread_count - 1) / thread_count;
    let chunks: Vec<_> = tasks.chunks(chunk_size).map(|c| c.to_vec()).collect();

    let queues: Vec<_> = chunks
        .into_iter()
        .map(|chunk| Arc::new(Mutex::new(chunk)))
        .collect();

    let results = Arc::new(Mutex::new(Vec::new()));

    py.allow_threads(|| {
        let handles: Vec<_> = (0..thread_count)
            .map(|i| {
                let queues = queues.clone();
                let results = Arc::clone(&results);

                thread::spawn(move || {
                    // Process local queue first
                    loop {
                        let task = queues[i].lock().unwrap().pop();

                        match task {
                            Some(value) => {
                                let result = value * value;
                                results.lock().unwrap().push(result);
                            }
                            None => {
                                // Try stealing from other queues
                                let mut stolen = false;
                                for (j, queue) in queues.iter().enumerate() {
                                    if i != j {
                                        if let Some(value) = queue.lock().unwrap().pop() {
                                            let result = value * value;
                                            results.lock().unwrap().push(result);
                                            stolen = true;
                                            break;
                                        }
                                    }
                                }
                                if !stolen {
                                    break;
                                }
                            }
                        }
                    }
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }
    });

    let final_results = results.lock().unwrap().clone();
    Ok(final_results)
}

/// Adaptive thread pool that adjusts size based on workload
#[pyfunction]
fn adaptive_parallel(py: Python, tasks: Vec<f64>) -> PyResult<Vec<f64>> {
    let optimal_threads = if tasks.len() < 1000 {
        2
    } else if tasks.len() < 100_000 {
        4
    } else {
        thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(4)
    };

    process_work_stealing(py, tasks, optimal_threads)
}

#[pymodule]
fn thread_pool(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ThreadPool>()?;
    m.add_class::<TaskQueue>()?;
    m.add_function(wrap_pyfunction!(process_work_stealing, m)?)?;
    m.add_function(wrap_pyfunction!(adaptive_parallel, m)?)?;
    Ok(())
}
