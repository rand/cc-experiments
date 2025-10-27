#!/bin/bash
# Health check script for Nginx Docker container

set -eo pipefail

# Check if nginx is running
if ! pgrep -x nginx > /dev/null; then
    echo "Nginx is not running"
    exit 1
fi

# Check if nginx can respond to requests
if ! curl -f http://localhost/health > /dev/null 2>&1; then
    echo "Nginx health endpoint not responding"
    exit 1
fi

echo "Nginx is healthy"
exit 0
