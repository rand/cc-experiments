#!/usr/bin/env node
/**
 * GraphQL Query Benchmark Tool
 *
 * Benchmarks GraphQL query performance with detailed metrics.
 * Supports concurrent requests, query complexity analysis, and timing breakdowns.
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

class BenchmarkResult {
  constructor() {
    this.totalRequests = 0;
    this.successfulRequests = 0;
    this.failedRequests = 0;
    this.timings = [];
    this.errors = [];
    this.minTime = Infinity;
    this.maxTime = 0;
    this.totalTime = 0;
    this.querySizes = [];
    this.responseSizes = [];
  }

  addTiming(timing) {
    this.totalRequests++;
    this.timings.push(timing);
    this.totalTime += timing;
    this.minTime = Math.min(this.minTime, timing);
    this.maxTime = Math.max(this.maxTime, timing);

    if (timing > 0) {
      this.successfulRequests++;
    }
  }

  addError(error) {
    this.failedRequests++;
    this.errors.push(error);
  }

  addQuerySize(size) {
    this.querySizes.push(size);
  }

  addResponseSize(size) {
    this.responseSizes.push(size);
  }

  getStats() {
    const sortedTimings = [...this.timings].sort((a, b) => a - b);
    const avgTime = this.totalTime / this.totalRequests || 0;

    const p50 = this.percentile(sortedTimings, 50);
    const p90 = this.percentile(sortedTimings, 90);
    const p95 = this.percentile(sortedTimings, 95);
    const p99 = this.percentile(sortedTimings, 99);

    const avgQuerySize = this.average(this.querySizes);
    const avgResponseSize = this.average(this.responseSizes);

    return {
      totalRequests: this.totalRequests,
      successfulRequests: this.successfulRequests,
      failedRequests: this.failedRequests,
      successRate: (this.successfulRequests / this.totalRequests * 100) || 0,
      timings: {
        min: this.minTime,
        max: this.maxTime,
        avg: avgTime,
        p50,
        p90,
        p95,
        p99,
      },
      throughput: {
        requestsPerSecond: this.totalRequests / (this.totalTime / 1000) || 0,
      },
      sizes: {
        avgQuerySize,
        avgResponseSize,
      },
      errors: this.errors,
    };
  }

  percentile(sorted, p) {
    if (sorted.length === 0) return 0;
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  average(arr) {
    if (arr.length === 0) return 0;
    return arr.reduce((sum, val) => sum + val, 0) / arr.length;
  }
}

class GraphQLBenchmark {
  constructor(endpoint, options = {}) {
    this.endpoint = endpoint;
    this.options = {
      concurrent: options.concurrent || 1,
      iterations: options.iterations || 10,
      warmup: options.warmup || 0,
      timeout: options.timeout || 30000,
      headers: options.headers || {},
      ...options,
    };
  }

  async benchmark(query, variables = {}) {
    const result = new BenchmarkResult();

    // Warmup phase
    if (this.options.warmup > 0) {
      console.error(`Warming up with ${this.options.warmup} requests...`);
      for (let i = 0; i < this.options.warmup; i++) {
        await this.executeQuery(query, variables);
      }
    }

    // Benchmark phase
    console.error(`Running ${this.options.iterations} iterations with concurrency ${this.options.concurrent}...`);

    const batches = Math.ceil(this.options.iterations / this.options.concurrent);

    for (let batch = 0; batch < batches; batch++) {
      const batchSize = Math.min(
        this.options.concurrent,
        this.options.iterations - batch * this.options.concurrent
      );

      const promises = [];
      for (let i = 0; i < batchSize; i++) {
        promises.push(
          this.executeQuery(query, variables)
            .then(({ timing, querySize, responseSize }) => {
              result.addTiming(timing);
              result.addQuerySize(querySize);
              result.addResponseSize(responseSize);
            })
            .catch((error) => {
              result.addError(error.message);
            })
        );
      }

      await Promise.all(promises);
    }

    return result.getStats();
  }

  async executeQuery(query, variables) {
    const payload = JSON.stringify({ query, variables });
    const querySize = Buffer.byteLength(payload);

    const url = new URL(this.endpoint);
    const isHttps = url.protocol === 'https:';
    const client = isHttps ? https : http;

    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const options = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': querySize,
          ...this.options.headers,
        },
        timeout: this.options.timeout,
      };

      const req = client.request(options, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', () => {
          const timing = Date.now() - startTime;
          const responseSize = Buffer.byteLength(data);

          if (res.statusCode !== 200) {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
            return;
          }

          try {
            const json = JSON.parse(data);
            if (json.errors) {
              reject(new Error(`GraphQL errors: ${JSON.stringify(json.errors)}`));
              return;
            }

            resolve({ timing, querySize, responseSize });
          } catch (error) {
            reject(new Error(`JSON parse error: ${error.message}`));
          }
        });
      });

      req.on('error', (error) => {
        reject(error);
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      req.write(payload);
      req.end();
    });
  }
}

function formatHumanOutput(stats, query) {
  const lines = [];

  lines.push('='.repeat(60));
  lines.push('GraphQL Query Benchmark Results');
  lines.push('='.repeat(60));
  lines.push('');

  // Query info
  lines.push('Query:');
  lines.push(query.trim().split('\n').map(l => '  ' + l).join('\n'));
  lines.push('');

  // Request stats
  lines.push('Requests:');
  lines.push(`  Total: ${stats.totalRequests}`);
  lines.push(`  Successful: ${stats.successfulRequests}`);
  lines.push(`  Failed: ${stats.failedRequests}`);
  lines.push(`  Success Rate: ${stats.successRate.toFixed(2)}%`);
  lines.push('');

  // Timing stats
  lines.push('Response Times (ms):');
  lines.push(`  Min: ${stats.timings.min.toFixed(2)}`);
  lines.push(`  Max: ${stats.timings.max.toFixed(2)}`);
  lines.push(`  Avg: ${stats.timings.avg.toFixed(2)}`);
  lines.push(`  P50: ${stats.timings.p50.toFixed(2)}`);
  lines.push(`  P90: ${stats.timings.p90.toFixed(2)}`);
  lines.push(`  P95: ${stats.timings.p95.toFixed(2)}`);
  lines.push(`  P99: ${stats.timings.p99.toFixed(2)}`);
  lines.push('');

  // Throughput
  lines.push('Throughput:');
  lines.push(`  Requests/sec: ${stats.throughput.requestsPerSecond.toFixed(2)}`);
  lines.push('');

  // Size stats
  lines.push('Payload Sizes (bytes):');
  lines.push(`  Avg Query Size: ${stats.sizes.avgQuerySize.toFixed(0)}`);
  lines.push(`  Avg Response Size: ${stats.sizes.avgResponseSize.toFixed(0)}`);
  lines.push('');

  // Errors
  if (stats.errors.length > 0) {
    lines.push('Errors:');
    stats.errors.slice(0, 10).forEach(error => {
      lines.push(`  - ${error}`);
    });
    if (stats.errors.length > 10) {
      lines.push(`  ... and ${stats.errors.length - 10} more`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

function parseArgs() {
  const args = process.argv.slice(2);

  const config = {
    endpoint: null,
    query: null,
    variables: {},
    concurrent: 1,
    iterations: 10,
    warmup: 0,
    timeout: 30000,
    headers: {},
    json: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    switch (arg) {
      case '--help':
      case '-h':
        showHelp();
        process.exit(0);
        break;

      case '--endpoint':
      case '-e':
        config.endpoint = args[++i];
        break;

      case '--query':
      case '-q':
        config.query = args[++i];
        break;

      case '--query-file':
        const fs = require('fs');
        config.query = fs.readFileSync(args[++i], 'utf8');
        break;

      case '--variables':
      case '-v':
        config.variables = JSON.parse(args[++i]);
        break;

      case '--concurrent':
      case '-c':
        config.concurrent = parseInt(args[++i], 10);
        break;

      case '--iterations':
      case '-i':
        config.iterations = parseInt(args[++i], 10);
        break;

      case '--warmup':
        config.warmup = parseInt(args[++i], 10);
        break;

      case '--timeout':
        config.timeout = parseInt(args[++i], 10);
        break;

      case '--header':
        const [key, value] = args[++i].split(':');
        config.headers[key.trim()] = value.trim();
        break;

      case '--json':
        config.json = true;
        break;

      default:
        if (!config.endpoint && arg.startsWith('http')) {
          config.endpoint = arg;
        }
        break;
    }
  }

  return config;
}

function showHelp() {
  console.log(`
GraphQL Query Benchmark Tool

Usage:
  benchmark_queries.js [options]

Options:
  -e, --endpoint <url>      GraphQL endpoint URL
  -q, --query <query>       GraphQL query string
  --query-file <file>       Read query from file
  -v, --variables <json>    Query variables as JSON
  -c, --concurrent <n>      Concurrent requests (default: 1)
  -i, --iterations <n>      Total iterations (default: 10)
  --warmup <n>              Warmup requests (default: 0)
  --timeout <ms>            Request timeout (default: 30000)
  --header <key:value>      Add HTTP header
  --json                    Output as JSON
  -h, --help                Show this help

Examples:
  # Basic benchmark
  benchmark_queries.js -e http://localhost:4000/graphql -q "{ users { id name } }"

  # With concurrency
  benchmark_queries.js -e http://localhost:4000/graphql -q "{ users { id } }" -c 10 -i 100

  # With variables
  benchmark_queries.js -e http://localhost:4000/graphql \\
    -q "query GetUser($id: ID!) { user(id: $id) { name } }" \\
    -v '{"id":"123"}'

  # With authentication
  benchmark_queries.js -e http://localhost:4000/graphql \\
    --query-file query.graphql \\
    --header "Authorization: Bearer token123"

  # JSON output
  benchmark_queries.js -e http://localhost:4000/graphql -q "{ users { id } }" --json
  `);
}

async function main() {
  const config = parseArgs();

  if (!config.endpoint || !config.query) {
    console.error('Error: --endpoint and --query are required');
    console.error('Use --help for usage information');
    process.exit(1);
  }

  try {
    const benchmark = new GraphQLBenchmark(config.endpoint, config);
    const stats = await benchmark.benchmark(config.query, config.variables);

    if (config.json) {
      console.log(JSON.stringify(stats, null, 2));
    } else {
      console.log(formatHumanOutput(stats, config.query));
    }

    // Exit with error if there were failures
    if (stats.failedRequests > 0) {
      process.exit(1);
    }
  } catch (error) {
    console.error('Benchmark failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { GraphQLBenchmark, BenchmarkResult };
