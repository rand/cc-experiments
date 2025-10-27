/**
 * Next.js Security Headers Configuration
 *
 * Production-ready security headers for Next.js applications.
 * Supports both next.config.js and middleware approaches.
 */

// ============================================================================
// Approach 1: next.config.js (Static Headers)
// ============================================================================

/**
 * Security headers configuration for next.config.js
 *
 * Usage in next.config.js:
 * ```javascript
 * const { securityHeaders } = require('./lib/security-headers');
 *
 * module.exports = {
 *   async headers() {
 *     return [
 *       {
 *         source: '/:path*',
 *         headers: securityHeaders(),
 *       },
 *     ];
 *   },
 * };
 * ```
 */
export function securityHeaders(
  options: SecurityHeadersOptions = {}
): Array<{ key: string; value: string }> {
  const {
    hsts = true,
    hstsMaxAge = 31536000,
    hstsIncludeSubDomains = true,
    hstsPreload = true,
    csp = defaultCSP(),
    xFrameOptions = 'DENY',
    referrerPolicy = 'strict-origin-when-cross-origin',
    permissionsPolicy = defaultPermissionsPolicy(),
  } = options;

  const headers: Array<{ key: string; value: string }> = [];

  // Strict-Transport-Security (HSTS)
  if (hsts) {
    let hstsValue = `max-age=${hstsMaxAge}`;
    if (hstsIncludeSubDomains) hstsValue += '; includeSubDomains';
    if (hstsPreload) hstsValue += '; preload';
    headers.push({ key: 'Strict-Transport-Security', value: hstsValue });
  }

  // Content-Security-Policy (CSP)
  if (csp) {
    headers.push({ key: 'Content-Security-Policy', value: csp });
  }

  // X-Frame-Options
  if (xFrameOptions) {
    headers.push({ key: 'X-Frame-Options', value: xFrameOptions });
  }

  // X-Content-Type-Options
  headers.push({ key: 'X-Content-Type-Options', value: 'nosniff' });

  // X-XSS-Protection (disable)
  headers.push({ key: 'X-XSS-Protection', value: '0' });

  // Referrer-Policy
  if (referrerPolicy) {
    headers.push({ key: 'Referrer-Policy', value: referrerPolicy });
  }

  // Permissions-Policy
  if (permissionsPolicy) {
    headers.push({ key: 'Permissions-Policy', value: permissionsPolicy });
  }

  return headers;
}

/**
 * Default CSP for Next.js applications
 */
function defaultCSP(): string {
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join('; ');
}

/**
 * Strict CSP (production-ready, requires proper setup)
 */
export function strictCSP(): string {
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data: https:",
    "font-src 'self'",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join('; ');
}

/**
 * CSP for API routes (strict)
 */
export function apiCSP(): string {
  return "default-src 'none'; frame-ancestors 'none'";
}

/**
 * Default Permissions-Policy
 */
function defaultPermissionsPolicy(): string {
  return [
    'geolocation=()',
    'camera=()',
    'microphone=()',
    'payment=()',
    'usb=()',
    'magnetometer=()',
    'gyroscope=()',
    'accelerometer=()',
  ].join(', ');
}

// ============================================================================
// Approach 2: Middleware (Dynamic Headers with Nonces)
// ============================================================================

/**
 * Next.js middleware for security headers with CSP nonces
 *
 * Create file: middleware.ts
 *
 * ```typescript
 * import { securityHeadersMiddleware } from './lib/security-headers';
 *
 * export const middleware = securityHeadersMiddleware();
 * ```
 */

import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';

