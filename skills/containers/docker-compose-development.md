---
name: containers-docker-compose-development
description: Setting up local development environments
---



# Docker Compose Development

**Scope**: Compose files, networking, volumes, service dependencies, healthchecks
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Setting up local development environments
- Orchestrating multi-container applications
- Defining service dependencies and startup order
- Configuring container networking
- Managing persistent data with volumes
- Implementing health checks
- Creating reproducible development environments
- Debugging container connectivity issues

## Core Concepts

### What is Docker Compose?

**Docker Compose**: Tool for defining and running multi-container Docker applications.

**Key properties**:
- **Declarative**: Define services in YAML (`docker-compose.yml`)
- **Reproducible**: Same environment across machines
- **Isolated**: Separate network per project
- **Convenient**: Single command to start/stop all services
- **Development-focused**: Not for production (use Kubernetes/Swarm)

**Basic workflow**:
```bash
docker compose up       # Start all services
docker compose down     # Stop and remove containers
docker compose logs     # View logs
docker compose ps       # List running containers
```

---

## Docker Compose File Structure

### Basic Compose File (v3.8+)

```yaml
version: '3.8'

services:
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html
    networks:
      - frontend

  api:
    build: ./api
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
    depends_on:
      - db
    networks:
      - frontend
      - backend

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend

networks:
  frontend:
  backend:

volumes:
  postgres_data:
```

### Service Definition Keys

**Essential keys**:
```yaml
services:
  app:
    image: myapp:latest        # Pre-built image
    build: ./app               # Build from Dockerfile
    container_name: my_app     # Custom container name
    ports:                     # Port mapping
      - "8080:80"
    volumes:                   # Mounts
      - ./data:/data
    environment:               # Environment variables
      - DEBUG=true
    depends_on:                # Service dependencies
      - db
    networks:                  # Networks to join
      - frontend
    command: ["npm", "start"]  # Override default command
    restart: unless-stopped    # Restart policy
```

---

## Service Configuration

### Building Images

**Simple build**:
```yaml
services:
  app:
    build: ./app        # Dockerfile in ./app directory
```

**Advanced build**:
```yaml
services:
  app:
    build:
      context: ./app              # Build context
      dockerfile: Dockerfile.dev  # Custom Dockerfile name
      args:                       # Build arguments
        - NODE_ENV=development
      target: development         # Multi-stage build target
      cache_from:                 # Cache sources
        - myapp:latest
```

### Environment Variables

**Inline**:
```yaml
services:
  app:
    environment:
      - DEBUG=true
      - API_KEY=secret123
```

**From .env file**:
```yaml
services:
  app:
    env_file:
      - .env
      - .env.local
```

**.env file**:
```bash
DEBUG=true
DATABASE_URL=postgres://localhost/mydb
API_KEY=secret123
```

**Using environment in compose**:
```yaml
services:
  app:
    image: myapp:${TAG:-latest}     # Default to 'latest'
    environment:
      - DATABASE_URL=${DATABASE_URL}
```

### Port Mapping

**Host:Container mapping**:
```yaml
services:
  web:
    ports:
      - "8080:80"          # Host 8080 → Container 80
      - "443:443"
      - "127.0.0.1:3000:3000"  # Bind to localhost only
```

**Expose (internal only)**:
```yaml
services:
  api:
    expose:
      - "3000"   # Accessible to other services, not host
```

**Dynamic ports**:
```yaml
services:
  web:
    ports:
      - "8080"   # Docker assigns random host port
```

---

## Volumes and Data Persistence

### Volume Types

**Named volumes** (managed by Docker):
```yaml
services:
  db:
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:    # Docker manages storage
```

**Bind mounts** (host directory):
```yaml
services:
  app:
    volumes:
      - ./app:/app              # Sync local code
      - ./config:/etc/config:ro # Read-only
```

**tmpfs** (in-memory):
```yaml
services:
  app:
    tmpfs:
      - /tmp
      - /run
```

