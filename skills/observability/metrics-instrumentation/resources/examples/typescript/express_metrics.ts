/**
 * Express Application with Prometheus Metrics
 *
 * Demonstrates comprehensive Prometheus instrumentation for an Express/Node.js
 * application including middleware, custom metrics, and best practices.
 *
 * Usage:
 *   npm install
 *   npm start
 *
 * Metrics available at: http://localhost:8080/metrics
 */

import express, { Request, Response, NextFunction } from 'express';
import client from 'prom-client';

const app = express();
app.use(express.json());

// ============================================================================
// Registry Setup
// ============================================================================

const register = new client.Registry();

// Add default metrics (CPU, memory, etc.)
client.collectDefaultMetrics({ register });

// ============================================================================
// HTTP Request Metrics
// ============================================================================

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'endpoint', 'status'],
  registers: [register]
});

const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request latency in seconds',
  labelNames: ['method', 'endpoint'],
  buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
  registers: [register]
});

const httpRequestsInProgress = new client.Gauge({
  name: 'http_requests_in_progress',
  help: 'Number of HTTP requests in progress',
  labelNames: ['method', 'endpoint'],
  registers: [register]
});

const httpRequestSize = new client.Summary({
  name: 'http_request_size_bytes',
  help: 'HTTP request size in bytes',
  labelNames: ['method', 'endpoint'],
  registers: [register]
});

const httpResponseSize = new client.Summary({
  name: 'http_response_size_bytes',
  help: 'HTTP response size in bytes',
  labelNames: ['method', 'endpoint'],
  registers: [register]
});

// ============================================================================
// Application Info
// ============================================================================

const appInfo = new client.Gauge({
  name: 'app_info',
  help: 'Application information',
  labelNames: ['version', 'node_version'],
  registers: [register]
});

appInfo.set({ version: '1.0.0', node_version: process.version }, 1);

// ============================================================================
// Business Metrics
// ============================================================================

const userLoginTotal = new client.Counter({
  name: 'user_login_total',
  help: 'Total user logins',
  labelNames: ['status'],
  registers: [register]
});

const userSessionsActive = new client.Gauge({
  name: 'user_sessions_active',
  help: 'Number of active user sessions',
  registers: [register]
});

const orderValueDollars = new client.Histogram({
  name: 'order_value_dollars',
  help: 'Order value in dollars',
  buckets: [1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000],
  registers: [register]
});

const ordersTotal = new client.Counter({
  name: 'orders_total',
  help: 'Total orders processed',
  labelNames: ['product_category', 'payment_method'],
  registers: [register]
});

const databaseQueriesTotal = new client.Counter({
  name: 'database_queries_total',
  help: 'Total database queries',
  labelNames: ['operation', 'table'],
  registers: [register]
});

const databaseQueryDuration = new client.Histogram({
  name: 'database_query_duration_seconds',
  help: 'Database query duration',
  labelNames: ['operation', 'table'],
  buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
  registers: [register]
});

const cacheOperationsTotal = new client.Counter({
  name: 'cache_operations_total',
  help: 'Total cache operations',
  labelNames: ['operation', 'result'],
  registers: [register]
});

// ============================================================================
// Middleware
// ============================================================================

interface RequestWithMetrics extends Request {
  startTime?: number;
}

const metricsMiddleware = (req: RequestWithMetrics, res: Response, next: NextFunction) => {
  const start = Date.now();
  req.startTime = start;

  // Normalize endpoint (use route pattern if available)
  const endpoint = (req.route?.path || req.path) as string;

  // Increment in-progress gauge
  httpRequestsInProgress.inc({ method: req.method, endpoint });

  // Track request size
  const requestSize = parseInt(req.headers['content-length'] || '0', 10);
  httpRequestSize.observe({ method: req.method, endpoint }, requestSize);

  // Hook into response finish
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    // Decrement in-progress gauge
    httpRequestsInProgress.dec({ method: req.method, endpoint });

    // Record metrics
    httpRequestsTotal.inc({
      method: req.method,
      endpoint,
      status: res.statusCode.toString()
    });

    httpRequestDuration.observe({ method: req.method, endpoint }, duration);

    // Track response size (estimate)
    const responseSize = parseInt(res.getHeader('content-length')?.toString() || '0', 10);
    httpResponseSize.observe({ method: req.method, endpoint }, responseSize);
  });

  next();
};