export function securityHeadersMiddleware(
  options: MiddlewareOptions = {}
) {
  return async function middleware(request: NextRequest) {
    const response = NextResponse.next();

    // Generate nonce for CSP
    const nonce = nanoid();

    // Add nonce to request headers (accessible in components)
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set('x-nonce', nonce);

    const {
      hsts = true,
      cspWithNonce = true,
      xFrameOptions = 'DENY',
      referrerPolicy = 'strict-origin-when-cross-origin',
    } = options;

    // HSTS
    if (hsts) {
      response.headers.set(
        'Strict-Transport-Security',
        'max-age=31536000; includeSubDomains; preload'
      );
    }

    // CSP with nonce
    if (cspWithNonce) {
      const csp = [
        "default-src 'self'",
        `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
        `style-src 'self' 'nonce-${nonce}'`,
        "img-src 'self' data: https: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
      ].join('; ');

      response.headers.set('Content-Security-Policy', csp);
    }

    // X-Frame-Options
    response.headers.set('X-Frame-Options', xFrameOptions);

    // X-Content-Type-Options
    response.headers.set('X-Content-Type-Options', 'nosniff');

    // X-XSS-Protection
    response.headers.set('X-XSS-Protection', '0');

    // Referrer-Policy
    response.headers.set('Referrer-Policy', referrerPolicy);

    // Permissions-Policy
    response.headers.set(
      'Permissions-Policy',
      'geolocation=(), camera=(), microphone=()'
    );

    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
      headers: response.headers,
    });
  };
}

// ============================================================================
// Helper: Access Nonce in Components
// ============================================================================

/**
 * Get CSP nonce from headers (Server Components)
 *
 * Usage in Server Component:
 * ```tsx
 * import { headers } from 'next/headers';
 * import { getNonce } from '@/lib/security-headers';
 *
 * export default function Page() {
 *   const nonce = getNonce();
 *
 *   return (
 *     <>
 *       <script nonce={nonce}>console.log('Hello');</script>
 *       <style nonce={nonce}>{`body { margin: 0; }`}</style>
 *     </>
 *   );
 * }
 * ```
 */
export function getNonce(): string | undefined {
  if (typeof window !== 'undefined') {
    // Client-side: Not available
    return undefined;
  }

  try {
    // Server-side: Get from headers
    const { headers } = require('next/headers');
    const headersList = headers();
    return headersList.get('x-nonce') || undefined;
  } catch {
    return undefined;
  }
}

// ============================================================================
// Helper: CSP Report Endpoint
// ============================================================================

/**
 * CSP violation report handler
 *
 * Create file: app/api/csp-report/route.ts
 *
 * ```typescript
 * import { handleCSPReport } from '@/lib/security-headers';
 *
 * export const POST = handleCSPReport;
 * ```
 */
export async function handleCSPReport(request: Request): Promise<Response> {
  try {
    const report = await request.json();

    // Log CSP violation
    console.warn('CSP Violation:', {
      documentUri: report['csp-report']?.['document-uri'],
      violatedDirective: report['csp-report']?.['violated-directive'],
      blockedUri: report['csp-report']?.['blocked-uri'],
      lineNumber: report['csp-report']?.['line-number'],
      columnNumber: report['csp-report']?.['column-number'],
      sourceFile: report['csp-report']?.['source-file'],
    });

    // Store in database, send to monitoring service, etc.
    // await db.cspViolations.create({ data: report });
    // await sendToMonitoring(report);

    return new Response(null, { status: 204 });
  } catch (error) {
    console.error('Error processing CSP report:', error);
    return new Response(null, { status: 500 });
  }
}

// ============================================================================
// Type Definitions
// ============================================================================

interface SecurityHeadersOptions {
  hsts?: boolean;
  hstsMaxAge?: number;
  hstsIncludeSubDomains?: boolean;
  hstsPreload?: boolean;
  csp?: string;
  xFrameOptions?: string;
  referrerPolicy?: string;
  permissionsPolicy?: string;
}

interface MiddlewareOptions {
  hsts?: boolean;
  cspWithNonce?: boolean;
  xFrameOptions?: string;
  referrerPolicy?: string;
}

// ============================================================================
// Example: Complete next.config.js
// ============================================================================

/**
 * Example next.config.js with security headers
 */
export const exampleNextConfig = {
  async headers() {
    return [
      {
        // Apply to all routes
        source: '/:path*',
        headers: securityHeaders({
          csp: [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https: blob:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
          ].join('; '),
        }),
      },
      {
        // Strict CSP for API routes
        source: '/api/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: apiCSP(),
          },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/csp-report',
        destination: '/api/csp-report',
      },
    ];
  },
};

// ============================================================================
// Example: Complete middleware.ts
// ============================================================================

/**
 * Example middleware.ts with security headers
 *
 * File: middleware.ts
 */
export const exampleMiddleware = `
import { NextRequest, NextResponse } from 'next/server';
import { nanoid } from 'nanoid';

export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  const nonce = nanoid();

  // Add nonce to request headers
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);

  // Security headers
  response.headers.set(
    'Strict-Transport-Security',
    'max-age=31536000; includeSubDomains; preload'
  );

  response.headers.set(
    'Content-Security-Policy',
    [
      "default-src 'self'",
      \`script-src 'self' 'nonce-\${nonce}' 'strict-dynamic'\`,
      \`style-src 'self' 'nonce-\${nonce}'\`,
      "img-src 'self' data: https: blob:",
      "font-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "object-src 'none'",
    ].join('; ')
  );

  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-XSS-Protection', '0');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'geolocation=(), camera=(), microphone=()');

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
    headers: response.headers,
  });
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
`;

// ============================================================================
// Example: Using Nonce in Components
// ============================================================================

/**
 * Example: Server Component with CSP nonce
 */
export const exampleServerComponent = `
import { headers } from 'next/headers';

export default function Page() {
  const nonce = headers().get('x-nonce');

  return (
    <html>
      <head>
        <style nonce={nonce}>
          {\`
            body {
              margin: 0;
              padding: 0;
              font-family: Arial, sans-serif;
            }
          \`}
        </style>
      </head>
      <body>
        <h1>Hello, World!</h1>
        <script nonce={nonce}>
          console.log('Script with nonce');
        </script>
      </body>
    </html>
  );
}
`;

/**
 * Example: Script component with nonce
 */
export const exampleScriptComponent = `
import Script from 'next/script';
import { headers } from 'next/headers';

export default function Page() {
  const nonce = headers().get('x-nonce');

  return (
    <>
      <h1>Page with External Script</h1>
      <Script
        src="https://example.com/script.js"
        nonce={nonce}
        strategy="afterInteractive"
      />
    </>
  );
}
`;
