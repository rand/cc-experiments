-- Lua Rate Limiter Scripts for Redis
--
-- Production-ready Lua scripts for atomic rate limiting operations in Redis.
-- These scripts ensure consistency in distributed environments by executing
-- atomically on the Redis server.
--
-- Usage:
--     script_sha = redis.script_load(script)
--     result = redis.evalsha(script_sha, num_keys, key1, arg1, arg2, ...)

--------------------------------------------------------------------------------
-- Token Bucket Algorithm
--------------------------------------------------------------------------------
-- Implements token bucket with automatic refilling based on time elapsed.
--
-- Arguments:
--   KEYS[1]: Rate limit key
--   ARGV[1]: capacity (maximum tokens)
--   ARGV[2]: refill_rate (tokens per second)
--   ARGV[3]: tokens_needed (tokens to consume)
--   ARGV[4]: now (current timestamp)
--
-- Returns:
--   {1, remaining} if allowed
--   {0, remaining} if denied
--------------------------------------------------------------------------------
local token_bucket_script = [[
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local tokens_needed = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

-- Get current state
local state = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(state[1])
local last_refill = tonumber(state[2])

-- Initialize if first request
if not tokens then
    tokens = capacity
    last_refill = now
end

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local tokens_to_add = elapsed * refill_rate
tokens = math.min(capacity, tokens + tokens_to_add)

-- Check if enough tokens available
if tokens >= tokens_needed then
    -- Consume tokens
    tokens = tokens - tokens_needed
    redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
    -- Set TTL to prevent memory leak
    redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) * 2)
    return {1, tokens}
else
    -- Not enough tokens
    return {0, tokens}
end
]]


--------------------------------------------------------------------------------
-- Sliding Window Algorithm
--------------------------------------------------------------------------------
-- Implements sliding window using Redis sorted sets with timestamps.
--
-- Arguments:
--   KEYS[1]: Rate limit key
--   ARGV[1]: limit (maximum requests)
--   ARGV[2]: window (window duration in seconds)
--   ARGV[3]: now (current timestamp)
--   ARGV[4]: request_id (unique identifier)
--
-- Returns:
--   {1, remaining} if allowed
--   {0, 0} if denied
--------------------------------------------------------------------------------
local sliding_window_script = [[
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local request_id = ARGV[4]

local window_start = now - window

-- Remove requests outside window
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- Count requests in window
local count = redis.call('ZCARD', key)

if count < limit then
    -- Add current request
    redis.call('ZADD', key, now, request_id)
    redis.call('EXPIRE', key, window * 2)
    return {1, limit - count - 1}
else
    return {0, 0}
end
]]


--------------------------------------------------------------------------------
-- Fixed Window Algorithm
--------------------------------------------------------------------------------
-- Implements fixed window with atomic increment.
--
-- Arguments:
--   KEYS[1]: Rate limit key (base key, script appends window ID)
--   ARGV[1]: limit (maximum requests)
--   ARGV[2]: window (window duration in seconds)
--   ARGV[3]: now (current timestamp)
--
-- Returns:
--   {1, remaining, reset} if allowed
--   {0, 0, reset} if denied
--------------------------------------------------------------------------------
local fixed_window_script = [[
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local window_id = math.floor(now / window)
local redis_key = key .. ":" .. window_id

-- Increment counter
local count = redis.call('INCR', redis_key)

-- Set TTL on first request
if count == 1 then
    redis.call('EXPIRE', redis_key, window * 2)
end

local allowed = count <= limit
local remaining = math.max(0, limit - count)
local reset = (window_id + 1) * window

return {allowed and 1 or 0, remaining, reset}
]]


--------------------------------------------------------------------------------
-- Leaky Bucket Algorithm
--------------------------------------------------------------------------------
-- Implements leaky bucket with constant leak rate.
--
-- Arguments:
--   KEYS[1]: Rate limit key
--   ARGV[1]: capacity (maximum queue size)
--   ARGV[2]: leak_rate (requests processed per second)
--   ARGV[3]: now (current timestamp)
--
-- Returns:
--   {1, remaining_capacity} if allowed
--   {0, 0} if denied (queue full)
--------------------------------------------------------------------------------
local leaky_bucket_script = [[
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local leak_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local state = redis.call('HMGET', key, 'size', 'last_leak')
local size = tonumber(state[1]) or 0
local last_leak = tonumber(state[2]) or now

-- Leak based on elapsed time
local elapsed = now - last_leak
local leaked = elapsed * leak_rate
size = math.max(0, size - leaked)

-- Check if space available
if size < capacity then
    size = size + 1
    redis.call('HMSET', key, 'size', size, 'last_leak', now)
    redis.call('EXPIRE', key, math.ceil(capacity / leak_rate) * 2)
    return {1, capacity - size}
else
    return {0, 0}
end
]]


