#!/usr/bin/env node
/**
 * cc-polymath MCP Server
 *
 * Provides skill discovery tools via MCP protocol, offloading
 * discovery from the context window to tool calls.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { buildIndex, searchSkills, listSkills, getSkillInfo, type SkillIndex } from "./skills.js";

const SKILLS_DIR = process.env.CC_POLYMATH_SKILLS_DIR
  ?? new URL("../../skills", import.meta.url).pathname;

let index: SkillIndex;

async function main() {
  index = await buildIndex(SKILLS_DIR);

  const server = new McpServer({
    name: "cc-polymath",
    version: "4.0.0",
  });

  server.tool(
    "search_skills",
    "Full-text search across all cc-polymath skill descriptions and content. Returns matching skills with relevance scores.",
    { query: z.string().describe("Search query (e.g., 'postgres optimization', 'react state')") },
    async ({ query }) => {
      const results = searchSkills(index, query);
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(results, null, 2),
        }],
      };
    },
  );

  server.tool(
    "list_skills",
    "List cc-polymath skills filtered by category or keywords. Shows skill names, descriptions, and paths.",
    {
      category: z.string().optional().describe("Category name (e.g., 'api', 'database', 'frontend')"),
      gateway: z.string().optional().describe("Gateway name (e.g., 'discover-api')"),
    },
    async ({ category, gateway }) => {
      const results = listSkills(index, { category, gateway });
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(results, null, 2),
        }],
      };
    },
  );

  server.tool(
    "skill_info",
    "Get metadata about a specific cc-polymath skill without loading its full content. Returns name, description, category, line count, and related skills.",
    { name: z.string().describe("Skill name (e.g., 'rest-api-design', 'postgres-migrations')") },
    async ({ name }) => {
      const result = getSkillInfo(index, name);
      return {
        content: [{
          type: "text" as const,
          text: result ? JSON.stringify(result, null, 2) : `Skill '${name}' not found`,
        }],
      };
    },
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
