import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, ClassVar
import uuid

from fastapi import HTTPException, Request, Response, status

from core.config.settings import Settings, get_settings

logger = logging.getLogger("core.api.rate_limiter")


class APIRateLimiter:
    """
    Provider-agnostic sliding-window rate limiter for API endpoints.
    Protects LLM inference, orchestration runs, and expensive adapter endpoints from quota drain.
    Uses Redis when CACHE_BACKEND is 'redis' with automatic in-memory fallback.
    """

    _requests: ClassVar[dict[str, list[float]]] = defaultdict(list)
    _lock: ClassVar[asyncio.Lock | None] = None
    _redis_client: ClassVar[Any] = None
    _redis_failed: ClassVar[bool] = False
    _last_failure_time: ClassVar[float] = 0.0
    _COOLDOWN_SECONDS: ClassVar[float] = 30.0

    LUA_SLIDING_WINDOW: ClassVar[str] = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]
    local clear_before = now - window

    redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)
    local current_count = redis.call('ZCARD', key)

    if current_count < limit then
        redis.call('ZADD', key, now, member)
        redis.call('EXPIRE', key, math.ceil(window) + 1)
        local remaining = limit - current_count - 1
        return {1, remaining, 0}
    else
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        local retry_after = 1
        if oldest and #oldest >= 2 then
            local oldest_ts = tonumber(oldest[2])
            retry_after = math.max(1, math.ceil(window - (now - oldest_ts)))
        end
        return {0, 0, retry_after}
    end
    """

    TRUSTED_PROXIES: ClassVar[set[str]] = {
        "127.0.0.1",
        "::1",
        "localhost",
        "testclient",
    }

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def set_redis_client(cls, client: Any) -> None:
        """Sets or mocks the Redis client for testing or custom lifecycle management."""
        cls._redis_client = client
        cls._redis_failed = False
        cls._last_failure_time = 0.0

    @classmethod
    async def _get_redis_client(cls, url: str) -> Any:
        if cls._redis_client is not None:
            return cls._redis_client
        try:
            import redis.asyncio as aioredis

            cls._redis_client = aioredis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            return cls._redis_client
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client for API rate limiter at {url}: {e}")
            return None

    @classmethod
    async def _check_redis(
        cls,
        client_id: str,
        resource_key: str,
        limit: int,
        window_seconds: int,
        settings: Settings,
    ) -> tuple[bool, int, int]:
        redis_url = settings.cache_url
        if (not redis_url or "localhost" in redis_url) and settings.broker_url and "localhost" not in settings.broker_url:
            redis_url = settings.broker_url
        if not redis_url:
            redis_url = settings.cache_url or "redis://localhost:6379/1"

        client = await cls._get_redis_client(redis_url)
        if client is None:
            raise RuntimeError("Redis client could not be initialized")

        prefix = settings.broker_key_prefix or "orb"
        key = f"{prefix}:ratelimit:api:{client_id}:{resource_key}"
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex[:8]}"

        res = await client.eval(
            cls.LUA_SLIDING_WINDOW,
            1,
            key,
            now,
            window_seconds,
            limit,
            member,
        )
        if isinstance(res, (list, tuple)) and len(res) >= 3:
            return bool(res[0]), int(res[1]), int(res[2])
        raise ValueError(f"Unexpected Redis rate limiter response: {res}")

    @classmethod
    async def _check_memory(
        cls,
        client_id: str,
        resource_key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - window_seconds
        bucket_key = f"{client_id}:{resource_key}"

        async with cls._get_lock():
            active_ts = [
                ts for ts in cls._requests.get(bucket_key, []) if ts > window_start
            ]
            if not active_ts and bucket_key in cls._requests:
                del cls._requests[bucket_key]
            elif active_ts:
                cls._requests[bucket_key] = active_ts

            current_count = len(cls._requests.get(bucket_key, []))
            if current_count >= limit:
                oldest_ts = cls._requests[bucket_key][0]
                retry_after = max(1, int(window_seconds - (now - oldest_ts)))
                return False, 0, retry_after

            cls._requests[bucket_key].append(now)
            remaining = max(0, limit - current_count - 1)
            return True, remaining, 0

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        """Extracts the client IP address, honoring proxy headers only when received from trusted upstream proxies."""
        direct_host = request.client.host if request.client and request.client.host else "127.0.0.1"

        # Check if direct connecting host is a trusted upstream proxy or local container network
        is_trusted = (
            direct_host in cls.TRUSTED_PROXIES
            or direct_host.startswith("10.")
            or direct_host.startswith("172.16.")
            or direct_host.startswith("192.168.")
        )
        if is_trusted:
            cf_ip = request.headers.get("CF-Connecting-IP")
            if cf_ip:
                return cf_ip.strip()
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()

        return direct_host

    @classmethod
    async def check(
        cls,
        client_id: str,
        resource_key: str,
        limit: int,
        window_seconds: int = 60,
        settings: Settings | None = None,
    ) -> tuple[bool, int, int]:
        """
        Checks if the request is allowed under the sliding window.
        Uses Redis if cache_backend is 'redis'; falls back to in-memory on failure or if not configured.
        Returns (is_allowed, remaining_quota, retry_after_seconds).
        """
        cfg = settings or get_settings()
        backend = (cfg.cache_backend or "").strip().lower()

        if backend == "redis":
            now = time.time()
            if cls._redis_failed and (now - cls._last_failure_time) < cls._COOLDOWN_SECONDS:
                return await cls._check_memory(
                    client_id=client_id,
                    resource_key=resource_key,
                    limit=limit,
                    window_seconds=window_seconds,
                )

            try:
                result = await cls._check_redis(
                    client_id=client_id,
                    resource_key=resource_key,
                    limit=limit,
                    window_seconds=window_seconds,
                    settings=cfg,
                )
                cls._redis_failed = False
                return result
            except Exception as err:
                cls._redis_failed = True
                cls._last_failure_time = time.time()
                cls._redis_client = None
                logger.warning(
                    f"Redis API rate limiter error ({err}). Falling back to in-memory limiter."
                )
                return await cls._check_memory(
                    client_id=client_id,
                    resource_key=resource_key,
                    limit=limit,
                    window_seconds=window_seconds,
                )

        return await cls._check_memory(
            client_id=client_id,
            resource_key=resource_key,
            limit=limit,
            window_seconds=window_seconds,
        )

    @classmethod
    def reset(cls) -> None:
        """Resets all tracked request buckets (useful for test isolation)."""
        cls._requests.clear()
        cls._redis_client = None
        cls._redis_failed = False
        cls._last_failure_time = 0.0


def rate_limit(
    resource_key: str,
    max_requests: int | None = None,
    window_seconds: int = 60,
) -> Callable:
    """
    FastAPI dependency for endpoint-level sliding window rate limiting.
    """

    async def _dependency(request: Request, response: Response) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        # Resolve limit from settings if not explicitly provided
        effective_limit = max_requests
        if effective_limit is None:
            if resource_key == "goal":
                effective_limit = settings.rate_limit_goal_per_minute
            elif resource_key == "run":
                effective_limit = settings.rate_limit_run_per_minute
            else:
                effective_limit = settings.rate_limit_default_per_minute

        client_ip = APIRateLimiter.get_client_ip(request)
        allowed, remaining, retry_after = await APIRateLimiter.check(
            client_id=client_ip,
            resource_key=resource_key,
            limit=effective_limit,
            window_seconds=window_seconds,
            settings=settings,
        )

        response.headers["X-RateLimit-Limit"] = str(effective_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        if not allowed:
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded for endpoint '{resource_key}'. "
                    f"Maximum {effective_limit} request(s) per {window_seconds}s allowed. "
                    f"Please retry in {retry_after} second(s)."
                ),
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(effective_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

    return _dependency
