/**
 * Express Rate Limiter Middleware
 *
 * Production-ready rate limiting middleware for Express applications
 * using Redis for distributed rate limiting.
 *
 * Features:
 * - Fixed window rate limiting
 * - Redis-backed for distributed systems
 * - Configurable per-route limits
 * - Standard rate limit headers
 * - Graceful error handling
 *
 * Usage:
 *   const rateLimiter = createRateLimiter(redisClient);
 *   app.use('/api', rateLimiter({ limit: 100, window: 60 }));
 */

const redis = require('redis');

/**
 * Create rate limiter middleware factory
 * @param {redis.RedisClient} redisClient - Redis client instance
 * @returns {Function} Middleware factory function
 */
function createRateLimiter(redisClient) {
    // Promisify Redis operations
    const evalAsync = (script, numKeys, ...args) => {
        return new Promise((resolve, reject) => {
            redisClient.eval(script, numKeys, ...args, (err, result) => {
                if (err) reject(err);
                else resolve(result);
            });
        });
    };

    // Lua script for atomic fixed window rate limiting
    const FIXED_WINDOW_SCRIPT = `
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local window_id = math.floor(now / window)
        local redis_key = key .. ":" .. window_id

        local count = redis.call('INCR', redis_key)
        if count == 1 then
            redis.call('EXPIRE', redis_key, window * 2)
        end

        local allowed = count <= limit
        local remaining = math.max(0, limit - count)
        local reset = (window_id + 1) * window

        return {allowed and 1 or 0, remaining, reset}
    `;

    /**
     * Rate limiter middleware
     * @param {Object} options - Rate limit options
     * @param {number} options.limit - Maximum requests per window
     * @param {number} options.window - Time window in seconds
     * @param {Function} options.keyGenerator - Function to generate rate limit key
     * @param {Function} options.skip - Function to skip rate limiting
     * @param {Function} options.handler - Custom rate limit exceeded handler
     * @returns {Function} Express middleware
     */
    return function rateLimiter(options = {}) {
        const {
            limit = 100,
            window = 60,
            keyGenerator = (req) => getClientIdentifier(req),
            skip = () => false,
            handler = defaultRateLimitHandler
        } = options;

        return async (req, res, next) => {
            // Skip rate limiting if configured
            if (skip(req)) {
                return next();
            }

            const key = keyGenerator(req);
            const now = Math.floor(Date.now() / 1000);

            try {
                // Check rate limit atomically
                const result = await evalAsync(
                    FIXED_WINDOW_SCRIPT,
                    1,
                    `rate_limit:${key}`,
                    limit,
                    window,
                    now
                );

                const allowed = result[0] === 1;
                const remaining = result[1];
                const reset = result[2];

                // Add rate limit headers
                res.setHeader('X-RateLimit-Limit', limit.toString());
                res.setHeader('X-RateLimit-Remaining', remaining.toString());
                res.setHeader('X-RateLimit-Reset', reset.toString());

                if (!allowed) {
                    const retryAfter = reset - now;
                    res.setHeader('Retry-After', retryAfter.toString());
                    return handler(req, res, retryAfter);
                }

                next();

            } catch (error) {
                // Log error and fail open (allow request)
                console.error('Rate limiter error:', error);
                next();
            }
        };
    };
}

/**
 * Get client identifier for rate limiting
 * @param {express.Request} req - Express request object
 * @returns {string} Client identifier
 */
function getClientIdentifier(req) {
    // Try API key from header
    const apiKey = req.headers['x-api-key'];
    if (apiKey) {
        return `api_key:${apiKey}`;
    }

    // Try authenticated user
    if (req.user && req.user.id) {
        return `user:${req.user.id}`;
    }

    // Fall back to IP address
    const ip = getClientIP(req);
    return `ip:${ip}`;
}

/**
 * Get real client IP address (handles proxies)
 * @param {express.Request} req - Express request object
 * @returns {string} Client IP address
 */
function getClientIP(req) {
    // Check Cloudflare header
    const cfIP = req.headers['cf-connecting-ip'];
    if (cfIP) return cfIP;

    // Check X-Forwarded-For (take first IP)
    const forwarded = req.headers['x-forwarded-for'];
    if (forwarded) {
        return forwarded.split(',')[0].trim();
    }

    // Check X-Real-IP
    const realIP = req.headers['x-real-ip'];
    if (realIP) return realIP;

    // Fall back to direct connection IP
    return req.ip || req.connection.remoteAddress;
}

/**
 * Default rate limit exceeded handler
 * @param {express.Request} req - Express request
 * @param {express.Response} res - Express response
 * @param {number} retryAfter - Seconds until retry allowed
 */
function defaultRateLimitHandler(req, res, retryAfter) {
    res.status(429).json({
        error: 'rate_limit_exceeded',
        message: `Too many requests. Please retry after ${retryAfter} seconds.`,
        retry_after: retryAfter
    });
}

// Example usage
if (require.main === module) {
    const express = require('express');
    const app = express();

    // Create Redis client
    const redisClient = redis.createClient({
        host: 'localhost',
        port: 6379
    });

    // Create rate limiter
    const rateLimiter = createRateLimiter(redisClient);

    // Global rate limit (100 requests per minute)
    app.use('/api', rateLimiter({
        limit: 100,
        window: 60
    }));

    // Stricter limit for expensive endpoint (5 requests per minute)
    app.get('/api/reports', rateLimiter({
        limit: 5,
        window: 60
    }), (req, res) => {
        res.json({ report: 'Generated' });
    });

    // Custom key generator for per-user limits
    app.get('/api/user-resource', rateLimiter({
        limit: 50,
        window: 60,
        keyGenerator: (req) => `user:${req.user?.id || 'anonymous'}`
    }), (req, res) => {
        res.json({ data: 'User resource' });
    });

    // Skip rate limiting for health checks
    app.get('/health', rateLimiter({
        skip: (req) => true
    }), (req, res) => {
        res.json({ status: 'ok' });
    });

    // Standard endpoint
    app.get('/api/posts', (req, res) => {
        res.json({ posts: [] });
    });

    app.listen(3000, () => {
        console.log('Server running on port 3000');
    });
}

module.exports = {
    createRateLimiter,
    getClientIdentifier,
    getClientIP,
    defaultRateLimitHandler
};
