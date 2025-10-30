"""
WASM Basic Example Tests

This example can be built for both WASM and Python:
- WASM: wasm-pack build --target web
- Python: maturin develop (requires not targeting wasm32)
"""

# Only test if built as Python extension
try:
    import wasm_basic

    def test_process_array():
        result = wasm_basic.py_process_array([1.0, 2.0, 3.0])
        assert result == [2.0, 4.0, 6.0]

    if __name__ == "__main__":
        print("Testing WASM Basic (Python mode)")
        result = wasm_basic.py_process_array([1.0, 2.0, 3.0, 4.0, 5.0])
        print(f"Processed: {result}")

except ImportError:
    print("Module not built. For Python: maturin develop")
    print("For WASM: wasm-pack build --target web")
    print("\nNote: This example demonstrates dual-target compilation.")
    print("The WASM build creates JavaScript bindings.")
