"""
Tests for app/utils/analytics.py — counter, gauge, histogram, registry.
"""

import os
import sys
import math
import importlib.util
import pytest
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
API_ROOT = os.path.abspath(os.path.join(HERE, ".."))
A_PATH = os.path.join(API_ROOT, "app", "utils", "analytics.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def an():
    return _load("_test_an", A_PATH)


# ==================== Counter ====================

class TestCounter:
    def test_inc_default(self, an):
        c = an.Counter("c1")
        c.inc()
        assert c.get() == 1.0
        c.inc()
        assert c.get() == 2.0

    def test_inc_with_amount(self, an):
        c = an.Counter("c1")
        c.inc(5.5)
        assert c.get() == 5.5

    def test_inc_negative_raises(self, an):
        c = an.Counter("c1")
        with pytest.raises(ValueError):
            c.inc(-1)

    def test_inc_with_labels(self, an):
        c = an.Counter("c1")
        c.inc(1, tenant="acme", source="signup")
        c.inc(3, tenant="acme", source="signup")
        c.inc(2, tenant="globex", source="signup")
        assert c.get(tenant="acme", source="signup") == 4
        assert c.get(tenant="globex", source="signup") == 2
        assert c.get(tenant="ghost", source="signup") == 0

    def test_total(self, an):
        c = an.Counter("c1")
        c.inc(1, tenant="a")
        c.inc(2, tenant="b")
        c.inc(3, tenant="c")
        assert c.total() == 6

    def test_snapshot(self, an):
        c = an.Counter("c1")
        c.inc(10, tenant="a")
        c.inc(5, tenant="b")
        snap = c.snapshot()
        # Now returns a list of {labels, value}
        assert {"labels": dict(tenant="a"), "value": 10} in snap
        assert {"labels": dict(tenant="b"), "value": 5} in snap


# ==================== Gauge ====================

class TestGauge:
    def test_set_and_get(self, an):
        g = an.Gauge("g1")
        g.set(42.5)
        assert g.get() == 42.5

    def test_inc_dec(self, an):
        g = an.Gauge("g1")
        g.set(10)
        g.inc(5)
        assert g.get() == 15
        g.dec(3)
        assert g.get() == 12

    def test_labeled_gauge(self, an):
        g = an.Gauge("g1")
        g.set(7, tenant="a")
        g.set(3, tenant="b")
        assert g.get(tenant="a") == 7
        assert g.get(tenant="b") == 3
        assert g.get(tenant="c") == 0

    def test_can_go_negative(self, an):
        g = an.Gauge("temperature")
        g.set(-5.0)
        assert g.get() == -5.0


# ==================== Histogram ====================

class TestHistogram:
    def test_observe_basic(self, an):
        h = an.Histogram("h1")
        for v in [1, 2, 3, 4, 5]:
            h.observe(v)
        assert h.count() == 5
        assert h.sum() == 15
        assert h.mean() == 3.0

    def test_empty_percentile_returns_zero(self, an):
        h = an.Histogram("h1")
        assert h.percentile(95) == 0.0

    def test_percentile_invalid_p_raises(self, an):
        h = an.Histogram("h1")
        h.observe(1)
        with pytest.raises(ValueError):
            h.percentile(-1)
        with pytest.raises(ValueError):
            h.percentile(101)

    def test_percentile_single_value(self, an):
        h = an.Histogram("h1")
        h.observe(42)
        assert h.percentile(50) == 42
        assert h.percentile(99) == 42

    def test_percentile_known_distribution(self, an):
        """For 1..100, p50 should be ~50, p99 should be ~99."""
        h = an.Histogram("h1")
        for v in range(1, 101):
            h.observe(v)
        p50 = h.percentile(50)
        p99 = h.percentile(99)
        # Allow small interpolation tolerance
        assert 49 <= p50 <= 51
        assert 98 <= p99 <= 100

    def test_quantiles(self, an):
        h = an.Histogram("h1")
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            h.observe(v)
        q = h.quantiles()
        assert set(q.keys()) == {"p50", "p90", "p95", "p99"}
        # With 10 evenly-spaced samples, p50 by linear interpolation
        # is the midpoint of 50 and 60 = 55
        assert q["p50"] == 55
        # p90 falls between 90 and 100, near 90
        assert 90 <= q["p90"] <= 91

    def test_labeled_histogram(self, an):
        h = an.Histogram("h1")
        h.observe(10, endpoint="/a")
        h.observe(20, endpoint="/a")
        h.observe(100, endpoint="/b")
        assert h.count(endpoint="/a") == 2
        assert h.count(endpoint="/b") == 1
        assert h.mean(endpoint="/a") == 15
        # 2 samples [10, 20]: p50 by interpolation = (10+20)/2 = 15
        assert h.percentile(50, endpoint="/a") == 15

    def test_capacity_enforced(self, an):
        h = an.Histogram("h1", capacity=10)
        for v in range(100):
            h.observe(v)
        assert h.count() <= 10


# ==================== Registry ====================

class TestRegistry:
    def test_counter_is_singleton_per_name(self, an):
        r = an.MetricsRegistry()
        a = r.counter("c1")
        b = r.counter("c1")
        assert a is b
        a.inc()
        assert b.get() == 1.0

    def test_different_names_different_objects(self, an):
        r = an.MetricsRegistry()
        a = r.counter("a")
        b = r.counter("b")
        assert a is not b

    def test_snapshot_structure(self, an):
        r = an.MetricsRegistry()
        r.counter("signups").inc(1, tenant="a")
        r.gauge("active_sessions").set(5)
        r.histogram("latency").observe(0.1)
        snap = r.snapshot()
        assert "signups" in snap["counters"]
        assert "active_sessions" in snap["gauges"]
        assert "latency" in snap["histograms"]

    def test_reset(self, an):
        r = an.MetricsRegistry()
        r.counter("c1").inc()
        r.reset()
        assert r.snapshot()["counters"] == {}
        assert r.snapshot()["gauges"] == {}


class TestBusinessMetrics:
    def test_signups_logins_posts(self, an):
        r = an.MetricsRegistry()
        r.counter("signups_total").inc(1, tenant="acme", source="organic")
        r.counter("signups_total").inc(2, tenant="acme", source="referral")
        r.counter("logins_total").inc(5, tenant="acme", success="true")
        r.counter("posts_created_total").inc(3, tenant="acme")
        bm = an.get_business_metrics(registry=r)
        # Each metric is a list of {labels, value}
        def find(metric_list, **want):
            for entry in metric_list:
                if entry["labels"] == dict(want):
                    return entry["value"]
            return None
        assert find(bm["signups"], tenant="acme", source="organic") == 1
        assert find(bm["signups"], tenant="acme", source="referral") == 2
        assert find(bm["logins"], tenant="acme", success="true") == 5
        assert find(bm["posts_created"], tenant="acme") == 3


# ==================== Thread safety ====================

class TestConcurrency:
    def test_concurrent_counter_inc(self, an):
        c = an.Counter("c1")
        def inc():
            for _ in range(100):
                c.inc()
        threads = [threading.Thread(target=inc) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert c.get() == 1000

    def test_concurrent_histogram_observe(self, an):
        h = an.Histogram("h1", capacity=10000)
        def obs():
            for v in range(100):
                h.observe(v)
        threads = [threading.Thread(target=obs) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert h.count() == 1000
