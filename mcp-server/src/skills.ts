/**
 * Skill indexing and search logic for cc-polymath MCP server.
 */

import { readdir, readFile } from "node:fs/promises";
import { join, relative, basename } from "node:path";

// ── Types ──────────────────────────────────────────────────

export interface SkillEntry {
  name: string;
  description: string;
  category: string;
  path: string;        // Relative path from skills dir
  lineCount: number;
  isGateway: boolean;
  keywords: string[];  // Extracted from "When to Use" / activation triggers
}

export interface SkillIndex {
  skills: SkillEntry[];
  gateways: SkillEntry[];
  categories: string[];
  byName: Map<string, SkillEntry>;
  byCategory: Map<string, SkillEntry[]>;
}

interface SearchResult {
  skill: SkillEntry;
  score: number;
  matchedIn: string[];
}

// ── Indexing ───────────────────────────────────────────────

function parseFrontmatter(content: string): Record<string, string> {
  if (!content.startsWith("---")) return {};
  const endIdx = content.indexOf("---", 3);
  if (endIdx === -1) return {};
  const block = content.slice(3, endIdx).trim();
  const result: Record<string, string> = {};
  for (const line of block.split("\n")) {
    const match = line.match(/^(\w[\w-]*)\s*:\s*(.+)/);
    if (match) {
      result[match[1]] = match[2].replace(/^["']|["']$/g, "").trim();
    }
  }
  return result;
}

function extractKeywords(content: string): string[] {
  const keywords: string[] = [];
  // Extract from "When This Skill Activates" or "When to Use" sections
  const match = content.match(/## When (?:This Skill Activates|to Use)[^\n]*\n([\s\S]*?)(?=\n## )/);
  if (match) {
    for (const line of match[1].split("\n")) {
      const stripped = line.replace(/^[-*]\s*/, "").trim();
      if (stripped && !stripped.startsWith("#")) {
        // Split comma-separated keywords
        for (const kw of stripped.split(/[,;()]/).map(s => s.trim())) {
          if (kw && kw.length > 1 && kw.length < 60) {
            keywords.push(kw.toLowerCase());
          }
        }
      }
    }
  }
  return keywords;
}

async function indexFile(skillsDir: string, filePath: string): Promise<SkillEntry | null> {
  const content = await readFile(filePath, "utf-8");
  const fm = parseFrontmatter(content);
  if (!fm.name && !fm.description) return null;

  const relPath = relative(skillsDir, filePath);
  const parts = relPath.split("/");
  const isGateway = parts[0]?.startsWith("discover-") && parts[1] === "SKILL.md";
  const lineCount = content.split("\n").length;

  let category: string;
  if (isGateway) {
    category = parts[0].replace("discover-", "");
  } else if (parts.length >= 2) {
    category = parts[0];
  } else {
    category = "root";
  }

  return {
    name: fm.name || basename(filePath, ".md"),
    description: fm.description || "",
    category,
    path: relPath,
    lineCount,
    isGateway,
    keywords: extractKeywords(content),
  };
}

async function walkMd(dir: string): Promise<string[]> {
  const results: string[] = [];
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.name.startsWith(".") || entry.name === "node_modules") continue;
    if (entry.name === "_SKILL_TEMPLATE.md") continue;
    if (entry.isDirectory()) {
      // Skip resources/references subdirs for indexing
      if (entry.name === "resources" || entry.name === "references" || entry.name === "scripts") continue;
      results.push(...await walkMd(full));
    } else if (entry.name.endsWith(".md") && entry.name !== "README.md") {
      results.push(full);
    }
  }
  return results;
}

export async function buildIndex(skillsDir: string): Promise<SkillIndex> {
  const files = await walkMd(skillsDir);
  const entries: SkillEntry[] = [];

  for (const f of files) {
    const entry = await indexFile(skillsDir, f);
    if (entry) entries.push(entry);
  }

  const byName = new Map<string, SkillEntry>();
  const byCategory = new Map<string, SkillEntry[]>();

  for (const entry of entries) {
    byName.set(entry.name, entry);
    const cat = byCategory.get(entry.category) ?? [];
    cat.push(entry);
    byCategory.set(entry.category, cat);
  }

  const categories = [...new Set(entries.map(e => e.category))].sort();

  return {
    skills: entries.filter(e => !e.isGateway),
    gateways: entries.filter(e => e.isGateway),
    categories,
    byName,
    byCategory,
  };
}

// ── Search ─────────────────────────────────────────────────

export function searchSkills(index: SkillIndex, query: string): SearchResult[] {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const results: SearchResult[] = [];

  for (const skill of index.skills) {
    let score = 0;
    const matchedIn: string[] = [];

    for (const term of terms) {
      // Name match (highest weight)
      if (skill.name.toLowerCase().includes(term)) {
        score += 10;
        matchedIn.push("name");
      }
      // Description match
      if (skill.description.toLowerCase().includes(term)) {
        score += 5;
        matchedIn.push("description");
      }
      // Category match
      if (skill.category.toLowerCase().includes(term)) {
        score += 3;
        matchedIn.push("category");
      }
      // Keyword match
      if (skill.keywords.some(kw => kw.includes(term))) {
        score += 4;
        matchedIn.push("keywords");
      }
    }

    if (score > 0) {
      results.push({ skill, score, matchedIn: [...new Set(matchedIn)] });
    }
  }

  return results
    .sort((a, b) => b.score - a.score)
    .slice(0, 20);
}

// ── List ───────────────────────────────────────────────────

interface ListOptions {
  category?: string;
  gateway?: string;
}

export function listSkills(
  index: SkillIndex,
  opts: ListOptions,
): { category: string; skills: Array<{ name: string; description: string; path: string }> }[] {
  const results: { category: string; skills: Array<{ name: string; description: string; path: string }> }[] = [];

  if (opts.gateway) {
    const cat = opts.gateway.replace("discover-", "");
    const skills = index.byCategory.get(cat) ?? [];
    results.push({
      category: cat,
      skills: skills.filter(s => !s.isGateway).map(s => ({
        name: s.name,
        description: s.description,
        path: s.path,
      })),
    });
  } else if (opts.category) {
    const skills = index.byCategory.get(opts.category) ?? [];
    results.push({
      category: opts.category,
      skills: skills.filter(s => !s.isGateway).map(s => ({
        name: s.name,
        description: s.description,
        path: s.path,
      })),
    });
  } else {
    // List all categories with skill counts
    for (const cat of index.categories) {
      const skills = index.byCategory.get(cat) ?? [];
      const leafSkills = skills.filter(s => !s.isGateway);
      if (leafSkills.length > 0) {
        results.push({
          category: cat,
          skills: leafSkills.map(s => ({
            name: s.name,
            description: s.description,
            path: s.path,
          })),
        });
      }
    }
  }

  return results;
}

// ── Skill Info ─────────────────────────────────────────────

export function getSkillInfo(
  index: SkillIndex,
  name: string,
): {
  name: string;
  description: string;
  category: string;
  path: string;
  lineCount: number;
  keywords: string[];
  relatedSkills: string[];
} | null {
  const skill = index.byName.get(name);
  if (!skill) {
    // Try partial match
    for (const [key, entry] of index.byName) {
      if (key.includes(name) || name.includes(key)) {
        return formatInfo(index, entry);
      }
    }
    return null;
  }
  return formatInfo(index, skill);
}

function formatInfo(index: SkillIndex, skill: SkillEntry) {
  // Find related skills in same category
  const siblings = (index.byCategory.get(skill.category) ?? [])
    .filter(s => s.name !== skill.name && !s.isGateway)
    .map(s => s.name)
    .slice(0, 5);

  return {
    name: skill.name,
    description: skill.description,
    category: skill.category,
    path: skill.path,
    lineCount: skill.lineCount,
    keywords: skill.keywords.slice(0, 10),
    relatedSkills: siblings,
  };
}
