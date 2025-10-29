#!/usr/bin/env node
/**
 * Express + Sentry Integration Example
 *
 * Production-ready Express application with comprehensive Sentry error tracking.
 *
 * Features:
 * - Automatic exception capture
 * - User context tracking
 * - Performance monitoring
 * - Custom error fingerprinting
 * - PII scrubbing
 * - Request context enrichment
 *
 * Usage:
 *   export SENTRY_DSN="https://..."
 *   export NODE_ENV=production
 *   node express-sentry.js
 */

const Sentry = require("@sentry/node");
const { ProfilingIntegration } = require("@sentry/profiling-node");
const express = require("express");

const app = express();
const PORT = process.env.PORT || 3000;

// Initialize Sentry BEFORE any other middleware
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV || "development",
  release: process.env.RELEASE || "1.0.0",

  // Performance monitoring
  tracesSampleRate: getTracesSampleRate(),
  profilesSampleRate: 0.1,

  integrations: [
    new Sentry.Integrations.Http({ tracing: true }),
    new Sentry.Integrations.Express({ app }),
    new ProfilingIntegration(),
  ],

  // Privacy
  beforeSend(event) {
    // Remove sensitive data
    if (event.request) {
      // Remove query parameters with tokens
      if (event.request.url) {
        event.request.url = event.request.url.replace(
          /([?&])(token|api_key|password|secret)=[^&]*/g,
          '$1$2=[Filtered]'
        );
      }

      // Remove sensitive headers
      if (event.request.headers) {
        delete event.request.headers['authorization'];
        delete event.request.headers['cookie'];
        delete event.request.headers['x-api-key'];
      }

      // Remove request body
      delete event.request.data;
    }

    // Sample common errors more aggressively
    if (event.exception) {
      const errorMessage = event.exception.values[0].value;
      if (errorMessage && (errorMessage.includes('ECONNREFUSED') || errorMessage.includes('ETIMEDOUT'))) {
        // Keep only 10% of connection errors
        if (Math.random() > 0.1) {
          return null;
        }
      }
    }

    return event;
  },

  beforeBreadcrumb(breadcrumb) {
    // Filter console breadcrumbs
    if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
      return null;
    }

    // Scrub sensitive data from HTTP breadcrumbs
    if (breadcrumb.category === 'http') {
      if (breadcrumb.data && breadcrumb.data.url) {
        breadcrumb.data.url = breadcrumb.data.url.replace(
          /([?&])(token|api_key|password)=[^&]*/g,
          '$1$2=[Filtered]'
        );
      }
    }

    return breadcrumb;
  },

  ignoreErrors: [
    // Browser extensions
    'top.GLOBALS',
    'Can\'t find variable: ZiteReader',

    // Network errors (handle separately)
    'NetworkError',
    'Network request failed',
  ],
});

function getTracesSampleRate() {
  const env = process.env.NODE_ENV;
  if (env === 'production') return 0.05;   // 5%
  if (env === 'staging') return 0.5;       // 50%
  return 1.0;                              // 100% for dev
}

// Request handler MUST be first middleware
app.use(Sentry.Handlers.requestHandler());
app.use(Sentry.Handlers.tracingHandler());

// Body parser
app.use(express.json());

// Custom middleware to add context
app.use((req, res, next) => {
  // Set user context
  const userId = req.headers['x-user-id'];
  if (userId) {
    Sentry.setUser({
      id: userId,
      ip_address: req.ip,
    });
  }

  // Set tags
  Sentry.setTag("request_id", req.headers['x-request-id'] || 'unknown');
  Sentry.setTag("endpoint", req.path);

  // Set context
  Sentry.setContext("request_info", {
    url: req.url,
    method: req.method,
    path: req.path,
    query: req.query,
    headers: {
      'user-agent': req.headers['user-agent'],
      'referer': req.headers['referer'],
    },
  });

  // Add breadcrumb
  Sentry.addBreadcrumb({
    category: 'request',
    message: `${req.method} ${req.path}`,
    level: 'info',
  });

  next();
});

// Routes

app.get('/', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'express-api',
    environment: process.env.NODE_ENV,
  });
});

app.get('/api/users/:userId', (req, res) => {
  const { userId } = req.params;

  // Set user context
  Sentry.setUser({ id: userId });

  // Add breadcrumb
  Sentry.addBreadcrumb({
    category: 'database',
    message: `Looking up user ${userId}`,
    level: 'info',
  });

  // Simulate error for testing
  if (userId === '999') {
    throw new Error(`User not found: ${userId}`);
  }

  res.json({
    id: userId,
    name: `User ${userId}`,
    email: `user${userId}@example.com`,
  });
});

app.post('/api/orders', (req, res) => {
  const { items, total } = req.body;

  // Add order context
  Sentry.setContext("order", {
    items_count: items ? items.length : 0,
    total: total || 0,
  });

  // Breadcrumb for order creation
  Sentry.addBreadcrumb({
    category: 'business',
    message: 'Creating order',
    level: 'info',
    data: { items_count: items ? items.length : 0, total },
  });

  // Validate order
  if (!total || total <= 0) {
    throw new Error('Order total must be positive');
  }

  // Simulate external API call
  Sentry.addBreadcrumb({
    category: 'http',
    message: 'Calling payment API',
    level: 'info',
  });

  res.status(201).json({
    order_id: 'ORD-12345',
    status: 'created',
  });
});

app.get('/api/test-error', (req, res) => {
  // Test error with full context
  Sentry.setTag("test", "true");

  throw new Error('Test error from Express API');
});

app.get('/api/test-performance', async (req, res) => {
  // Test performance monitoring
  const transaction = Sentry.startTransaction({
    op: "http.server",
    name: "GET /api/test-performance",
  });

  const span1 = transaction.startChild({
    op: "business_logic",
    description: "process_data",
  });
  await new Promise(resolve => setTimeout(resolve, 100));
  span1.finish();

  const span2 = transaction.startChild({
    op: "database",
    description: "query_users",
  });
  await new Promise(resolve => setTimeout(resolve, 50));
  span2.finish();

  const span3 = transaction.startChild({
    op: "external",
    description: "call_api",
  });
  await new Promise(resolve => setTimeout(resolve, 150));
  span3.finish();

  transaction.finish();

  res.json({ status: 'completed' });
});

// Error handler MUST be last middleware
app.use(Sentry.Handlers.errorHandler({
  shouldHandleError(error) {
    // Capture all errors
    return true;
  },
}));

// Custom error handler
app.use((err, req, res, next) => {
  // Add error-specific context
  Sentry.withScope((scope) => {
    scope.setContext("error_info", {
      type: err.constructor.name,
      message: err.message,
      endpoint: req.path,
    });

    // Custom fingerprinting
    if (err.message.includes('ECONNREFUSED')) {
      scope.setFingerprint(['connection-error', req.path]);
    } else if (err.message.includes('ETIMEDOUT')) {
      scope.setFingerprint(['timeout-error', req.path]);
    }

    Sentry.captureException(err);
  });

  res.status(500).json({
    error: 'Internal server error',
    message: 'An unexpected error occurred',
  });
});

// Start server
if (!process.env.SENTRY_DSN) {
  console.error('ERROR: SENTRY_DSN environment variable not set');
  process.exit(1);
}

app.listen(PORT, () => {
  console.log(`Express API with Sentry error tracking`);
  console.log(`Environment: ${process.env.NODE_ENV}`);
  console.log(`Release: ${process.env.RELEASE || '1.0.0'}`);
  console.log(`Server listening on port ${PORT}`);
});
