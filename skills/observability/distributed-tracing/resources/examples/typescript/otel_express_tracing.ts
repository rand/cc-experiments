/**
 * OpenTelemetry Express.js Distributed Tracing Example
 *
 * Complete example showing auto-instrumentation and manual spans in Express
 * with trace context propagation to downstream services.
 *
 * Requirements:
 *   npm install express
 *   npm install @opentelemetry/api @opentelemetry/sdk-node
 *   npm install @opentelemetry/auto-instrumentations-node
 *   npm install @opentelemetry/exporter-trace-otlp-grpc
 *
 * Usage:
 *   ts-node otel_express_tracing.ts
 *
 *   # With custom OTLP endpoint
 *   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 ts-node otel_express_tracing.ts
 */

import express, { Request, Response, NextFunction } from 'express';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { trace, context, SpanStatusCode, SpanKind } from '@opentelemetry/api';

// Configuration
const SERVICE_NAME = process.env.SERVICE_NAME || 'order-api';
const OTLP_ENDPOINT = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317';
const PORT = parseInt(process.env.PORT || '8002', 10);

// Initialize OpenTelemetry SDK
const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: SERVICE_NAME,
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
    [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: 'development',
  }),
  traceExporter: new OTLPTraceExporter({
    url: OTLP_ENDPOINT,
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      // Customize auto-instrumentation
      '@opentelemetry/instrumentation-http': {
        requestHook: (span, request) => {
          // Add custom attributes to HTTP spans
          span.setAttribute('http.user_agent', request.headers['user-agent'] || 'unknown');
        },
      },
      '@opentelemetry/instrumentation-express': {
        requestHook: (span, info) => {
          // Add Express-specific attributes
          span.setAttribute('express.route', info.route || 'unknown');
        },
      },
    }),
  ],
});

// Start SDK
sdk.start();

// Handle shutdown gracefully
process.on('SIGTERM', () => {
  sdk.shutdown()
    .then(() => console.log('Tracing terminated'))
    .catch((error) => console.error('Error terminating tracing', error))
    .finally(() => process.exit(0));
});

// Get tracer
const tracer = trace.getTracer(SERVICE_NAME, '1.0.0');

// Create Express app
const app = express();
app.use(express.json());

// In-memory order database (mock)
interface Order {
  id: string;
  userId: string;
  items: Array<{ productId: string; quantity: number; price: number }>;
  total: number;
  status: string;
  createdAt: string;
}

const ORDERS_DB: Map<string, Order> = new Map([
  [
    'order-1',
    {
      id: 'order-1',
      userId: '123',
      items: [
        { productId: 'prod-1', quantity: 2, price: 29.99 },
        { productId: 'prod-2', quantity: 1, price: 49.99 },
      ],
      total: 109.97,
      status: 'completed',
      createdAt: '2025-01-15T10:00:00Z',
    },
  ],
]);

// Middleware: Add custom trace context
app.use((req: Request, res: Response, next: NextFunction) => {
  const activeSpan = trace.getActiveSpan();

  if (activeSpan) {
    // Add request metadata to span
    activeSpan.setAttribute('http.request_id', req.headers['x-request-id'] || 'unknown');
    activeSpan.setAttribute('http.client_ip', req.ip || 'unknown');

    // Add user context if available
    const userId = req.headers['x-user-id'] as string;
    if (userId) {
      activeSpan.setAttribute('user.id', userId);
    }
  }

  next();
});

// Health check endpoint
app.get('/', (req: Request, res: Response) => {
  res.json({ service: SERVICE_NAME, status: 'healthy' });
});