### Volume Configuration

**Advanced volume options**:
```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/on/host

  nfs_data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.1.100,rw
      device: ":/export/data"
```

### Bind Mount Performance (Mac/Windows)

**Problem**: Bind mounts are slow on Mac/Windows.

**Solution**: Use delegated/cached modes:
```yaml
services:
  app:
    volumes:
      - ./app:/app:delegated     # Performance over consistency
      - ./logs:/logs:cached      # Container writes prioritized
```

**Modes**:
- `consistent` - Default, slowest, most consistent
- `delegated` - Host writes delayed to container (faster)
- `cached` - Container writes delayed to host (faster)

---

## Networking

### Default Bridge Network

**Automatic**:
```yaml
services:
  web:
    # Automatically joins 'default' network
  api:
    # Can reach 'web' via hostname 'web'
```

**Services communicate via service name**:
```bash
# Inside 'api' container
curl http://web:80
```

### Custom Networks

```yaml
services:
  web:
    networks:
      - frontend

  api:
    networks:
      - frontend
      - backend

  db:
    networks:
      - backend   # Isolated from 'web'

networks:
  frontend:
  backend:
```

**Result**: `web` and `api` can communicate, `web` and `db` cannot.

### Network Aliases

```yaml
services:
  api:
    networks:
      frontend:
        aliases:
          - api-server
          - backend-api
```

**Access via**:
```bash
curl http://api:3000
curl http://api-server:3000
curl http://backend-api:3000
```

### External Networks

```yaml
networks:
  existing-network:
    external: true   # Use existing network

services:
  app:
    networks:
      - existing-network
```

### Network Drivers

```yaml
networks:
  frontend:
    driver: bridge    # Default (single host)

  overlay:
    driver: overlay   # Multi-host (Swarm)

  host:
    driver: host      # Use host network (no isolation)
```

---

## Service Dependencies

### depends_on (Basic)

```yaml
services:
  api:
    depends_on:
      - db
      - redis

  db:
    image: postgres:16

  redis:
    image: redis:7
```

**Behavior**: Starts `db` and `redis` before `api`.

**Limitation**: Doesn't wait for services to be **ready**, only **started**.

### Health Checks (Wait for Ready)

```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  api:
    depends_on:
      db:
        condition: service_healthy   # Wait for healthy
```

**Health check commands**:
```yaml
# Postgres
test: ["CMD-SHELL", "pg_isready -U postgres"]

# MySQL
test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]

# Redis
test: ["CMD", "redis-cli", "ping"]

# HTTP endpoint
test: ["CMD", "curl", "-f", "http://localhost:8080/health"]

# Custom script
test: ["CMD", "/app/healthcheck.sh"]
```

### Long Dependencies (Retry Logic)

**Problem**: Some services take time to initialize.

**Solution**: Use `restart` + application-level retries:
```yaml
services:
  api:
    depends_on:
      - db
    restart: on-failure
    environment:
      - DB_RETRY_ATTEMPTS=10
      - DB_RETRY_DELAY=5
```

**Application code** (example in Python):
```python
import time
import psycopg2

def connect_with_retry(max_attempts=10, delay=5):
    for attempt in range(max_attempts):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except psycopg2.OperationalError:
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                raise
```

---

## Common Service Patterns

### Pattern 1: Web App + Database + Redis

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./app:/app
    networks:
      - app-network

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - app-network

networks:
  app-network:

volumes:
  postgres_data:
  redis_data:
```

### Pattern 2: Frontend + Backend + Database

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    networks:
      - frontend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
    depends_on:
      - db
    volumes:
      - ./backend:/app
    networks:
      - frontend
      - backend

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend

networks:
  frontend:
  backend:

volumes:
  postgres_data:
```

