---
name: tailscale-vpn
description: Creating secure private networks (mesh VPN)
---



# Tailscale VPN Setup

**Use this skill when:**
- Creating secure private networks (mesh VPN)
- Connecting services across cloud providers
- Accessing development machines remotely
- Building zero-trust networks
- Simplifying network configuration

## Installation

### Install Tailscale

```bash
# macOS
brew install tailscale

# Ubuntu/Debian
⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
```bash
# Download script first
curl -O https://tailscale.com/install.sh
# Verify checksum
sha256sum install.sh
# Review content
less install.sh
# Then execute
bash install.sh
```
For development/learning only:
```bash
curl -fsSL https://tailscale.com/install.sh | sh

# Docker
docker pull tailscale/tailscale
```

### Initial Setup

```bash
# Start tailscale
sudo tailscale up

# Authenticate (opens browser)
# Follow link to authenticate with your account

# Check status
tailscale status

# Get your IP
tailscale ip -4
```

## Basic Usage

### Connect Machines

All authenticated devices automatically connect:

```bash
# On machine A
tailscale up
# Gets IP: 100.64.0.1

# On machine B
tailscale up
# Gets IP: 100.64.0.2

# Now machines can reach each other
# From A: ping 100.64.0.2
# From B: ping 100.64.0.1
```

### SSH Over Tailscale

Use Tailscale IPs for SSH:

```bash
# Traditional SSH (need to configure firewalls, ports)
ssh user@public-ip-address

# Tailscale SSH (just works)
ssh user@100.64.0.2

# Enable Tailscale SSH (simpler auth)
tailscale up --ssh

# Then SSH without password
ssh username@machine-name
```

## Service Exposure

### Expose Local Services

Access local services from anywhere:

```python
# Run web service on 100.64.0.1:8000
# Accessible from any tailscale device at http://100.64.0.1:8000

# Example: Flask app
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Tailscale!"

if __name__ == '__main__':
    # Listen on tailscale interface
    app.run(host='100.64.0.1', port=8000)
```

### Database Access

Connect to databases securely:

```python
# PostgreSQL on machine A (100.64.0.1)
# Start postgres listening on tailscale IP

# From machine B
import psycopg2

conn = psycopg2.connect(
    host="100.64.0.1",  # Tailscale IP
    port=5432,
    database="mydb",
    user="user",
    password="password"
)

# No need for public IPs or complex firewall rules!
```

## MagicDNS

### Use Machine Names

Access machines by name instead of IP:

```bash
# Enable MagicDNS in Tailscale admin console

# Now use machine names
ssh user@machine-name

# In code
import requests
response = requests.get("http://api-server:8000/data")
```

```python
# Python example with MagicDNS
import psycopg2

# Use machine name instead of IP
conn = psycopg2.connect(
    host="postgres-server",  # MagicDNS name
    database="mydb"
)
```

## Subnet Routing

### Share Entire Networks

Expose entire subnets:

```bash
# On gateway machine with access to 192.168.1.0/24
tailscale up --advertise-routes=192.168.1.0/24

# Approve route in admin console

# Now other tailscale machines can access 192.168.1.*
ping 192.168.1.100
```

### Docker Network Access

Access Docker containers:

```bash
# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Advertise Docker network
tailscale up --advertise-routes=172.17.0.0/16

# Access containers from other machines
curl http://172.17.0.2:8000
```

## Exit Nodes

### Use as VPN Exit Node

Route all traffic through a machine:

```bash
# On exit node machine
tailscale up --advertise-exit-node

# On client machine
tailscale up --exit-node=exit-node-name

# Now all traffic routes through exit node
curl ifconfig.me  # Shows exit node's IP
```

## ACLs (Access Control Lists)

### Restrict Access

Control who can access what:

```json
// In Tailscale admin console > Access Controls
{
  "acls": [
    // Allow devs to access staging
    {
      "action": "accept",
      "src": ["group:devs"],
      "dst": ["tag:staging:*"]
    },

    // Allow production access only from specific IPs
    {
      "action": "accept",
      "src": ["group:ops"],
      "dst": ["tag:production:*"]
    }
  ],

  "groups": {
    "group:devs": ["alice@example.com", "bob@example.com"],
    "group:ops": ["ops@example.com"]
  },

  "tagOwners": {
    "tag:staging": ["group:devs"],
    "tag:production": ["group:ops"]
  }
}
```

## Tailscale in Docker

### Docker Container with Tailscale

```dockerfile
FROM ubuntu:22.04

