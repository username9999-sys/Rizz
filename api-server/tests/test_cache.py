"""
Tests for app/utils/cache.py — Redis cache-aside helpers.
"""

import os
import sys
import time
import pytest
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
CACHE_PATH = os.path.join(API_ROOT, "app", "utils", "cache.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def cache():
    """Force a fresh module load (so env changes apply)."""
    # Ensure no REDIS_URL is set so we use the no-op
    os.environ.pop("REDIS_URL", None)
    # Reload
    if "app.utils.cache" in sys.modules:
        del sys.modules["app.utils.cache"]
    return _load("app.utils.cache", CACHE_PATH)


class TestNoOpFallback:
    def test_no_redis_url_uses_noop(self, cache):
        assert cache._get_redis().__class__.__name__ == "_NoOpCache"

    def test_cached_decorator_with_noop_works(self, cache):
        @cache.cached(ttl=60, key="x:{0}")
        def fn(x):
            return x * 2
        assert fn(5) == 10
        assert fn(5) == 10  # second call still works


class TestKeyBuilding:
    def test_positional_args(self, cache):
        result = cache._make_key("user:{0}", (42,), {})
        assert result == "user:42"

    def test_keyword_args(self, cache):
        result = cache._make_key("post:{slug}", (), {"slug": "hello"})
        assert result == "post:hello"

    def test_mixed_prefers_positional(self, cache):
        # If both args and kwargs match, positional wins
        result = cache._make_key("{0}-{name}", (1,), {"name": "x"})
        assert result == "1-x"


class TestSerialize:
    def test_basic_types(self, cache):
        assert cache._serialize("hello") == '"hello"'
        assert cache._serialize(42) == "42"
        assert cache._serialize(None) == "null"

    def test_dict(self, cache):
        out = cache._serialize({"a": 1, "b": [2, 3]})
        d = cache._deserialize(out)
        assert d == {"a": 1, "b": [2, 3]}

    def test_deserialize_none(self, cache):
        assert cache._deserialize(None) is None

    def test_deserialize_invalid(self, cache):
        assert cache._deserialize("not-json{") is None


class TestGetOrSet:
    """Without a real Redis, get_or_set always calls the factory."""
    def test_calls_factory_when_no_cache(self, cache):
        calls = []
        def factory():
            calls.append(1)
            return {"x": 1}
        result = cache.get_or_set("k1", 60, factory)
        assert result == {"x": 1}
        assert len(calls) == 1

    def test_returns_factory_value(self, cache):
        result = cache.get_or_set("k2", 60, lambda: [1, 2, 3])
        assert result == [1, 2, 3]


class TestInvalidate:
    def test_invalidate_noop_returns_zero(self, cache):
        n = cache.invalidate("user:1", "user:2")
        assert n == 0

    def test_invalidate_with_wildcard_noop(self, cache):
        n = cache.invalidate("user:*")
        assert n == 0

    def test_flush_namespace_noop(self, cache):
        n = cache.flush_namespace()
        assert n == 0


class TestWithRedisStub:
    """Verify caching behavior using a stub Redis client."""

    @pytest.fixture
    def cache_with_stub(self, monkeypatch, cache):
        """Inject a fake redis client that behaves like a dict."""
        store = {}
        stub = _StubRedis(store)
        # Patch _get_redis to return our stub
        monkeypatch.setattr(cache, "_get_redis", lambda: stub)
        return cache, stub, store

    def test_cached_miss_then_hit(self, cache_with_stub):
        cache, stub, store = cache_with_stub
        calls = []

        @cache.cached(ttl=60, key="user:{0}")
        def get_user(uid):
            calls.append(uid)
            return {"id": uid, "name": f"user{uid}"}

        # First call: miss, executes
        r1 = get_user(42)
        assert r1 == {"id": 42, "name": "user42"}
        assert calls == [42]

        # Second call: hit, no execution
        r2 = get_user(42)
        assert r2 == r1
        assert calls == [42]  # not called again

    def test_cached_different_keys(self, cache_with_stub):
        cache, stub, store = cache_with_stub
        calls = []

        @cache.cached(ttl=60, key="user:{0}")
        def get_user(uid):
            calls.append(uid)
            return uid

        get_user(1)
        get_user(2)
        get_user(1)
        assert calls == [1, 2]  # third call was a cache hit

    def test_invalidate_specific_key(self, cache_with_stub):
        cache, stub, store = cache_with_stub

        @cache.cached(ttl=60, key="user:{0}")
        def get_user(uid):
            return uid

        get_user(1)
        get_user(2)
        assert len(store) >= 2

        cache.invalidate("user:1")
        assert "rizz:user:1" not in store

    def test_invalidate_wildcard(self, cache_with_stub):
        cache, stub, store = cache_with_stub

        @cache.cached(ttl=60, key="user:{0}")
        def get_user(uid):
            return uid

        get_user(1)
        get_user(2)
        get_user(3)
        n = cache.invalidate("user:*")
        assert n == 3
        assert "rizz:user:1" not in store
        assert "rizz:user:3" not in store

    def test_cache_none_value(self, cache_with_stub):
        cache, stub, store = cache_with_stub

        @cache.cached(ttl=60, key="maybe:{0}")
        def get_maybe(x):
            return None

        # None result should still be cached and not re-execute
        get_maybe(1)
        get_maybe(1)
        # Cannot easily assert without instrumenting, but the call should
        # not raise and second call should return None
        assert get_maybe(1) is None

    def test_redis_error_does_not_break_call(self, cache, monkeypatch):
        """If Redis is misbehaving, the function still works."""

        class BrokenRedis:
            def get(self, *a, **kw): raise ConnectionError("redis down")
            def setex(self, *a, **kw): raise ConnectionError("redis down")

        monkeypatch.setattr(cache, "_get_redis", lambda: BrokenRedis())

        @cache.cached(ttl=60, key="x:{0}")
        def f(x):
            return x * 2

        assert f(3) == 6  # should not raise


class _StubRedis:
    """Minimal Redis-like stub for testing."""

    def __init__(self, store):
        self.store = store

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, *keys):
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n

    def scan_iter(self, match=None, count=100):
        import fnmatch
        for k in list(self.store.keys()):
            if fnmatch.fnmatchcase(k, match):
                yield k

    def ping(self):
        return True
