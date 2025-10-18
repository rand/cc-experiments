---
name: containers-container-networking
description: Configuring container network connectivity
---



# Container Networking

**Scope**: Bridge/host/overlay networks, service discovery, port mapping, DNS
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Configuring container network connectivity
- Debugging inter-container communication
- Implementing service discovery
- Isolating services with custom networks
- Choosing network drivers (bridge/host/overlay)
- Troubleshooting DNS resolution
- Optimizing network performance
- Setting up multi-host networking

## Core Concepts

### Docker Networking Fundamentals

**Network drivers**: Docker supports multiple network types.

**Key properties**:
- **Isolated**: Each network provides isolation
- **DNS-based discovery**: Containers resolve via service names
- **Software-defined**: Networks created/destroyed dynamically
- **Driver-based**: Different drivers for different use cases
- **Pluggable**: Custom network drivers via plugins

**Default behavior**:
```bash
# Containers on default bridge network can communicate
docker run -d --name web nginx
docker run -d --name api node
# 'web' and 'api' can reach each other via IP, not name
```

---

## Network Drivers

### Bridge (Default for Single Host)

**Purpose**: Isolated network on single host.

**Characteristics**:
- **Default driver**: Used if no network specified
- **DNS resolution**: Custom bridges support name resolution
- **Isolation**: Containers on different bridges can't communicate
- **Port mapping**: Required to expose to host

**Create bridge network**:
```bash
docker network create mynetwork

docker run -d --name web --network mynetwork nginx
docker run -d --name api --network mynetwork node

# 'web' can reach 'api' via hostname
docker exec web curl http://api:3000
```

**Bridge vs default bridge**:
```bash
# Default bridge (docker0)
docker run -d --name web nginx
# No automatic DNS, use IP addresses

# Custom bridge
docker network create mybridge
docker run -d --name web --network mybridge nginx
# DNS works, can use container names
```

**docker-compose.yml** (automatic custom bridge):
```yaml
services:
  web:
    image: nginx
  api:
    image: node
# Docker Compose creates custom bridge automatically
# Services resolve each other by name
```

### Host Network

**Purpose**: Use host's network directly (no isolation).

**Characteristics**:
- **No isolation**: Container shares host network stack
- **No port mapping**: Container binds directly to host ports
- **Performance**: Faster (no NAT overhead)
- **Use cases**: Performance-critical apps, network monitoring

**Run with host network**:
```bash
docker run -d --network host nginx
# Nginx binds to host's port 80 directly
# No -p flag needed
```

**Trade-offs**:
```
Pros:
- Highest performance (no NAT)
- Direct access to host network interfaces
- Lower latency

Cons:
- No network isolation
- Port conflicts between containers
- Linux only (not Mac/Windows)
```

**docker-compose.yml**:
```yaml
services:
  monitor:
    image: netdata/netdata
    network_mode: host   # Use host network
```

### Overlay Network (Multi-Host)

**Purpose**: Span containers across multiple Docker hosts.

**Characteristics**:
- **Requires Swarm**: Docker Swarm or Kubernetes
- **Multi-host**: Containers on different hosts communicate
- **Encrypted**: Optional encryption
- **Use cases**: Swarm services, distributed apps

**Create overlay network** (Swarm):
```bash
# Initialize swarm
docker swarm init

# Create overlay network
docker network create -d overlay myoverlay

# Deploy service
docker service create \
  --name web \
  --network myoverlay \
  --replicas 3 \
  nginx
```

**Encrypted overlay**:
```bash
docker network create \
  -d overlay \
  --opt encrypted \
  secure-overlay
```

### Macvlan Network

**Purpose**: Assign MAC address to container (appears as physical device).

**Characteristics**:
- **Direct L2 access**: Container on physical network
- **MAC address**: Each container gets unique MAC
- **Use cases**: Legacy apps expecting physical network

**Create macvlan**:
```bash
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  macvlan-net

docker run -d \
  --network macvlan-net \
  --ip=192.168.1.100 \
  nginx
```

### None Network

**Purpose**: No networking (isolated container).

```bash
docker run -d --network none alpine
# No network interfaces (except loopback)
```

---

## Port Mapping

### Publishing Ports

**Basic mapping**:
```bash
# -p HOST_PORT:CONTAINER_PORT
docker run -d -p 8080:80 nginx
# Access via http://localhost:8080
```

