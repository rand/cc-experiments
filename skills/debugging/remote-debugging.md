---
name: debugging-remote-debugging
description: Comprehensive guide to remote debugging techniques for production and development environments. Covers SSH port forwarding, VSCode Remote Development, JetBrains Gateway, container debugging (Docker), Kubernetes debugging, production-safe debugging, debug symbols, and source maps.
---

# Remote Debugging

**Last Updated**: 2025-10-26

## Overview

Remote debugging enables debugging applications running on remote servers, containers, or cloud environments. This guide covers safe and effective remote debugging strategies.

## Core Concepts

### Remote Debugging Architecture

```
Local Machine (Debugger)
  ↓ SSH / Network
Remote Machine (Debuggee)
  ↓
Debug Server (gdbserver, debugpy, etc.)
  ↓
Application Process
```

### When to Use Remote Debugging

```
✅ Development on remote server (cloud VM)
✅ Docker container debugging
✅ Kubernetes pod debugging
✅ Production issue investigation (with caution)
✅ IoT / embedded device debugging
✅ Cross-platform debugging (Windows ↔ Linux)

❌ Local development (use local debugger)
❌ Production without monitoring (risky)
❌ High-throughput systems (performance impact)
```

---

## SSH Port Forwarding

### Local Port Forwarding

**Forward remote port to local machine**:
```bash
# Forward remote debugger port 5678 to local 5678
ssh -L 5678:localhost:5678 user@remote-server.com

# Now connect local debugger to localhost:5678
# It tunnels to remote-server.com:5678
```

**Example: Python debugpy**:
```bash
# On remote server:
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client script.py

# On local machine:
ssh -L 5678:localhost:5678 user@remote-server.com

# In VSCode: Attach to localhost:5678
```

### Remote Port Forwarding

**Forward local port to remote machine**:
```bash
# Make local port 8080 accessible on remote at port 9090
ssh -R 9090:localhost:8080 user@remote-server.com

# Remote can now access localhost:9090 → your local 8080
```

### Dynamic Port Forwarding (SOCKS Proxy)

**Create SOCKS proxy for multiple ports**:
```bash
# Dynamic proxy on local port 1080
ssh -D 1080 user@remote-server.com

# Configure browser/app to use SOCKS proxy localhost:1080
# All connections tunnel through SSH
```

### Persistent SSH Tunnels

**Keep tunnel alive**:
```bash
# Auto-reconnect on disconnect
ssh -L 5678:localhost:5678 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 user@remote-server.com

# Or use autossh
autossh -M 0 -L 5678:localhost:5678 user@remote-server.com
```

---

## VSCode Remote Development

### Remote - SSH Extension

**Install extension**:
```
Extensions → Search "Remote - SSH" → Install
```

**Connect to remote**:
```
1. Cmd+Shift+P → "Remote-SSH: Connect to Host"
2. Enter: user@remote-server.com
3. Select platform: Linux / Windows / macOS
4. Opens new VSCode window connected to remote

Now:
  - File Explorer shows remote files
  - Terminal is remote shell
  - Debugger runs on remote
  - Extensions installed on remote
```

**SSH Config** (~/.ssh/config):
```
Host my-remote
    HostName 192.168.1.100
    User myuser
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes

# Connect in VSCode: "Remote-SSH: Connect to Host" → my-remote
```

### Remote Debugging Python

**Install Python extension on remote**:
```
VSCode → Remote connection → Extensions → Install Python
```

**launch.json** (remote debugging):
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File (Remote)",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

**Workflow**:
```
1. Open remote folder in VSCode
2. Set breakpoint in Python file
3. F5 to debug
4. Debugger runs on remote, UI in local VSCode
```

### Remote - Containers Extension

**Debug inside Docker container**:
```
1. Install "Remote - Containers" extension
2. Cmd+Shift+P → "Remote-Containers: Attach to Running Container"
3. Select container
4. Debug inside container environment
```

**devcontainer.json**:
```json
{
    "name": "Python Dev",
    "image": "python:3.11",
    "extensions": [
        "ms-python.python"
    ],
    "forwardPorts": [5678],
    "postCreateCommand": "pip install debugpy"
}
```

---

## JetBrains Gateway

### Remote Development via Gateway

**Setup**:
```
1. Download JetBrains Gateway
2. New Connection → SSH
3. Enter: user@remote-server.com
4. Select IDE (PyCharm, IntelliJ, etc.)
5. Gateway installs IDE backend on remote
6. Opens IDE UI locally, runs on remote
```

