"""
Test script for embedded Python example

This is not a traditional test file - the Rust binary embeds Python
and runs it internally. This script demonstrates what the Rust code does.
"""
import sys


def demonstrate_embedding():
    """Show what the Rust embedding example does"""

    print("=== Python Side Demonstration ===\n")

    # Example 1: Simple execution
    print("1. Simple expressions:")
    print(f"   2 + 2 = {2 + 2}")

    # Example 2: Variables
    print("\n2. Variables and computation:")
    rust_value = 42
    multiplier = 3
    result = rust_value * multiplier
    print(f"   {rust_value} * {multiplier} = {result}")

    # Example 3: Standard library
    print("\n3. Standard library:")
    print(f"   Python version: {sys.version}")
    import math

    print(f"   Pi: {math.pi}")
    print(f"   sqrt(16): {math.sqrt(16)}")
    print(f"   sum([1,2,3,4,5]): {sum([1,2,3,4,5])}")

    # Example 4: Functions
    print("\n4. Fibonacci function:")

    def fibonacci(n):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    fibs = [fibonacci(i) for i in range(10)]
    print(f"   First 10: {fibs}")

    # Example 5: Collections
    print("\n5. Collections:")
    py_list = [1, 2, 3, 4, 5]
    py_list.extend([6, 7])
    print(f"   List: {py_list}")

    py_dict = {"name": "Alice", "role": "Developer", "language": "Rust"}
    print(f"   Dict: {py_dict}")

    # Example 6: Data processing
    print("\n6. Data processing function:")

    def process_data(data, operation):
        if operation == "sum":
            return sum(data)
        elif operation == "product":
            result = 1
            for x in data:
                result *= x
            return result
        elif operation == "max":
            return max(data)
        return None

    data = [1, 2, 3, 4, 5]
    print(f"   Sum: {process_data(data, 'sum')}")
    print(f"   Product: {process_data(data, 'product')}")
    print(f"   Max: {process_data(data, 'max')}")

    # Example 7: Error handling
    print("\n7. Error handling:")
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        print(f"   Caught: {type(e).__name__}: {e}")

    try:
        nonexistent_variable
    except NameError as e:
        print(f"   Caught: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("This script demonstrates what the Rust embedded example does.")
    print("To run the actual embedded example, use: cargo run\n")

    demonstrate_embedding()

    print("\n=== Run 'cargo run' to see Rust embedding Python ===")
