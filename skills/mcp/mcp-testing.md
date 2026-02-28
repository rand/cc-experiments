---
name: mcp-testing
description: Testing MCP servers with Inspector, unit tests, integration tests, transport debugging, and CI/CD patterns
---

# MCP Testing

**Scope**: MCP Inspector, unit testing, integration testing, transport debugging, CI/CD
**Lines**: ~250
**Last Updated**: 2025-11-01

## When to Use This Skill

Activate this skill when:
- Testing MCP tools, resources, or prompts
- Using the MCP Inspector for interactive debugging
- Writing unit tests for tool handlers
- Building integration tests with mock MCP clients
- Debugging transport-level issues (stdio, SSE, Streamable HTTP)
- Setting up CI/CD pipelines for MCP servers
- Diagnosing schema validation or capability negotiation errors

## Core Concepts

### MCP Inspector

The MCP Inspector is the primary debugging tool for MCP servers. It provides an interactive UI to call tools, read resources, and test prompts.

#### Installation and Usage

```bash
# Run Inspector against a stdio server
npx @modelcontextprotocol/inspector node build/index.js

# With arguments
npx @modelcontextprotocol/inspector node build/index.js -- --config path/to/config

# For Python servers
npx @modelcontextprotocol/inspector python -m my_server

# For uv-managed Python servers
npx @modelcontextprotocol/inspector uv run my-server
```

#### Inspector Features
- **Tools tab**: List all tools, view schemas, call with custom input, see responses
- **Resources tab**: Browse resources, read contents, test URI patterns
- **Prompts tab**: List prompts, fill arguments, preview generated messages
- **Notifications panel**: See server-sent notifications in real time
- **Request history**: Review all JSON-RPC messages exchanged

#### Debugging with Inspector

**Common workflow**:
1. Start Inspector with your server
2. Verify all tools/resources/prompts appear (capability check)
3. Call each tool with valid input -- verify response format
4. Call each tool with invalid input -- verify error handling
5. Test edge cases: empty strings, large inputs, special characters
6. Check that descriptions and schemas look correct for LLM consumption

---

### Unit Testing Tools

Test tool handlers in isolation without running the full MCP server.

#### TypeScript

```typescript
import { describe, it, expect } from "vitest";

// Extract handler logic into testable functions
async function searchFiles(pattern: string, directory?: string) {
  const results = await glob(pattern, { cwd: directory || "." });
  return results;
}

describe("searchFiles", () => {
  it("finds matching files", async () => {
    const results = await searchFiles("*.ts", "./src");
    expect(results).toContain("index.ts");
  });

  it("returns empty array for no matches", async () => {
    const results = await searchFiles("*.xyz", "./src");
    expect(results).toEqual([]);
  });

  it("handles invalid directory", async () => {
    await expect(searchFiles("*", "/nonexistent"))
      .rejects.toThrow();
  });
});
```

#### Python

```python
import pytest
from my_server import search_files

@pytest.mark.asyncio
async def test_search_files_finds_matches():
    results = await search_files("*.py", "./src")
    assert "main.py" in results

@pytest.mark.asyncio
async def test_search_files_empty_results():
    results = await search_files("*.xyz", "./src")
    assert results == []

@pytest.mark.asyncio
async def test_search_files_invalid_directory():
    with pytest.raises(FileNotFoundError):
        await search_files("*", "/nonexistent")
```

**Key principle**: Separate business logic from MCP wiring. Test the logic directly.

---

### Integration Testing with Mock Clients

Test the full MCP protocol flow including serialization, schema validation, and transport.

#### TypeScript SDK Client

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

describe("MCP Server Integration", () => {
  let client: Client;
  let transport: StdioClientTransport;

  beforeAll(async () => {
    transport = new StdioClientTransport({
      command: "node",
      args: ["build/index.js"],
    });
    client = new Client({ name: "test-client", version: "1.0.0" });
    await client.connect(transport);
  });

  afterAll(async () => {
    await client.close();
  });

  it("lists expected tools", async () => {
    const tools = await client.listTools();
    const names = tools.tools.map(t => t.name);
    expect(names).toContain("search_files");
    expect(names).toContain("read_file");
  });

  it("calls search_files successfully", async () => {
    const result = await client.callTool("search_files", {
      pattern: "*.ts",
    });
    expect(result.isError).toBeFalsy();
    expect(result.content).toBeDefined();
    expect(result.content[0].type).toBe("text");
  });

  it("returns error for invalid input", async () => {
    const result = await client.callTool("read_file", {
      path: "/nonexistent/file.txt",
    });
    expect(result.isError).toBe(true);
  });
});
```

#### Python SDK Client

```python
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.fixture
async def client():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "my_server"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

