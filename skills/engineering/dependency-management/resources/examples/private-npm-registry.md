# Private npm Registry Setup (Verdaccio)

Complete guide to setting up and using a private npm registry with Verdaccio.

## Installation

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  verdaccio:
    image: verdaccio/verdaccio:5
    container_name: verdaccio
    ports:
      - "4873:4873"
    volumes:
      - ./config:/verdaccio/conf
      - ./storage:/verdaccio/storage
      - ./plugins:/verdaccio/plugins
    environment:
      - VERDACCIO_PORT=4873
    restart: unless-stopped
    networks:
      - npm-registry

networks:
  npm-registry:
    driver: bridge
```

### Verdaccio Configuration

```yaml
# config/config.yaml
storage: /verdaccio/storage
plugins: /verdaccio/plugins

# Web UI configuration
web:
  title: Company Private npm Registry
  logo: logo.png
  primary_color: "#4b5563"
  gravatar: true
  scope: "@mycompany"

# Authentication
auth:
  htpasswd:
    file: /verdaccio/conf/htpasswd
    algorithm: bcrypt
    max_users: 1000

# Package access control
packages:
  # Scoped packages for your organization
  '@mycompany/*':
    access: $authenticated
    publish: $authenticated
    unpublish: $authenticated
    proxy: npmjs

  # Internal packages (no proxy)
  '@internal/*':
    access: $authenticated
    publish: $authenticated
    unpublish: $authenticated

  # All other packages proxy to npm
  '**':
    access: $all
    publish: $authenticated
    unpublish: $authenticated
    proxy: npmjs

# Upstream npm registry
uplinks:
  npmjs:
    url: https://registry.npmjs.org/
    cache: true
    timeout: 30s
    max_age: 2m
    fail_timeout: 5m
    maxage: 2m

# Security
security:
  api:
    jwt:
      sign:
        expiresIn: 7d
      verify:
        maxAge: 7d

# Server configuration
server:
  keepAliveTimeout: 60

# Logging
logs:
  - { type: stdout, format: pretty, level: http }
  - { type: file, path: /verdaccio/storage/verdaccio.log, level: info }

# Maximum body size
max_body_size: 100mb

# Notifications
notify:
  method: POST
  headers: [{ "Content-Type": "application/json" }]
  endpoint: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
  content: '{ "text": "Package {{name}}@{{version}} published by {{publishedBy}}" }'

# Middleware
middlewares:
  audit:
    enabled: true
```

## Usage

### Configure npm Client

```bash
# Set registry for scoped packages
npm config set @mycompany:registry http://localhost:4873

# Or set as default registry
npm config set registry http://localhost:4873

# Login
npm login --registry http://localhost:4873
```

### Configure .npmrc (Project-level)

```ini
# .npmrc
@mycompany:registry=http://localhost:4873/
//localhost:4873/:_authToken=${NPM_TOKEN}

# Use npm for non-scoped packages
registry=https://registry.npmjs.org/
```

### Configure .npmrc (User-level)

```ini
# ~/.npmrc
@mycompany:registry=http://verdaccio.company.com/
//verdaccio.company.com/:_authToken=YOUR_AUTH_TOKEN

# Optional: Set npm as fallback
registry=https://registry.npmjs.org/
```

## Publishing Packages

### Prepare Package

```json
// package.json
{
  "name": "@mycompany/my-package",
  "version": "1.0.0",
  "publishConfig": {
    "registry": "http://localhost:4873",
    "access": "restricted"
  }
}
```

### Publish

```bash
# Build package
npm run build

# Publish to private registry
npm publish --registry http://localhost:4873
```

### Automated Publishing (CI/CD)

```yaml
# .github/workflows/publish.yml
name: Publish Package

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          registry-url: 'http://verdaccio.company.com'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Publish to private registry
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## Security Best Practices

### 1. Enable HTTPS

```yaml
# config/config.yaml
https:
  key: /verdaccio/conf/server.key
  cert: /verdaccio/conf/server.crt
```

### 2. Use Strong Authentication

```bash
# Create users with bcrypt
npm adduser --registry http://localhost:4873
```

### 3. Configure Rate Limiting

