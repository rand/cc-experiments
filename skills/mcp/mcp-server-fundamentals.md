---
name: mcp-server-fundamentals
description: MCP server architecture, transports (stdio, SSE, Streamable HTTP), and the three primitives (tools, resources, prompts) with TypeScript and Python SDK examples
---

# MCP Server Fundamentals

**Scope**: MCP architecture, transports, tools/resources/prompts primitives, server lifecycle
**Lines**: ~300
**Last Updated**: 2025-11-01

## When to Use This Skill

Activate this skill when:
- Building a new MCP server from scratch
- Choosing a transport (stdio, SSE, Streamable HTTP)
- Implementing tools, resources, or prompts
- Understanding client-server capability negotiation
- Setting up TypeScript or Python MCP SDKs
- Debugging server initialization or lifecycle issues

## Core Concepts

### MCP Architecture

MCP follows a **client-server** model over **JSON-RPC 2.0**:

```
Host Application (e.g., Claude Code)
  └── MCP Client
        ↕ JSON-RPC 2.0 (over transport)
      MCP Server
        └── Tools, Resources, Prompts
```

**Key roles**:
- **Host**: The application embedding MCP (Claude Desktop, Claude Code, custom app)
- **Client**: Maintains a 1:1 connection with a server, handles protocol negotiation
- **Server**: Exposes capabilities (tools, resources, prompts) to the client

MCP servers are **stateful**. Each client-server pair maintains a session with capability negotiation at initialization.

---

### Transports

#### stdio (Standard I/O)
Best for local processes. Client spawns the server as a subprocess.

```
Client --stdin--> Server
Client <--stdout-- Server
```

- Simplest to implement and debug
- Used by Claude Code for local MCP servers
- No network configuration needed
- Server logs must go to stderr (stdout is the transport)

#### SSE (Server-Sent Events)
HTTP-based, suitable for remote servers. Uses SSE for server-to-client and HTTP POST for client-to-server.

- Works through firewalls and proxies
- One-directional streaming (server to client)
- Client sends requests via POST to a message endpoint
- Being superseded by Streamable HTTP

#### Streamable HTTP
The modern HTTP transport. Single HTTP endpoint supporting both request-response and streaming.

- Replaces SSE as the recommended HTTP transport
- Supports bidirectional communication
- Stateless-friendly (can work without persistent connections)
- Better for serverless and load-balanced deployments

**Transport selection guide**:
| Scenario | Transport |
|----------|-----------|
| Local CLI tool / Claude Code plugin | stdio |
| Remote server, simple deployment | Streamable HTTP |
| Legacy remote server | SSE |
| Serverless / load-balanced | Streamable HTTP |

---

### The Three Primitives

MCP exposes three types of capabilities, each with different control semantics:

#### Tools (Model-Controlled)
Functions the LLM can invoke. The model decides when and how to call them.

```typescript
// TypeScript SDK
server.tool(
  "search_files",
  "Search for files matching a pattern",
  {
    pattern: z.string().describe("Glob pattern to match"),
    directory: z.string().optional().describe("Directory to search in"),
  },
  async ({ pattern, directory }) => {
    const results = await glob(pattern, { cwd: directory });
    return {
      content: [{ type: "text", text: results.join("\n") }],
    };
  }
);
```

```python
# Python SDK
@server.tool()
async def search_files(pattern: str, directory: str | None = None) -> str:
    """Search for files matching a glob pattern."""
    results = glob.glob(pattern, root_dir=directory or ".")
    return "\n".join(results)
```

**Key properties**:
- Invoked by the AI model based on user intent
- Accept structured JSON input (validated against schema)
- Return content (text, images, embedded resources)
- Can indicate errors via `isError: true`

#### Resources (Application-Controlled)
Data sources the client application can read. Like GET endpoints.

```typescript
server.resource(
  "config",
  "config://app/settings",
  "Application configuration",
  async () => ({
    contents: [{
      uri: "config://app/settings",
      mimeType: "application/json",
      text: JSON.stringify(await loadConfig()),
    }],
  })
);
```