--------------------------------------------------------------------------------
-- Multi-Tier Rate Limiting
--------------------------------------------------------------------------------
-- Check multiple rate limits atomically (per-second, per-minute, per-hour).
--
-- Arguments:
--   KEYS[1]: Base key for rate limits
--   ARGV[1]: limit_per_second
--   ARGV[2]: limit_per_minute
--   ARGV[3]: limit_per_hour
--   ARGV[4]: now (current timestamp)
--
-- Returns:
--   {1, tier_name} if all allowed
--   {0, tier_name} if any tier exceeded (tier_name indicates which tier failed)
--------------------------------------------------------------------------------
local multi_tier_script = [[
local base_key = KEYS[1]
local limit_second = tonumber(ARGV[1])
local limit_minute = tonumber(ARGV[2])
local limit_hour = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

-- Check per-second limit (fixed window)
local second_id = math.floor(now)
local second_key = base_key .. ":second:" .. second_id
local second_count = redis.call('INCR', second_key)
if second_count == 1 then
    redis.call('EXPIRE', second_key, 2)
end
if second_count > limit_second then
    return {0, "per_second"}
end

-- Check per-minute limit (fixed window)
local minute_id = math.floor(now / 60)
local minute_key = base_key .. ":minute:" .. minute_id
local minute_count = redis.call('INCR', minute_key)
if minute_count == 1 then
    redis.call('EXPIRE', minute_key, 120)
end
if minute_count > limit_minute then
    return {0, "per_minute"}
end

-- Check per-hour limit (fixed window)
local hour_id = math.floor(now / 3600)
local hour_key = base_key .. ":hour:" .. hour_id
local hour_count = redis.call('INCR', hour_key)
if hour_count == 1 then
    redis.call('EXPIRE', hour_key, 7200)
end
if hour_count > limit_hour then
    return {0, "per_hour"}
end

return {1, "allowed"}
]]


--------------------------------------------------------------------------------
-- Distributed Lock with Timeout
--------------------------------------------------------------------------------
-- Acquire distributed lock with automatic expiration.
-- Useful for coordinating rate limiter state updates.
--
-- Arguments:
--   KEYS[1]: Lock key
--   ARGV[1]: lock_value (unique identifier)
--   ARGV[2]: ttl (lock timeout in seconds)
--
-- Returns:
--   1 if lock acquired
--   0 if lock already held
--------------------------------------------------------------------------------
local acquire_lock_script = [[
local key = KEYS[1]
local value = ARGV[1]
local ttl = tonumber(ARGV[2])

-- Try to set lock with NX (only if not exists)
local result = redis.call('SET', key, value, 'NX', 'EX', ttl)

if result then
    return 1
else
    return 0
end
]]


--------------------------------------------------------------------------------
-- Release Distributed Lock
--------------------------------------------------------------------------------
-- Release lock only if we own it (compare lock value).
--
-- Arguments:
--   KEYS[1]: Lock key
--   ARGV[1]: lock_value (unique identifier)
--
-- Returns:
--   1 if lock released
--   0 if lock not owned by us
--------------------------------------------------------------------------------
local release_lock_script = [[
local key = KEYS[1]
local value = ARGV[1]

-- Only delete if value matches (we own the lock)
if redis.call('GET', key) == value then
    redis.call('DEL', key)
    return 1
else
    return 0
end
]]


-- Return all scripts for easy access
return {
    token_bucket = token_bucket_script,
    sliding_window = sliding_window_script,
    fixed_window = fixed_window_script,
    leaky_bucket = leaky_bucket_script,
    multi_tier = multi_tier_script,
    acquire_lock = acquire_lock_script,
    release_lock = release_lock_script
}