```yaml
# config/config.yaml
middlewares:
  ratelimit:
    enabled: true
    max: 100
    windowMs: 60000
```

### 4. Enable Audit Logging

```yaml
# config/config.yaml
logs:
  - { type: file, path: /verdaccio/storage/audit.log, level: info }
  - { type: rotating-file, path: /verdaccio/storage/access.log, level: http }
```

## Docker Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  verdaccio:
    image: verdaccio/verdaccio:5
    container_name: verdaccio-prod
    restart: always
    ports:
      - "4873:4873"
    volumes:
      - verdaccio-storage:/verdaccio/storage
      - ./config:/verdaccio/conf:ro
    environment:
      - VERDACCIO_PUBLIC_URL=https://npm.company.com
      - VERDACCIO_PORT=4873
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4873/-/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - npm-registry

  nginx:
    image: nginx:alpine
    container_name: verdaccio-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - verdaccio
    networks:
      - npm-registry

volumes:
  verdaccio-storage:
    driver: local

networks:
  npm-registry:
    driver: bridge
```

### Nginx Configuration

```nginx
# nginx.conf
upstream verdaccio {
    server verdaccio:4873;
    keepalive 64;
}

server {
    listen 80;
    server_name npm.company.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name npm.company.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://verdaccio;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_read_timeout 600s;
    }
}
```

## Kubernetes Deployment

```yaml
# verdaccio-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: verdaccio-config
data:
  config.yaml: |
    storage: /verdaccio/storage
    auth:
      htpasswd:
        file: /verdaccio/conf/htpasswd
    packages:
      '@mycompany/*':
        access: $authenticated
        publish: $authenticated
        proxy: npmjs
      '**':
        access: $all
        proxy: npmjs
    uplinks:
      npmjs:
        url: https://registry.npmjs.org/

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: verdaccio-storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: verdaccio
spec:
  replicas: 2
  selector:
    matchLabels:
      app: verdaccio
  template:
    metadata:
      labels:
        app: verdaccio
    spec:
      containers:
      - name: verdaccio
        image: verdaccio/verdaccio:5
        ports:
        - containerPort: 4873
        volumeMounts:
        - name: config
          mountPath: /verdaccio/conf
        - name: storage
          mountPath: /verdaccio/storage
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /-/ping
            port: 4873
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /-/ping
            port: 4873
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: verdaccio-config
      - name: storage
        persistentVolumeClaim:
          claimName: verdaccio-storage

---
apiVersion: v1
kind: Service
metadata:
  name: verdaccio
spec:
  selector:
    app: verdaccio
  ports:
  - port: 4873
    targetPort: 4873
  type: LoadBalancer
```

## Monitoring

```yaml
# config/config.yaml
middlewares:
  metrics:
    enabled: true

# Prometheus metrics available at:
# http://localhost:4873/-/metrics
```

## Backup Strategy

```bash
#!/bin/bash
# backup-verdaccio.sh

BACKUP_DIR="/backups/verdaccio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup storage
tar -czf "$BACKUP_DIR/storage-$TIMESTAMP.tar.gz" /verdaccio/storage

# Backup config
tar -czf "$BACKUP_DIR/config-$TIMESTAMP.tar.gz" /verdaccio/conf

# Keep only last 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

## Troubleshooting

### Check Registry Health

```bash
curl http://localhost:4873/-/ping
```

### View Logs

```bash
docker logs verdaccio -f
```

### Clear Cache

```bash
# Remove all cached packages (⚠️ WARNING: Deletes all Verdaccio cache)
# Only run this if you're experiencing cache corruption issues
rm -rf /verdaccio/storage/.cache

# Safer: Use npm cache clean (recommended)
npm cache clean --force
```

## Migration from npm Registry

```bash
#!/bin/bash
# migrate-packages.sh

# List all private packages
PACKAGES=$(npm search @mycompany --registry https://registry.npmjs.org --json | jq -r '.[].name')

for PACKAGE in $PACKAGES; do
  echo "Migrating $PACKAGE..."

  # Download from npm
  npm pack $PACKAGE --registry https://registry.npmjs.org

  # Publish to Verdaccio
  npm publish *.tgz --registry http://localhost:4873

  # Cleanup
  rm *.tgz
done
```
