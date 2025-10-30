"""Test suite for progress bars example."""
import time
import progress_bars


def test_progress_bar():
    """Test basic progress bar."""
    pb = progress_bars.ProgressBar(100, "Processing")
    pb.start()

    for i in range(0, 101, 10):
        pb.set(i)
        time.sleep(0.1)

    pb.finish()
    print("\nProgress bar test completed")


def test_progress_update():
    """Test incremental updates."""
    pb = progress_bars.ProgressBar(50, "Loading")
    pb.start()

    for _ in range(50):
        pb.update(1)
        time.sleep(0.02)

    pb.finish()
    print("Incremental update test completed")


def test_spinner():
    """Test spinner animation."""
    spinner = progress_bars.Spinner("Processing")
    spinner.start()
    time.sleep(2)
    spinner.stop()
    print("✓ Spinner test completed")


def test_multi_progress():
    """Test multiple progress bars."""
    mp = progress_bars.MultiProgress()
    mp.add_bar("Task 1", 100)
    mp.add_bar("Task 2", 200)
    mp.add_bar("Task 3", 150)
    mp.render()

    for i in range(100):
        mp.update_bar("Task 1", i)
        mp.update_bar("Task 2", i * 2)
        mp.update_bar("Task 3", int(i * 1.5))
        time.sleep(0.02)

    mp.clear()
    print("\n\nMulti-progress test completed")


if __name__ == "__main__":
    print("=" * 60)
    print("Progress Bars Example Tests")
    print("=" * 60)

    test_progress_bar()
    test_progress_update()
    test_spinner()
    test_multi_progress()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
