---
name: discover-networking
description: Automatically discover networking and connectivity skills when working with TCP, UDP, DNS, mTLS, NAT traversal, SSH, Mosh, Tailscale, or network resilience. Activates for networking development tasks.
license: MIT
metadata:
  author: rand
  version: "4.0"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# Networking Skills Discovery

Provides automatic access to comprehensive networking skills.

## When This Skill Activates
This skill auto-activates when you're working with:
- networking
- SSH
- mTLS
- NAT traversal
- VPN
- Tailscale
- network resilience
- connection reliability
- HTTP, HTTP/2, HTTP/3
- TCP, UDP, QUIC
- network protocols
- protocol debugging
- protocol selection
- network communication
- web protocols
- transport layer
- application layer protocols
- Forward/reverse proxies
- HTTP proxy configuration
- Nginx, Traefik, Envoy, Caddy
- Load balancing
- SSL/TLS termination
- HTTP caching and CDN
- Cache invalidation
- NATS messaging
- Service mesh patterns

## Available Skills

### Quick Reference

The Networking category contains 20 skills across 3 subcategories:

**Networking (5 skills):**
1. **mosh-resilient-ssh**
2. **mtls-implementation**
3. **nat-traversal**
4. **network-resilience-patterns**
5. **tailscale-vpn**

**Protocols (8 skills):** See `../protocols/INDEX.md`
**Proxies (7 skills):** See `../proxies/INDEX.md`

### Load Full Category Details
Read ../networking/INDEX.md
Read ../protocols/INDEX.md
Read ../proxies/INDEX.md

## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects networking work
2. **Browse skills**: Run `Read ../networking/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills


**Next Steps**: Run `Read ../networking/INDEX.md` to see full category details.
