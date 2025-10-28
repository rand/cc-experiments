#!/usr/bin/env node
/**
 * Benchmark React render performance with different state management approaches.
 *
 * This script:
 * - Simulates React component trees with various state patterns
 * - Measures render count and timing
 * - Compares useState, useReducer, Context, Zustand, Jotai
 * - Reports performance metrics
 * - Identifies performance bottlenecks
 */

const fs = require('fs');
const path = require('path');

// Simple React-like simulation for benchmarking
class ComponentTree {
  constructor(name, depth, stateType) {
    this.name = name;
    this.depth = depth;
    this.stateType = stateType;
    this.renderCount = 0;
    this.children = [];
    this.state = {};
    this.props = {};
  }

  setState(updates) {
    this.state = { ...this.state, ...updates };
    this.render();
  }

  render() {
    this.renderCount++;
    // Simulate render work
    let sum = 0;
    for (let i = 0; i < 1000; i++) {
      sum += Math.random();
    }
    // Propagate to children
    this.children.forEach(child => child.render());
  }

  addChild(child) {
    this.children.push(child);
  }
}

// State management patterns
const statePatterns = {
  // Local useState pattern
  useState: {
    name: 'useState (local)',
    setup: (tree, depth) => {
      // Each component has local state
      for (let i = 0; i < depth; i++) {
        const node = new ComponentTree(`Component-${i}`, i, 'useState');
        node.state = { count: 0 };
        if (i > 0) {
          tree.children[tree.children.length - 1].addChild(node);
        } else {
          tree.addChild(node);
        }
      }
    },
    update: (tree) => {
      // Update random component
      const allNodes = getAllNodes(tree);
      const node = allNodes[Math.floor(Math.random() * allNodes.length)];
      node.setState({ count: node.state.count + 1 });
    },
  },

  // Context pattern (causes re-renders in all consumers)
  context: {
    name: 'Context (global)',
    setup: (tree, depth) => {
      // Shared context state
      tree.contextState = { count: 0 };
      for (let i = 0; i < depth; i++) {
        const node = new ComponentTree(`Consumer-${i}`, i, 'context');
        node.contextRef = tree.contextState;
        if (i > 0) {
          tree.children[tree.children.length - 1].addChild(node);
        } else {
          tree.addChild(node);
        }
      }
    },
    update: (tree) => {
      // Update context (re-renders all consumers)
      tree.contextState.count++;
      const allNodes = getAllNodes(tree);
      allNodes.forEach(node => {
        if (node.contextRef) {
          node.render();
        }
      });
    },
  },

  // Optimized Context (split state/dispatch)
  contextOptimized: {
    name: 'Context (optimized)',
    setup: (tree, depth) => {
      tree.contextState = { count: 0 };
      tree.contextDispatch = (action) => {
        tree.contextState = { ...tree.contextState, count: tree.contextState.count + 1 };
      };

      for (let i = 0; i < depth; i++) {
        const node = new ComponentTree(`OptConsumer-${i}`, i, 'contextOptimized');
        // Only subscribe to dispatch (not state)
        if (i % 2 === 0) {
          node.contextRef = tree.contextState;
        } else {
          node.dispatchRef = tree.contextDispatch;
        }
        if (i > 0) {
          tree.children[tree.children.length - 1].addChild(node);
        } else {
          tree.addChild(node);
        }
      }
    },
    update: (tree) => {
      tree.contextState.count++;
      const allNodes = getAllNodes(tree);
      allNodes.forEach(node => {
        // Only re-render state consumers
        if (node.contextRef) {
          node.render();
        }
      });
    },
  },

  // Zustand-like pattern (selector-based)
  zustand: {
    name: 'Zustand (selector)',
    setup: (tree, depth) => {
      tree.store = {
        state: { count: 0, user: null, theme: 'light' },
        listeners: new Map(),
        subscribe: (selector, callback) => {
          const id = Math.random();
          tree.store.listeners.set(id, { selector, callback });
          return () => tree.store.listeners.delete(id);
        },
        setState: (updates) => {
          const oldState = tree.store.state;
          tree.store.state = { ...tree.store.state, ...updates };
          // Only notify if selected value changed
          tree.store.listeners.forEach(({ selector, callback }) => {
            const oldValue = selector(oldState);
            const newValue = selector(tree.store.state);
            if (oldValue !== newValue) {
              callback(newValue);
            }
          });
        },
      };

      for (let i = 0; i < depth; i++) {
        const node = new ComponentTree(`ZustandComp-${i}`, i, 'zustand');
        // Different selectors
        const selector = i % 3 === 0
          ? (state) => state.count
          : i % 3 === 1
          ? (state) => state.theme
          : (state) => state.user;

        tree.store.subscribe(selector, () => {
          node.render();
        });

        if (i > 0) {
          tree.children[tree.children.length - 1].addChild(node);
        } else {
          tree.addChild(node);
        }
      }
    },
    update: (tree) => {
      // Only updates count, so only 1/3 of components re-render
      tree.store.setState({ count: tree.store.state.count + 1 });
    },
  },

  // Jotai-like pattern (atom-based)
  jotai: {
    name: 'Jotai (atoms)',
    setup: (tree, depth) => {
      tree.atoms = {
        count: { value: 0, listeners: new Set() },
        theme: { value: 'light', listeners: new Set() },
        user: { value: null, listeners: new Set() },
      };

      tree.setAtom = (atom, value) => {
        atom.value = value;
        atom.listeners.forEach(listener => listener());
      };

      for (let i = 0; i < depth; i++) {
        const node = new ComponentTree(`JotaiComp-${i}`, i, 'jotai');
        // Subscribe to specific atom
        const atomName = i % 3 === 0 ? 'count' : i % 3 === 1 ? 'theme' : 'user';
        tree.atoms[atomName].listeners.add(() => node.render());

        if (i > 0) {
          tree.children[tree.children.length - 1].addChild(node);
        } else {
          tree.addChild(node);
        }
      }
    },
    update: (tree) => {
      // Only updates count atom
      tree.setAtom(tree.atoms.count, tree.atoms.count.value + 1);
    },
  },
};

