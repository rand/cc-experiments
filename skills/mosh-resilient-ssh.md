---
name: mosh-resilient-ssh
description: Connecting over unreliable networks (mobile, WiFi)
---



# Mosh - Resilient SSH Alternative

**Use this skill when:**
- Connecting over unreliable networks (mobile, WiFi)
- Working with high-latency connections
- Needing to survive network disconnects
- Roaming between networks while maintaining sessions
- Improving SSH user experience

## Installation

```bash
# macOS
brew install mosh

# Ubuntu/Debian
sudo apt install mosh

# Server must also have mosh installed
```

## Basic Usage

```bash
# Instead of SSH
ssh user@server

# Use Mosh
mosh user@server

# With specific port
mosh --ssh="ssh -p 2222" user@server

# With different mosh port range
mosh -p 60001 user@server
```

## Key Features

### Survives Disconnects

```bash
# Start mosh session
mosh user@server

# Network disconnects (sleep laptop, switch WiFi)
# Session continues when network returns

# Compare to SSH:
# ssh user@server
# [network disconnect]
# -> Connection lost, need to reconnect
```

### Local Echo

```bash
# Mosh predicts typing locally
# No lag when typing even on high-latency links

# Underlined text = predicted (not yet confirmed by server)
# Normal text = confirmed by server
```

### IP Roaming

```bash
# Start mosh on WiFi
mosh user@server

# Switch to cellular
# Session continues seamlessly

# SSH would require reconnect
```

## Configuration

### Server Setup

```bash
# Open UDP ports (mosh uses 60000-61000 by default)
sudo ufw allow 60000:61000/udp

# Or specific range
sudo ufw allow 60001/udp
```

### Custom Port Range

```bash
# Server: restrict port range
export MOSH_SERVER_PORT_RANGE=60001-60010

# Client: use restricted range
mosh -p 60001 user@server
```

## Advanced Usage

### With Tailscale

```bash
# Use mosh over Tailscale
mosh user@100.64.0.5

# Benefits:
# - Encrypted by Tailscale
# - No need to open ports publicly
# - Resilient connection
```

### SSH Configuration

```bash
# ~/.ssh/config
Host myserver
    HostName server.example.com
    User myuser
    Port 2222

# Now use
mosh myserver
```

### Tmux Integration

```bash
# Ultimate resilient setup
mosh user@server -- tmux attach

# Benefits:
# - Mosh handles network disruption
# - Tmux persists session on server
# - Can disconnect mosh and reconnect to same tmux
```

## Limitations

### Not for File Transfers

```bash
# ❌ Can't use scp/rsync over mosh
# Mosh is terminal-only

# ✅ Use SSH for file transfers
scp file.txt user@server:

# Or rsync
rsync -avz --progress file.txt user@server:
```

### Port Requirements

```bash
# Mosh needs UDP ports open
# Some restrictive networks block UDP

# Fallback to SSH if UDP blocked
```

## Comparison

```bash
# SSH:
# - Works everywhere (TCP port 22)
# - File transfers (scp/sftp)
# - Port forwarding
# - Breaks on network change

# Mosh:
# - Survives disconnects
# - IP roaming
# - Low-latency typing
# - Requires UDP ports
# - Terminal only
```

## Related Skills

- **tailscale-vpn.md** - Use mosh over Tailscale
- **secure-networking.md** - Overall networking patterns
