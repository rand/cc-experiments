/**
 * Type-Safe REST API Client
 *
 * Demonstrates:
 * - Type-safe API client
 * - Error handling
 * - Request/response interceptors
 * - Retry logic
 * - Caching
 */

// Types
export interface User {
  id: number;
  name: string;
  email: string;
  role: 'user' | 'admin' | 'editor';
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface UserCreate {
  name: string;
  email: string;
  role?: 'user' | 'admin' | 'editor';
  password: string;
}

export interface UserUpdate {
  name?: string;
  email?: string;
  role?: 'user' | 'admin' | 'editor';
}

export interface Pagination {
  limit: number;
  offset: number;
  total: number;
  has_more: boolean;
}

export interface PaginationLinks {
  self: string;
  first: string;
  prev?: string;
  next?: string;
  last: string;
}

export interface UserListResponse {
  data: User[];
  pagination: Pagination;
  links: PaginationLinks;
}

export interface APIError {
  error: string;
  message: string;
  details?: Array<{
    field: string;
    message: string;
  }>;
  request_id?: string;
}

export interface ListUsersParams {
  limit?: number;
  offset?: number;
  status?: 'active' | 'inactive';
  role?: 'user' | 'admin' | 'editor';
  sort?: string;
}

// Configuration
export interface APIClientConfig {
  baseURL: string;
  apiKey?: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
  cache?: boolean;
}

// Request options
export interface RequestOptions {
  method: string;
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, any>;
  cache?: boolean;
}

// Cache entry
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  etag?: string;
}

/**
 * API Client
 */
export class APIClient {
  private baseURL: string;
  private apiKey?: string;
  private timeout: number;
  private retryAttempts: number;
  private retryDelay: number;
  private cacheEnabled: boolean;
  private cache: Map<string, CacheEntry<any>>;

  constructor(config: APIClientConfig) {
    this.baseURL = config.baseURL.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
    this.retryAttempts = config.retryAttempts || 3;
    this.retryDelay = config.retryDelay || 1000;
    this.cacheEnabled = config.cache !== false;
    this.cache = new Map();
  }

  /**
   * Make HTTP request
   */
  private async request<T>(
    path: string,
    options: RequestOptions
  ): Promise<T> {
    const url = this.buildURL(path, options.params);
    const cacheKey = `${options.method}:${url}`;

    // Check cache for GET requests
    if (options.method === 'GET' && this.cacheEnabled && options.cache !== false) {
      const cached = this.getFromCache<T>(cacheKey);
      if (cached) {
        return cached;
      }
    }

    // Build request
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers
    };

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const requestInit: RequestInit = {
      method: options.method,
      headers,
      signal: AbortSignal.timeout(this.timeout)
    };

    if (options.body) {
      requestInit.body = JSON.stringify(options.body);
    }

    // Make request with retries
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, requestInit);

        // Handle non-OK responses
        if (!response.ok) {
          const errorData = await response.json() as APIError;
          throw new APIClientError(
            errorData.message || 'Request failed',
            response.status,
            errorData
          );
        }

        // Handle 204 No Content
        if (response.status === 204) {
          return null as T;
        }

        // Parse response
        const data = await response.json() as T;

        // Cache successful GET requests
        if (options.method === 'GET' && this.cacheEnabled) {
          const etag = response.headers.get('ETag');
          this.saveToCache(cacheKey, data, etag || undefined);
        }

        return data;

      } catch (error) {
        lastError = error as Error;

        // Don't retry on client errors (4xx)
        if (error instanceof APIClientError && error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === this.retryAttempts - 1) {
          break;
        }

        // Wait before retrying
        await this.sleep(this.retryDelay * (attempt + 1));
      }
    }

    throw lastError || new Error('Request failed');
  }

  /**
   * Build URL with query parameters
   */
  private buildURL(path: string, params?: Record<string, any>): string {
    const url = new URL(path, this.baseURL);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  /**
   * Get from cache
   */
  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // Check if cache is expired (5 minutes)
    const now = Date.now();
    const maxAge = 5 * 60 * 1000;

    if (now - entry.timestamp > maxAge) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  /**
   * Save to cache
   */
  private saveToCache<T>(key: string, data: T, etag?: string): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      etag
    });
  }

  /**
   * Sleep for specified milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * List users
   */
  async listUsers(params?: ListUsersParams): Promise<UserListResponse> {
    return this.request<UserListResponse>('/api/users', {
      method: 'GET',
      params
    });
  }

  /**
   * Get user by ID
   */
  async getUser(userId: number): Promise<User> {
    return this.request<User>(`/api/users/${userId}`, {
      method: 'GET'
    });
  }

  /**
   * Create user
   */
  async createUser(user: UserCreate): Promise<User> {
    return this.request<User>('/api/users', {
      method: 'POST',
      body: user
    });
  }

  /**
   * Update user (full)
   */
  async updateUser(userId: number, user: UserUpdate): Promise<User> {
    return this.request<User>(`/api/users/${userId}`, {
      method: 'PUT',
      body: user
    });
  }

  /**
   * Update user (partial)
   */
  async patchUser(userId: number, updates: UserUpdate): Promise<User> {
    return this.request<User>(`/api/users/${userId}`, {
      method: 'PATCH',
      body: updates
    });
  }

  /**
   * Delete user
   */
  async deleteUser(userId: number): Promise<void> {
    return this.request<void>(`/api/users/${userId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }
}

/**
 * API Client Error
 */
export class APIClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: APIError
  ) {
    super(message);
    this.name = 'APIClientError';
  }
}

/**
 * Example usage
 */
async function example() {
  // Create client
  const client = new APIClient({
    baseURL: 'https://api.example.com',
    apiKey: 'your-api-key',
    timeout: 30000,
    retryAttempts: 3,
    cache: true
  });

  try {
    // List users
    const users = await client.listUsers({
      limit: 20,
      offset: 0,
      status: 'active',
      sort: '-created_at'
    });

    console.log('Users:', users.data);
    console.log('Total:', users.pagination.total);

    // Get single user
    const user = await client.getUser(123);
    console.log('User:', user);

    // Create user
    const newUser = await client.createUser({
      name: 'John Doe',
      email: 'john@example.com',
      password: 'secretpassword'
    });

    console.log('Created:', newUser);

    // Update user
    const updated = await client.patchUser(newUser.id, {
      email: 'john.new@example.com'
    });

    console.log('Updated:', updated);

    // Delete user
    await client.deleteUser(newUser.id);
    console.log('Deleted');

  } catch (error) {
    if (error instanceof APIClientError) {
      console.error('API Error:', error.message);
      console.error('Status:', error.status);
      console.error('Details:', error.data);
    } else {
      console.error('Error:', error);
    }
  }
}

// Export for use
export default APIClient;
