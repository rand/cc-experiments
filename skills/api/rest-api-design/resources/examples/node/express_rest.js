/**
 * Complete REST API Example with Express.js
 *
 * Demonstrates:
 * - Resource-based URLs
 * - Proper HTTP methods
 * - Status codes
 * - Pagination
 * - Filtering and sorting
 * - Error handling
 * - Authentication
 * - Caching
 * - Rate limiting
 * - Validation
 */

const express = require('express');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const { body, param, query, validationResult } = require('express-validator');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(helmet());

// Request ID middleware
app.use((req, res, next) => {
  req.id = `req-${Date.now()}`;
  res.setHeader('X-Request-ID', req.id);
  next();
});

// Rate limiting
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    res.status(429).json({
      error: 'rate_limit_exceeded',
      message: 'Rate limit exceeded. Try again later.',
      retry_after: 60
    });
  }
});

app.use('/api', limiter);

// In-memory database (replace with real database)
let users = [
  {
    id: 1,
    name: 'John Doe',
    email: 'john@example.com',
    role: 'admin',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_active: true
  },
  {
    id: 2,
    name: 'Jane Smith',
    email: 'jane@example.com',
    role: 'user',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_active: true
  }
];

// Authentication middleware
const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'unauthorized',
      message: 'Authentication required',
      request_id: req.id
    });
  }

  const token = authHeader.substring(7);

  // In production, verify JWT token
  if (token !== 'valid-token') {
    return res.status(401).json({
      error: 'unauthorized',
      message: 'Invalid authentication token',
      request_id: req.id
    });
  }

  req.user = { id: 1, role: 'admin' };
  next();
};

// Validation middleware
const validate = (req, res, next) => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    return res.status(422).json({
      error: 'validation_error',
      message: 'Request validation failed',
      details: errors.array().map(err => ({
        field: err.path,
        message: err.msg,
        value: err.value
      })),
      request_id: req.id
    });
  }

  next();
};

