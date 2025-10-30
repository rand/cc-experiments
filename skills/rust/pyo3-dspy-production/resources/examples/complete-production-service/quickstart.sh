#!/bin/bash
set -e

echo "==================================================================="
echo "Complete Production DSpy Service - Quick Start"
echo "==================================================================="
echo ""

# Check for required tools
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after you've added your API key to .env..."
fi

# Verify API key is set
if grep -q "sk-your-openai-api-key-here" .env; then
    echo "⚠️  WARNING: It looks like you haven't set your OPENAI_API_KEY in .env"
    echo "   The service will start but predictions may fail."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Please edit .env and set your OPENAI_API_KEY, then run this script again."
        exit 1
    fi
fi

echo "Starting services with Docker Compose..."
echo ""
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Wait for service to be ready
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✓ Service is healthy!"
        break
    fi
    echo "  Waiting for service to start... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Service failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "==================================================================="
echo "Services are running!"
echo "==================================================================="
echo ""
echo "Available endpoints:"
echo "  • Application:  http://localhost:8080"
echo "  • Health check: http://localhost:8080/health"
echo "  • Metrics:      http://localhost:8080/metrics"
echo "  • Costs:        http://localhost:8080/costs"
echo "  • Prometheus:   http://localhost:9090"
echo "  • Grafana:      http://localhost:3000 (admin/admin)"
echo ""
echo "Quick test commands:"
echo "  • Health check:  make test-health"
echo "  • Prediction:    make test-predict"
echo "  • Metrics:       make test-metrics"
echo "  • Costs:         make test-costs"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
echo "==================================================================="
echo ""

# Run a quick health check
echo "Running quick health check..."
curl -s http://localhost:8080/health | python3 -m json.tool || echo "(Install jq for formatted output: brew install jq)"

echo ""
echo "Ready! Try making a prediction:"
echo ""
echo 'curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '"'"'{
    "request_id": "test-1",
    "model": "gpt-3.5-turbo",
    "input": "What is 2+2?",
    "parameters": {},
    "use_cache": true
  }'"'"' | python3 -m json.tool'
echo ""
