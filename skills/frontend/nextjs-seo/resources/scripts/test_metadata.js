#!/usr/bin/env node
/**
 * Next.js Metadata Test Utility
 *
 * Test metadata generation for Next.js pages. Validates metadata structure,
 * checks for required fields, and verifies Open Graph and Twitter Card tags.
 *
 * Usage:
 *   ./test_metadata.js <path-to-page>
 *   ./test_metadata.js app/page.tsx
 *   ./test_metadata.js app/blog/[slug]/page.tsx --json
 *   ./test_metadata.js app/products/[id]/page.tsx --params id=123
 *   ./test_metadata.js --help
 */

const fs = require('fs');
const path = require('path');

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    file: null,
    json: false,
    params: {},
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--params') {
      i++;
      if (i < args.length) {
        const paramPairs = args[i].split(',');
        paramPairs.forEach(pair => {
          const [key, value] = pair.split('=');
          if (key && value) {
            options.params[key.trim()] = value.trim();
          }
        });
      }
    } else if (!options.file && !arg.startsWith('--')) {
      options.file = arg;
    }
  }

  return options;
}

// Print help
function printHelp() {
  console.log(`
Next.js Metadata Test Utility

Usage:
  test_metadata.js <path-to-page> [options]

Options:
  --json                Output results as JSON
  --params <params>     Provide route params (e.g., id=123,slug=hello)
  --help, -h            Show this help message

Examples:
  test_metadata.js app/page.tsx
  test_metadata.js app/blog/[slug]/page.tsx --params slug=my-post
  test_metadata.js app/products/[id]/page.tsx --params id=123 --json

Description:
  Analyzes Next.js page files for metadata exports and validates:
  - Static metadata objects
  - Dynamic generateMetadata functions
  - Required fields (title, description)
  - Open Graph tags
  - Twitter Card tags
  - Canonical URLs
  - Character count recommendations
  `);
}

// Analyze file content
function analyzeMetadata(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  const content = fs.readFileSync(filePath, 'utf8');
  const results = {
    file: filePath,
    hasStaticMetadata: false,
    hasDynamicMetadata: false,
    issues: [],
    warnings: [],
    successes: [],
    metadata: {},
  };

  // Check for static metadata export
  const staticMetadataRegex = /export\s+const\s+metadata\s*[:=]\s*\{/;
  if (staticMetadataRegex.test(content)) {
    results.hasStaticMetadata = true;
    results.successes.push({
      category: 'export',
      message: 'Found static metadata export',
    });
  }

  // Check for dynamic metadata function
  const dynamicMetadataRegex = /export\s+async\s+function\s+generateMetadata/;
  if (dynamicMetadataRegex.test(content)) {
    results.hasDynamicMetadata = true;
    results.successes.push({
      category: 'export',
      message: 'Found generateMetadata function',
    });
  }

  if (!results.hasStaticMetadata && !results.hasDynamicMetadata) {
    results.issues.push({
      category: 'export',
      message: 'No metadata export found',
      severity: 'error',
    });
  }

  // Check for title
  if (content.includes('title:') || content.includes('title =')) {
    results.successes.push({
      category: 'title',
      message: 'Title field found',
    });

    // Check for title template
    if (content.includes('template:')) {
      results.successes.push({
        category: 'title',
        message: 'Title template found',
      });
    }
  } else {
    results.warnings.push({
      category: 'title',
      message: 'No title field found',
    });
  }

  // Check for description
  if (content.includes('description:') || content.includes('description =')) {
    results.successes.push({
      category: 'description',
      message: 'Description field found',
    });
  } else {
    results.warnings.push({
      category: 'description',
      message: 'No description field found',
    });
  }

  // Check for Open Graph
  if (content.includes('openGraph:') || content.includes('openGraph =')) {
    results.successes.push({
      category: 'open_graph',
      message: 'Open Graph tags found',
    });

    // Check for OG image
    if (content.includes('images:') || content.includes('images =')) {
      results.successes.push({
        category: 'open_graph',
        message: 'Open Graph images configured',
      });
    } else {
      results.warnings.push({
        category: 'open_graph',
        message: 'Open Graph missing images',
      });
    }
  } else {
    results.warnings.push({
      category: 'open_graph',
      message: 'No Open Graph tags found',
    });
  }

  // Check for Twitter Cards
  if (content.includes('twitter:') || content.includes('twitter =')) {
    results.successes.push({
      category: 'twitter',
      message: 'Twitter Card tags found',
    });
  } else {
    results.warnings.push({
      category: 'twitter',
      message: 'No Twitter Card tags found',
    });
  }

  // Check for canonical URL
  if (content.includes('canonical:') || content.includes('alternates:')) {
    results.successes.push({
      category: 'canonical',
      message: 'Canonical URL configuration found',
    });
  } else {
    results.warnings.push({
      category: 'canonical',
      message: 'No canonical URL found',
    });
  }

  // Check for robots
  if (content.includes('robots:') || content.includes('robots =')) {
    results.successes.push({
      category: 'robots',
      message: 'Robots configuration found',
    });
  }

  // Check for metadataBase
  if (content.includes('metadataBase:') || content.includes('metadataBase =')) {
    results.successes.push({
      category: 'metadata_base',
      message: 'metadataBase configured',
    });
  } else if (!content.includes('layout.tsx') && !content.includes('layout.ts')) {
    results.warnings.push({
      category: 'metadata_base',
      message: 'metadataBase not found (should be in root layout)',
    });
  }

  // Check for TypeScript types
  if (content.includes('import { Metadata }') || content.includes('import type { Metadata }')) {
    results.successes.push({
      category: 'types',
      message: 'TypeScript Metadata type imported',
    });
  } else if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) {
    results.warnings.push({
      category: 'types',
      message: 'Metadata type not imported',
    });
  }

  // Check for async data fetching in generateMetadata
  if (results.hasDynamicMetadata) {
    if (content.includes('await ') && content.includes('generateMetadata')) {
      results.successes.push({
        category: 'async',
        message: 'generateMetadata uses async data fetching',
      });
    }

    // Check for error handling
    if (content.includes('try') && content.includes('catch')) {
      results.successes.push({
        category: 'error_handling',
        message: 'Error handling found in metadata generation',
      });
    } else {
      results.warnings.push({
        category: 'error_handling',
        message: 'No error handling in generateMetadata',
      });
    }
  }

  // Check for dynamic routes
  const isDynamicRoute = /\[.*\]/.test(filePath);
  if (isDynamicRoute && !results.hasDynamicMetadata) {
    results.warnings.push({
      category: 'dynamic_route',
      message: 'Dynamic route should use generateMetadata function',
    });
  }

  return results;
}

