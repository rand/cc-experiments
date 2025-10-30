#!/usr/bin/env python3
"""
Debug script for testing debugging_setup module
Run under debugger to practice debugging techniques
"""
import sys
import debugging_setup


def test_basic():
    """Test basic operations."""
    print("Testing divide...")
    result = debugging_setup.divide(10.0, 2.0)
    print(f"  Result: {result}")

    print("Testing complex calculation...")
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = debugging_setup.complex_calculation(data)
    print(f"  Result: {result}")


def test_error_cases():
    """Test error cases (good for debugging)."""
    print("\nTesting error cases...")

    try:
        debugging_setup.divide(10.0, 0.0)
    except ValueError as e:
        print(f"  Caught expected error: {e}")

    try:
        debugging_setup.complex_calculation([])
    except ValueError as e:
        print(f"  Caught expected error: {e}")


def test_with_breakpoint():
    """Test with a natural breakpoint location."""
    print("\nTesting with debug output...")
    for i in range(5):
        result = debugging_setup.process_with_debug(i)
        print(f"  {result}")


if __name__ == "__main__":
    print("=== Debugging Setup Test ===\n")

    test_basic()
    test_error_cases()
    test_with_breakpoint()

    print("\n=== All tests completed ===")
