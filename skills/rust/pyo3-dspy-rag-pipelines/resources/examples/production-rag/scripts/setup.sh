#!/bin/bash
# Setup script for Production RAG system

set -e

echo "Production RAG System - Setup"
echo "=============================="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "Error: Rust/Cargo is not installed"
    exit 1
fi

echo "✓ All prerequisites found"

# Create .env from example if not exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠ Please edit .env and add your OPENAI_API_KEY"
else
    echo "✓ .env file exists"
fi

# Start infrastructure
echo ""
echo "Starting infrastructure (Qdrant + Redis)..."
docker-compose up -d qdrant redis

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check Qdrant
echo "Checking Qdrant..."
until curl -s http://localhost:6333/healthz > /dev/null 2>&1; do
    echo "  Waiting for Qdrant..."
    sleep 2
done
echo "✓ Qdrant is ready"

# Check Redis
echo "Checking Redis..."
until docker exec production-rag-redis redis-cli ping > /dev/null 2>&1; do
    echo "  Waiting for Redis..."
    sleep 2
done
echo "✓ Redis is ready"

# Create Qdrant collection
echo ""
echo "Creating Qdrant collection..."
curl -X PUT http://localhost:6333/collections/documents \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }' > /dev/null 2>&1 || echo "⚠ Collection may already exist"

echo "✓ Qdrant collection ready"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --quiet sentence-transformers openai torch 2>&1 | grep -v "Requirement already satisfied" || true
echo "✓ Python dependencies installed"

# Build Rust application
echo ""
echo "Building Rust application..."
cargo build --release

echo ""
echo "=============================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your OPENAI_API_KEY"
echo "  2. Run: cargo run --release"
echo "  3. Test: ./scripts/test_api.sh"
echo ""
echo "Services:"
echo "  - RAG API: http://localhost:8080"
echo "  - Qdrant: http://localhost:6333/dashboard"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
