.PHONY: help build test run docker-build docker-run docker-compose-up docker-compose-down k8s-deploy k8s-delete clean

# Default target
.DEFAULT_GOAL := help

# Variables
IMAGE_NAME := dspy-production-service
IMAGE_TAG := latest
NAMESPACE := default

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Development
# =============================================================================

build: ## Build the project
	cargo build --release

test: ## Run tests
	cargo test --all-features

run: ## Run the service locally
	cargo run --release

check: ## Run clippy and format checks
	cargo clippy --all-features -- -D warnings
	cargo fmt -- --check

fmt: ## Format code
	cargo fmt

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run: ## Run Docker container
	docker run -d \
		--name dspy-service \
		-p 8080:8080 \
		-e REDIS_URL=redis://host.docker.internal:6379 \
		-e OPENAI_API_KEY=${OPENAI_API_KEY} \
		$(IMAGE_NAME):$(IMAGE_TAG)

docker-stop: ## Stop Docker container
	docker stop dspy-service || true
	docker rm dspy-service || true

docker-logs: ## View Docker container logs
	docker logs -f dspy-service

# =============================================================================
# Docker Compose
# =============================================================================

docker-compose-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-compose-down: ## Stop all services with Docker Compose
	docker-compose down

docker-compose-logs: ## View Docker Compose logs
	docker-compose logs -f

docker-compose-build: ## Build and start with Docker Compose
	docker-compose up -d --build

# =============================================================================
# Kubernetes
# =============================================================================

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-delete: ## Delete from Kubernetes
	kubectl delete -f k8s/hpa.yaml || true
	kubectl delete -f k8s/service.yaml || true
	kubectl delete -f k8s/deployment.yaml || true
	kubectl delete -f k8s/configmap.yaml || true

k8s-status: ## Check Kubernetes deployment status
	kubectl get pods -l app=dspy-production-service
	kubectl get svc dspy-production-service
	kubectl get hpa dspy-production-service-hpa

k8s-logs: ## View Kubernetes pod logs
	kubectl logs -f -l app=dspy-production-service --all-containers=true

k8s-port-forward: ## Port forward to Kubernetes service
	kubectl port-forward svc/dspy-production-service 8080:80

# =============================================================================
# Testing
# =============================================================================

test-health: ## Test health endpoint
	curl -s http://localhost:8080/health | jq

test-ready: ## Test readiness endpoint
	curl -s http://localhost:8080/ready

test-metrics: ## Test metrics endpoint
	curl -s http://localhost:8080/metrics | head -20

test-predict: ## Test prediction endpoint
	curl -s -X POST http://localhost:8080/v1/predict \
		-H "Content-Type: application/json" \
		-d '{"request_id": "test-123", "model": "gpt-3.5-turbo", "input": "Hello, world!", "parameters": {}, "use_cache": true}' \
		| jq

test-costs: ## Test cost metrics endpoint
	curl -s http://localhost:8080/costs | jq

test-config: ## Test config endpoint
	curl -s http://localhost:8080/config | jq

# =============================================================================
# Monitoring
# =============================================================================

prometheus: ## Open Prometheus UI
	open http://localhost:9090

grafana: ## Open Grafana UI
	open http://localhost:3000

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts
	cargo clean
	rm -rf target/

distclean: clean docker-compose-down ## Complete cleanup
	docker rmi $(IMAGE_NAME):$(IMAGE_TAG) || true
	docker volume prune -f
