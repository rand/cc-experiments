# Multi-stage Dockerfile for production deployment

# =============================================================================
# Stage 1: Build
# =============================================================================
FROM rust:1.75-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    python3 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml ./

# Create dummy src to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    echo "pub fn dummy() {}" > src/lib.rs

# Build dependencies (cached layer)
RUN cargo build --release && \
    rm -rf src

# Copy actual source code
COPY src ./src

# Build application
RUN touch src/main.rs src/lib.rs && \
    cargo build --release

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for DSpy
RUN pip3 install --no-cache-dir \
    dspy-ai \
    openai

# Copy binary from builder
COPY --from=builder /build/target/release/complete-production-service /app/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Set environment defaults
ENV HOST=0.0.0.0 \
    PORT=8080 \
    LOG_LEVEL=info \
    LOG_FORMAT=json \
    SERVICE_NAME=complete-production-service \
    SERVICE_VERSION=0.1.0 \
    MEMORY_CACHE_SIZE=10000 \
    MEMORY_CACHE_TTL_SECS=300 \
    REDIS_CACHE_TTL_SECS=3600 \
    CIRCUIT_BREAKER_FAILURE_THRESHOLD=5 \
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2 \
    CIRCUIT_BREAKER_TIMEOUT_SECS=60

# Run the application
CMD ["/app/complete-production-service"]
