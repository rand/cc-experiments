#!/bin/bash
set -e

echo "================================"
echo "Qdrant Integration Quick Start"
echo "================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "Step 1: Starting Qdrant with Docker Compose..."
docker-compose up -d

echo ""
echo "Step 2: Waiting for Qdrant to be ready..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo "Qdrant is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo ""
    echo "Error: Qdrant did not start in time"
    echo "Check logs with: docker-compose logs qdrant"
    exit 1
fi

echo ""
echo "Step 3: Building Rust example..."
cargo build --release

echo ""
echo "Step 4: Running Rust example..."
cargo run --release

echo ""
echo "================================"
echo "Quick Start Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  - Run Python examples: python examples/python_client.py"
echo "  - Run DSPy integration: python examples/dspy_integration.py"
echo "  - View Qdrant dashboard: http://localhost:6333/dashboard"
echo "  - Stop Qdrant: docker-compose down"
echo ""
