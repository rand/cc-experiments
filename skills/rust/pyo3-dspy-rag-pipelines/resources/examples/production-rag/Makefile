.PHONY: help setup build run test clean docker-build docker-up docker-down lint format check

# Default target
help:
	@echo "Production RAG System - Available Commands"
	@echo "=========================================="
	@echo "setup          - Run initial setup (infrastructure + dependencies)"
	@echo "build          - Build the Rust application"
	@echo "run            - Run the application"
	@echo "test           - Run tests"
	@echo "lint           - Run clippy linter"
	@echo "format         - Format code with rustfmt"
	@echo "check          - Run cargo check"
	@echo "docker-build   - Build Docker image"
	@echo "docker-up      - Start all services with Docker Compose"
	@echo "docker-down    - Stop all services"
	@echo "clean          - Clean build artifacts"
	@echo ""

# Setup infrastructure and dependencies
setup:
	@./scripts/setup.sh

# Build the application
build:
	cargo build --release

# Run the application
run:
	cargo run --release

# Run tests
test:
	cargo test

# Run API tests
test-api:
	@./scripts/test_api.sh

# Run integration tests
test-integration:
	cargo test --test integration

# Lint with clippy
lint:
	cargo clippy -- -D warnings

# Format code
format:
	cargo fmt

# Check formatting
format-check:
	cargo fmt -- --check

# Run cargo check
check:
	cargo check

# Build Docker image
docker-build:
	docker build -t production-rag:latest .

# Start all services
docker-up:
	docker-compose up -d

# Stop all services
docker-down:
	docker-compose down

# View logs
docker-logs:
	docker-compose logs -f

# Start only infrastructure (Qdrant + Redis)
infra-up:
	docker-compose up -d qdrant redis

# Stop infrastructure
infra-down:
	docker-compose down qdrant redis

# Clean build artifacts
clean:
	cargo clean
	rm -rf target/

# Full clean including Docker volumes
clean-all: clean
	docker-compose down -v

# Watch and rebuild on changes
watch:
	cargo watch -x 'run --release'

# Generate documentation
docs:
	cargo doc --no-deps --open

# Check dependencies for updates
deps-update:
	cargo update

# Audit dependencies for security issues
deps-audit:
	cargo audit

# Benchmark
bench:
	cargo bench

# Profile with flamegraph
profile:
	cargo flamegraph --release

# Create Qdrant collection
qdrant-create-collection:
	@curl -X PUT http://localhost:6333/collections/documents \
		-H "Content-Type: application/json" \
		-d '{"vectors": {"size": 384, "distance": "Cosine"}}'

# Delete Qdrant collection
qdrant-delete-collection:
	@curl -X DELETE http://localhost:6333/collections/documents

# Show Qdrant collection info
qdrant-info:
	@curl http://localhost:6333/collections/documents | jq

# Redis CLI
redis-cli:
	docker exec -it production-rag-redis redis-cli

# Check system health
health:
	@curl -s http://localhost:8080/health | jq

# Show metrics
metrics:
	@curl -s http://localhost:8080/metrics | grep rag_

# Load test with Apache Bench
load-test:
	@echo '{"query": "What is Rust?", "top_k": 3}' > /tmp/query.json
	ab -n 100 -c 10 -p /tmp/query.json -T application/json \
		http://localhost:8080/query

# Python client example
client:
	@python3 scripts/client.py

# Install development tools
install-tools:
	cargo install cargo-watch cargo-audit cargo-flamegraph
	pip3 install black mypy ruff
