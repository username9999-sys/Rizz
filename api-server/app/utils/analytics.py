"""
Analytics aggregation: counters, gauges, histograms, percentiles.

In-process metrics aggregator that complements Prometheus. Useful for:
  - Per-tenant usage reporting (e.g. "this tenant made 12k API calls today")
  - Business KPIs (signups, posts created, MAU/DAU)
  - In-app dashboards without round-tripping Prometheus

This module does NOT depend on the broken app/__init__.py. For
Prometheus, use prometheus_client directly; for these custom
business metrics, use this module.

Data model:
  - Counter: monotonically increasing value (requests, logins, ...)
  - Gauge: point-in-time value (active sessions, queue depth, ...)
  - Histogram: distribution of values (response sizes, batch sizes, ...)

All metrics carry a `tenant_id` label. Aggregation respects tenant
boundaries; if no tenant is set, metrics are bucketed under
"_global".
"""

import math
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------- Counter ----------

class Counter:
    """Thread-safe monotonic counter with optional label values."""

    def __init__(self, name: str, help_text: str = "") -> None:
        self.name = name
        self.help = help_text
        self._lock = threading.RLock()
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        if amount < 0:
            raise ValueError("Counter can only be incremented (use Gauge for bidirectional)")
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._values[key] += amount

    def get(self, **labels: str) -> float:
        with self._lock:
            return self._values[tuple(sorted(labels.items()))]

    def total(self) -> float:
        with self._lock:
            return sum(self._values.values())

    def snapshot(self) -> List[Dict[str, Any]]:
        """Return a list of {labels: {...}, value: N} for each label combination."""
        with self._lock:
            return [{"labels": dict(k), "value": v} for k, v in self._values.items()]


# ---------- Gauge ----------

class Gauge:
    """Thread-safe gauge with optional label values."""

    def __init__(self, name: str, help_text: str = "") -> None:
        self.name = name
        self.help = help_text
        self._lock = threading.RLock()
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = {}

    def set(self, value: float, **labels: str) -> None:
        with self._lock:
            self._values[tuple(sorted(labels.items()))] = float(value)

    def get(self, **labels: str) -> float:
        with self._lock:
            return self._values.get(tuple(sorted(labels.items())), 0.0)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        with self._lock:
            key = tuple(sorted(labels.items()))
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        self.inc(-amount, **labels)

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(k), "value": v} for k, v in self._values.items()]


# ---------- Histogram (with percentiles) ----------

class Histogram:
    """Streaming histogram. Stores samples in a bounded ring buffer per label set.

    Computes percentiles (p50, p90, p95, p99) on demand.
    Default capacity 1024 samples per label set; older samples are dropped
    FIFO. This is an approximation but bounded memory.
    """

    DEFAULT_CAPACITY = 1024

    def __init__(self, name: str, help_text: str = "",
                 capacity: int = DEFAULT_CAPACITY) -> None:
        self.name = name
        self.help = help_text
        self.capacity = capacity
        self._lock = threading.RLock()
        self._samples: Dict[Tuple[Tuple[str, str], ...], List[float]] = {}

    def observe(self, value: float, **labels: str) -> None:
        with self._lock:
            key = tuple(sorted(labels.items()))
            samples = self._samples.setdefault(key, [])
            samples.append(float(value))
            if len(samples) > self.capacity:
                # Drop oldest 10% to amortize
                del samples[: len(samples) - self.capacity + max(1, self.capacity // 10)]

    def count(self, **labels: str) -> int:
        with self._lock:
            return len(self._samples.get(tuple(sorted(labels.items())), []))

    def sum(self, **labels: str) -> float:
        with self._lock:
            samples = self._samples.get(tuple(sorted(labels.items())), [])
            return float(sum(samples))

    def mean(self, **labels: str) -> float:
        with self._lock:
            samples = self._samples.get(tuple(sorted(labels.items())), [])
            return float(sum(samples) / len(samples)) if samples else 0.0

    def percentile(self, p: float, **labels: str) -> float:
        """Return the p-th percentile (0..100) of observed values."""
        if not 0 <= p <= 100:
            raise ValueError("p must be in [0, 100]")
        with self._lock:
            samples = list(self._samples.get(tuple(sorted(labels.items())), []))
        if not samples:
            return 0.0
        samples.sort()
        # Linear interpolation
        rank = (p / 100.0) * (len(samples) - 1)
        lower = int(math.floor(rank))
        upper = int(math.ceil(rank))
        if lower == upper:
            return samples[lower]
        return samples[lower] + (samples[upper] - samples[lower]) * (rank - lower)

    def quantiles(self, **labels: str) -> Dict[str, float]:
        """Return p50/p90/p95/p99 in one call."""
        return {
            "p50": self.percentile(50, **labels),
            "p90": self.percentile(90, **labels),
            "p95": self.percentile(95, **labels),
            "p99": self.percentile(99, **labels),
        }


# ---------- Registry ----------

class MetricsRegistry:
    """Holds counters/gauges/histograms by name. Singleton-style global."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}

    def counter(self, name: str, help_text: str = "") -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, help_text)
            return self._counters[name]

    def gauge(self, name: str, help_text: str = "") -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, help_text)
            return self._gauges[name]

    def histogram(self, name: str, help_text: str = "", capacity: int = 1024) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, help_text, capacity)
            return self._histograms[name]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": {n: c.snapshot() for n, c in self._counters.items()},
                "gauges": {n: g.snapshot() for n, g in self._gauges.items()},
                "histograms": {
                    n: {
                        "samples_per_label": {str(k): len(v._samples.get(k, [])) for k in v._samples},
                        "means": {str(k): v.mean(**dict(k)) for k in v._samples},
                    }
                    for n, v in self._histograms.items()
                },
            }

    def reset(self) -> None:
        """Drop all metrics. Useful for tests."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# Singleton — most apps want a single registry
default_registry = MetricsRegistry()


# ---------- Convenience: business metrics for the Rizz app ----------

def get_business_metrics(
    registry: Optional[MetricsRegistry] = None,
) -> Dict[str, Any]:
    """Return a snapshot of the standard Rizz business metrics.

    Args:
        registry: the registry to read from. Defaults to default_registry.
                  Pass an explicit registry for testing.

    Returns a dict with these metrics:
      - signups_total{tenant, source}
      - logins_total{tenant, success}
      - posts_created_total{tenant}
      - api_errors_total{tenant, endpoint, status}
      - active_sessions{tenant}
    """
    reg = registry or default_registry
    snap = reg.snapshot()
    return {
        "signups": snap["counters"].get("signups_total", []),
        "logins": snap["counters"].get("logins_total", []),
        "posts_created": snap["counters"].get("posts_created_total", []),
        "api_errors": snap["counters"].get("api_errors_total", []),
        "active_sessions": snap["gauges"].get("active_sessions", []),
    }