**Advantages**:
```
✅ Full IDE features on remote
✅ Large codebase stays on remote (fast indexing)
✅ Automatic port forwarding
✅ Integrated debugger
```

**Remote debugging**:
```
1. Open project on remote via Gateway
2. Set breakpoints
3. Run → Debug (Shift+F9)
4. Debugger runs on remote, UI local
```

---

## Docker Debugging

### Attach to Running Container

**VSCode attach**:
```bash
# Start container with debugger port exposed
docker run -p 5678:5678 my-image

# In VSCode launch.json:
{
    "name": "Python: Attach to Docker",
    "type": "python",
    "request": "attach",
    "connect": {
        "host": "localhost",
        "port": 5678
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/app"
        }
    ]
}
```

**Python container example**:
```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install debugpy
COPY . .

# Start with debugger
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "app.py"]
```

```bash
# Build and run
docker build -t my-app .
docker run -p 5678:5678 my-app

# Attach VSCode debugger to localhost:5678
```

### Docker Exec (Interactive Debugging)

**Attach to running container**:
```bash
# Find container ID
docker ps

# Exec into container
docker exec -it <container-id> /bin/bash

# Install debugger
pip install ipdb

# Add breakpoint in code
import ipdb; ipdb.set_trace()

# Run app, drops into debugger in terminal
```

### Docker Compose Debugging

**docker-compose.yml**:
```yaml
services:
  app:
    build: .
    ports:
      - "5678:5678"
    environment:
      - DEBUGPY_ENABLED=true
    volumes:
      - .:/app  # Mount source for live editing
    command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client app.py
```

```bash
# Start with compose
docker-compose up

# Attach debugger to localhost:5678
```

---

## Kubernetes Debugging

### kubectl debug (Ephemeral Containers)

**Debug running pod** (Kubernetes 1.23+):
```bash
# Create ephemeral debug container in pod
kubectl debug my-pod -it --image=busybox --target=my-container

# Or with debug utilities
kubectl debug my-pod -it --image=nicolaka/netshoot --target=my-container

# Inside debug container:
# Can inspect processes, network, filesystem
ps aux
netstat -tuln
ls /proc/1/root/app
```

**Debug with copy**:
```bash
# Create copy of pod for debugging
kubectl debug my-pod --copy-to=my-pod-debug --container=my-container

# Modify container in copy
kubectl debug my-pod --copy-to=my-pod-debug --container=my-container --image=python:3.11-debug
```

### Port Forwarding

**Forward pod port to local**:
```bash
# Forward pod port 5678 to local 5678
kubectl port-forward pod/my-pod 5678:5678

# Attach debugger to localhost:5678
```

**Forward service**:
```bash
# Forward service port
kubectl port-forward service/my-service 5678:5678
```

### Remote Debugging in Pod

**Deploy with debugger**:
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 5678  # Debug port
        env:
        - name: DEBUG_MODE
          value: "true"
        command: ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "app.py"]
```

```bash
# Apply deployment
kubectl apply -f deployment.yaml

# Forward port
kubectl port-forward deployment/my-app 5678:5678

# Attach debugger to localhost:5678
```

### Kubernetes Debugging Best Practices

```
✅ Use ephemeral containers for live debugging
✅ Create pod copy for intrusive debugging
✅ Use port-forward for debugger access
✅ Remove debug configuration from production
✅ Use separate debug environment/namespace

❌ Don't debug production pods directly (use copy)
❌ Don't leave debug ports exposed
❌ Don't modify production deployments for debugging
```

---

## Production-Safe Debugging

### Principles

**Safety rules**:
```
1. NEVER pause execution in production
   → Use logging, tracing, metrics instead

2. MINIMIZE performance impact
   → Use sampling, not continuous debugging

3. ISOLATE debugging sessions
   → Debug copy of pod/container, not live instance

4. TIME-BOX sessions
   → Set max debug duration, auto-timeout

5. AUDIT access
   → Log who debugged what and when

6. REVERT changes
   → Never leave debug code in production
```

### Read-Only Debugging

**Observe without modifying**:
```python
# ❌ Bad: Modify state in production
def debug_user(user_id):
    user = get_user(user_id)
    user.role = 'admin'  # DANGEROUS IN PRODUCTION
    save_user(user)

# ✅ Good: Observe only
def debug_user(user_id):
    user = get_user(user_id)
    logger.info(f"User state: {user}")  # Read-only
    # Don't modify, just observe
```

### Logging-Based Debugging

**Use structured logging instead of breakpoints**:
```python
import logging
import json

