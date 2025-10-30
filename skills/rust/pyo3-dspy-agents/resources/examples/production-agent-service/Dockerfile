# Multi-stage Dockerfile for Production Agent Service

# ============================================================================
# Stage 1: Build Rust binary
# ============================================================================
FROM rust:1.75-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy main to cache dependencies
RUN mkdir -p src && \
    echo "fn main() {}" > src/main.rs && \
    echo "pub fn dummy() {}" > src/lib.rs

# Build dependencies (cached layer)
RUN cargo build --release && \
    rm -rf src

# Copy actual source code
COPY src ./src

# Build the application
RUN cargo build --release

# ============================================================================
# Stage 2: Runtime image
# ============================================================================
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir dspy-ai openai

# Create app user
RUN useradd -m -u 1000 agent && \
    mkdir -p /app /app/agent_memories && \
    chown -R agent:agent /app

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/server /app/server

# Change ownership
RUN chown agent:agent /app/server

# Switch to non-root user
USER agent

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/api/v1/health || exit 1

# Run the server
ENTRYPOINT ["/app/server"]
