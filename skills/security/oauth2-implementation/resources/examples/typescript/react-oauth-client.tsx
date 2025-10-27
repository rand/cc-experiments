/**
 * React OAuth 2.0 Client with PKCE - Production Example
 *
 * Complete React implementation of OAuth 2.0 authorization code flow with PKCE
 * for Single-Page Applications. Includes hooks, context, protected routes,
 * and automatic token refresh.
 *
 * Dependencies:
 *   npm install react react-router-dom
 *
 * Environment Variables (.env):
 *   REACT_APP_AUTH_SERVER=https://auth.example.com
 *   REACT_APP_CLIENT_ID=spa-client-id
 *   REACT_APP_REDIRECT_URI=http://localhost:3000/callback
 *   REACT_APP_API_BASE_URL=https://api.example.com
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';

// Configuration
const AUTH_SERVER = process.env.REACT_APP_AUTH_SERVER || 'https://auth.example.com';
const CLIENT_ID = process.env.REACT_APP_CLIENT_ID || 'spa-client-id';
const REDIRECT_URI = process.env.REACT_APP_REDIRECT_URI || 'http://localhost:3000/callback';
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://api.example.com';

// Types
interface TokenData {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  scope?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  accessToken: string | null;
  login: () => void;
  logout: () => void;
  callApi: (url: string, options?: RequestInit) => Promise<Response>;
}

interface PKCEPair {
  codeVerifier: string;
  codeChallenge: string;
}

// PKCE Utilities
class PKCEGenerator {
  /**
   * Generate cryptographically secure random string
   */
  static generateRandomString(length: number): string {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  /**
   * Base64URL encode without padding
   */
  static base64URLEncode(buffer: Uint8Array): string {
    const base64 = btoa(String.fromCharCode.apply(null, Array.from(buffer)));
    return base64
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  /**
   * SHA-256 hash
   */
  static async sha256(plain: string): Promise<ArrayBuffer> {
    const encoder = new TextEncoder();
    const data = encoder.encode(plain);
    return await crypto.subtle.digest('SHA-256', data);
  }

  /**
   * Generate PKCE code_verifier and code_challenge pair
   */
  static async generatePKCE(): Promise<PKCEPair> {
    // Generate code_verifier (43-128 chars)
    const codeVerifier = this.generateRandomString(32); // 256 bits

    // Generate code_challenge (S256)
    const hashed = await this.sha256(codeVerifier);
    const codeChallenge = this.base64URLEncode(new Uint8Array(hashed));

    return {
      codeVerifier,
      codeChallenge
    };
  }
}

// OAuth Client
class OAuth2Client {
  private authServer: string;
  private clientId: string;
  private redirectUri: string;

  constructor(authServer: string, clientId: string, redirectUri: string) {
    this.authServer = authServer;
    this.clientId = clientId;
    this.redirectUri = redirectUri;
  }

  /**
   * Initiate OAuth authorization code flow with PKCE
   */
  async startAuthFlow(): Promise<void> {
    // Generate PKCE pair
    const pkce = await PKCEGenerator.generatePKCE();

    // Store code_verifier in session storage (cleared on tab close)
    sessionStorage.setItem('pkce_code_verifier', pkce.codeVerifier);

    // Generate state for CSRF protection
    const state = PKCEGenerator.generateRandomString(16);
    sessionStorage.setItem('oauth_state', state);

    // Build authorization URL
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      scope: 'openid profile email',
      state: state,
      code_challenge: pkce.codeChallenge,
      code_challenge_method: 'S256'
    });

    // Redirect to authorization server
    window.location.href = `${this.authServer}/authorize?${params.toString()}`;
  }

  /**
   * Handle OAuth callback and exchange code for tokens
   */
  async handleCallback(): Promise<TokenData> {
    const urlParams = new URLSearchParams(window.location.search);

    // Validate state
    const receivedState = urlParams.get('state');
    const storedState = sessionStorage.getItem('oauth_state');

    if (!receivedState || receivedState !== storedState) {
      throw new Error('Invalid state parameter');
    }

    sessionStorage.removeItem('oauth_state');

    // Check for errors
    const error = urlParams.get('error');
    if (error) {
      const errorDescription = urlParams.get('error_description') || error;
      throw new Error(`Authorization failed: ${errorDescription}`);
    }

    // Get authorization code
    const code = urlParams.get('code');
    if (!code) {
      throw new Error('Missing authorization code');
    }

    // Retrieve code_verifier
    const codeVerifier = sessionStorage.getItem('pkce_code_verifier');
    if (!codeVerifier) {
      throw new Error('Missing code_verifier');
    }

    sessionStorage.removeItem('pkce_code_verifier');

    // Exchange code for tokens
    const tokenResponse = await fetch(`${this.authServer}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: this.redirectUri,
        client_id: this.clientId,
        code_verifier: codeVerifier
      })
    });

    if (!tokenResponse.ok) {
      const error = await tokenResponse.json();
      throw new Error(`Token exchange failed: ${error.error_description || error.error}`);
    }

    const tokens: TokenData = await tokenResponse.json();
    return tokens;
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<TokenData> {
    const response = await fetch(`${this.authServer}/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: this.clientId
      })
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    return await response.json();
  }

  /**
   * Revoke token
   */
  async revokeToken(token: string, tokenTypeHint: string = 'access_token'): Promise<void> {
    await fetch(`${this.authServer}/revoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        token: token,
        token_type_hint: tokenTypeHint,
        client_id: this.clientId
      })
    });
  }
}

// Auth Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// Auth Provider
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [tokenExpiresAt, setTokenExpiresAt] = useState<number>(0);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  const oauthClient = new OAuth2Client(AUTH_SERVER, CLIENT_ID, REDIRECT_URI);

  // Store tokens
  const storeTokens = (tokens: TokenData) => {
    setAccessToken(tokens.access_token);
    setTokenExpiresAt(Date.now() + tokens.expires_in * 1000);
    setIsAuthenticated(true);

    if (tokens.refresh_token) {
      setRefreshToken(tokens.refresh_token);
    }

    // Store in sessionStorage for persistence across page reloads
    sessionStorage.setItem('access_token', tokens.access_token);
    sessionStorage.setItem('token_expires_at', String(Date.now() + tokens.expires_in * 1000));
    if (tokens.refresh_token) {
      sessionStorage.setItem('refresh_token', tokens.refresh_token);
    }
  };

  // Clear tokens
  const clearTokens = () => {
    setAccessToken(null);
    setRefreshToken(null);
    setTokenExpiresAt(0);
    setIsAuthenticated(false);
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('token_expires_at');
  };

  // Check if token is expired
  const isTokenExpired = (): boolean => {
    return Date.now() >= tokenExpiresAt - 60000; // 60s buffer
  };

  // Refresh token if needed
  const refreshAccessToken = async (): Promise<string | null> => {
    if (!refreshToken) {
      return null;
    }

    try {
      const tokens = await oauthClient.refreshToken(refreshToken);
      storeTokens(tokens);
      return tokens.access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      clearTokens();
      return null;
    }
  };

  // Get valid access token
  const getValidAccessToken = async (): Promise<string | null> => {
    if (!accessToken) {
      return null;
    }

    if (isTokenExpired()) {
      return await refreshAccessToken();
    }

    return accessToken;
  };

  // Login
  const login = () => {
    oauthClient.startAuthFlow();
  };

  // Logout
  const logout = async () => {
    // Revoke tokens
    if (refreshToken) {
      await oauthClient.revokeToken(refreshToken, 'refresh_token');
    }
    if (accessToken) {
      await oauthClient.revokeToken(accessToken, 'access_token');
    }

    clearTokens();
  };

  // API call with automatic token refresh
  const callApi = async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = await getValidAccessToken();

    if (!token) {
      throw new Error('Not authenticated');
    }

    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${token}`);

    const response = await fetch(url, {
      ...options,
      headers
    });

    // If 401, try refreshing token once
    if (response.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        headers.set('Authorization', `Bearer ${newToken}`);
        return await fetch(url, {
          ...options,
          headers
        });
      }
    }

    return response;
  };

  // Restore session on mount
  useEffect(() => {
    const storedToken = sessionStorage.getItem('access_token');
    const storedExpiresAt = sessionStorage.getItem('token_expires_at');
    const storedRefreshToken = sessionStorage.getItem('refresh_token');

    if (storedToken && storedExpiresAt) {
      setAccessToken(storedToken);
      setTokenExpiresAt(Number(storedExpiresAt));
      setIsAuthenticated(true);

      if (storedRefreshToken) {
        setRefreshToken(storedRefreshToken);
      }
    }
  }, []);

  const value: AuthContextType = {
    isAuthenticated,
    accessToken,
    login,
    logout,
    callApi
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// OAuth Callback Component
export const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        const oauthClient = new OAuth2Client(AUTH_SERVER, CLIENT_ID, REDIRECT_URI);
        const tokens = await oauthClient.handleCallback();

        // Store tokens in session storage
        sessionStorage.setItem('access_token', tokens.access_token);
        sessionStorage.setItem('token_expires_at', String(Date.now() + tokens.expires_in * 1000));
        if (tokens.refresh_token) {
          sessionStorage.setItem('refresh_token', tokens.refresh_token);
        }

        // Redirect to home (will be picked up by AuthProvider)
        navigate('/');
      } catch (error) {
        setError((error as Error).message);
      }
    };

    handleCallback();
  }, [navigate]);

  if (error) {
    return (
      <div>
        <h1>Authentication Error</h1>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>Go Home</button>
      </div>
    );
  }

  return <div>Processing authentication...</div>;
};

// Protected Route Component
export const ProtectedRoute: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Example Components
const HomePage: React.FC = () => {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div>
      <h1>Home Page</h1>
      {isAuthenticated ? (
        <>
          <p>You are logged in!</p>
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <p>You are not logged in.</p>
      )}
    </div>
  );
};

const LoginPage: React.FC = () => {
  const { login } = useAuth();

  return (
    <div>
      <h1>Login</h1>
      <button onClick={login}>Login with OAuth</button>
    </div>
  );
};

const ProfilePage: React.FC = () => {
  const { callApi } = useAuth();
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await callApi(`${API_BASE_URL}/userinfo`);
        const data = await response.json();
        setProfile(data);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };

    fetchProfile();
  }, [callApi]);

  return (
    <div>
      <h1>Profile</h1>
      {profile ? (
        <pre>{JSON.stringify(profile, null, 2)}</pre>
      ) : (
        <p>Loading profile...</p>
      )}
    </div>
  );
};

// Main App
export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/callback" element={<OAuthCallback />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