@pytest.mark.asyncio
async def test_list_tools(client):
    tools = await client.list_tools()
    names = [t.name for t in tools.tools]
    assert "search_files" in names

@pytest.mark.asyncio
async def test_call_tool(client):
    result = await client.call_tool("search_files", {"pattern": "*.py"})
    assert not result.isError
    assert len(result.content) > 0
```

---

### Transport-Level Testing

#### stdio Testing
- Verify server does not write non-JSON-RPC content to stdout
- Check that logs go to stderr only
- Test with malformed JSON input -- server should return JSON-RPC error, not crash
- Verify server exits cleanly when stdin closes

```bash
# Manual stdio test: send initialize request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | node build/index.js 2>/dev/null
```

#### HTTP Transport Testing
- Test SSE/Streamable HTTP endpoint responds to health checks
- Verify CORS headers if browser clients will connect
- Test connection drop and reconnection behavior
- Verify session management across requests

```bash
# Test Streamable HTTP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}'
```

---

### Debugging Common Issues

#### Tool Not Appearing in Client
1. Check capability declaration includes `tools: {}`
2. Verify tool registration happens before `server.connect()`
3. Use Inspector to confirm tool is listed
4. Check for registration errors in stderr logs

#### Schema Validation Failures
1. Inspect the schema sent to clients (use Inspector's raw view)
2. Verify Zod/Pydantic schema matches what the model generates
3. Test with exact JSON the model would produce
4. Check for mismatched required/optional fields

#### Transport Errors
1. **stdio**: Check nothing else writes to stdout (no `console.log`!)
2. **SSE**: Verify event stream format (`data: {...}\n\n`)
3. **Streamable HTTP**: Check Content-Type headers
4. Use `MCP_DEBUG=1` environment variable for protocol-level logging

#### Initialization Failures
1. Check protocol version compatibility
2. Verify capability object structure
3. Ensure `initialized` notification is sent after init response
4. Test with Inspector first (it handles init automatically)

---

### CI/CD Patterns

#### Basic CI Pipeline

```yaml
# .github/workflows/mcp-test.yml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - run: npm ci
      - run: npm run build
      - run: npm test

      # Integration test: verify server starts and responds
      - name: MCP smoke test
        run: |
          echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"ci","version":"1.0"}}}' \
          | timeout 10 node build/index.js 2>/dev/null \
          | head -1 \
          | jq -e '.result.serverInfo'
```

#### Python CI

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest
      - name: MCP smoke test
        run: |
          echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"ci","version":"1.0"}}}' \
          | timeout 10 python -m my_server 2>/dev/null \
          | head -1 \
          | jq -e '.result.serverInfo'
```

#### What to Test in CI
- [ ] Unit tests pass (tool logic)
- [ ] Integration tests pass (protocol flow)
- [ ] Server starts and responds to initialize
- [ ] All declared tools are callable
- [ ] Schema validation rejects bad input
- [ ] Build artifacts are valid (TypeScript compiles, Python imports)

---

## Anti-Patterns

- **Testing only happy paths**: Always test error cases, empty results, invalid input
- **Testing through the model**: Use direct tool calls, not LLM-in-the-loop tests
- **Skipping Inspector**: Always validate with Inspector before integrating with clients
- **No CI smoke test**: At minimum, verify the server starts and responds to init
- **Testing transport and logic together**: Separate concerns for faster, reliable tests
- **Hardcoded test data paths**: Use temp directories and fixtures

## Checklist

- [ ] All tool handlers have unit tests (happy + error paths)
- [ ] Integration tests cover full protocol flow
- [ ] Inspector used to verify tool listing and schemas
- [ ] Transport-level smoke test exists
- [ ] CI pipeline runs tests on every push
- [ ] Error responses tested (isError, structured messages)
- [ ] Edge cases covered (empty input, large payloads, special chars)
- [ ] Schema validation tested with invalid input
- [ ] Server startup and shutdown tested

## Related Skills

- `mcp-server-fundamentals.md` - Server architecture and lifecycle
- `mcp-tool-design.md` - Tool design and error handling
- `../testing` - General testing strategies
- `../cicd` - CI/CD pipeline design