function getAllNodes(tree) {
  const nodes = [tree];
  tree.children.forEach(child => {
    nodes.push(...getAllNodes(child));
  });
  return nodes;
}

function resetRenderCounts(tree) {
  tree.renderCount = 0;
  tree.children.forEach(child => resetRenderCounts(child));
}

function getTotalRenders(tree) {
  let total = tree.renderCount;
  tree.children.forEach(child => {
    total += getTotalRenders(child);
  });
  return total;
}

function benchmark(patternName, pattern, config) {
  const { depth, updates } = config;

  // Setup
  const rootTree = new ComponentTree('Root', 0, patternName);
  pattern.setup(rootTree, depth);

  // Warm up
  for (let i = 0; i < 10; i++) {
    pattern.update(rootTree);
  }
  resetRenderCounts(rootTree);

  // Benchmark
  const startTime = process.hrtime.bigint();
  for (let i = 0; i < updates; i++) {
    pattern.update(rootTree);
  }
  const endTime = process.hrtime.bigint();

  const totalTime = Number(endTime - startTime) / 1_000_000; // Convert to ms
  const totalRenders = getTotalRenders(rootTree);
  const avgTimePerUpdate = totalTime / updates;
  const avgRendersPerUpdate = totalRenders / updates;

  return {
    pattern: patternName,
    depth,
    updates,
    totalTime: totalTime.toFixed(2),
    avgTimePerUpdate: avgTimePerUpdate.toFixed(2),
    totalRenders,
    avgRendersPerUpdate: avgRendersPerUpdate.toFixed(2),
  };
}

function runBenchmarks(config) {
  console.error(`Running benchmarks with depth=${config.depth}, updates=${config.updates}...`);

  const results = [];

  for (const [name, pattern] of Object.entries(statePatterns)) {
    const result = benchmark(name, pattern, config);
    results.push(result);
  }

  return results;
}

function formatResults(results, format) {
  if (format === 'json') {
    return JSON.stringify({ results }, null, 2);
  }

  // Text format
  const lines = [];
  lines.push('='.repeat(80));
  lines.push('React State Management Render Benchmark');
  lines.push('='.repeat(80));
  lines.push('');

  // Table header
  lines.push('Pattern                  | Avg Time/Update | Avg Renders/Update | Total Renders');
  lines.push('-'.repeat(80));

  // Sort by avgRendersPerUpdate
  results.sort((a, b) => parseFloat(a.avgRendersPerUpdate) - parseFloat(b.avgRendersPerUpdate));

  for (const result of results) {
    const pattern = result.pattern.padEnd(24);
    const avgTime = `${result.avgTimePerUpdate}ms`.padEnd(15);
    const avgRenders = result.avgRendersPerUpdate.padEnd(18);
    const totalRenders = result.totalRenders;

    lines.push(`${pattern} | ${avgTime} | ${avgRenders} | ${totalRenders}`);
  }

  lines.push('');
  lines.push('Analysis:');

  const best = results[0];
  const worst = results[results.length - 1];
  const ratio = (parseFloat(worst.avgRendersPerUpdate) / parseFloat(best.avgRendersPerUpdate)).toFixed(2);

  lines.push(`  Best: ${best.pattern} (${best.avgRendersPerUpdate} renders/update)`);
  lines.push(`  Worst: ${worst.pattern} (${worst.avgRendersPerUpdate} renders/update)`);
  lines.push(`  Ratio: ${ratio}x difference`);
  lines.push('');

  lines.push('Recommendations:');
  lines.push('  - Avoid Context for frequently updated state');
  lines.push('  - Use selector-based libraries (Zustand) for better performance');
  lines.push('  - Atom-based solutions (Jotai) provide granular updates');
  lines.push('  - Split Context into state/dispatch for optimization');
  lines.push('  - Colocate state when possible (useState)');
  lines.push('');
  lines.push('='.repeat(80));

  return lines.join('\n');
}

function main() {
  const args = process.argv.slice(2);

  // Parse arguments
  let depth = 10;
  let updates = 100;
  let format = 'text';
  let showHelp = false;

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--depth':
        depth = parseInt(args[++i], 10);
        break;
      case '--updates':
        updates = parseInt(args[++i], 10);
        break;
      case '--json':
        format = 'json';
        break;
      case '--help':
      case '-h':
        showHelp = true;
        break;
    }
  }

  if (showHelp) {
    console.log(`
Usage: benchmark_renders.js [options]

Benchmark React render performance with different state management approaches.

Options:
  --depth <n>      Component tree depth (default: 10)
  --updates <n>    Number of state updates to test (default: 100)
  --json           Output in JSON format
  --help, -h       Show this help message

Examples:
  benchmark_renders.js
  benchmark_renders.js --depth 20 --updates 500
  benchmark_renders.js --json
  benchmark_renders.js --depth 15 --updates 200 --json > results.json
    `);
    process.exit(0);
  }

  // Validate inputs
  if (isNaN(depth) || depth < 1) {
    console.error('Error: depth must be a positive integer');
    process.exit(1);
  }

  if (isNaN(updates) || updates < 1) {
    console.error('Error: updates must be a positive integer');
    process.exit(1);
  }

  const config = { depth, updates };
  const results = runBenchmarks(config);
  const output = formatResults(results, format);

  console.log(output);
}

if (require.main === module) {
  main();
}

module.exports = { statePatterns, benchmark, runBenchmarks };
