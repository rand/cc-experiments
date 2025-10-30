#!/usr/bin/env bash
set -euo pipefail

echo "Setting up ChromaDB Basic Example"
echo "=================================="
echo

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo
echo "Upgrading pip..."
pip install --upgrade pip

# Install required packages
echo
echo "Installing Python dependencies..."
pip install chromadb dspy-ai openai

# Verify installations
echo
echo "Verifying installations..."
python3 -c "import chromadb; print(f'ChromaDB version: {chromadb.__version__}')" || {
    echo "Error: Failed to import chromadb"
    exit 1
}

python3 -c "import dspy; print('DSPy installed successfully')" || {
    echo "Error: Failed to import dspy"
    exit 1
}

python3 -c "import openai; print(f'OpenAI version: {openai.__version__}')" || {
    echo "Error: Failed to import openai"
    exit 1
}

# Check for OpenAI API key
echo
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Warning: OPENAI_API_KEY environment variable is not set"
    echo "Please set it before running the example:"
    echo "  export OPENAI_API_KEY='your-key-here'"
else
    echo "OPENAI_API_KEY is set"
fi

echo
echo "Setup complete!"
echo
echo "To build and run the example:"
echo "  1. Make sure OPENAI_API_KEY is set: export OPENAI_API_KEY='your-key'"
echo "  2. Build: cargo build"
echo "  3. Run: cargo run"
echo
echo "To activate the virtual environment in your shell:"
echo "  source venv/bin/activate"
