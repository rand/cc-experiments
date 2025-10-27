# Production-Ready Nginx Docker Container
#
# Multi-stage build for optimized Nginx container with custom configuration

# Stage 1: Build custom Nginx modules (if needed)
FROM nginx:1.25-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    libc-dev \
    make \
    openssl-dev \
    pcre-dev \
    zlib-dev \
    linux-headers \
    curl \
    gnupg \
    libxslt-dev \
    gd-dev \
    geoip-dev

# Download and build additional modules (example: headers-more)
WORKDIR /tmp
RUN curl -fSL https://github.com/openresty/headers-more-nginx-module/archive/v0.34.tar.gz -o headers-more.tar.gz \
    && tar -xzf headers-more.tar.gz

# Stage 2: Final production image
FROM nginx:1.25-alpine

LABEL maintainer="ops@example.com"
LABEL description="Production Nginx with custom configuration"

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    curl \
    bash

# Create nginx user and directories
RUN addgroup -g 101 -S nginx && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx

# Create required directories
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp \
    /var/cache/nginx/cache \
    /var/log/nginx \
    /etc/nginx/conf.d \
    /etc/nginx/snippets \
    /var/www/html

# Set correct permissions
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/www/html && \
    chmod -R 755 /var/cache/nginx /var/log/nginx

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
COPY snippets/ /etc/nginx/snippets/

# Copy static files (if any)
COPY html/ /var/www/html/

# Copy health check script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Remove default configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Test nginx configuration
RUN nginx -t

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1

# Use non-root user
USER nginx

# Start nginx
STOPSIGNAL SIGQUIT
CMD ["nginx", "-g", "daemon off;"]
