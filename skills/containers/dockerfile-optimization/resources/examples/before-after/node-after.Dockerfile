# AFTER OPTIMIZATION
# Improvements: Alpine base, production deps only, multi-stage, non-root

FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./

# Production dependencies only with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --only=production && \
    npm cache clean --force

FROM node:20-alpine
WORKDIR /app

# Create non-root user
RUN addgroup -g 1001 nodejs && \
    adduser -D -u 1001 -G nodejs nodejs && \
    chown -R nodejs:nodejs /app

# Copy production deps and app
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .

USER nodejs

ENV NODE_ENV=production
EXPOSE 3000

# Add health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

# Use exec form
CMD ["node", "index.js"]

# Result: ~180MB image (83% reduction), faster builds, production-ready
