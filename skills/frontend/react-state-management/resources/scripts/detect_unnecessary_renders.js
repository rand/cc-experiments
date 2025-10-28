#!/usr/bin/env node
/**
 * Detect unnecessary re-renders in React components.
 *
 * This script analyzes React component code to identify:
 * - Components that should be wrapped in React.memo
 * - Props that change on every render (object/array literals)
 * - Missing dependencies in useMemo/useCallback
 * - Unstable callback props
 * - Context that triggers too many re-renders
 */

const fs = require('fs');
const path = require('path');

class UnnecessaryRenderDetector {
  constructor(directory, extensions = ['.tsx', '.ts', '.jsx', '.js']) {
    this.directory = directory;
    this.extensions = extensions;
    this.issues = [];
  }

  analyze() {
    const files = this.findReactFiles(this.directory);

    for (const file of files) {
      try {
        const content = fs.readFileSync(file, 'utf-8');
        this.analyzeFile(file, content);
      } catch (error) {
        console.error(`Error analyzing ${file}:`, error.message);
      }
    }

    return this.generateReport();
  }

  findReactFiles(dir) {
    const files = [];

    const walk = (currentPath) => {
      const entries = fs.readdirSync(currentPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentPath, entry.name);

        // Skip node_modules and hidden directories
        if (entry.name.startsWith('.') || entry.name === 'node_modules') {
          continue;
        }

        if (entry.isDirectory()) {
          walk(fullPath);
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name);
          if (this.extensions.includes(ext)) {
            files.push(fullPath);
          }
        }
      }
    };

    walk(dir);
    return files;
  }

  analyzeFile(filePath, content) {
    const lines = content.split('\n');

    // Check if file imports React
    if (!this.isReactFile(content)) {
      return;
    }

    // Find component definitions
    const components = this.findComponents(content);

    for (const component of components) {
      this.analyzeComponent(filePath, content, component, lines);
    }
  }

  isReactFile(content) {
    return (
      content.includes('from "react"') ||
      content.includes("from 'react'") ||
      content.includes('import React') ||
      /<[A-Z]/.test(content)
    );
  }

  findComponents(content) {
    const components = [];

    // Function component pattern
    const functionPattern = /(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w*)\s*(?:<[^>]*>)?\s*\([^)]*\)/g;
    let match;

    // NOTE: .exec() is regex pattern matching, not command execution - no security risk
    while ((match = functionPattern.exec(content)) !== null) {
      components.push({
        name: match[1],
        start: match.index,
        type: 'function',
      });
    }

    // Arrow function component pattern
    const arrowPattern = /(?:export\s+)?(?:default\s+)?const\s+([A-Z]\w*)\s*(?::\s*React\.FC[^=]*)?\s*=\s*(?:React\.memo\s*\()?\s*\([^)]*\)\s*=>/g;

    while ((match = arrowPattern.exec(content)) !== null) {
      components.push({
        name: match[1],
        start: match.index,
        type: 'arrow',
        isMemoized: match[0].includes('React.memo'),
      });
    }

    return components;
  }

  analyzeComponent(filePath, content, component, lines) {
    const componentContent = this.extractComponentBody(content, component.start);

    // Issue 1: Inline object/array props
    this.detectInlineObjectProps(filePath, component, componentContent, lines);

    // Issue 2: Missing React.memo with many props
    this.detectMissingMemo(filePath, component, componentContent, lines);

    // Issue 3: Unstable callbacks
    this.detectUnstableCallbacks(filePath, component, componentContent, lines);

    // Issue 4: Missing dependencies in useMemo/useCallback
    this.detectMissingDependencies(filePath, component, componentContent, lines);

    // Issue 5: Context overuse
    this.detectContextOveruse(filePath, component, componentContent, lines);

    // Issue 6: Expensive computations without memoization
    this.detectExpensiveComputations(filePath, component, componentContent, lines);
  }

  extractComponentBody(content, start) {
    // Extract component body (simplified)
    const remaining = content.substring(start);
    let braceCount = 0;
    let inBody = false;
    let end = 0;

    for (let i = 0; i < remaining.length; i++) {
      if (remaining[i] === '{') {
        braceCount++;
        inBody = true;
      } else if (remaining[i] === '}') {
        braceCount--;
        if (inBody && braceCount === 0) {
          end = i + 1;
          break;
        }
      }
    }

    return remaining.substring(0, end || remaining.length);
  }

  detectInlineObjectProps(filePath, component, content, lines) {
    // Pattern: <Component prop={{ ... }} />
    const inlineObjectPattern = /<[A-Z]\w+[^>]*\w+\s*=\s*\{\{[^}]+\}\}[^>]*>/g;
    const matches = [...content.matchAll(inlineObjectPattern)];

    if (matches.length > 0) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'warning',
        type: 'inline_object_prop',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `${matches.length} inline object props detected. Extract to variables or useMemo.`,
        count: matches.length,
      });
    }

    // Pattern: <Component prop={[...]} />
    const inlineArrayPattern = /<[A-Z]\w+[^>]*\w+\s*=\s*\{\[[^\]]+\]\}[^>]*>/g;
    const arrayMatches = [...content.matchAll(inlineArrayPattern)];

    if (arrayMatches.length > 0) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'warning',
        type: 'inline_array_prop',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `${arrayMatches.length} inline array props detected. Extract to variables or useMemo.`,
        count: arrayMatches.length,
      });
    }
  }

  detectMissingMemo(filePath, component, content, lines) {
    if (component.isMemoized) {
      return; // Already memoized
    }

    // Count props
    const propsMatch = content.match(/\(\s*\{([^}]+)\}\s*[:|,)]/) || content.match(/\(\s*(\w+):\s*\w+/);
    if (!propsMatch) return;

    const propsText = propsMatch[1] || '';
    const propCount = propsText.split(',').filter(p => p.trim()).length;

    // Check if component is memoized
    const hasMemo = content.includes('React.memo') || content.includes('memo(');

    if (propCount >= 3 && !hasMemo) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'info',
        type: 'missing_memo',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `Component has ${propCount} props but is not memoized. Consider React.memo.`,
        propCount,
      });
    }
  }

  detectUnstableCallbacks(filePath, component, content, lines) {
    // Pattern: inline arrow functions in JSX
    const inlineCallbackPattern = /<[A-Z]\w+[^>]*\w+\s*=\s*\{[^}]*=>[^}]*\}/g;
    const matches = [...content.matchAll(inlineCallbackPattern)];

    if (matches.length > 2) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'info',
        type: 'inline_callbacks',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `${matches.length} inline callbacks detected. Consider useCallback for expensive child components.`,
        count: matches.length,
      });
    }
  }

  detectMissingDependencies(filePath, component, content, lines) {
    // Pattern: useMemo/useCallback with potentially missing deps
    const useMemoPattern = /useMemo\(\s*\(\)\s*=>\s*\{[^}]+\},\s*\[([^\]]*)\]/g;
    const useCallbackPattern = /useCallback\(\s*\([^)]*\)\s*=>\s*\{[^}]+\},\s*\[([^\]]*)\]/g;

    let match;

    // Check useMemo
    while ((match = useMemoPattern.exec(content)) !== null) {
      const deps = match[1].trim();
      const body = match[0];

      // Simple check: if body contains variables but deps is empty
      const hasVariables = /\b[a-z]\w+\b/.test(body);
      if (hasVariables && deps === '') {
        const lineNum = this.getLineNumber(lines, component.start + match.index);
        this.issues.push({
          severity: 'warning',
          type: 'missing_memo_deps',
          file: filePath,
          component: component.name,
          line: lineNum,
          message: 'useMemo has empty dependencies but uses variables. May cause stale values.',
        });
      }
    }

    // Check useCallback
    while ((match = useCallbackPattern.exec(content)) !== null) {
      const deps = match[1].trim();
      const body = match[0];

      const hasVariables = /\b[a-z]\w+\b/.test(body);
      if (hasVariables && deps === '') {
        const lineNum = this.getLineNumber(lines, component.start + match.index);
        this.issues.push({
          severity: 'warning',
          type: 'missing_callback_deps',
          file: filePath,
          component: component.name,
          line: lineNum,
          message: 'useCallback has empty dependencies but uses variables. May cause stale values.',
        });
      }
    }
  }

  detectContextOveruse(filePath, component, content, lines) {
    // Count useContext calls
    const contextPattern = /useContext\(/g;
    const matches = [...content.matchAll(contextPattern)];

    if (matches.length > 3) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'warning',
        type: 'excessive_context',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `Component uses ${matches.length} contexts. Consider consolidating or using a state library.`,
        count: matches.length,
      });
    }
  }

  detectExpensiveComputations(filePath, component, content, lines) {
    // Check for expensive operations without useMemo
    const expensivePatterns = [
      { name: 'filter', pattern: /\.filter\(/g },
      { name: 'map', pattern: /\.map\(/g },
      { name: 'reduce', pattern: /\.reduce\(/g },
      { name: 'sort', pattern: /\.sort\(/g },
      { name: 'find', pattern: /\.find\(/g },
    ];

    const hasMemo = /useMemo\(/.test(content);
    let expensiveOps = 0;

    for (const { pattern } of expensivePatterns) {
      const matches = [...content.matchAll(pattern)];
      expensiveOps += matches.length;
    }

    if (expensiveOps > 2 && !hasMemo) {
      const lineNum = this.getLineNumber(lines, component.start);
      this.issues.push({
        severity: 'info',
        type: 'missing_memoization',
        file: filePath,
        component: component.name,
        line: lineNum,
        message: `${expensiveOps} expensive operations detected without useMemo. Consider memoization.`,
        count: expensiveOps,
      });
    }
  }

  getLineNumber(lines, position) {
    let currentPos = 0;
    for (let i = 0; i < lines.length; i++) {
      currentPos += lines[i].length + 1; // +1 for newline
      if (currentPos >= position) {
        return i + 1;
      }
    }
    return 1;
  }

  generateReport() {
    const issuesBySeverity = {
      error: [],
      warning: [],
      info: [],
    };

    for (const issue of this.issues) {
      issuesBySeverity[issue.severity].push(issue);
    }

    const summary = {
      total: this.issues.length,
      error: issuesBySeverity.error.length,
      warning: issuesBySeverity.warning.length,
      info: issuesBySeverity.info.length,
    };

    const issuesByType = {};
    for (const issue of this.issues) {
      if (!issuesByType[issue.type]) {
        issuesByType[issue.type] = [];
      }
      issuesByType[issue.type].push(issue);
    }

    return {
      summary,
      issuesBySeverity,
      issuesByType,
      issues: this.issues,
    };
  }
}

function formatReport(report, format) {
  if (format === 'json') {
    return JSON.stringify(report, null, 2);
  }

  // Text format
  const lines = [];
  lines.push('='.repeat(80));
  lines.push('React Unnecessary Render Detection');
  lines.push('='.repeat(80));
  lines.push('');

  lines.push('Summary:');
  lines.push(`  Total issues: ${report.summary.total}`);
  lines.push(`  Errors: ${report.summary.error}`);
  lines.push(`  Warnings: ${report.summary.warning}`);
  lines.push(`  Info: ${report.summary.info}`);
  lines.push('');

  if (report.issues.length === 0) {
    lines.push('No issues detected!');
    lines.push('');
    lines.push('='.repeat(80));
    return lines.join('\n');
  }

  lines.push('Issues by Type:');
  for (const [type, issues] of Object.entries(report.issuesByType)) {
    lines.push(`  ${type}: ${issues.length}`);
  }
  lines.push('');

  // Group by file
  const issuesByFile = {};
  for (const issue of report.issues) {
    if (!issuesByFile[issue.file]) {
      issuesByFile[issue.file] = [];
    }
    issuesByFile[issue.file].push(issue);
  }

  lines.push('Details:');
  lines.push('');

  for (const [file, issues] of Object.entries(issuesByFile)) {
    lines.push(`File: ${file}`);

    // Group by component
    const issuesByComponent = {};
    for (const issue of issues) {
      if (!issuesByComponent[issue.component]) {
        issuesByComponent[issue.component] = [];
      }
      issuesByComponent[issue.component].push(issue);
    }

    for (const [component, componentIssues] of Object.entries(issuesByComponent)) {
      lines.push(`  Component: ${component}`);

      for (const issue of componentIssues) {
        const severity = issue.severity.toUpperCase();
        lines.push(`    [${severity}] Line ${issue.line}: ${issue.message}`);
      }
    }

    lines.push('');
  }

  lines.push('Recommendations:');
  lines.push('  1. Wrap expensive components in React.memo');
  lines.push('  2. Extract inline objects/arrays to variables or useMemo');
  lines.push('  3. Use useCallback for callbacks passed to memoized components');
  lines.push('  4. Ensure useMemo/useCallback have correct dependencies');
  lines.push('  5. Split large contexts into smaller, focused contexts');
  lines.push('  6. Memoize expensive computations with useMemo');
  lines.push('');
  lines.push('='.repeat(80));

  return lines.join('\n');
}

function main() {
  const args = process.argv.slice(2);

  let directory = '.';
  let format = 'text';
  let extensions = ['.tsx', '.ts', '.jsx', '.js'];
  let showHelp = false;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--json':
        format = 'json';
        break;
      case '--extensions':
        extensions = args[++i].split(',');
        break;
      case '--help':
      case '-h':
        showHelp = true;
        break;
      default:
        if (!args[i].startsWith('--')) {
          directory = args[i];
        }
        break;
    }
  }

  if (showHelp) {
    console.log(`
Usage: detect_unnecessary_renders.js [directory] [options]

Detect unnecessary re-renders in React components.

Arguments:
  directory              Directory to analyze (default: current directory)

Options:
  --json                 Output in JSON format
  --extensions <exts>    Comma-separated file extensions (default: .tsx,.ts,.jsx,.js)
  --help, -h             Show this help message

Examples:
  detect_unnecessary_renders.js ./src
  detect_unnecessary_renders.js ./src --json
  detect_unnecessary_renders.js ./components --extensions .tsx,.jsx
  detect_unnecessary_renders.js ./src --json > report.json
    `);
    process.exit(0);
  }

  // Check if directory exists
  if (!fs.existsSync(directory)) {
    console.error(`Error: Directory ${directory} does not exist`);
    process.exit(1);
  }

  if (!fs.statSync(directory).isDirectory()) {
    console.error(`Error: ${directory} is not a directory`);
    process.exit(1);
  }

  console.error(`Analyzing React components in ${directory}...`);

  const detector = new UnnecessaryRenderDetector(directory, extensions);
  const report = detector.analyze();
  const output = formatReport(report, format);

  console.log(output);

  // Exit with error if critical issues found
  if (report.summary.error > 0) {
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { UnnecessaryRenderDetector };
