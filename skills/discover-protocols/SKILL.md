---
name: discover-protocols
description: Automatically discover protocol skills when working with HTTP, TCP, UDP, QUIC, and network protocols
---

# Protocols Skills Discovery

Provides automatic access to comprehensive network protocol skills.

## When This Skill Activates

This skill auto-activates when you're working with:
- HTTP, HTTP/2, HTTP/3
- TCP, UDP, QUIC
- network protocols
- protocol debugging
- protocol selection
- network communication
- web protocols
- transport layer
- application layer protocols

## Available Skills

### Quick Reference

The Protocols category contains 8 skills:

1. **http-fundamentals** - HTTP/1.1 basics, methods, headers, status codes
2. **http2-multiplexing** - HTTP/2 with multiplexing, server push, HPACK
3. **http3-quic** - HTTP/3 over QUIC, 0-RTT, connection migration
4. **tcp-fundamentals** - TCP protocol, handshake, flow control, congestion
5. **udp-fundamentals** - UDP protocol, connectionless communication
6. **quic-protocol** - QUIC transport layer deep dive
7. **protocol-selection** - Guide for choosing protocols
8. **protocol-debugging** - Debug protocols with tcpdump, Wireshark, curl

### Load Full Category Details

For complete descriptions and workflows:

```bash
cat skills/protocols/INDEX.md
```

This loads the full Protocols category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

```bash
cat skills/protocols/http-fundamentals.md
cat skills/protocols/http2-multiplexing.md
cat skills/protocols/tcp-fundamentals.md
cat skills/protocols/protocol-debugging.md
```

## Common Workflows

### Web Development
```bash
# HTTP basics → HTTP/2 optimization → Debugging
cat skills/protocols/http-fundamentals.md
cat skills/protocols/http2-multiplexing.md
cat skills/protocols/protocol-debugging.md
```

### Protocol Selection
```bash
# Understand options → Choose protocol → Implement
cat skills/protocols/protocol-selection.md
cat skills/protocols/tcp-fundamentals.md
cat skills/protocols/udp-fundamentals.md
```

### Performance Optimization
```bash
# Current protocol → Modern alternatives → Debug issues
cat skills/protocols/http-fundamentals.md
cat skills/protocols/http3-quic.md
cat skills/protocols/protocol-debugging.md
```

## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects protocol work
2. **Browse skills**: Run `cat skills/protocols/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills

---

**Next Steps**: Run `cat skills/protocols/INDEX.md` to see full category details.