**Bind to specific interface**:
```bash
# Localhost only
docker run -d -p 127.0.0.1:8080:80 nginx

# Specific IP
docker run -d -p 192.168.1.10:8080:80 nginx
```

**Dynamic port** (Docker assigns random port):
```bash
docker run -d -p 80 nginx

# Find assigned port
docker port <container_id> 80
# 0.0.0.0:32768
```

**Multiple ports**:
```bash
docker run -d \
  -p 8080:80 \
  -p 8443:443 \
  nginx
```

**UDP ports**:
```bash
docker run -d -p 53:53/udp dns-server
```

### Expose vs Publish

**EXPOSE** (Dockerfile):
```dockerfile
EXPOSE 80
# Documents intent, doesn't publish port
```

**Publish** (runtime):
```bash
docker run -d -p 8080:80 nginx
# Actually maps port to host
```

**docker-compose.yml**:
```yaml
services:
  web:
    expose:
      - "80"   # Available to other services only

  api:
    ports:
      - "8080:80"   # Published to host
```

---

## Service Discovery and DNS

### Automatic DNS Resolution

**Custom bridge networks**: Container names resolve automatically.

```bash
# Create network
docker network create mynet

# Run containers
docker run -d --name db --network mynet postgres
docker run -d --name api --network mynet node

# DNS works automatically
docker exec api ping db
# PING db (172.18.0.2): 56 data bytes
```

**Service name resolution**:
```bash
# Inside 'api' container
curl http://db:5432
# Resolves 'db' to container IP
```

**docker-compose.yml** (automatic):
```yaml
services:
  web:
    image: nginx
  api:
    image: node
    environment:
      - DB_HOST=db   # Resolves to 'db' service
  db:
    image: postgres
```

### Network Aliases

**Multiple aliases per container**:
```bash
docker run -d \
  --name api \
  --network mynet \
  --network-alias backend \
  --network-alias api-server \
  node

# Reachable via 'api', 'backend', or 'api-server'
```

**docker-compose.yml**:
```yaml
services:
  api:
    networks:
      mynet:
        aliases:
          - backend
          - api-server
```

### Custom DNS Servers

```bash
docker run -d \
  --dns 8.8.8.8 \
  --dns 1.1.1.1 \
  nginx
```

**docker-compose.yml**:
```yaml
services:
  web:
    dns:
      - 8.8.8.8
      - 1.1.1.1
    dns_search:
      - example.com
```

---

## Network Isolation and Segmentation

### Multiple Networks per Container

```bash
docker network create frontend
docker network create backend

# Web server on frontend only
docker run -d --name web --network frontend nginx

# API on both networks
docker run -d --name api node
docker network connect frontend api
docker network connect backend api

# Database on backend only
docker run -d --name db --network backend postgres
```

**Result**:
- `web` ↔ `api` (via frontend)
- `api` ↔ `db` (via backend)
- `web` ✗ `db` (isolated)

**docker-compose.yml**:
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
      - backend

networks:
  frontend:
  backend:
```

### Internal Networks (No External Access)

```bash
docker network create \
  --internal \
  isolated-network

docker run -d \
  --name secure-db \
  --network isolated-network \
  postgres
# Can't reach internet, only other containers on network
```

**docker-compose.yml**:
```yaml
networks:
  internal:
    internal: true   # No external connectivity

services:
  db:
    networks:
      - internal
```

---

## Network Inspection and Debugging

### Inspecting Networks

```bash
# List networks
docker network ls

# Inspect network
docker network inspect mynetwork

# See containers on network
docker network inspect mynetwork --format='{{range .Containers}}{{.Name}} {{end}}'
```

### Testing Connectivity

**Ping between containers**:
```bash
docker exec web ping api
```

**Check DNS resolution**:
```bash
docker exec web nslookup api
docker exec web dig api
```

**Test HTTP connectivity**:
```bash
docker exec web curl http://api:3000/health
```

**Check listening ports**:
```bash
docker exec api netstat -tuln
docker exec api ss -tuln
```

### Common Network Issues

**Issue 1: Container can't resolve names**

**Symptom**: `curl: (6) Could not resolve host: api`

**Solution**: Ensure containers on custom bridge network
```bash
# Check network
docker inspect api --format='{{.NetworkSettings.Networks}}'

