#!/bin/bash
# Verification script for all examples

set -e

EXAMPLES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$EXAMPLES_DIR"

echo "=== PyO3 Examples Verification ==="
echo ""

# Count examples
EXAMPLE_DIRS=(01_* 02_* 03_* 04_* 05_* 06_* 07_* 08_* 09_* 10_*)
echo "Found ${#EXAMPLE_DIRS[@]} examples"
echo ""

# Verify each example has required files
for ex in "${EXAMPLE_DIRS[@]}"; do
    echo "Checking $ex..."
    
    if [[ ! -f "$ex/src/lib.rs" ]]; then
        echo "  ❌ Missing src/lib.rs"
        exit 1
    fi
    
    if [[ ! -f "$ex/Cargo.toml" ]]; then
        echo "  ❌ Missing Cargo.toml"
        exit 1
    fi
    
    if [[ ! -f "$ex/pyproject.toml" ]]; then
        echo "  ❌ Missing pyproject.toml"
        exit 1
    fi
    
    if [[ ! -f "$ex/test_example.py" ]]; then
        echo "  ❌ Missing test_example.py"
        exit 1
    fi
    
    if [[ ! -f "$ex/README.md" ]]; then
        echo "  ❌ Missing README.md"
        exit 1
    fi
    
    echo "  ✅ All required files present"
done

echo ""
echo "=== Verification Complete ==="
echo ""
echo "To build and test an example:"
echo "  cd 01_basic_module"
echo "  maturin develop"
echo "  pytest test_example.py -v"
echo ""
echo "To test all examples:"
echo "  for ex in 01_* 02_* 03_* 04_* 05_* 06_* 07_* 08_* 09_* 10_*; do"
echo "    (cd \$ex && maturin develop -q && pytest test_example.py -q)"
echo "  done"