// Format text output
function formatTextOutput(results) {
  const lines = [];

  lines.push('');
  lines.push('='.repeat(60));
  lines.push(`NEXT.JS METADATA TEST: ${results.file}`);
  lines.push('='.repeat(60));
  lines.push('');

  // Summary
  lines.push('SUMMARY');
  lines.push('-'.repeat(60));
  lines.push(`Metadata Type: ${results.hasStaticMetadata ? 'Static' : ''}${results.hasDynamicMetadata ? 'Dynamic' : ''}${!results.hasStaticMetadata && !results.hasDynamicMetadata ? 'None' : ''}`);
  lines.push(`Issues:        ${results.issues.length}`);
  lines.push(`Warnings:      ${results.warnings.length}`);
  lines.push(`Successes:     ${results.successes.length}`);
  lines.push('');

  // Issues
  if (results.issues.length > 0) {
    lines.push('ISSUES');
    lines.push('-'.repeat(60));
    results.issues.forEach(issue => {
      lines.push(`[${issue.severity.toUpperCase()}] ${issue.category}: ${issue.message}`);
    });
    lines.push('');
  }

  // Warnings
  if (results.warnings.length > 0) {
    lines.push('WARNINGS');
    lines.push('-'.repeat(60));
    results.warnings.forEach(warning => {
      lines.push(`[WARN] ${warning.category}: ${warning.message}`);
    });
    lines.push('');
  }

  // Successes
  if (results.successes.length > 0) {
    lines.push('SUCCESSES');
    lines.push('-'.repeat(60));
    results.successes.forEach(success => {
      lines.push(`[OK] ${success.category}: ${success.message}`);
    });
    lines.push('');
  }

  // Recommendations
  lines.push('RECOMMENDATIONS');
  lines.push('-'.repeat(60));

  if (!results.hasStaticMetadata && !results.hasDynamicMetadata) {
    lines.push('- Add metadata export to this page');
  }

  if (results.warnings.some(w => w.category === 'title')) {
    lines.push('- Add a title field (50-60 characters recommended)');
  }

  if (results.warnings.some(w => w.category === 'description')) {
    lines.push('- Add a description field (150-160 characters recommended)');
  }

  if (results.warnings.some(w => w.category === 'open_graph')) {
    lines.push('- Add Open Graph tags for social media sharing');
  }

  if (results.warnings.some(w => w.category === 'twitter')) {
    lines.push('- Add Twitter Card tags for Twitter/X sharing');
  }

  if (results.warnings.some(w => w.category === 'canonical')) {
    lines.push('- Add canonical URL to prevent duplicate content issues');
  }

  if (results.warnings.length === 0 && results.issues.length === 0) {
    lines.push('No issues found. Metadata configuration looks good!');
  }

  lines.push('');
  lines.push('='.repeat(60));
  lines.push('');

  return lines.join('\n');
}

// Main
function main() {
  const options = parseArgs();

  if (options.help) {
    printHelp();
    process.exit(0);
  }

  if (!options.file) {
    console.error('Error: No file specified');
    console.error('Run with --help for usage information');
    process.exit(1);
  }

  try {
    const results = analyzeMetadata(options.file);

    if (options.json) {
      console.log(JSON.stringify(results, null, 2));
    } else {
      console.log(formatTextOutput(results));
    }

    // Exit with error code if there are issues
    process.exit(results.issues.length > 0 ? 1 : 0);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

main();