// Get order by ID
app.get('/orders/:orderId', async (req: Request, res: Response) => {
  const { orderId } = req.params;

  // Get current span (created by Express instrumentation)
  const currentSpan = trace.getActiveSpan();
  if (currentSpan) {
    currentSpan.setAttribute('order.id', orderId);
  }

  // Create manual span for database lookup
  await tracer.startActiveSpan('db.get_order', async (span) => {
    span.setAttribute('db.system', 'in-memory');
    span.setAttribute('db.operation', 'SELECT');
    span.setAttribute('db.table', 'orders');
    span.setAttribute('order.id', orderId);

    try {
      // Simulate database query
      await sleep(50);

      const order = ORDERS_DB.get(orderId);

      if (!order) {
        span.addEvent('order.not_found', { order_id: orderId });
        span.setStatus({ code: SpanStatusCode.ERROR, message: 'Order not found' });
        res.status(404).json({ error: 'Order not found' });
        return;
      }

      span.addEvent('order.found', { order_id: orderId });
      span.setAttribute('order.status', order.status);
      span.setAttribute('order.total', order.total);
      span.setStatus({ code: SpanStatusCode.OK });

      res.json(order);
    } finally {
      span.end();
    }
  });
});

// Create new order
app.post('/orders', async (req: Request, res: Response) => {
  const { userId, items } = req.body;

  // Validate input
  await tracer.startActiveSpan('validate_order_input', async (span) => {
    span.setAttribute('user.id', userId);
    span.setAttribute('items.count', items?.length || 0);

    try {
      if (!userId || !items || items.length === 0) {
        span.addEvent('validation.failed', {
          reason: 'missing_required_fields',
        });
        span.setStatus({ code: SpanStatusCode.ERROR, message: 'Invalid input' });
        res.status(400).json({ error: 'userId and items are required' });
        return;
      }

      span.addEvent('validation.passed');
      span.setStatus({ code: SpanStatusCode.OK });
    } finally {
      span.end();
    }
  });

  if (res.headersSent) return;

  // Calculate total
  let total = 0;
  await tracer.startActiveSpan('calculate_order_total', async (span) => {
    span.setAttribute('items.count', items.length);

    try {
      for (const item of items) {
        total += item.price * item.quantity;
      }

      span.setAttribute('order.total', total);
      span.addEvent('total.calculated', { total });
      span.setStatus({ code: SpanStatusCode.OK });
    } finally {
      span.end();
    }
  });

  // Create order
  const orderId = `order-${Date.now()}`;
  let order: Order;

  await tracer.startActiveSpan('db.insert_order', async (span) => {
    span.setAttribute('db.system', 'in-memory');
    span.setAttribute('db.operation', 'INSERT');
    span.setAttribute('db.table', 'orders');
    span.setAttribute('order.id', orderId);

    try {
      // Simulate database insert
      await sleep(30);

      order = {
        id: orderId,
        userId,
        items,
        total,
        status: 'pending',
        createdAt: new Date().toISOString(),
      };

      ORDERS_DB.set(orderId, order);

      span.addEvent('order.created', { order_id: orderId });
      span.setStatus({ code: SpanStatusCode.OK });
    } finally {
      span.end();
    }
  });

  // Publish event (fire and forget)
  tracer.startActiveSpan(
    'publish_order_created_event',
    { kind: SpanKind.PRODUCER },
    async (span) => {
      span.setAttribute('messaging.system', 'kafka');
      span.setAttribute('messaging.destination', 'order.events');
      span.setAttribute('messaging.operation', 'send');
      span.setAttribute('order.id', orderId);

      try {
        // Simulate publishing to message queue
        await sleep(10);

        span.addEvent('event.published', {
          event_type: 'order.created',
          order_id: orderId,
        });
        span.setStatus({ code: SpanStatusCode.OK });
      } catch (error) {
        span.recordException(error as Error);
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: (error as Error).message,
        });
      } finally {
        span.end();
      }
    }
  );

  res.status(201).json(order!);
});

// Get orders for user
app.get('/users/:userId/orders', async (req: Request, res: Response) => {
  const { userId } = req.params;

  await tracer.startActiveSpan('db.get_user_orders', async (span) => {
    span.setAttribute('db.system', 'in-memory');
    span.setAttribute('db.operation', 'SELECT');
    span.setAttribute('user.id', userId);

    try {
      // Simulate database query
      await sleep(40);

      const userOrders = Array.from(ORDERS_DB.values()).filter(
        (order) => order.userId === userId
      );

      span.setAttribute('orders.count', userOrders.length);
      span.addEvent('orders.retrieved', { count: userOrders.length });
      span.setStatus({ code: SpanStatusCode.OK });

      res.json({ userId, orders: userOrders });
    } finally {
      span.end();
    }
  });
});

