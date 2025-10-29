/**
 * Structured Logging Example - Node.js with Winston
 *
 * Demonstrates best practices for structured JSON logging in Node.js applications.
 *
 * Install:
 *   npm install winston
 *
 * Run:
 *   node nodejs-winston.js
 */

const winston = require('winston');

/**
 * Configure Winston for structured JSON logging
 */
function configureLogging(serviceName, version, environment) {
  const logger = winston.createLogger({
    level: environment === 'production' ? 'info' : 'debug',

    format: winston.format.combine(
      winston.format.timestamp({
        format: 'YYYY-MM-DDTHH:mm:ss.SSSZ'
      }),
      winston.format.errors({ stack: true }),
      winston.format.json()
    ),

    defaultMeta: {
      service: serviceName,
      version: version,
      environment: environment
    },

    transports: [
      // Console output
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          winston.format.simple()
        )
      }),

      // File output - all logs
      new winston.transports.File({
        filename: 'logs/combined.log',
        maxsize: 5242880, // 5MB
        maxFiles: 5
      }),

      // File output - errors only
      new winston.transports.File({
        filename: 'logs/error.log',
        level: 'error',
        maxsize: 5242880,
        maxFiles: 5
      })
    ]
  });

  return logger;
}

/**
 * Add distributed tracing context
 */
function addTraceContext(logger, traceId, spanId) {
  return logger.child({
    trace_id: traceId,
    span_id: spanId
  });
}

/**
 * Log HTTP request
 */
function logHttpRequest(logger, req, res, duration) {
  const logLevel = res.statusCode >= 400 ? 'error' : 'info';

  logger.log(logLevel, 'HTTP request', {
    method: req.method,
    path: req.path,
    status_code: res.statusCode,
    duration_ms: duration,
    user_id: req.user?.id,
    ip: req.ip,
    user_agent: req.get('user-agent'),
    request_id: req.id
  });
}

/**
 * Log database query information
 * NOTE: This only LOGS query info - it does not execute any database operations
 * @param {Object} logger - Winston logger instance
 * @param {string} query - SQL query string (already executed, for logging only)
 * @param {number} duration - Query duration in milliseconds
 * @param {number} rowsAffected - Number of rows affected
 */
function logDatabaseQuery(logger, query, duration, rowsAffected) {
  // Truncate query string for logging (does not execute query)
  const querySnippet = query.substring(0, 100);
  logger.info('Database query', {
    query: querySnippet,
    duration_ms: duration,
    rows_affected: rowsAffected,
    slow_query: duration > 1000
  });
}

/**
 * Log error with full context
 */
function logError(logger, error, context = {}) {
  logger.error('Error occurred', {
    error_type: error.name,
    error_message: error.message,
    error_stack: error.stack,
    context: context
  });
}

/**
 * Express middleware for request logging
 */
function requestLoggingMiddleware(logger) {
  return (req, res, next) => {
    const startTime = Date.now();

    // Add request ID
    req.id = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    // Log when response is finished
    res.on('finish', () => {
      const duration = Date.now() - startTime;
      logHttpRequest(logger, req, res, duration);
    });

    next();
  };
}

/**
 * Express middleware for error logging
 */
function errorLoggingMiddleware(logger) {
  return (err, req, res, next) => {
    logError(logger, err, {
      method: req.method,
      path: req.path,
      user_id: req.user?.id,
      request_id: req.id
    });

    next(err);
  };
}

/**
 * Example application
 */
function exampleApplication() {
  // Initialize logging
  const logger = configureLogging(
    'api-gateway',
    '1.2.3',
    'production'
  );

  // Add tracing context
  const tracedLogger = addTraceContext(
    logger,
    'abc123def456',
    'span789'
  );

  // Application startup
  tracedLogger.info('Application started', {
    port: 8080,
    workers: 4,
    node_version: process.version
  });

  // Simulate HTTP request
  const mockReq = {
    method: 'GET',
    path: '/api/users/123',
    ip: '192.168.1.1',
    get: (header) => 'Mozilla/5.0...',
    id: 'req_12345',
    user: { id: 'user_456' }
  };

  const mockRes = {
    statusCode: 200,
    on: (event, handler) => {
      if (event === 'finish') {
        setTimeout(() => handler(), 10);
      }
    }
  };

  logHttpRequest(tracedLogger, mockReq, mockRes, 45.3);

  // Log database query
  logDatabaseQuery(
    tracedLogger,
    'SELECT * FROM users WHERE id = $1',
    12.5,
    1
  );

  // Log slow query warning
  logDatabaseQuery(
    tracedLogger,
    'SELECT * FROM orders JOIN order_items ON orders.id = order_items.order_id',
    1250.0,
    5000
  );

  // Log business event
  tracedLogger.info('User action', {
    action: 'login',
    user_id: 'user_456',
    ip: '192.168.1.1',
    success: true
  });

  // Log error with context
  try {
    throw new Error('Database connection timeout');
  } catch (error) {
    logError(tracedLogger, error, {
      operation: 'connect_to_database',
      database: 'postgres',
      host: 'db.example.com'
    });
  }

  // Log with additional context
  const orderLogger = tracedLogger.child({
    order_id: 'order_789',
    customer_id: 'customer_123'
  });

  orderLogger.info('Order created', {
    total_amount: 99.99,
    items_count: 3,
    shipping_address: {
      city: 'San Francisco',
      state: 'CA',
      country: 'US'
    }
  });

  orderLogger.info('Payment processed', {
    payment_method: 'credit_card',
    transaction_id: 'txn_abc',
    amount: 99.99
  });

  // Log warning
  tracedLogger.warn('High memory usage', {
    memory_used_mb: 1800,
    memory_limit_mb: 2048,
    percentage: 88
  });

  // Log debug (only in non-production)
  tracedLogger.debug('Cache hit', {
    key: 'user:123',
    ttl_seconds: 300
  });

  // Application shutdown
  logger.info('Application stopped', {
    uptime_seconds: 3600,
    reason: 'SIGTERM'
  });
}

// Run example
if (require.main === module) {
  exampleApplication();
}

module.exports = {
  configureLogging,
  addTraceContext,
  logHttpRequest,
  logDatabaseQuery,
  logError,
  requestLoggingMiddleware,
  errorLoggingMiddleware
};
