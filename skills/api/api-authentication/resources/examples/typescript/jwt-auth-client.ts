/**
 * JWT Authentication Client for React/TypeScript
 *
 * Secure JWT token management with automatic refresh,
 * memory-based storage (XSS safe), and TypeScript types.
 *
 * Usage:
 *   pnpm add axios
 *   import { AuthClient } from './jwt-auth-client';
 */

import axios, { AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

interface User {
  id: number;
  username: string;
  email: string;
}

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData extends LoginCredentials {
  email: string;
}

export class AuthClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private tokenExpiry: number | null = null;
  private refreshPromise: Promise<string> | null = null;
  private api: AxiosInstance;

  constructor(baseURL: string) {
    this.api = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: add auth token and refresh if needed
    this.api.interceptors.request.use(
      async (config) => {
        // Get valid token (refreshes if needed)
        const token = await this.getValidToken();

        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: handle 401 errors
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // If 401 and we haven't retried yet
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Try to refresh token
            await this.refresh();

            // Retry original request with new token
            const token = this.accessToken;
            if (token && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }

            return this.api(originalRequest);
          } catch (refreshError) {
            // Refresh failed, logout user
            this.logout();
            throw refreshError;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<User> {
    const response = await this.api.post<TokenResponse>('/register', data);
    this.setTokens(response.data);

    const user = await this.getCurrentUser();
    return user;
  }

  /**
   * Login with username and password
   */
  async login(credentials: LoginCredentials): Promise<User> {
    const response = await this.api.post<TokenResponse>('/login', credentials);
    this.setTokens(response.data);

    const user = await this.getCurrentUser();
    return user;
  }

  /**
   * Logout and revoke tokens
   */
  async logout(): Promise<void> {
    try {
      if (this.refreshToken) {
        await this.api.post('/logout', {
          refresh_token: this.refreshToken,
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearTokens();
    }
  }

  /**
   * Refresh access token
   */
  async refresh(): Promise<string> {
    // Prevent multiple simultaneous refresh requests
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        if (!this.refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await axios.post<TokenResponse>(
          `${this.api.defaults.baseURL}/refresh`,
          { refresh_token: this.refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        );

        this.setTokens(response.data);
        return this.accessToken!;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<User> {
    const response = await this.api.get<User>('/me');
    return response.data;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.accessToken !== null && !this.isTokenExpired();
  }

  /**
   * Get valid access token (refreshes if needed)
   */
  private async getValidToken(): Promise<string | null> {
    if (!this.accessToken) {
      return null;
    }

    // Refresh 5 minutes before expiry
    const refreshThreshold = 5 * 60 * 1000; // 5 minutes in ms

    if (this.tokenExpiry && Date.now() > this.tokenExpiry - refreshThreshold) {
      try {
        await this.refresh();
      } catch (error) {
        console.error('Token refresh failed:', error);
        this.clearTokens();
        return null;
      }
    }

    return this.accessToken;
  }

  /**
   * Check if token is expired
   */
  private isTokenExpired(): boolean {
    if (!this.tokenExpiry) {
      return false;
    }

    return Date.now() > this.tokenExpiry;
  }

  /**
   * Store tokens in memory
   */
  private setTokens(tokenResponse: TokenResponse): void {
    this.accessToken = tokenResponse.access_token;
    this.refreshToken = tokenResponse.refresh_token;
    this.tokenExpiry = Date.now() + tokenResponse.expires_in * 1000;
  }

  /**
   * Clear tokens from memory
   */
  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpiry = null;
    this.refreshPromise = null;
  }

  /**
   * Make authenticated API request
   */
  async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.api.request<T>(config);
    return response.data;
  }

  /**
   * GET request
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.request<T>({ ...config, method: 'GET', url });
  }

  /**
   * POST request
   */
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.request<T>({ ...config, method: 'POST', url, data });
  }

  /**
   * PUT request
   */
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.request<T>({ ...config, method: 'PUT', url, data });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.request<T>({ ...config, method: 'DELETE', url });
  }
}

/**
 * React Hook for Authentication
 */
export function createAuthHook(authClient: AuthClient) {
  return function useAuth() {
    const [user, setUser] = React.useState<User | null>(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
      // Check authentication status on mount
      const checkAuth = async () => {
        try {
          if (authClient.isAuthenticated()) {
            const currentUser = await authClient.getCurrentUser();
            setUser(currentUser);
          }
        } catch (err) {
          console.error('Auth check failed:', err);
        } finally {
          setLoading(false);
        }
      };

      checkAuth();
    }, []);

    const login = async (credentials: LoginCredentials) => {
      setLoading(true);
      setError(null);

      try {
        const loggedInUser = await authClient.login(credentials);
        setUser(loggedInUser);
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || 'Login failed';
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    const register = async (data: RegisterData) => {
      setLoading(true);
      setError(null);

      try {
        const newUser = await authClient.register(data);
        setUser(newUser);
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || 'Registration failed';
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    const logout = async () => {
      setLoading(true);

      try {
        await authClient.logout();
        setUser(null);
      } catch (err) {
        console.error('Logout error:', err);
      } finally {
        setLoading(false);
      }
    };

    return {
      user,
      loading,
      error,
      login,
      register,
      logout,
      isAuthenticated: authClient.isAuthenticated(),
    };
  };
}

/**
 * Example Usage
 */
/*
// Create auth client
const authClient = new AuthClient('https://api.example.com');

// Create React hook
const useAuth = createAuthHook(authClient);

// Use in component
function App() {
  const { user, loading, error, login, logout, isAuthenticated } = useAuth();

  const handleLogin = async () => {
    try {
      await login({
        username: 'user@example.com',
        password: 'password123',
      });
    } catch (err) {
      console.error('Login failed:', err);
    }
  };

  if (loading) return <div>Loading...</div>;

  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} error={error} />;
  }

  return (
    <div>
      <h1>Welcome, {user?.username}</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

// Make authenticated API requests
const data = await authClient.get('/api/protected-resource');
const result = await authClient.post('/api/create', { name: 'Test' });
*/