# Connect to network
docker network connect mynetwork api
```

**Issue 2: Port already in use**

**Symptom**: `Bind for 0.0.0.0:8080 failed: port is already allocated`

**Solution**: Change port or stop conflicting service
```bash
# Find process
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
docker run -d -p 8081:80 nginx
```

**Issue 3: Container can reach internet but not other containers**

**Symptom**: `curl https://google.com` works, `curl http://api` fails

**Solution**: Check if on same network
```bash
docker network inspect mynetwork
# Ensure both containers listed
```

---

## Network Performance Optimization

### Technique 1: Use Host Network for High Performance

```bash
# Bypass Docker networking stack
docker run -d --network host nginx
```

**Use cases**: High-throughput apps, low-latency requirements.

### Technique 2: Optimize MTU

```bash
docker network create \
  --opt com.docker.network.driver.mtu=9000 \
  jumbo-network
```

**Benefit**: Larger frames, fewer packets (if network supports).

### Technique 3: Disable iptables (Advanced)

```bash
docker network create \
  --opt com.docker.network.bridge.enable_icc=true \
  --opt com.docker.network.bridge.enable_ip_masquerade=false \
  fast-network
```

**Warning**: Reduces isolation, use carefully.

---

## docker-compose Networking Patterns

### Pattern 1: Multi-Tier Application

```yaml
version: '3.8'

services:
  web:
    image: nginx
    networks:
      - public
    ports:
      - "80:80"

  api:
    image: node
    networks:
      - public
      - private
    environment:
      - DB_HOST=db

  db:
    image: postgres
    networks:
      - private
    environment:
      POSTGRES_PASSWORD: secret

networks:
  public:   # Internet-facing
  private:  # Backend only
```

### Pattern 2: External Network

```yaml
networks:
  existing-net:
    external: true   # Use pre-existing network

services:
  app:
    networks:
      - existing-net
```

### Pattern 3: Custom Subnet

```yaml
networks:
  mynet:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1

services:
  web:
    networks:
      mynet:
        ipv4_address: 172.28.0.10
```

---

## Network Security Best Practices

### Practice 1: Network Segmentation

```yaml
# Isolate services by function
networks:
  frontend:   # Public-facing
  backend:    # Internal only
  data:       # Database tier
    internal: true
```

### Practice 2: Limit Published Ports

```yaml
services:
  api:
    expose:
      - "3000"   # Available to services only (not host)

  web:
    ports:
      - "80:80"  # Published to host (necessary)
```

### Practice 3: Use Internal Networks

```yaml
networks:
  secure:
    internal: true   # No internet access

services:
  db:
    networks:
      - secure   # Isolated from internet
```

---

## Network Troubleshooting Checklist

```
Connectivity:
[ ] Containers on same network?
[ ] DNS resolution working? (nslookup/dig)
[ ] Firewall blocking ports?
[ ] Correct port mapping?
[ ] Service listening on correct port?

Performance:
[ ] Consider host network for high throughput
[ ] Optimize MTU if using jumbo frames
[ ] Check for network congestion
[ ] Monitor with docker stats

Security:
[ ] Segment networks by tier (frontend/backend)
[ ] Use internal networks for databases
[ ] Minimize published ports
[ ] Use TLS for inter-service communication

Debugging:
[ ] Inspect network: docker network inspect
[ ] Check container IPs: docker inspect
[ ] Test ping/curl between containers
[ ] Review docker logs for network errors
```

---

## Quick Reference

### Network Commands

```bash
# Create network
docker network create mynet

# List networks
docker network ls

# Inspect network
docker network inspect mynet

# Connect container
docker network connect mynet container_name

# Disconnect container
docker network disconnect mynet container_name

# Remove network
docker network rm mynet

# Prune unused networks
docker network prune
```

### Common Network Drivers

| Driver | Scope | Use Case |
|--------|-------|----------|
| `bridge` | Single host | Default, isolated containers |
| `host` | Single host | High performance, no isolation |
| `overlay` | Multi-host | Swarm, distributed apps |
| `macvlan` | Single host | Legacy apps, L2 access |
| `none` | N/A | Completely isolated |

---

## Related Skills

- `docker-compose-development.md` - Compose networking config
- `container-security.md` - Network isolation for security
- `kubernetes-networking.md` - Advanced multi-host networking
- `service-mesh.md` - Istio/Linkerd for microservices

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