logger = logging.getLogger(__name__)

def process_order(order):
    # Instead of breakpoint(), log context
    logger.info("Processing order", extra={
        "order_id": order.id,
        "user_id": order.user_id,
        "items": [item.id for item in order.items],
        "total": order.total
    })

    result = calculate_total(order)

    logger.info("Order processed", extra={
        "order_id": order.id,
        "result": result
    })

    return result
```

### Sampling and Rate Limiting

**Debug subset of requests**:
```python
import random

def should_debug():
    # Debug 1% of requests
    return random.random() < 0.01

def handle_request(request):
    if should_debug():
        logger.debug("Full request context", extra={
            "headers": request.headers,
            "body": request.body,
            "params": request.params
        })

    # Normal processing
    return process(request)
```

### Time-Limited Debugging

**Auto-disable debug mode**:
```python
import time

DEBUG_ENABLED_UNTIL = None  # Unix timestamp

def enable_debug(duration_seconds):
    global DEBUG_ENABLED_UNTIL
    DEBUG_ENABLED_UNTIL = time.time() + duration_seconds
    logger.warning(f"Debug mode enabled for {duration_seconds}s")

def is_debug_enabled():
    if DEBUG_ENABLED_UNTIL is None:
        return False
    if time.time() > DEBUG_ENABLED_UNTIL:
        logger.info("Debug mode expired")
        return False
    return True

def process_data(data):
    if is_debug_enabled():
        logger.debug(f"Processing: {data}")
    # Normal processing
```

---

## Debug Symbols

### Debug Symbols for Compiled Languages

**C/C++ with GDB**:
```bash
# Compile with debug symbols
gcc -g program.c -o program

# Strip symbols for production (smaller binary)
strip program -o program-stripped

# Debug with separate symbol file
gcc -g program.c -o program
objcopy --only-keep-debug program program.debug
strip program
objcopy --add-gnu-debuglink=program.debug program

# GDB loads symbols automatically
gdb program
(gdb) file program
(gdb) symbol-file program.debug
```

**Rust**:
```bash
# Debug build (includes symbols)
cargo build

# Release build (optimized, no symbols)
cargo build --release

# Release with debug symbols
cargo build --release --config profile.release.debug=true
```

**Go**:
```bash
# Build with symbols (default)
go build -o myapp

# Strip symbols
go build -ldflags="-s -w" -o myapp

# Delve debugger
dlv exec ./myapp
```

### Symbol Servers

**Microsoft Symbol Server** (Windows debugging):
```
Use symbol server for Windows binaries:
SRV*c:\symbols*https://msdl.microsoft.com/download/symbols
```

**Linux debug symbols**:
```bash
# Ubuntu: install debug symbols
sudo apt install <package>-dbg

# Example: Python debug symbols
sudo apt install python3.11-dbg
```

---

## Source Maps (JavaScript/TypeScript)

### Generating Source Maps

**TypeScript**:
```json
// tsconfig.json
{
  "compilerOptions": {
    "sourceMap": true,
    "inlineSourceMap": false,  // Separate .map files
    "inlineSources": false,
    "sourceRoot": "/"
  }
}
```

**Webpack**:
```javascript
// webpack.config.js
module.exports = {
  devtool: 'source-map',  // Production: separate files
  // devtool: 'inline-source-map',  // Development: inline
  // devtool: 'eval-source-map',    // Fastest rebuild
};
```

**Vite**:
```javascript
// vite.config.js
export default {
  build: {
    sourcemap: true,  // Generate .map files
  }
}
```

### Using Source Maps

**Browser DevTools**:
```
Settings (⚙️) → Sources → Enable JavaScript source maps

Loads .map files automatically:
  app.min.js
  app.min.js.map  // Loaded automatically

Debug shows original TypeScript/source code
```

**Node.js**:
```bash
# Enable source maps
node --enable-source-maps app.js

# Stack traces show original source, not transpiled
```

### Production Source Maps

**Security considerations**:
```
❌ Don't expose source maps publicly
   → Reveals source code to attackers

✅ Host source maps separately, restrict access
✅ Use Sentry/error tracking to symbolicate server-side
✅ Strip source maps from public builds
```

**Sentry source maps**:
```bash
# Upload source maps to Sentry
sentry-cli releases files <release> upload-sourcemaps ./dist --rewrite

# Sentry symbolicates errors using uploaded maps
# Users never see source maps
```

---

## Remote Debugging Tools by Language

### Python: debugpy

**Remote script**:
```python
import debugpy

