---
name: mcp-index
description: Index of MCP (Model Context Protocol) Skills
---

# MCP (Model Context Protocol) Skills

Comprehensive skills for building MCP servers, designing tools, implementing resources and prompts, and testing MCP integrations.

## Category Overview

**Total Skills**: 3
**Focus**: MCP server architecture, tool design, testing and debugging
**Use Cases**: Building MCP servers, creating AI-agent-accessible tools, extending Claude Code and other AI clients

## Skills in This Category

### mcp-server-fundamentals.md
**Description**: MCP architecture, transports, and the three primitives (tools, resources, prompts)
**Lines**: ~300
**Use When**:
- Building a new MCP server from scratch
- Choosing between stdio, SSE, or Streamable HTTP transports
- Implementing tools, resources, or prompts
- Understanding the MCP client-server lifecycle
- Setting up TypeScript or Python MCP SDKs
- Implementing capability negotiation and server initialization
- Working with JSON-RPC 2.0 over MCP transports

**Key Concepts**: Client-server architecture, JSON-RPC 2.0, stdio/SSE/Streamable HTTP transports, tools, resources, prompts, capability negotiation, server lifecycle

---

### mcp-tool-design.md
**Description**: Designing effective MCP tools with proper schemas, error handling, and annotations
**Lines**: ~280
**Use When**:
- Designing MCP tool interfaces and parameter schemas
- Naming tools and writing descriptions for LLM consumption
- Implementing error handling with isError flag
- Adding tool annotations (readOnlyHint, destructiveHint, openWorldHint)
- Making tools idempotent and safe
- Applying progressive disclosure patterns (list -> detail -> execute)
- Avoiding common MCP tool anti-patterns

**Key Concepts**: Tool naming, JSON Schema input validation, error handling, tool annotations, idempotency, progressive disclosure, LLM-friendly descriptions

---

### mcp-testing.md
**Description**: Testing MCP servers with Inspector, unit tests, integration tests, and CI/CD
**Lines**: ~250
**Use When**:
- Testing MCP tools, resources, or prompts in isolation
- Using the MCP Inspector for interactive debugging
- Writing integration tests with mock MCP clients
- Debugging transport-level issues (stdio, SSE)
- Setting up CI/CD pipelines for MCP servers
- Diagnosing schema validation or capability errors
- Load testing MCP server endpoints

**Key Concepts**: MCP Inspector, unit testing, integration testing, mock clients, transport debugging, schema validation, CI/CD patterns

---

## Common Workflows

### New MCP Server
**Goal**: Build an MCP server from scratch

**Sequence**:
1. `mcp-server-fundamentals.md` - Architecture, transport selection, SDK setup
2. `mcp-tool-design.md` - Design tool interfaces and schemas
3. `mcp-testing.md` - Test with Inspector, write integration tests

**Example**: File management server exposing read/write/search tools

---

### Adding Tools to Existing Server
**Goal**: Extend an MCP server with new tools

**Sequence**:
1. `mcp-tool-design.md` - Design tool interface, naming, schema
2. `mcp-server-fundamentals.md` - Reference primitives and capability patterns
3. `mcp-testing.md` - Test new tools in isolation and integration

**Example**: Adding a database query tool to an existing server

---

### Debugging MCP Issues
**Goal**: Diagnose and fix MCP server problems

**Sequence**:
1. `mcp-testing.md` - Use Inspector, check transport and schema errors
2. `mcp-server-fundamentals.md` - Verify lifecycle and capability negotiation
3. `mcp-tool-design.md` - Review error handling and schema compliance

**Example**: Tool calls returning unexpected errors or missing from tool list

---

### Production MCP Server
**Goal**: Ship a production-ready MCP server

**Sequence**:
1. `mcp-server-fundamentals.md` - Choose transport, implement lifecycle
2. `mcp-tool-design.md` - Design robust tool interfaces with annotations
3. `mcp-testing.md` - Full test suite, CI/CD pipeline

**Example**: Publishing an MCP server as an npm/pip package

---

## Skill Combinations

### With API Skills (`discover-api`)
- MCP servers wrapping REST or GraphQL APIs
- Authentication patterns for MCP tool backends
- Rate limiting MCP tool invocations

**Common combos**:
- `mcp-tool-design.md` + `api/rest-api-design.md`
- `mcp-server-fundamentals.md` + `api/api-authentication.md`

---

### With Testing Skills (`discover-testing`)
- Comprehensive test strategies for MCP servers
- Contract testing between MCP clients and servers
- Performance testing tool execution

**Common combos**:
- `mcp-testing.md` + `testing/integration-testing.md`
- `mcp-testing.md` + `testing/performance-testing.md`

---

### With Infrastructure Skills (`discover-infra`, `discover-infra`)
- Deploying MCP servers (Docker, serverless)
- Scaling SSE/Streamable HTTP transports
- Monitoring MCP server health

**Common combos**:
- `mcp-server-fundamentals.md` + `infrastructure/infrastructure-security.md`
- `mcp-server-fundamentals.md` + `containers/docker-fundamentals.md`

---

## Loading Skills

All skills are available in the `skills/mcp/` directory:

Read mcp-server-fundamentals.md
Read mcp-tool-design.md
Read mcp-testing.md


**Pro tip**: Start with fundamentals for new servers, jump to tool design when extending existing servers, and use testing when debugging issues.

---

**Related Categories**:
- `discover-api` - API design patterns (REST, GraphQL) that MCP servers often wrap
- `discover-testing` - General testing strategies
- `discover-infra` - Deployment and scaling
- `discover-networking` - Protocol design fundamentals