// Error handler
app.use((err, req, res, next) => {
  console.error(err.stack);

  res.status(err.status || 500).json({
    error: err.error || 'internal_error',
    message: err.message || 'An unexpected error occurred',
    request_id: req.id
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

// List users
app.get('/api/users', [
  authenticate,
  query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
  query('offset').optional().isInt({ min: 0 }).withMessage('Offset must be non-negative'),
  query('status').optional().isIn(['active', 'inactive']).withMessage('Status must be active or inactive'),
  query('role').optional().isString(),
  query('sort').optional().isString(),
  validate
], (req, res) => {
  const limit = parseInt(req.query.limit) || 20;
  const offset = parseInt(req.query.offset) || 0;
  const status = req.query.status;
  const role = req.query.role;
  const sort = req.query.sort;

  // Filter
  let filtered = users;

  if (status) {
    const isActive = status === 'active';
    filtered = filtered.filter(u => u.is_active === isActive);
  }

  if (role) {
    filtered = filtered.filter(u => u.role === role);
  }

  // Sort
  if (sort) {
    const reverse = sort.startsWith('-');
    const field = reverse ? sort.substring(1) : sort;

    filtered.sort((a, b) => {
      const aVal = a[field] || '';
      const bVal = b[field] || '';
      const comparison = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
      return reverse ? -comparison : comparison;
    });
  }

  // Paginate
  const total = filtered.length;
  const paginated = filtered.slice(offset, offset + limit);

  // Build links
  const baseUrl = `${req.protocol}://${req.get('host')}${req.path}`;
  let queryParams = `limit=${limit}`;
  if (status) queryParams += `&status=${status}`;
  if (role) queryParams += `&role=${role}`;
  if (sort) queryParams += `&sort=${sort}`;

  const links = {
    self: `${baseUrl}?${queryParams}&offset=${offset}`,
    first: `${baseUrl}?${queryParams}&offset=0`,
    last: `${baseUrl}?${queryParams}&offset=${Math.max(0, total - limit)}`
  };

  if (offset > 0) {
    links.prev = `${baseUrl}?${queryParams}&offset=${Math.max(0, offset - limit)}`;
  }

  if (offset + limit < total) {
    links.next = `${baseUrl}?${queryParams}&offset=${offset + limit}`;
  }

  // Response
  res.set({
    'Cache-Control': 'private, max-age=60'
  });

  res.json({
    data: paginated,
    pagination: {
      limit,
      offset,
      total,
      has_more: offset + limit < total
    },
    links
  });
});

// Get user
app.get('/api/users/:id', [
  authenticate,
  param('id').isInt().withMessage('User ID must be an integer'),
  validate
], (req, res) => {
  const userId = parseInt(req.params.id);
  const user = users.find(u => u.id === userId);

  if (!user) {
    return res.status(404).json({
      error: 'not_found',
      message: `User with id ${userId} not found`,
      request_id: req.id
    });
  }

  // Add ETag
  const etag = `"${new Date(user.updated_at).getTime()}"`;

  res.set({
    'ETag': etag,
    'Cache-Control': 'private, max-age=300'
  });

  res.json(user);
});

// Create user
app.post('/api/users', [
  authenticate,
  body('name').isLength({ min: 1, max: 100 }).withMessage('Name must be between 1 and 100 characters'),
  body('email').isEmail().withMessage('Invalid email format'),
  body('role').optional().isIn(['user', 'admin', 'editor']).withMessage('Invalid role'),
  body('password').isLength({ min: 8 }).withMessage('Password must be at least 8 characters'),
  validate
], (req, res) => {
  const { name, email, role = 'user' } = req.body;

  // Check if email exists
  if (users.find(u => u.email === email)) {
    return res.status(409).json({
      error: 'conflict',
      message: `User with email ${email} already exists`,
      request_id: req.id
    });
  }

  // Create user
  const newUser = {
    id: Math.max(...users.map(u => u.id)) + 1,
    name,
    email,
    role,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_active: true
  };

  users.push(newUser);

  res.status(201)
    .set('Location', `/api/users/${newUser.id}`)
    .json(newUser);
});

// Update user (full)
app.put('/api/users/:id', [
  authenticate,
  param('id').isInt().withMessage('User ID must be an integer'),
  body('name').isLength({ min: 1, max: 100 }).withMessage('Name must be between 1 and 100 characters'),
  body('email').isEmail().withMessage('Invalid email format'),
  body('role').optional().isIn(['user', 'admin', 'editor']).withMessage('Invalid role'),
  validate
], (req, res) => {
  const userId = parseInt(req.params.id);
  const user = users.find(u => u.id === userId);

  if (!user) {
    return res.status(404).json({
      error: 'not_found',
      message: `User with id ${userId} not found`,
      request_id: req.id
    });
  }

  // Update all fields
  user.name = req.body.name;
  user.email = req.body.email;
  user.role = req.body.role || user.role;
  user.updated_at = new Date().toISOString();

  res.json(user);
});

// Update user (partial)
app.patch('/api/users/:id', [
  authenticate,
  param('id').isInt().withMessage('User ID must be an integer'),
  body('name').optional().isLength({ min: 1, max: 100 }).withMessage('Name must be between 1 and 100 characters'),
  body('email').optional().isEmail().withMessage('Invalid email format'),
  body('role').optional().isIn(['user', 'admin', 'editor']).withMessage('Invalid role'),
  validate
], (req, res) => {
  const userId = parseInt(req.params.id);
  const user = users.find(u => u.id === userId);

  if (!user) {
    return res.status(404).json({
      error: 'not_found',
      message: `User with id ${userId} not found`,
      request_id: req.id
    });
  }

  // Update only provided fields
  if (req.body.name !== undefined) user.name = req.body.name;
  if (req.body.email !== undefined) user.email = req.body.email;
  if (req.body.role !== undefined) user.role = req.body.role;
  user.updated_at = new Date().toISOString();

  res.json(user);
});

// Delete user
app.delete('/api/users/:id', [
  authenticate,
  param('id').isInt().withMessage('User ID must be an integer'),
  validate
], (req, res) => {
  const userId = parseInt(req.params.id);
  const userIndex = users.findIndex(u => u.id === userId);

  if (userIndex === -1) {
    return res.status(404).json({
      error: 'not_found',
      message: `User with id ${userId} not found`,
      request_id: req.id
    });
  }

  users.splice(userIndex, 1);

  res.status(204).send();
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'not_found',
    message: 'Endpoint not found',
    request_id: req.id
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`API: http://localhost:${PORT}/api/users`);
});

module.exports = app;