```python
@server.resource("config://app/settings")
async def get_config() -> str:
    """Application configuration."""
    return json.dumps(load_config())
```

**Key properties**:
- Identified by URI (any scheme: `file://`, `config://`, `db://`, etc.)
- Read by the application, not directly by the model
- Can be static or dynamic (with list-changed notifications)
- Support subscriptions for real-time updates

#### Prompts (User-Controlled)
Reusable prompt templates the user can select. Like prompt shortcuts.

```typescript
server.prompt(
  "code_review",
  "Review code for issues",
  [{ name: "code", description: "Code to review", required: true }],
  async ({ code }) => ({
    messages: [{
      role: "user",
      content: { type: "text", text: `Review this code:\n\n${code}` },
    }],
  })
);
```

```python
@server.prompt()
async def code_review(code: str) -> str:
    """Review code for issues."""
    return f"Review this code:\n\n{code}"
```

**Key properties**:
- Selected by the user (e.g., via slash commands)
- Accept arguments to customize the prompt
- Return message arrays (can include context and instructions)
- Useful for standardizing common workflows

**Control model summary**:
| Primitive | Controlled By | Analogy |
|-----------|--------------|---------|
| Tools | AI Model | POST endpoints (actions) |
| Resources | Application | GET endpoints (data) |
| Prompts | User | Saved templates |

---

### Server Lifecycle

#### Initialization
```
Client                    Server
  |--- initialize -------->|    (send capabilities, protocol version)
  |<-- initialize result --|    (server capabilities, protocol version)
  |--- initialized ------->|    (acknowledgment, ready to use)
  |                        |
  |--- tool/resource/etc ->|    (normal operations)
```

The `initialize` handshake includes:
- **Protocol version**: Both sides agree on MCP version
- **Capabilities**: Server declares which primitives it supports
- **Client info**: Name and version of the host application
- **Server info**: Name and version of the server

#### Capability Declaration

```typescript
const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
  capabilities: {
    tools: {},          // Server provides tools
    resources: {},      // Server provides resources
    prompts: {},        // Server provides prompts
  },
});
```

Only declare capabilities you actually implement. Clients use this to know what to request.

#### Shutdown
- Client sends a close signal or drops the transport
- Server should clean up resources (close DB connections, temp files)
- For stdio: closing stdin signals shutdown
- For HTTP: client stops sending requests

---

### TypeScript SDK Setup

```bash
npm install @modelcontextprotocol/sdk zod
```

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

// Register tools, resources, prompts here...

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Python SDK Setup

```bash
pip install mcp
# or: uv add mcp
```

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP("my-server")

# Register tools, resources, prompts with decorators...

if __name__ == "__main__":
    server.run()  # Defaults to stdio transport
```

For SSE/Streamable HTTP in Python:
```python
if __name__ == "__main__":
    server.run(transport="sse", port=8080)
    # or: server.run(transport="streamable-http", port=8080)
```

---

## Anti-Patterns

- **Logging to stdout on stdio transport**: stdout IS the transport. Use stderr for logs.
- **Not declaring capabilities**: Client won't know what the server offers.
- **Skipping initialization handshake**: Required by protocol; can't skip it.
- **Mixing concerns in one server**: Prefer focused servers over monolithic ones.
- **Ignoring shutdown**: Clean up resources; don't leave dangling connections.
- **Hardcoding transport**: Design server logic independent of transport for flexibility.

## Checklist

- [ ] Server name and version set correctly
- [ ] Transport chosen based on deployment scenario
- [ ] Capabilities declared for all implemented primitives
- [ ] Initialization handshake implemented
- [ ] Graceful shutdown handling
- [ ] Logs go to stderr (not stdout) for stdio transport
- [ ] Error responses use proper JSON-RPC error format
- [ ] Server tested with MCP Inspector before integration

## Related Skills

- `mcp-tool-design.md` - Designing effective tool interfaces
- `mcp-testing.md` - Testing MCP servers
- `../api/rest-api-design.md` - REST patterns that MCP tools often wrap
- `../protocols` - Protocol design fundamentals
