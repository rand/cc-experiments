---
name: discover-proxies
description: Automatically discover proxy skills when working with forward/reverse proxies, nginx, traefik, envoy, caching, or NATS messaging
license: MIT
metadata:
  author: rand
  version: "3.1"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# Proxies Skills Discovery

Provides automatic access to comprehensive proxy and messaging skills.

## When This Skill Activates

This skill auto-activates when you're working with:
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

The Proxies category contains 7 skills:

1. **forward-proxy** - Forward proxy fundamentals, HTTP CONNECT, SOCKS protocols
2. **reverse-proxy** - Reverse proxy patterns, load balancing, SSL termination
3. **nginx-configuration** - Nginx setup, locations, upstreams, caching, SSL
4. **traefik-configuration** - Traefik dynamic config, middleware, Let's Encrypt
5. **envoy-proxy** - Envoy architecture, filters, clusters, observability
6. **cache-control** - HTTP caching, cache headers, CDN patterns, invalidation
7. **nats-messaging** - NATS pub/sub, request-reply, JetStream, clustering

### Load Full Category Details

For complete descriptions and workflows:

Read <cc-polymath-root>/skills/proxies/INDEX.md


This loads the full Proxies category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

Read <cc-polymath-root>/skills/proxies/forward-proxy.md
Read <cc-polymath-root>/skills/proxies/reverse-proxy.md
Read <cc-polymath-root>/skills/proxies/nginx-configuration.md
Read <cc-polymath-root>/skills/proxies/traefik-configuration.md
Read <cc-polymath-root>/skills/proxies/envoy-proxy.md
Read <cc-polymath-root>/skills/proxies/cache-control.md
Read <cc-polymath-root>/skills/proxies/nats-messaging.md


## Common Workflows

### Setting Up Reverse Proxy
# Reverse proxy → Nginx/Traefik → Caching
Read <cc-polymath-root>/skills/proxies/reverse-proxy.md
Read <cc-polymath-root>/skills/proxies/nginx-configuration.md
Read <cc-polymath-root>/skills/proxies/cache-control.md


### Cloud-Native Proxy Stack
# Traefik → Service discovery → Let's Encrypt
Read <cc-polymath-root>/skills/proxies/traefik-configuration.md
Read <cc-polymath-root>/skills/proxies/reverse-proxy.md


### Service Mesh and Observability
# Envoy → Advanced routing → Messaging
Read <cc-polymath-root>/skills/proxies/envoy-proxy.md
Read <cc-polymath-root>/skills/proxies/nats-messaging.md


### Caching and CDN Optimization
# HTTP caching → CDN patterns → Nginx
Read <cc-polymath-root>/skills/proxies/cache-control.md
Read <cc-polymath-root>/skills/proxies/nginx-configuration.md
Read <cc-polymath-root>/skills/proxies/reverse-proxy.md


### Microservices Communication
# NATS → Load balancing → Proxy patterns
Read <cc-polymath-root>/skills/proxies/nats-messaging.md
Read <cc-polymath-root>/skills/proxies/reverse-proxy.md
Read <cc-polymath-root>/skills/proxies/envoy-proxy.md


## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects proxy/messaging work
2. **Browse skills**: Run `Read <cc-polymath-root>/skills/proxies/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills


**Next Steps**: Run `Read <cc-polymath-root>/skills/proxies/INDEX.md` to see full category details.
