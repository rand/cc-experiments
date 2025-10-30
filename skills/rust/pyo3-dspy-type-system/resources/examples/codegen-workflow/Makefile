.PHONY: build run clean regenerate check test fmt clippy help

# Default target
help:
	@echo "Codegen Workflow - Available targets:"
	@echo ""
	@echo "  make build      - Build the project (generates types)"
	@echo "  make run        - Run the example"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make regenerate - Clean and rebuild (full regeneration)"
	@echo "  make check      - Check code without building"
	@echo "  make fmt        - Format code"
	@echo "  make clippy     - Run clippy lints"
	@echo "  make show-gen   - Display generated types"
	@echo "  make test-gen   - Test code generation manually"
	@echo ""

# Build the project (triggers codegen)
build:
	@echo "Building project and generating types..."
	cargo build
	@echo ""
	@echo "Generated types:"
	@grep "pub struct" src/generated.rs | wc -l | xargs echo "  Struct count:"

# Run the example
run:
	@echo "Running example..."
	cargo run

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	cargo clean
	@echo "Note: src/generated.rs preserved (edit signatures.txt to regenerate)"

# Clean and rebuild (full regeneration)
regenerate:
	@echo "Full regeneration..."
	cargo clean
	cargo build --verbose
	@echo ""
	@echo "Generation complete. Generated types:"
	@cat src/generated.rs | grep "pub struct"

# Check code without building
check:
	cargo check

# Run tests (when added)
test:
	cargo test

# Format code
fmt:
	cargo fmt
	@echo "Code formatted"

# Run clippy
clippy:
	cargo clippy -- -D warnings

# Show generated types
show-gen:
	@echo "Generated types in src/generated.rs:"
	@echo "===================================="
	@cat src/generated.rs
	@echo ""
	@echo "Struct count: $(shell grep -c 'pub struct' src/generated.rs)"

# Test code generation manually
test-gen:
	@echo "Testing code generation manually..."
	python3 ../../signature_codegen.py signatures.txt /tmp/test_generated.rs
	@echo ""
	@echo "Generated to /tmp/test_generated.rs:"
	@head -20 /tmp/test_generated.rs
	@echo "..."
	@echo ""
	@echo "Struct count: $(shell grep -c 'pub struct' /tmp/test_generated.rs)"

# Add a new signature (example)
add-signature:
	@echo "Example: Adding new signature..."
	@echo "prompt, context -> response" >> signatures.txt
	@echo "Added: prompt, context -> response"
	@echo "Run 'make build' to regenerate types"

# Development workflow
dev: clean regenerate run

# Release build
release:
	cargo build --release

# Verbose build
verbose:
	cargo build --verbose
