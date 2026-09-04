"""
Cache-aside helpers built on Redis.

Usage:
    from app.utils.cache import cached, invalidate

    @cached(ttl=300, key="user:{user_id}")
    def get_user_profile(user_id: int) -> dict:
        return db.query(...)

    # Invalidate after write
    @app.route("/users/<id>", methods=["PUT"])
    def update_user(id):
        ...
        invalidate("user:{user_id}".format(user_id=id))
        return ...

This module is framework-agnostic and does not import the broken
app/__init__.py. The cache instance is created lazily and can be
configured via env vars.
"""

import os
import json
import hashlib
import logging
import threading
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Default TTL: 5 minutes
DEFAULT_TTL = 300

# Connection pool (lazy)
_pool_lock = threading.Lock()
_redis_client = None


def _get_redis():
    """Get or create the Redis client. Falls back to a no-op if unreachable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    with _pool_lock:
        if _redis_client is not None:
            return _redis_client
        url = os.environ.get("REDIS_URL")
        if not url:
            logger.debug("REDIS_URL not set; cache will be a no-op")
            _redis_client = _NoOpCache()
            return _redis_client
        try:
            import redis
            _redis_client = redis.Redis.from_url(
                url,
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            # Sanity-check
            _redis_client.ping()
            return _redis_client
        except Exception as e:
            logger.warning(f"Redis unavailable, cache disabled: {e}")
            _redis_client = _NoOpCache()
            return _redis_client


class _NoOpCache:
    """Fallback when Redis is unavailable. No errors, no caching."""

    def get(self, *_args, **_kwargs):
        return None

    def setex(self, *_args, **_kwargs):
        pass

    def set(self, *_args, **_kwargs):
        pass

    def delete(self, *_args, **_kwargs):
        return 0

    def keys(self, *_args, **_kwargs):
        return []

    def ping(self):
        return False


def _serialize(value: Any) -> str:
    """Serialize a Python value to a JSON string for storage."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return json.dumps(value)
    return json.dumps(value, default=str)


def _deserialize(raw: Optional[str]) -> Any:
    """Deserialize a cached JSON string back to a Python value."""
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _make_key(template: str, args: tuple, kwargs: dict) -> str:
    """Build a cache key from a template string and the function's args.

    Examples:
        _make_key("user:{0}", (42,), {})            -> "user:42"
        _make_key("post:{slug}", (), {"slug": "x"})  -> "post:x"
        _make_key("{0}-{name}", (1,), {"name": "x"}) -> "1-x"
    """
    if args:
        # Use positional format. Pass args + kwargs as extra so
        # templates mixing {0} and {name} still work.
        return template.format(*args, **kwargs)
    return template.format(**kwargs)


# ---------- Public API ----------

def cached(
    ttl: int = DEFAULT_TTL,
    key: Optional[str] = None,
    namespace: str = "rizz",
) -> Callable:
    """Decorator: cache the result of a function for `ttl` seconds.

    Args:
        ttl: seconds to cache the result
        key: template string using positional {0}, {1}... or keyword {name}
             If None, a key is generated from the function's qualified name
             and the args (hashed).
        namespace: prefix for all keys (use per-app, e.g. "rizz:v1")
    """
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            r = _get_redis()
            # If the cache is a no-op, just call the function
            if isinstance(r, _NoOpCache):
                return view(*args, **kwargs)

            # Build key
            if key:
                cache_key = f"{namespace}:{_make_key(key, args, kwargs)}"
            else:
                # Auto-generate from function name + hashed args
                h = hashlib.sha256(repr((args, sorted(kwargs.items()))).encode()).hexdigest()[:16]
                cache_key = f"{namespace}:{view.__qualname__}:{h}"

            try:
                cached_raw = r.get(cache_key)
            except Exception as e:
                logger.warning(f"cache get failed: {e}")
                return view(*args, **kwargs)

            hit = _deserialize(cached_raw)
            if hit is not None and not (isinstance(hit, dict) and hit.get("__miss__")):
                return hit

            result = view(*args, **kwargs)
            try:
                # Allow None to be cached (as a sentinel dict)
                payload = result if result is not None else {"__miss__": True}
                r.setex(cache_key, ttl, _serialize(payload))
            except Exception as e:
                logger.warning(f"cache set failed: {e}")
            return result

        return wrapper

    return decorator


def invalidate(*patterns: str, namespace: str = "rizz") -> int:
    """Invalidate cache keys matching one or more glob patterns.

    Args:
        patterns: one or more glob patterns relative to the namespace
                  (e.g. "user:42", "user:*", "post:slug-x")
        namespace: same namespace as the @cached decorator

    Returns:
        Number of keys deleted.
    """
    r = _get_redis()
    if isinstance(r, _NoOpCache):
        return 0
    total = 0
    try:
        for pattern in patterns:
            full = f"{namespace}:{pattern}"
            # If pattern is exact, delete directly
            if "*" not in pattern and "?" not in pattern:
                total += r.delete(full)
            else:
                # Use SCAN to avoid blocking
                for key in r.scan_iter(match=full, count=100):
                    total += r.delete(key)
    except Exception as e:
        logger.warning(f"cache invalidate failed: {e}")
    return total


def flush_namespace(namespace: str = "rizz") -> int:
    """Delete every key in the namespace. Use carefully."""
    return invalidate("*", namespace=namespace)


# ---------- Cache-aside helper for ad-hoc use ----------

def get_or_set(key: str, ttl: int, factory: Callable[[], Any],
              namespace: str = "rizz") -> Any:
    """Read-through cache helper. Returns the cached value or calls factory()."""
    r = _get_redis()
    if isinstance(r, _NoOpCache):
        return factory()
    full = f"{namespace}:{key}"
    try:
        cached_raw = r.get(full)
    except Exception:
        return factory()
    if cached_raw is not None:
        result = _deserialize(cached_raw)
        if result is not None and not (isinstance(result, dict) and result.get("__miss__")):
            return result
    value = factory()
    try:
        payload = value if value is not None else {"__miss__": True}
        r.setex(full, ttl, _serialize(payload))
    except Exception:
        pass
    return value