// Update order status
app.patch('/orders/:orderId/status', async (req: Request, res: Response) => {
  const { orderId } = req.params;
  const { status } = req.body;

  await tracer.startActiveSpan('update_order_status', async (span) => {
    span.setAttribute('order.id', orderId);
    span.setAttribute('order.new_status', status);

    try {
      const order = ORDERS_DB.get(orderId);

      if (!order) {
        span.addEvent('order.not_found');
        span.setStatus({ code: SpanStatusCode.ERROR, message: 'Order not found' });
        res.status(404).json({ error: 'Order not found' });
        return;
      }

      const oldStatus = order.status;
      order.status = status;

      span.addEvent('status.changed', {
        old_status: oldStatus,
        new_status: status,
      });

      span.setAttribute('order.old_status', oldStatus);
      span.setStatus({ code: SpanStatusCode.OK });

      res.json(order);
    } finally {
      span.end();
    }
  });
});

// Complex operation: Order fulfillment
app.post('/orders/:orderId/fulfill', async (req: Request, res: Response) => {
  const { orderId } = req.params;

  await tracer.startActiveSpan('fulfill_order', async (fulfillSpan) => {
    fulfillSpan.setAttribute('order.id', orderId);

    try {
      // Step 1: Validate order
      await tracer.startActiveSpan('validate_order', async (span) => {
        try {
          const order = ORDERS_DB.get(orderId);

          if (!order) {
            throw new Error('Order not found');
          }

          if (order.status !== 'pending') {
            throw new Error(`Cannot fulfill order in status: ${order.status}`);
          }

          span.setAttribute('order.valid', true);
          span.setStatus({ code: SpanStatusCode.OK });
        } finally {
          span.end();
        }
      });

      // Step 2: Check inventory
      await tracer.startActiveSpan('check_inventory', async (span) => {
        span.setAttribute('check.type', 'inventory');

        try {
          // Simulate inventory check
          await sleep(30);

          span.addEvent('inventory.checked', { available: true });
          span.setStatus({ code: SpanStatusCode.OK });
        } finally {
          span.end();
        }
      });

      // Step 3: Process payment
      await tracer.startActiveSpan('process_payment', async (span) => {
        span.setAttribute('payment.method', 'credit_card');

        try {
          // Simulate payment processing
          await sleep(100);

          span.addEvent('payment.authorized');
          span.addEvent('payment.captured');
          span.setStatus({ code: SpanStatusCode.OK });
        } finally {
          span.end();
        }
      });

      // Step 4: Update order status
      const order = ORDERS_DB.get(orderId)!;
      order.status = 'fulfilled';

      fulfillSpan.addEvent('order.fulfilled', { order_id: orderId });
      fulfillSpan.setStatus({ code: SpanStatusCode.OK });

      res.json({ success: true, order });
    } catch (error) {
      fulfillSpan.recordException(error as Error);
      fulfillSpan.setStatus({
        code: SpanStatusCode.ERROR,
        message: (error as Error).message,
      });

      res.status(400).json({ error: (error as Error).message });
    } finally {
      fulfillSpan.end();
    }
  });
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  const activeSpan = trace.getActiveSpan();

  if (activeSpan) {
    activeSpan.recordException(err);
    activeSpan.setStatus({
      code: SpanStatusCode.ERROR,
      message: err.message,
    });
  }

  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Helper: Sleep function
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Start server
app.listen(PORT, () => {
  console.log(`${SERVICE_NAME} listening on port ${PORT}`);
  console.log(`Traces will be sent to: ${OTLP_ENDPOINT}`);
  console.log('');
  console.log('Endpoints:');
  console.log('  GET  /');
  console.log('  GET  /orders/:orderId');
  console.log('  POST /orders');
  console.log('  GET  /users/:userId/orders');
  console.log('  PATCH /orders/:orderId/status');
  console.log('  POST /orders/:orderId/fulfill');
  console.log('');
});