app.use(metricsMiddleware);

// ============================================================================
// Database Query Tracker
// ============================================================================

async function trackDBQuery<T>(
  operation: string,
  table: string,
  fn: () => Promise<T>
): Promise<T> {
  const start = Date.now();

  try {
    const result = await fn();
    return result;
  } finally {
    const duration = (Date.now() - start) / 1000;

    databaseQueriesTotal.inc({ operation, table });
    databaseQueryDuration.observe({ operation, table }, duration);
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randomChoice<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ============================================================================
// Route Handlers
// ============================================================================

app.get('/', (req: Request, res: Response) => {
  res.json({
    name: 'Express Metrics Demo',
    version: '1.0.0',
    metrics_url: '/metrics'
  });
});

app.get('/api/users', async (req: Request, res: Response) => {
  // Check cache (simulated)
  const cacheHit = Math.random() > 0.3;
  const cacheResult = cacheHit ? 'hit' : 'miss';

  cacheOperationsTotal.inc({ operation: 'get', result: cacheResult });

  let users;

  if (!cacheHit) {
    // Simulate database query
    users = await trackDBQuery('select', 'users', async () => {
      await sleep(Math.random() * 50);
      return [
        { id: 1, name: 'Alice' },
        { id: 2, name: 'Bob' }
      ];
    });

    // Cache result
    cacheOperationsTotal.inc({ operation: 'set', result: 'success' });
  } else {
    users = [
      { id: 1, name: 'Alice' },
      { id: 2, name: 'Bob' }
    ];
  }

  res.json({ users });
});

app.post('/api/login', (req: Request, res: Response) => {
  // Simulate login logic (90% success rate)
  const success = Math.random() > 0.1;

  const status = success ? 'success' : 'failure';
  userLoginTotal.inc({ status });

  if (success) {
    userSessionsActive.inc();
    res.json({ status: 'success', token: 'fake-token' });
  } else {
    res.status(401).json({ status: 'failure', error: 'Invalid credentials' });
  }
});

app.post('/api/logout', (req: Request, res: Response) => {
  userSessionsActive.dec();
  res.json({ status: 'success' });
});

app.post('/api/orders', async (req: Request, res: Response) => {
  // Simulate order data
  const orderValue = Math.random() * 490 + 10;
  const productCategory = randomChoice(['electronics', 'books', 'clothing']);
  const paymentMethod = randomChoice(['credit_card', 'paypal', 'bank_transfer']);

  // Track business metrics
  orderValueDollars.observe(orderValue);
  ordersTotal.inc({ product_category: productCategory, payment_method: paymentMethod });

  // Simulate database insert
  await trackDBQuery('insert', 'orders', async () => {
    await sleep(Math.random() * 60 + 20);
  });

  res.status(201).json({
    order_id: Math.floor(Math.random() * 9000) + 1000,
    value: orderValue,
    category: productCategory,
    payment_method: paymentMethod
  });
});

app.get('/api/slow', async (req: Request, res: Response) => {
  // Intentionally slow
  await sleep(Math.random() * 2000 + 1000);
  res.json({ status: 'slow response' });
});

app.get('/api/error', (req: Request, res: Response) => {
  // Randomly fail
  if (Math.random() > 0.5) {
    res.status(500).json({ error: 'Simulated error' });
  } else {
    res.json({ status: 'ok' });
  }
});

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'healthy' });
});

// ============================================================================
// Metrics Endpoint
// ============================================================================

app.get('/metrics', async (req: Request, res: Response) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// ============================================================================
// Error Handler
// ============================================================================

app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});

// ============================================================================
// Start Server
// ============================================================================

const PORT = process.env.PORT || 8080;

app.listen(PORT, () => {
  console.log('Starting Express application with Prometheus metrics...');
  console.log(`Metrics endpoint: http://localhost:${PORT}/metrics`);
  console.log('API endpoints:');
  console.log('  - GET  /api/users');
  console.log('  - POST /api/login');
  console.log('  - POST /api/logout');
  console.log('  - POST /api/orders');
  console.log('  - GET  /api/slow');
  console.log('  - GET  /api/error');
  console.log('  - GET  /health');
});
