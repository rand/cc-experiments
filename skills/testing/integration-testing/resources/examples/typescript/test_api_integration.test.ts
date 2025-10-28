/**
 * Integration tests for API endpoints using Vitest/Jest.
 *
 * Demonstrates testing Express/Fastify APIs with real dependencies.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import request from 'supertest';
import { Pool } from 'pg';
import express, { Express, Request, Response, NextFunction } from 'express';

// Example Express application
interface User {
  id: number;
  name: string;
  email: string;
  created_at: Date;
}

interface CreateUserDTO {
  name: string;
  email: string;
}

class UserRepository {
  constructor(private pool: Pool) {}

  async create(name: string, email: string): Promise<User> {
    const result = await this.pool.query(
      'INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *',
      [name, email]
    );
    return result.rows[0];
  }

  async findById(id: number): Promise<User | null> {
    const result = await this.pool.query(
      'SELECT * FROM users WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async findByEmail(email: string): Promise<User | null> {
    const result = await this.pool.query(
      'SELECT * FROM users WHERE email = $1',
      [email]
    );
    return result.rows[0] || null;
  }

  async list(skip: number = 0, limit: number = 100): Promise<User[]> {
    const result = await this.pool.query(
      'SELECT * FROM users ORDER BY id OFFSET $1 LIMIT $2',
      [skip, limit]
    );
    return result.rows;
  }

  async update(id: number, name: string, email: string): Promise<User | null> {
    const result = await this.pool.query(
      'UPDATE users SET name = $1, email = $2 WHERE id = $3 RETURNING *',
      [name, email, id]
    );
    return result.rows[0] || null;
  }

  async delete(id: number): Promise<boolean> {
    const result = await this.pool.query(
      'DELETE FROM users WHERE id = $1',
      [id]
    );
    return result.rowCount > 0;
  }
}

function createApp(pool: Pool): Express {
  const app = express();
  app.use(express.json());

  const userRepo = new UserRepository(pool);

  // Error handler
  const asyncHandler = (fn: Function) => {
    return (req: Request, res: Response, next: NextFunction) => {
      Promise.resolve(fn(req, res, next)).catch(next);
    };
  };

  // Routes
  app.post('/users', asyncHandler(async (req: Request, res: Response) => {
    const { name, email }: CreateUserDTO = req.body;

    if (!name || !email) {
      return res.status(400).json({ error: 'Name and email are required' });
    }

    // Check for duplicate email
    const existing = await userRepo.findByEmail(email);
    if (existing) {
      return res.status(409).json({ error: 'Email already exists' });
    }

    const user = await userRepo.create(name, email);
    res.status(201).json(user);
  }));

  app.get('/users/:id', asyncHandler(async (req: Request, res: Response) => {
    const id = parseInt(req.params.id);
    const user = await userRepo.findById(id);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user);
  }));

  app.get('/users', asyncHandler(async (req: Request, res: Response) => {
    const skip = parseInt(req.query.skip as string) || 0;
    const limit = parseInt(req.query.limit as string) || 100;

    const users = await userRepo.list(skip, limit);
    res.json(users);
  }));

  app.patch('/users/:id', asyncHandler(async (req: Request, res: Response) => {
    const id = parseInt(req.params.id);
    const { name, email }: CreateUserDTO = req.body;

    const user = await userRepo.update(id, name, email);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user);
  }));

  app.delete('/users/:id', asyncHandler(async (req: Request, res: Response) => {
    const id = parseInt(req.params.id);
    const deleted = await userRepo.delete(id);

    if (!deleted) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.status(204).send();
  }));

  // Error handler
  app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    console.error(err);
    res.status(500).json({ error: 'Internal server error' });
  });

  return app;
}

// Test setup
let pool: Pool;
let app: Express;

beforeAll(async () => {
  // Connect to test database
  pool = new Pool({
    host: process.env.TEST_DB_HOST || 'localhost',
    port: parseInt(process.env.TEST_DB_PORT || '5432'),
    database: process.env.TEST_DB_NAME || 'testdb',
    user: process.env.TEST_DB_USER || 'test',
    password: process.env.TEST_DB_PASSWORD || 'test',
  });

  // Create tables
  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      email VARCHAR(255) UNIQUE NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  app = createApp(pool);
});

afterAll(async () => {
  // Clean up test database after all tests complete
  await pool.query('DROP TABLE IF EXISTS users');
  await pool.end();
});

beforeEach(async () => {
  // Clean test database before each test - safe cleanup in test environment
  await pool.query('TRUNCATE TABLE users RESTART IDENTITY CASCADE');
});

// Integration Tests
describe('User API Integration Tests', () => {
  describe('POST /users', () => {
    it('should create a new user', async () => {
      const response = await request(app)
        .post('/users')
        .send({
          name: 'Alice Smith',
          email: 'alice@example.com'
        })
        .expect(201);

      expect(response.body).toMatchObject({
        name: 'Alice Smith',
        email: 'alice@example.com'
      });
      expect(response.body.id).toBeDefined();
      expect(response.body.created_at).toBeDefined();
    });

    it('should return 400 for missing name', async () => {
      const response = await request(app)
        .post('/users')
        .send({ email: 'test@example.com' })
        .expect(400);

      expect(response.body.error).toContain('required');
    });

    it('should return 400 for missing email', async () => {
      const response = await request(app)
        .post('/users')
        .send({ name: 'Test User' })
        .expect(400);

      expect(response.body.error).toContain('required');
    });

    it('should return 409 for duplicate email', async () => {
      // Create first user
      await request(app)
        .post('/users')
        .send({
          name: 'Alice',
          email: 'alice@example.com'
        })
        .expect(201);

      // Try to create duplicate
      const response = await request(app)
        .post('/users')
        .send({
          name: 'Alice Duplicate',
          email: 'alice@example.com'
        })
        .expect(409);

      expect(response.body.error).toContain('already exists');
    });
  });

  describe('GET /users/:id', () => {
    it('should return user by id', async () => {
      // Create user
      const createResponse = await request(app)
        .post('/users')
        .send({
          name: 'Bob Johnson',
          email: 'bob@example.com'
        });

      const userId = createResponse.body.id;

      // Get user
      const response = await request(app)
        .get(`/users/${userId}`)
        .expect(200);

      expect(response.body).toMatchObject({
        id: userId,
        name: 'Bob Johnson',
        email: 'bob@example.com'
      });
    });

    it('should return 404 for non-existent user', async () => {
      const response = await request(app)
        .get('/users/99999')
        .expect(404);

      expect(response.body.error).toContain('not found');
    });
  });

  describe('GET /users', () => {
    it('should list all users', async () => {
      // Create multiple users
      await request(app).post('/users').send({ name: 'User 1', email: 'user1@example.com' });
      await request(app).post('/users').send({ name: 'User 2', email: 'user2@example.com' });
      await request(app).post('/users').send({ name: 'User 3', email: 'user3@example.com' });

      const response = await request(app)
        .get('/users')
        .expect(200);

      expect(response.body).toHaveLength(3);
      expect(response.body[0]).toHaveProperty('id');
      expect(response.body[0]).toHaveProperty('name');
      expect(response.body[0]).toHaveProperty('email');
    });

    it('should support pagination with skip and limit', async () => {
      // Create 5 users
      for (let i = 1; i <= 5; i++) {
        await request(app).post('/users').send({
          name: `User ${i}`,
          email: `user${i}@example.com`
        });
      }

      // Get first page
      const page1 = await request(app)
        .get('/users?skip=0&limit=2')
        .expect(200);

      expect(page1.body).toHaveLength(2);

      // Get second page
      const page2 = await request(app)
        .get('/users?skip=2&limit=2')
        .expect(200);

      expect(page2.body).toHaveLength(2);

      // Verify different users
      expect(page1.body[0].id).not.toBe(page2.body[0].id);
    });

    it('should return empty array when no users exist', async () => {
      const response = await request(app)
        .get('/users')
        .expect(200);

      expect(response.body).toEqual([]);
    });
  });

  describe('PATCH /users/:id', () => {
    it('should update user', async () => {
      // Create user
      const createResponse = await request(app)
        .post('/users')
        .send({
          name: 'Charlie Brown',
          email: 'charlie@example.com'
        });

      const userId = createResponse.body.id;

      // Update user
      const response = await request(app)
        .patch(`/users/${userId}`)
        .send({
          name: 'Charles Brown',
          email: 'charles@example.com'
        })
        .expect(200);

      expect(response.body).toMatchObject({
        id: userId,
        name: 'Charles Brown',
        email: 'charles@example.com'
      });

      // Verify update persisted
      const getResponse = await request(app).get(`/users/${userId}`);
      expect(getResponse.body.name).toBe('Charles Brown');
    });

    it('should return 404 for non-existent user', async () => {
      const response = await request(app)
        .patch('/users/99999')
        .send({
          name: 'Nobody',
          email: 'nobody@example.com'
        })
        .expect(404);

      expect(response.body.error).toContain('not found');
    });
  });

  describe('DELETE /users/:id', () => {
    it('should delete user', async () => {
      // Create user
      const createResponse = await request(app)
        .post('/users')
        .send({
          name: 'Diana Prince',
          email: 'diana@example.com'
        });

      const userId = createResponse.body.id;

      // Delete user
      await request(app)
        .delete(`/users/${userId}`)
        .expect(204);

      // Verify deletion
      await request(app)
        .get(`/users/${userId}`)
        .expect(404);
    });

    it('should return 404 for non-existent user', async () => {
      await request(app)
        .delete('/users/99999')
        .expect(404);
    });
  });

  describe('Complete User Lifecycle', () => {
    it('should handle full CRUD lifecycle', async () => {
      // Create
      const createResponse = await request(app)
        .post('/users')
        .send({
          name: 'Eva Green',
          email: 'eva@example.com'
        })
        .expect(201);

      const userId = createResponse.body.id;

      // Read
      const getResponse = await request(app)
        .get(`/users/${userId}`)
        .expect(200);

      expect(getResponse.body.email).toBe('eva@example.com');

      // Update
      const updateResponse = await request(app)
        .patch(`/users/${userId}`)
        .send({
          name: 'Eva Green Updated',
          email: 'eva.updated@example.com'
        })
        .expect(200);

      expect(updateResponse.body.name).toBe('Eva Green Updated');

      // Delete
      await request(app)
        .delete(`/users/${userId}`)
        .expect(204);

      // Verify deleted
      await request(app)
        .get(`/users/${userId}`)
        .expect(404);
    });
  });
});

describe('API Performance Tests', () => {
  it('should create user within acceptable time', async () => {
    const start = Date.now();

    await request(app)
      .post('/users')
      .send({
        name: 'Fast User',
        email: 'fast@example.com'
      })
      .expect(201);

    const duration = Date.now() - start;

    expect(duration).toBeLessThan(1000); // Should complete in under 1 second
  });

  it('should list users within acceptable time', async () => {
    // Create some users
    for (let i = 0; i < 10; i++) {
      await request(app).post('/users').send({
        name: `User ${i}`,
        email: `user${i}@perf.com`
      });
    }

    const start = Date.now();

    await request(app)
      .get('/users')
      .expect(200);

    const duration = Date.now() - start;

    expect(duration).toBeLessThan(500); // Should complete in under 500ms
  });
});

// Run tests with: vitest run
// Run with coverage: vitest run --coverage
// Run in watch mode: vitest
