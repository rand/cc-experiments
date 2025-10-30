use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// Progress bar state
#[pyclass]
pub struct ProgressBar {
    total: usize,
    current: Arc<Mutex<usize>>,
    start_time: Arc<Mutex<Option<Instant>>>,
    message: String,
}

#[pymethods]
impl ProgressBar {
    #[new]
    fn new(total: usize, message: Option<String>) -> Self {
        ProgressBar {
            total,
            current: Arc::new(Mutex::new(0)),
            start_time: Arc::new(Mutex::new(None)),
            message: message.unwrap_or_else(|| "Progress".to_string()),
        }
    }

    fn start(&self) {
        let mut start = self.start_time.lock().unwrap();
        *start = Some(Instant::now());
        self.render();
    }

    fn update(&self, n: usize) {
        let mut current = self.current.lock().unwrap();
        *current += n;
        drop(current);
        self.render();
    }

    fn set(&self, n: usize) {
        let mut current = self.current.lock().unwrap();
        *current = n;
        drop(current);
        self.render();
    }

    fn finish(&self) {
        let mut current = self.current.lock().unwrap();
        *current = self.total;
        drop(current);
        self.render();
        println!();
    }

    fn render(&self) {
        let current = *self.current.lock().unwrap();
        let percent = if self.total > 0 {
            (current as f64 / self.total as f64) * 100.0
        } else {
            0.0
        };

        let bar_width = 40;
        let filled = ((percent / 100.0) * bar_width as f64) as usize;
        let empty = bar_width - filled;

        let bar = format!("[{}{}]", "█".repeat(filled), "░".repeat(empty));

        // Calculate ETA
        let eta = if let Some(start) = *self.start_time.lock().unwrap() {
            if current > 0 {
                let elapsed = start.elapsed().as_secs_f64();
                let rate = current as f64 / elapsed;
                let remaining = (self.total - current) as f64 / rate;
                format!(" ETA: {:.1}s", remaining)
            } else {
                String::new()
            }
        } else {
            String::new()
        };

        print!("\r{}: {} {:.1}% {}/{}{}",
               self.message, bar, percent, current, self.total, eta);
        use std::io::Write;
        std::io::stdout().flush().unwrap();
    }
}

/// Spinner animation
#[pyclass]
pub struct Spinner {
    message: String,
    running: Arc<Mutex<bool>>,
    handle: Arc<Mutex<Option<std::thread::JoinHandle<()>>>>,
}

#[pymethods]
impl Spinner {
    #[new]
    fn new(message: Option<String>) -> Self {
        Spinner {
            message: message.unwrap_or_else(|| "Loading".to_string()),
            running: Arc::new(Mutex::new(false)),
            handle: Arc::new(Mutex::new(None)),
        }
    }

    fn start(&self) {
        let mut running = self.running.lock().unwrap();
        *running = true;
        drop(running);

        let running_clone = Arc::clone(&self.running);
        let message = self.message.clone();

        let handle = std::thread::spawn(move || {
            let frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
            let mut i = 0;

            while *running_clone.lock().unwrap() {
                print!("\r{} {}", frames[i % frames.len()], message);
                use std::io::Write;
                std::io::stdout().flush().unwrap();

                std::thread::sleep(Duration::from_millis(80));
                i += 1;
            }

            print!("\r\x1B[K");
            std::io::stdout().flush().unwrap();
        });

        let mut h = self.handle.lock().unwrap();
        *h = Some(handle);
    }

    fn stop(&self) {
        let mut running = self.running.lock().unwrap();
        *running = false;
        drop(running);

        // Wait for thread to finish
        std::thread::sleep(Duration::from_millis(100));
    }
}

/// Multi-progress bar manager
#[pyclass]
pub struct MultiProgress {
    bars: Arc<Mutex<Vec<(String, usize, usize)>>>,
}

#[pymethods]
impl MultiProgress {
    #[new]
    fn new() -> Self {
        MultiProgress {
            bars: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn add_bar(&self, id: String, total: usize) {
        let mut bars = self.bars.lock().unwrap();
        bars.push((id, 0, total));
    }

    fn update_bar(&self, id: String, current: usize) {
        let mut bars = self.bars.lock().unwrap();
        if let Some(bar) = bars.iter_mut().find(|(bar_id, _, _)| bar_id == &id) {
            bar.1 = current;
        }
        drop(bars);
        self.render();
    }

    fn render(&self) {
        let bars = self.bars.lock().unwrap();

        // Move cursor up and clear lines
        print!("\x1B[{}A", bars.len());

        for (id, current, total) in bars.iter() {
            let percent = if *total > 0 {
                (*current as f64 / *total as f64) * 100.0
            } else {
                0.0
            };

            let bar_width = 20;
            let filled = ((percent / 100.0) * bar_width as f64) as usize;
            let empty = bar_width - filled;

            println!("{:<20} [{}{}] {:.1}%",
                     id,
                     "█".repeat(filled),
                     "░".repeat(empty),
                     percent);
        }

        use std::io::Write;
        std::io::stdout().flush().unwrap();
    }

    fn clear(&self) {
        let mut bars = self.bars.lock().unwrap();
        bars.clear();
    }
}

#[pymodule]
fn progress_bars(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<ProgressBar>()?;
    m.add_class::<Spinner>()?;
    m.add_class::<MultiProgress>()?;
    Ok(())
}
