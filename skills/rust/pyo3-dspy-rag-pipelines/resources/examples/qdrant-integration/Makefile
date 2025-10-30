.PHONY: help build run test clean docker-up docker-down docker-logs install-deps python-example

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Rust binary
	cargo build --release

run: ## Run the example
	cargo run --release

test: ## Run tests
	cargo test

test-integration: docker-up ## Run integration tests with Qdrant
	@sleep 5
	cargo test --test integration
	$(MAKE) docker-down

bench: ## Run benchmarks
	cargo bench

clean: ## Clean build artifacts
	cargo clean
	rm -rf target/

docker-up: ## Start Qdrant with Docker Compose
	docker-compose up -d
	@echo "Waiting for Qdrant to be ready..."
	@sleep 3
	@curl -s http://localhost:6333/health || echo "Qdrant may not be ready yet"

docker-down: ## Stop Qdrant
	docker-compose down

docker-logs: ## Show Qdrant logs
	docker-compose logs -f qdrant

docker-clean: ## Remove Qdrant data volume
	docker-compose down -v

install-deps: ## Install Python dependencies
	pip install -r requirements.txt

python-example: ## Run Python DSPy integration example
	python examples/dspy_integration.py

check: ## Check code with clippy
	cargo clippy -- -D warnings

fmt: ## Format code
	cargo fmt

fmt-check: ## Check code formatting
	cargo fmt -- --check

doc: ## Generate documentation
	cargo doc --open

watch: ## Watch for changes and rebuild
	cargo watch -x build

health: ## Check Qdrant health
	@curl -s http://localhost:6333/health | jq .

collections: ## List Qdrant collections
	@curl -s http://localhost:6333/collections | jq .

all: clean build test ## Clean, build, and test

dev: docker-up ## Start development environment
	@echo "Development environment ready!"
	@echo "Qdrant: http://localhost:6333"
	@echo ""
	@echo "Run 'make run' to start the example"
	@echo "Run 'make python-example' for Python integration"
