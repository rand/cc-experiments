# Optimized Go Dockerfile
# Demonstrates: Scratch base, static binary, minimal image size

# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git ca-certificates

# Copy go mod files first (better caching)
COPY go.mod go.sum ./

# Download dependencies with cache mount
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Copy source code
COPY . .

# Build static binary with optimizations
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-s -w -X main.version=${VERSION:-dev}" \
    -trimpath \
    -o app \
    ./cmd/app

# Runtime stage - scratch for minimal image
FROM scratch

# Copy CA certificates for HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy static binary
COPY --from=builder /app/app /app

# Run as non-root user (nobody)
USER 65534:65534

# Expose port (documentation only)
EXPOSE 8080

# No shell available in scratch, so no shell-form health check
# Health checks must be done externally or via orchestrator

# Use exec form (only option with scratch)
ENTRYPOINT ["/app"]
