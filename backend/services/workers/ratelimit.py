"""Distributed token-bucket rate limiter (Redis + Lua).

This is the backpressure mechanism. Work is bounded by EXTERNAL limits, not your
CPU:

  - LLM calls are gated by the provider's requests-per-minute budget.
  - Website fetches are gated by per-domain politeness.

A task tries to take a token before doing the rate-limited call. If the bucket
is empty, the task does NOT spin or fail — it gets a `wait` time and the caller
re-queues it with that countdown. Excess load just waits in the queue. That's
correct backpressure: we never overwhelm the provider or hammer a target site.

The Lua script runs atomically inside Redis so many workers share one bucket."""

import time

import redis

from config.settings import settings

_r = redis.Redis.from_url(settings.ratelimit_redis_url)

# Classic token bucket. Returns {allowed (0/1), wait_seconds}.
_LUA = """
local key       = KEYS[1]
local rate      = tonumber(ARGV[1])   -- tokens added per second
local capacity  = tonumber(ARGV[2])   -- max tokens (burst size)
local now       = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local data   = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts     = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

-- refill based on elapsed time
local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * rate)

local allowed = 0
local wait = 0.0
if tokens >= requested then
  tokens = tokens - requested
  allowed = 1
else
  wait = (requested - tokens) / rate
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / rate) + 10)
return {allowed, tostring(wait)}
"""

_script = _r.register_script(_LUA)


def acquire(key: str, rate: float, capacity: float, requested: float = 1.0):
    """Try to take `requested` tokens. Returns (allowed: bool, wait: float seconds)."""
    allowed, wait = _script(keys=[key], args=[rate, capacity, time.time(), requested])
    return bool(allowed), float(wait)


def llm_gate():
    """Global OpenAI budget shared by all AI workers."""
    rate = settings.llm_max_rpm / 60.0          # tokens/sec
    capacity = max(1.0, settings.llm_max_rpm)   # allow a 1-minute burst
    return acquire("ratelimit:llm:openai", rate=rate, capacity=capacity)


def domain_gate(domain: str):
    """Per-domain politeness budget for website fetches."""
    rate = settings.scrape_per_domain_rps
    capacity = max(1.0, rate * 2)               # small burst allowance
    return acquire(f"ratelimit:domain:{domain}", rate=rate, capacity=capacity)
