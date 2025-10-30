#!/bin/bash
# Run the pydantic-integration example with proper Python environment

set -e

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Check if pydantic is installed
if ! python3 -c "import pydantic" 2>/dev/null; then
    echo "Installing pydantic..."
    pip3 install -q pydantic
fi

# Build the project
echo "Building project..."
cargo build --release

# Run the example
echo "Running pydantic-integration example..."
./target/release/pydantic-integration
