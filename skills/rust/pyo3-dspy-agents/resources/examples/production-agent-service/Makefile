.PHONY: help build build-release run run-release test test-unit test-integration clean \
        docker-build docker-run docker-push docker-stop infra-up infra-down logs metrics \
        format lint check install dev

# Variables
BINARY_NAME := production-agent-service
DOCKER_IMAGE := $(BINARY_NAME)
DOCKER_TAG := latest
DOCKER_REGISTRY := # Set to your registry (e.g., ghcr.io/username)

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(CYAN)Production Agent Service - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Build Commands
# =============================================================================

build: ## Build debug binary
	@echo "$(CYAN)Building debug binary...$(NC)"
	cargo build
	@echo "$(GREEN)✓ Build complete: target/debug/server$(NC)"

build-release: ## Build optimized release binary
	@echo "$(CYAN)Building release binary...$(NC)"
	cargo build --release
	@echo "$(GREEN)✓ Build complete: target/release/server$(NC)"

install: ## Install development dependencies
	@echo "$(CYAN)Installing dependencies...$(NC)"
	@echo "Checking Python environment..."
	@python3 -c "import dspy" 2>/dev/null || (echo "$(YELLOW)Installing dspy-ai...$(NC)" && pip install dspy-ai)
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

# =============================================================================
# Run Commands
# =============================================================================

run: build ## Run development server
	@echo "$(CYAN)Starting development server...$(NC)"
	RUST_LOG=debug,production_agent_service=trace cargo run --bin server

run-release: build-release ## Run production server
	@echo "$(CYAN)Starting production server...$(NC)"
	./target/release/server

dev: install infra-up ## Start development environment (infra + server)
	@echo "$(CYAN)Starting development environment...$(NC)"
	@sleep 2
	$(MAKE) run

# =============================================================================
# Test Commands
# =============================================================================

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests
	@echo "$(CYAN)Running unit tests...$(NC)"
	cargo test --lib
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

test-integration: ## Run integration tests
	@echo "$(CYAN)Running integration tests...$(NC)"
	@echo "$(YELLOW)Ensuring infrastructure is running...$(NC)"
	@docker-compose up -d redis prometheus
	@sleep 2
	cargo test --test '*'
	@echo "$(GREEN)✓ Integration tests passed$(NC)"

check: ## Run cargo check
	@echo "$(CYAN)Running cargo check...$(NC)"
	cargo check
	@echo "$(GREEN)✓ Check complete$(NC)"

# =============================================================================
# Code Quality
# =============================================================================

format: ## Format code with rustfmt
	@echo "$(CYAN)Formatting code...$(NC)"
	cargo fmt
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run clippy linter
	@echo "$(CYAN)Running clippy...$(NC)"
	cargo clippy -- -D warnings
	@echo "$(GREEN)✓ Lint complete$(NC)"

# =============================================================================
# Docker Commands
# =============================================================================

docker-build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