# Install Tailscale
RUN apt-get update && apt-get install -y \
    curl \
    iptables \
    iproute2

⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
```dockerfile
# Download script first
RUN curl -O https://tailscale.com/install.sh && \
    sha256sum install.sh && \
    less install.sh && \
    bash install.sh
```
For development/learning only:
```dockerfile
RUN curl -fsSL https://tailscale.com/install.sh | sh

# Your app
COPY app.py /app/
WORKDIR /app

CMD ["sh", "-c", "tailscaled & tailscale up --authkey=$TAILSCALE_AUTH_KEY && python app.py"]
```

```bash
# Run with auth key
docker run -e TAILSCALE_AUTH_KEY=tskey-auth-xxx my-app
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    image: myapp
    environment:
      - DATABASE_HOST=postgres-server  # MagicDNS name
    depends_on:
      - tailscale

  tailscale:
    image: tailscale/tailscale
    hostname: myapp-tailscale
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTH_KEY}
      - TS_STATE_DIR=/var/lib/tailscale
    volumes:
      - tailscale-state:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
      - SYS_MODULE

volumes:
  tailscale-state:
```

## Kubernetes Integration

### Tailscale Operator

```yaml
# Install Tailscale operator
kubectl apply -f https://github.com/tailscale/tailscale/releases/latest/download/operator.yaml

# Expose service via Tailscale
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    tailscale.com/expose: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 8000
  selector:
    app: my-app
```

## Common Patterns

### Development Environment

Access dev services from laptop:

```bash
# On dev server (100.64.0.5)
# Run services normally on localhost

# On laptop
# Add to /etc/hosts or use MagicDNS
# 100.64.0.5  dev-server

# Access services
curl http://dev-server:3000    # React dev server
curl http://dev-server:8000    # Django backend
psql -h dev-server mydb        # PostgreSQL
```

### Multi-Cloud Networking

Connect AWS, GCP, and on-prem:

```bash
# AWS EC2 instance
tailscale up --advertise-routes=10.0.0.0/16

# GCP instance
tailscale up --advertise-routes=10.1.0.0/16

# On-prem
tailscale up --advertise-routes=192.168.1.0/24

# All networks can now communicate
# AWS -> GCP: ssh 10.1.0.50
# GCP -> on-prem: curl http://192.168.1.100
```

## Security Best Practices

### Use Auth Keys Safely

```bash
# Generate auth keys in admin console with:
# - Expiration date
# - Tags for ACL enforcement
# - One-time use (for ephemeral nodes)

# Use environment variables
export TAILSCALE_AUTH_KEY=tskey-auth-xxx
tailscale up --authkey=$TAILSCALE_AUTH_KEY

# Never commit auth keys to git!
```

### Enable MFA

```bash
# Enable in admin console
# All users required to use MFA for authentication

# Enforce key expiry
# Set device authorization expiry
```

## Monitoring

### Check Network Status

```bash
# List all peers
tailscale status

# Show detailed peer info
tailscale status --peers

# Check routes
tailscale status --peers --active

# Test connectivity
tailscale ping peer-name
```

## Anti-Patterns to Avoid

**DON'T expose services on 0.0.0.0 without firewall:**
```bash
# ❌ BAD - Exposed to entire internet
app.run(host='0.0.0.0', port=8000)

# ✅ GOOD - Only on Tailscale
app.run(host='100.64.0.1', port=8000)
```

**DON'T share auth keys:**
```bash
# ❌ BAD - Reusing same key
export SHARED_KEY=tskey-auth-xxx

# ✅ GOOD - Generate unique keys
# Use one-time keys for each deployment
```

## Related Skills

- **mtls-implementation.md** - Layer mTLS on Tailscale
- **mosh-resilient-ssh.md** - Combine with mosh for resilience
- **network-resilience-patterns.md** - Handle Tailscale disconnects
