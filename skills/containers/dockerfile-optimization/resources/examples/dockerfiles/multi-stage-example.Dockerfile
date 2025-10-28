# Multi-Stage Build Example
# Demonstrates: Parallel stages, test stage, multiple outputs

# Base stage - shared dependencies
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Test stage - runs tests
FROM base AS test
COPY . .
RUN npm run test && \
    npm run lint

# Build stage - compiles application
FROM base AS builder
COPY . .
RUN npm run build

# Documentation stage - generates docs (parallel to build)
FROM base AS docs
COPY . .
RUN npm run docs

# Production runtime stage
FROM node:20-alpine AS production
WORKDIR /app

# Install only production dependencies
COPY package*.json ./
RUN npm ci --only=production && \
    npm cache clean --force

# Copy built application
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV NODE_ENV=production
EXPOSE 3000

HEALTHCHECK CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "dist/index.js"]

# Development stage - includes dev tools
FROM base AS development
COPY . .
ENV NODE_ENV=development
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Debug stage - includes debugging tools
FROM production AS debug
USER root
RUN apk add --no-cache \
    curl \
    vim \
    net-tools
USER appuser