docker-run: docker-build ## Run Docker container
	@echo "$(CYAN)Running Docker container...$(NC)"
	docker run -d \
		--name $(BINARY_NAME) \
		-p 3000:3000 \
		-e OPENAI_API_KEY=${OPENAI_API_KEY} \
		-e RUST_LOG=info,production_agent_service=debug \
		--network agent-network \
		$(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Container running at http://localhost:3000$(NC)"

docker-stop: ## Stop and remove Docker container
	@echo "$(CYAN)Stopping Docker container...$(NC)"
	docker stop $(BINARY_NAME) 2>/dev/null || true
	docker rm $(BINARY_NAME) 2>/dev/null || true
	@echo "$(GREEN)✓ Container stopped$(NC)"

docker-push: docker-build ## Push Docker image to registry
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
		echo "$(RED)Error: DOCKER_REGISTRY not set$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Pushing to $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)...$(NC)"
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Image pushed$(NC)"

# =============================================================================
# Infrastructure Commands
# =============================================================================

infra-up: ## Start infrastructure (Redis, Prometheus, Grafana)
	@echo "$(CYAN)Starting infrastructure...$(NC)"
	docker-compose up -d redis prometheus grafana
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	@sleep 5
	@echo "$(GREEN)✓ Infrastructure running$(NC)"
	@echo "  Redis:      http://localhost:6379"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001 (admin/admin)"

infra-down: ## Stop infrastructure
	@echo "$(CYAN)Stopping infrastructure...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Infrastructure stopped$(NC)"

infra-logs: ## View infrastructure logs
	docker-compose logs -f

infra-restart: infra-down infra-up ## Restart infrastructure

# =============================================================================
# Monitoring Commands
# =============================================================================

logs: ## View service logs (Docker Compose)
	docker-compose logs -f agent-service

metrics: ## Query Prometheus metrics
	@echo "$(CYAN)Fetching metrics from http://localhost:3000/api/v1/metrics$(NC)"
	@curl -s http://localhost:3000/api/v1/metrics || echo "$(RED)Error: Service not running$(NC)"

health: ## Check service health
	@echo "$(CYAN)Checking service health...$(NC)"
	@curl -s http://localhost:3000/api/v1/health | jq '.' || echo "$(RED)Error: Service not running$(NC)"

# =============================================================================
# Utility Commands
# =============================================================================

clean: ## Clean build artifacts
	@echo "$(CYAN)Cleaning build artifacts...$(NC)"
	cargo clean
	rm -rf agent_memories/
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-all: clean infra-down ## Clean everything including Docker volumes
	@echo "$(CYAN)Removing Docker volumes...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)✓ All cleaned$(NC)"

# =============================================================================
# Development Workflow Commands
# =============================================================================

watch: ## Watch for changes and rebuild
	@echo "$(CYAN)Watching for changes...$(NC)"
	cargo watch -x 'run --bin server'

bench: ## Run benchmarks
	@echo "$(CYAN)Running benchmarks...$(NC)"
	cargo bench

doc: ## Generate documentation
	@echo "$(CYAN)Generating documentation...$(NC)"
	cargo doc --no-deps --open

# =============================================================================
# Testing Utilities
# =============================================================================

test-query: ## Send test query to service
	@echo "$(CYAN)Sending test query...$(NC)"
	@curl -X POST http://localhost:3000/api/v1/query \
		-H "Content-Type: application/json" \
		-d '{"user_id":"test_user","question":"What is 2+2?"}' | jq '.'

load-test: ## Run simple load test
	@echo "$(CYAN)Running load test (100 requests)...$(NC)"
	@echo '{"user_id":"load_test","question":"Test question"}' > /tmp/query.json
	@ab -n 100 -c 10 -p /tmp/query.json -T application/json \
		http://localhost:3000/api/v1/query
	@rm /tmp/query.json

# =============================================================================
# Deployment Commands
# =============================================================================

deploy-local: build-release infra-up ## Deploy locally with all services
	@echo "$(CYAN)Deploying locally...$(NC)"
	@$(MAKE) run-release &
	@sleep 3
	@$(MAKE) health
	@echo "$(GREEN)✓ Local deployment complete$(NC)"

deploy-docker: ## Deploy full stack with Docker Compose
	@echo "$(CYAN)Deploying with Docker Compose...$(NC)"
	docker-compose up -d
	@echo "$(YELLOW)Waiting for services...$(NC)"
	@sleep 10
	@$(MAKE) health
	@echo "$(GREEN)✓ Docker deployment complete$(NC)"

# =============================================================================
# Database/Memory Commands
# =============================================================================

redis-cli: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

redis-flush: ## Flush all Redis data
	@echo "$(YELLOW)Flushing Redis data...$(NC)"
	docker-compose exec redis redis-cli FLUSHALL
	@echo "$(GREEN)✓ Redis flushed$(NC)"

backup-memories: ## Backup agent memories
	@echo "$(CYAN)Backing up agent memories...$(NC)"
	@mkdir -p backups
	@if [ -d agent_memories ]; then \
		tar -czf backups/memories-$$(date +%Y%m%d-%H%M%S).tar.gz agent_memories; \
		echo "$(GREEN)✓ Backup created$(NC)"; \
	else \
		echo "$(YELLOW)No memories to backup$(NC)"; \
	fi

# =============================================================================
# Information Commands
# =============================================================================

info: ## Display service information
	@echo "$(CYAN)Service Information:$(NC)"
	@echo "  Name:    $(BINARY_NAME)"
	@echo "  Version: $$(cargo read-manifest | jq -r .version)"
	@echo ""
	@echo "$(CYAN)Endpoints:$(NC)"
	@echo "  POST /api/v1/query              - Execute agent query"
	@echo "  GET  /api/v1/metrics            - Prometheus metrics"
	@echo "  GET  /api/v1/health             - Health check"
	@echo "  GET  /api/v1/ready              - Readiness probe"
	@echo "  GET  /api/v1/live               - Liveness probe"
	@echo "  GET  /api/v1/info               - Service info"
	@echo "  POST /api/v1/circuit-breaker/reset - Reset circuit breaker"

status: ## Check all services status
	@echo "$(CYAN)Service Status:$(NC)"
	@echo ""
	@echo "$(CYAN)Docker Containers:$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(CYAN)Service Health:$(NC)"
	@$(MAKE) health 2>/dev/null || echo "$(RED)Service not running$(NC)"
