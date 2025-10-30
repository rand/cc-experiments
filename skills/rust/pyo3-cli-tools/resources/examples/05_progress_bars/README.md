# Example 05: Progress Bars and Spinners

Demonstrates creating progress indicators with PyO3 including bars, spinners, and multi-progress displays.

## Key Components

- **ProgressBar**: Full-featured progress bar with percentage, ETA
- **Spinner**: Animated spinner with Unicode frames
- **MultiProgress**: Multiple concurrent progress bars

## Building

```bash
pip install maturin
maturin develop --release
python test_example.py
```

## Usage

```python
import progress_bars
import time

# Progress bar
pb = progress_bars.ProgressBar(100, "Processing")
pb.start()
for i in range(100):
    pb.update(1)
    time.sleep(0.01)
pb.finish()

# Spinner
spinner = progress_bars.Spinner("Loading")
spinner.start()
# do work...
spinner.stop()
```

## Next Steps

- Example 06: Parallel file processing with progress
