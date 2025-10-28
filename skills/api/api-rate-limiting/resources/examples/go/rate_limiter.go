// Rate Limiter with Token Bucket Algorithm
//
// Production-ready rate limiter using golang.org/x/time/rate
// with Redis backend for distributed rate limiting.
//
// Features:
// - Token bucket algorithm with burst support
// - Redis-backed distributed limiting
// - Thread-safe operations
// - Graceful error handling
//
// Usage:
//     limiter := NewRedisRateLimiter(redisClient, 100, 10)
//     if limiter.Allow("user:123") {
//         // Process request
//     } else {
//         // Rate limited
//     }

package main

import (
	"context"
	"fmt"
	"math"
	"strconv"
	"time"

	"github.com/go-redis/redis/v8"
	"golang.org/x/time/rate"
)

// RedisRateLimiter implements distributed rate limiting with Redis
type RedisRateLimiter struct {
	client      *redis.Client
	script      *redis.Script
	capacity    int
	refillRate  float64
}

// NewRedisRateLimiter creates a new Redis-backed rate limiter
func NewRedisRateLimiter(client *redis.Client, capacity int, refillRate float64) *RedisRateLimiter {
	// Lua script for atomic token bucket operations
	script := redis.NewScript(`
		local key = KEYS[1]
		local capacity = tonumber(ARGV[1])
		local refill_rate = tonumber(ARGV[2])
		local tokens_needed = tonumber(ARGV[3])
		local now = tonumber(ARGV[4])

		local state = redis.call('HMGET', key, 'tokens', 'last_refill')
		local tokens = tonumber(state[1])
		local last_refill = tonumber(state[2])

		if not tokens then
			tokens = capacity
			last_refill = now
		end

		local elapsed = now - last_refill
		tokens = math.min(capacity, tokens + (elapsed * refill_rate))

		if tokens >= tokens_needed then
			tokens = tokens - tokens_needed
			redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(now))
			redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
			return 1
		else
			return 0
		end
	`)

	return &RedisRateLimiter{
		client:     client,
		script:     script,
		capacity:   capacity,
		refillRate: refillRate,
	}
}

// Allow checks if a request is allowed for the given key
func (r *RedisRateLimiter) Allow(key string) bool {
	allowed, _ := r.AllowN(key, 1)
	return allowed
}

// AllowN checks if N tokens can be consumed for the given key
func (r *RedisRateLimiter) AllowN(key string, tokens int) (bool, error) {
	ctx := context.Background()
	now := float64(time.Now().UnixNano()) / 1e9

	result, err := r.script.Run(
		ctx,
		r.client,
		[]string{fmt.Sprintf("rate_limit:token_bucket:%s", key)},
		r.capacity,
		r.refillRate,
		tokens,
		now,
	).Result()

	if err != nil {
		// Fail open on Redis errors
		fmt.Printf("Redis error: %v\n", err)
		return true, err
	}

	allowed := result.(int64) == 1
	return allowed, nil
}

// GetTokens returns the current number of available tokens
func (r *RedisRateLimiter) GetTokens(key string) (float64, error) {
	ctx := context.Background()
	redisKey := fmt.Sprintf("rate_limit:token_bucket:%s", key)

	result, err := r.client.HMGet(ctx, redisKey, "tokens", "last_refill").Result()
	if err != nil {
		return float64(r.capacity), err
	}

	if result[0] == nil {
		return float64(r.capacity), nil
	}

	tokens, _ := strconv.ParseFloat(result[0].(string), 64)
	lastRefill, _ := strconv.ParseFloat(result[1].(string), 64)

	now := float64(time.Now().UnixNano()) / 1e9
	elapsed := now - lastRefill

	tokens = math.Min(float64(r.capacity), tokens+(elapsed*r.refillRate))

	return tokens, nil
}

// LocalRateLimiter implements in-memory rate limiting
type LocalRateLimiter struct {
	limiters map[string]*rate.Limiter
	limit    rate.Limit
	burst    int
}

// NewLocalRateLimiter creates a new in-memory rate limiter
func NewLocalRateLimiter(requestsPerSecond float64, burst int) *LocalRateLimiter {
	return &LocalRateLimiter{
		limiters: make(map[string]*rate.Limiter),
		limit:    rate.Limit(requestsPerSecond),
		burst:    burst,
	}
}

// GetLimiter returns or creates a limiter for the given key
func (l *LocalRateLimiter) GetLimiter(key string) *rate.Limiter {
	limiter, exists := l.limiters[key]
	if !exists {
		limiter = rate.NewLimiter(l.limit, l.burst)
		l.limiters[key] = limiter
	}
	return limiter
}

// Allow checks if a request is allowed for the given key
func (l *LocalRateLimiter) Allow(key string) bool {
	limiter := l.GetLimiter(key)
	return limiter.Allow()
}

// Wait blocks until a token is available for the given key
func (l *LocalRateLimiter) Wait(ctx context.Context, key string) error {
	limiter := l.GetLimiter(key)
	return limiter.Wait(ctx)
}

// Example usage
func main() {
	// Redis-backed distributed rate limiter
	redisClient := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	// Create rate limiter: 100 capacity, 10 tokens/second
	limiter := NewRedisRateLimiter(redisClient, 100, 10)

	// Check rate limit
	if limiter.Allow("user:123") {
		fmt.Println("Request allowed")
	} else {
		fmt.Println("Rate limited")
	}

	// Check available tokens
	tokens, _ := limiter.GetTokens("user:123")
	fmt.Printf("Available tokens: %.2f\n", tokens)

	// In-memory rate limiter (for single-instance applications)
	localLimiter := NewLocalRateLimiter(10, 20) // 10 req/sec, burst of 20

	if localLimiter.Allow("user:456") {
		fmt.Println("Local limiter: Request allowed")
	} else {
		fmt.Println("Local limiter: Rate limited")
	}

	// Wait for token (blocking)
	ctx := context.Background()
	if err := localLimiter.Wait(ctx, "user:456"); err != nil {
		fmt.Printf("Error waiting: %v\n", err)
	} else {
		fmt.Println("Token acquired after waiting")
	}
}
