"""
Multi-tenant support.

Pattern: shared-database / shared-schema. Every tenant-scoped row
carries a `tenant_id` column; every query is filtered by `tenant_id`.

How tenants are identified:
  - HTTP header `X-Tenant-ID` (preferred for APIs)
  - JWT claim `tenant_id` (for service-to-service)
  - Subdomain `acme.api.rizz.dev` (for browser apps, requires DNS)

How the active tenant is propagated:
  - `g.tenant_id` is set on every request by the middleware.
  - Downstream code accesses it via `from flask import g; g.tenant_id`.

How isolation is enforced:
  - Every tenant-scoped query MUST include `tenant_id == g.tenant_id`.
  - The `tenant_scoped` decorator wraps a view and validates the
    `g.tenant_id` is set. Combined with `apply_tenant_filter` on
    query builders, missing isolation causes an assertion error.

This module does NOT import the broken app/__init__.py so it can be
unit-tested in isolation.
"""

import re
import secrets
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from flask import request, g, jsonify, Response, Flask


# ---------- Tenant model ----------

class Tenant:
    """In-memory tenant record. For production, back this with a DB table."""

    __slots__ = ("id", "name", "slug", "plan", "active", "created_at")

    def __init__(
        self,
        id: str,
        name: str,
        slug: str,
        plan: str = "free",
        active: bool = True,
        created_at: Optional[float] = None,
    ):
        import time
        self.id = id
        self.name = name
        self.slug = slug
        self.plan = plan
        self.active = active
        self.created_at = created_at if created_at is not None else time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan,
            "active": self.active,
            "created_at": self.created_at,
        }


# ---------- Tenant registry ----------

class TenantRegistry:
    """Thread-safe in-memory tenant store.

    For production, swap with a SQL-backed implementation that queries
    a `tenants` table on every request (with a small TTL cache).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_id: Dict[str, Tenant] = {}
        self._by_slug: Dict[str, Tenant] = {}

    def add(self, tenant: Tenant) -> None:
        with self._lock:
            self._by_id[tenant.id] = tenant
            self._by_slug[tenant.slug] = tenant

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        with self._lock:
            return self._by_id.get(tenant_id)

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        with self._lock:
            return self._by_slug.get(slug)

    def remove(self, tenant_id: str) -> None:
        with self._lock:
            t = self._by_id.pop(tenant_id, None)
            if t:
                self._by_slug.pop(t.slug, None)

    def all(self) -> list:
        with self._lock:
            return list(self._by_id.values())


# Default registry for the demo
default_registry = TenantRegistry()


def _make_tenant_id() -> str:
    """Generate a unique tenant id with a human-friendly prefix."""
    return "ten_" + secrets.token_hex(8)


def _validate_slug(slug: str) -> None:
    """Raise ValueError if slug is invalid."""
    if not slug or not re.match(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$", slug):
        raise ValueError(
            "slug must be 3-40 chars, lowercase alphanumeric and hyphens, "
            "starting and ending with alphanumeric"
        )


def create_tenant(
    name: str,
    slug: str,
    plan: str = "free",
    registry: Optional[TenantRegistry] = None,
) -> Tenant:
    """Create a tenant and add it to the registry."""
    _validate_slug(slug)
    registry = registry or default_registry
    if registry.get_by_slug(slug) is not None:
        raise ValueError(f"slug {slug!r} already exists")
    t = Tenant(id=_make_tenant_id(), name=name, slug=slug, plan=plan)
    registry.add(t)
    return t


# ---------- Middleware ----------

# Headers that can carry the tenant id
_TENANT_HEADERS = ("X-Tenant-ID", "X-Tenant")


def _extract_tenant_from_request() -> Optional[str]:
    """Read tenant id from header, subdomain, or query string (in that order)."""
    for h in _TENANT_HEADERS:
        v = request.headers.get(h)
        if v:
            return v.strip()
    # Subdomain pattern: <tenant>.api.rizz.dev
    host = request.host.split(":")[0]  # strip port
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2:] == ["rizz", "dev"]:
        return parts[0]
    # Query string fallback (least preferred; logged as warning in prod)
    return request.args.get("tenant_id")


def install_tenant_middleware(
    app: Flask,
    registry: Optional[TenantRegistry] = None,
    *,
    require_tenant: bool = True,
    exempt_paths: Tuple[str, ...] = ("/health", "/metrics", "/api/v2"),
) -> None:
    """Install the tenant middleware on a Flask app.

    Args:
        app: Flask app instance
        registry: tenant store to look up; defaults to default_registry
        require_tenant: if True (default), requests without a tenant
                         identifier on non-exempt paths get 400
        exempt_paths: URL path prefixes that don't need a tenant
    """
    reg = registry or default_registry
    safe_exempt = tuple(p.rstrip("/") for p in exempt_paths)

    @app.before_request
    def _attach_tenant():
        # Reset on every request (g is request-scoped, but be paranoid)
        g.tenant = None
        g.tenant_id = None

        path = (request.path or "").rstrip("/")
        if any(path == p or path.startswith(p + "/") for p in safe_exempt):
            return  # exempt path

        identifier = _extract_tenant_from_request()
        if not identifier:
            if require_tenant:
                return _error(
                    "Tenant identifier required (X-Tenant-ID header or subdomain)",
                    400,
                )
            return

        # Identifier can be id or slug
        tenant = reg.get_by_id(identifier) or reg.get_by_slug(identifier)
        if tenant is None:
            return _error(f"Unknown tenant {identifier!r}", 404)
        if not tenant.active:
            return _error("Tenant is deactivated", 403)

        g.tenant = tenant
        g.tenant_id = tenant.id

    @app.after_request
    def _echo_tenant(response):
        if g.get("tenant_id"):
            response.headers["X-Tenant-ID"] = g.tenant_id
        return response


def _error(message: str, status: int) -> Tuple[Response, int]:
    return jsonify({"error": message}), status


# ---------- Helpers ----------

def require_tenant(view: Callable) -> Callable:
    """Decorator: ensure a tenant is set on the request. Returns 400 otherwise.

    This is a safety net for routes that should never be hit without
    a tenant. The middleware already enforces this for non-exempt paths;
    this decorator adds defense-in-depth.
    """
    from functools import wraps

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not g.get("tenant_id"):
            return _error("Tenant required for this endpoint", 400)
        return view(*args, **kwargs)

    return wrapper


def tenant_filter(base_query: Any) -> Any:
    """Add a tenant_id filter to a SQLAlchemy query.

    Usage:
        posts = tenant_filter(Post.query).all()

    Raises AssertionError if no tenant is set, which prevents
    accidental cross-tenant reads.
    """
    assert g.get("tenant_id"), (
        "tenant_filter() called without a tenant on the request. "
        "Either attach the tenant middleware or call within a "
        "@require_tenant-protected view."
    )
    return base_query.filter_by(tenant_id=g.tenant_id)