### Pattern 3: Development with Live Reload

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      target: development   # Multi-stage build
    ports:
      - "3000:3000"
    volumes:
      - ./src:/app/src:delegated      # Sync source code
      - /app/node_modules             # Don't sync node_modules
    environment:
      - NODE_ENV=development
      - CHOKIDAR_USEPOLLING=true      # File watching (Windows/Mac)
    command: npm run dev              # Override with dev command
```

---

## Docker Compose Commands

### Starting and Stopping

```bash
# Start all services (attached)
docker compose up

# Start in background (detached)
docker compose up -d

# Start specific services
docker compose up web db

# Rebuild images
docker compose up --build

# Stop services
docker compose stop

# Stop and remove containers
docker compose down

# Remove containers, volumes, networks
docker compose down -v
```

### Viewing Logs

```bash
# All services
docker compose logs

# Follow logs
docker compose logs -f

# Specific service
docker compose logs web

# Last N lines
docker compose logs --tail=100 web

# Timestamps
docker compose logs -t
```

### Running Commands

```bash
# Execute command in running container
docker compose exec web sh

# Run one-off command (new container)
docker compose run web npm test

# Run without starting dependencies
docker compose run --no-deps web npm test
```

### Inspecting Services

```bash
# List running containers
docker compose ps

# List all containers (including stopped)
docker compose ps -a

# Show service configuration
docker compose config

# Validate compose file
docker compose config --quiet
```

---

## Development Workflow Best Practices

### Practice 1: Environment-Specific Overrides

**docker-compose.yml** (base):
```yaml
version: '3.8'
services:
  app:
    image: myapp:latest
    ports:
      - "8000:8000"
```

**docker-compose.override.yml** (development, auto-loaded):
```yaml
version: '3.8'
services:
  app:
    build: .
    volumes:
      - ./src:/app/src
    environment:
      - DEBUG=true
```

**docker-compose.prod.yml** (production):
```yaml
version: '3.8'
services:
  app:
    image: myapp:v1.2.3
    restart: always
```

**Use**:
```bash
# Development (auto-loads override)
docker compose up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### Practice 2: Health Checks for All Services

```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Practice 3: Resource Limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

## Troubleshooting

### Issue 1: Services Can't Communicate

**Symptom**: `curl: (6) Could not resolve host: api`

**Solution**: Check networks
```bash
# Ensure services on same network
docker compose config | grep networks

# Verify DNS
docker compose exec web ping api
```

### Issue 2: Permission Denied (Volumes)

**Symptom**: `Permission denied: '/data/file.txt'`

**Solution**: Match user IDs
```yaml
services:
  app:
    user: "${UID}:${GID}"
    volumes:
      - ./data:/data
```

```bash
# Set in .env
UID=1000
GID=1000
```

### Issue 3: Port Already in Use

**Symptom**: `Bind for 0.0.0.0:8080 failed: port is already allocated`

**Solution**: Change host port or stop conflicting service
```bash
# Find process
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
# ports: - "8081:8080"
```

---

## Docker Compose Checklist

```
Configuration:
[ ] Use version 3.8+
[ ] Define named volumes for persistence
[ ] Configure custom networks for isolation
[ ] Use .env files for secrets (not committed to git)
[ ] Pin image versions (not :latest)

Development:
[ ] Use bind mounts for live code reload
[ ] Configure health checks
[ ] Set depends_on with conditions
[ ] Use docker-compose.override.yml for local config
[ ] Enable file watching (CHOKIDAR_USEPOLLING)

Production:
[ ] Use built images (not build context)
[ ] Set restart policies (restart: always)
[ ] Configure resource limits
[ ] Use production compose file override
[ ] Remove debug/dev tools

Networking:
[ ] Isolate services with custom networks
[ ] Expose only necessary ports
[ ] Use service names for DNS
[ ] Configure network aliases if needed
```

---

## Related Skills

- `dockerfile-optimization.md` - Building efficient images
- `container-security.md` - Securing containers
- `container-networking.md` - Advanced networking
- `kubernetes-basics.md` - Production orchestration

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