# Listen on all interfaces, port 5678
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger...")
debugpy.wait_for_client()  # Block until debugger attaches

# Your code
def main():
    for i in range(10):
        print(f"Iteration {i}")

if __name__ == "__main__":
    main()
```

**VSCode attach**:
```json
{
    "name": "Python: Remote Attach",
    "type": "python",
    "request": "attach",
    "connect": {
        "host": "remote-server.com",
        "port": 5678
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/app"
        }
    ]
}
```

### Node.js: Inspector

**Start with inspector**:
```bash
# Remote Node.js
node --inspect=0.0.0.0:9229 app.js

# Or debug-brk (pause at start)
node --inspect-brk=0.0.0.0:9229 app.js
```

**Chrome DevTools**:
```
1. SSH tunnel: ssh -L 9229:localhost:9229 user@remote
2. Chrome: chrome://inspect
3. Configure: Add localhost:9229
4. Click "inspect" under Remote Target
```

**VSCode attach**:
```json
{
    "name": "Node: Attach to Remote",
    "type": "node",
    "request": "attach",
    "address": "localhost",
    "port": 9229,
    "localRoot": "${workspaceFolder}",
    "remoteRoot": "/app"
}
```

### Go: Delve

**Remote debugging**:
```bash
# On remote server
dlv debug --headless --listen=:2345 --api-version=2 --accept-multiclient

# Local machine
dlv connect remote-server.com:2345
```

**VSCode attach**:
```json
{
    "name": "Go: Connect to Remote",
    "type": "go",
    "request": "attach",
    "mode": "remote",
    "remotePath": "/app",
    "port": 2345,
    "host": "remote-server.com"
}
```

### Java: JDWP

**Start JVM with debug agent**:
```bash
# Remote Java
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005 -jar app.jar
```

**IntelliJ remote debug**:
```
1. Run → Edit Configurations
2. Add → Remote JVM Debug
3. Host: remote-server.com
4. Port: 5005
5. Click Debug
```

---

## Anti-Patterns

### Common Mistakes

```
❌ NEVER: Debug production without copy/staging
   → Pausing production = downtime

❌ NEVER: Leave debug ports exposed to internet
   → Security vulnerability, remote code execution

❌ NEVER: Commit debug code (breakpoint(), debugger;)
   → Pauses production app

❌ NEVER: Debug without SSH tunnel on public network
   → Unencrypted debug traffic

❌ NEVER: Modify production state while debugging
   → Data corruption, undefined behavior

❌ NEVER: Debug high-traffic endpoints
   → Performance impact affects all users
```

### Best Practices

```
✅ ALWAYS: Use SSH tunnels for remote debugging
✅ ALWAYS: Debug on copy/staging, not production
✅ ALWAYS: Time-limit debug sessions
✅ ALWAYS: Use read-only debugging in production
✅ ALWAYS: Prefer logging/tracing over breakpoints
✅ ALWAYS: Remove debug configuration after session
✅ ALWAYS: Audit who debugged what and when
```

---

## Related Skills

- **gdb-fundamentals.md**: GDB for C/C++/Rust
- **lldb-macos-debugging.md**: LLDB for macOS/iOS
- **python-debugging.md**: Python debugging tools
- **browser-devtools.md**: Browser debugging
- **docker-debugging.md**: Docker-specific debugging
- **kubernetes-debugging.md**: Kubernetes debugging strategies

---

## Summary

Remote debugging enables debugging applications in remote environments:

1. **SSH tunneling**: Port forwarding for secure remote access
2. **VSCode Remote**: Remote-SSH, Remote-Containers extensions
3. **JetBrains Gateway**: Full IDE on remote servers
4. **Docker debugging**: Attach to containers, exec debugging
5. **Kubernetes debugging**: Ephemeral containers, port forwarding
6. **Production safety**: Read-only, sampling, time-limited debugging
7. **Debug symbols**: Separate symbols for production binaries
8. **Source maps**: JavaScript/TypeScript source mapping

**Quick start (Python)**:
```bash
# Remote server
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client app.py

# Local machine
ssh -L 5678:localhost:5678 user@remote-server.com

# VSCode: Attach to localhost:5678
```

**Production debugging**:
```python
# Use logging, not breakpoints
logger.info("Debug context", extra={"user_id": user.id, "state": state})

# Sample 1% of requests
if random.random() < 0.01:
    logger.debug("Full request", extra={"request": request})
```

Master remote debugging for efficient distributed system troubleshooting.
